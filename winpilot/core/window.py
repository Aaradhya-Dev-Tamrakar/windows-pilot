"""
Window Management Module: HWND encapsulation, discovery, foreground unlocking, and window positioning.
"""

from __future__ import annotations

import ctypes
import os
import re
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

if sys.platform == "win32":
    import win32con
    import win32gui
    import win32process


def attach_default_desktop() -> bool:
    """Attach current thread to the interactive Default desktop of WinSta0."""
    if sys.platform != "win32":
        return False
    try:
        user32 = ctypes.windll.user32
        user32.OpenDesktopW.restype = ctypes.c_void_p
        user32.OpenDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        user32.SetThreadDesktop.restype = wintypes.BOOL
        user32.SetThreadDesktop.argtypes = [ctypes.c_void_p]

        h_def = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if h_def:
            return bool(user32.SetThreadDesktop(h_def))
    except Exception:
        pass
    return False


class Window:
    """Represents a Windows top-level or child window identified by HWND."""

    def __init__(self, hwnd: int):
        self.hwnd = int(hwnd)

    def __repr__(self) -> str:
        return f"<Window hwnd={self.hwnd} title={self.title!r} pid={self.pid}>"

    @property
    def is_valid(self) -> bool:
        if sys.platform != "win32" or not self.hwnd:
            return False
        return bool(win32gui.IsWindow(self.hwnd))

    @property
    def title(self) -> str:
        if not self.is_valid:
            return ""
        return win32gui.GetWindowText(self.hwnd)

    @property
    def class_name(self) -> str:
        if not self.is_valid:
            return ""
        return win32gui.GetClassName(self.hwnd)

    @property
    def pid(self) -> int:
        if not self.is_valid:
            return 0
        _, pid = win32process.GetWindowThreadProcessId(self.hwnd)
        return pid

    @property
    def process_name(self) -> str:
        pid = self.pid
        if not pid:
            return ""
        try:
            import win32api
            h_proc = win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if h_proc:
                try:
                    import win32process
                    exe = win32process.GetModuleFileNameEx(h_proc, 0)
                    return Path(exe).name
                finally:
                    win32api.CloseHandle(h_proc)
        except Exception:
            pass
        return ""

    @property
    def is_visible(self) -> bool:
        if not self.is_valid:
            return False
        return bool(win32gui.IsWindowVisible(self.hwnd))

    @property
    def is_minimized(self) -> bool:
        if not self.is_valid:
            return False
        return bool(win32gui.IsIconic(self.hwnd))

    @property
    def is_cloaked(self) -> bool:
        """Returns True if the window is cloaked by DWM (e.g., hidden on an inactive virtual desktop)."""
        if not self.is_valid:
            return False
        try:
            DWMWA_CLOAKED = 14
            cloaked = ctypes.c_uint()
            res = ctypes.windll.dwmapi.DwmGetWindowAttribute(
                ctypes.c_void_p(self.hwnd),
                ctypes.c_uint(DWMWA_CLOAKED),
                ctypes.byref(cloaked),
                ctypes.sizeof(cloaked),
            )
            return res == 0 and cloaked.value != 0
        except Exception:
            return False

    @property
    def rect(self) -> tuple[int, int, int, int]:
        """Returns (left, top, right, bottom) coordinates."""
        if not self.is_valid:
            return (0, 0, 0, 0)
        return win32gui.GetWindowRect(self.hwnd)

    @property
    def width(self) -> int:
        l, _, r, _ = self.rect
        return r - l

    @property
    def height(self) -> int:
        _, t, _, b = self.rect
        return b - t

    def focus(self, ensure_uncloaked: bool = True) -> bool:
        """
        Brings window to foreground using Win32 unlock sequences:
        1. Checks DWM cloaking & attempts virtual desktop switch if cloaked.
        2. Unlocks Windows foreground permission (AllowSetForegroundWindow + VK_MENU tap).
        3. Attaches thread input queue to sync foreground privileges.
        4. Restores and brings window to front.
        """
        if not self.is_valid:
            return False
        attach_default_desktop()

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        # 1. Check if window is cloaked on another virtual desktop
        if ensure_uncloaked and self.is_cloaked:
            self._switch_to_window_desktop()

        try:
            if self.is_minimized:
                win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)

            # 2. Reset foreground lock
            user32.AllowSetForegroundWindow(-1)
            VK_MENU = 0x12
            KEYEVENTF_KEYUP = 0x0002
            user32.keybd_event(VK_MENU, 0, 0, 0)
            time.sleep(0.01)
            user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)

            # 3. Thread input attachment
            curr_thread = kernel32.GetCurrentThreadId()
            target_thread, _ = win32process.GetWindowThreadProcessId(self.hwnd)
            if curr_thread != target_thread:
                user32.AttachThreadInput(curr_thread, target_thread, True)

            user32.ShowWindow(self.hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(self.hwnd)
            try:
                user32.SwitchToThisWindow(self.hwnd, True)
            except Exception:
                pass
            user32.BringWindowToTop(self.hwnd)

            if curr_thread != target_thread:
                user32.AttachThreadInput(curr_thread, target_thread, False)

            time.sleep(0.05)
            return True
        except Exception:
            return False

    def _switch_to_window_desktop(self) -> bool:
        """Attempt to switch to the virtual desktop containing this window."""
        # Check standard VirtualDesktop.exe paths
        possible_vd = [
            Path(__file__).resolve().parent.parent.parent / "tools" / "VirtualDesktop.exe",
            Path(os.environ.get("VIRTUAL_DESKTOP_EXE", "")),
        ]
        for vd_exe in possible_vd:
            if vd_exe.exists():
                try:
                    res = subprocess.run(
                        [str(vd_exe), f"/GetDesktopFromWindowHandle:{self.hwnd}"],
                        capture_output=True,
                        text=True,
                        timeout=2.0,
                    )
                    m = re.search(r"desktop number (\d+)", res.stdout, re.IGNORECASE)
                    if m:
                        subprocess.run([str(vd_exe), f"/Switch:{m.group(1)}"], capture_output=True, timeout=2.0)
                        time.sleep(0.2)
                        return True
                except Exception:
                    pass
        return False

    def move(self, x: int, y: int, width: int, height: int, restore: bool = True) -> bool:
        """Move and resize window."""
        if not self.is_valid:
            return False
        attach_default_desktop()
        if restore and self.is_minimized:
            win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
        return bool(
            win32gui.SetWindowPos(
                self.hwnd,
                0,
                x,
                y,
                width,
                height,
                win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW,
            )
        )

    def minimize(self) -> bool:
        if not self.is_valid:
            return False
        return bool(win32gui.ShowWindow(self.hwnd, win32con.SW_MINIMIZE))

    def maximize(self) -> bool:
        if not self.is_valid:
            return False
        return bool(win32gui.ShowWindow(self.hwnd, win32con.SW_MAXIMIZE))

    def restore(self) -> bool:
        if not self.is_valid:
            return False
        return bool(win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE))

    def close(self) -> bool:
        if not self.is_valid:
            return False
        return bool(win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0))


def list_windows(
    title_regex: str | None = None,
    process_name: str | None = None,
    visible_only: bool = True,
) -> list[Window]:
    """Enumerate desktop windows matching title or process filters."""
    if sys.platform != "win32":
        return []

    result: list[Window] = []
    pattern = re.compile(title_regex, re.IGNORECASE) if title_regex else None

    def _process_hwnd(hwnd: int) -> None:
        try:
            w = Window(hwnd)
            if visible_only and not w.is_visible:
                return
            t = w.title
            if visible_only and not t.strip():
                return
            if pattern and not pattern.search(t):
                return
            if process_name and process_name.lower() not in w.process_name.lower():
                return
            result.append(w)
        except Exception:
            pass

    # 1. Try EnumDesktopWindows on WinSta0\Default
    try:
        user32 = ctypes.windll.user32
        user32.OpenDesktopW.restype = ctypes.c_void_p
        user32.OpenDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]

        h_def = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if h_def:
            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

            def _desktop_cb(hwnd: int, _: int) -> bool:
                _process_hwnd(hwnd)
                return True

            cb_func = WNDENUMPROC(_desktop_cb)
            user32.EnumDesktopWindows(ctypes.c_void_p(h_def), cb_func, 0)
            if result:
                return result
    except Exception:
        pass

    # 2. Fallback to standard EnumWindows
    def enum_cb(hwnd: int, _):
        _process_hwnd(hwnd)
        return True

    try:
        win32gui.EnumWindows(enum_cb, 0)
    except Exception:
        pass

    return result


def find_window(
    title_regex: str | None = None,
    process_name: str | None = None,
    hwnd: int | None = None,
) -> Window | None:
    """Find a single window matching criteria."""
    if hwnd:
        w = Window(hwnd)
        return w if w.is_valid else None

    wins = list_windows(title_regex=title_regex, process_name=process_name, visible_only=True)
    return wins[0] if wins else None
