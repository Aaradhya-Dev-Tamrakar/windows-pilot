"""
Input Simulation Module: Hardware-level keyboard, mouse, and clipboard automation for Windows.
"""

from __future__ import annotations

import ctypes
import sys
import time

from winpilot.core.window import attach_default_desktop

if sys.platform == "win32":
    import win32api
    import win32clipboard

# Keycode mapping table for common key names
VK_MAP = {
    "enter": 0x0D,
    "return": 0x0D,
    "tab": 0x09,
    "esc": 0x1B,
    "escape": 0x1B,
    "space": 0x20,
    "backspace": 0x08,
    "delete": 0x2E,
    "del": 0x2E,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "ctrl": 0x11,
    "control": 0x11,
    "shift": 0x10,
    "alt": 0x12,
    "win": 0x5B,
    "f1": 0x70,
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
}


class Input:
    """Hardware input and clipboard controller."""

    @staticmethod
    def set_clipboard(text: str, retries: int = 5) -> bool:
        """Copies Unicode text to the Windows clipboard safely."""
        attach_default_desktop()
        for _ in range(retries):
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
                return True
            except Exception:
                time.sleep(0.05)
        return False

    @staticmethod
    def get_clipboard() -> str:
        """Reads text from the Windows clipboard."""
        attach_default_desktop()
        try:
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            else:
                data = ""
            win32clipboard.CloseClipboard()
            return str(data)
        except Exception:
            return ""

    @staticmethod
    def paste_text(text: str, submit_enter: bool = False, delay_before_enter: float = 0.25) -> bool:
        """Copies text to clipboard, performs Ctrl+V keystroke, and optionally presses Enter."""
        if not Input.set_clipboard(text):
            return False
        time.sleep(0.05)
        Input.send_combo("ctrl", "v")
        if submit_enter:
            time.sleep(delay_before_enter)
            Input.press("enter")
        return True

    @staticmethod
    def send_combo(*keys: str, hold_delay: float = 0.05) -> None:
        """
        Press and release a combination of keys (e.g. ('ctrl', 'shift', 'n') or ('ctrl', 'v')).
        """
        attach_default_desktop()
        user32 = ctypes.windll.user32
        vk_codes = []
        for k in keys:
            k_lower = k.lower().strip()
            if k_lower in VK_MAP:
                vk_codes.append(VK_MAP[k_lower])
            elif len(k_lower) == 1:
                vk_codes.append(ord(k_lower.upper()))
            else:
                pass

        KEYEVENTF_KEYUP = 0x0002
        # Press down in order
        for vk in vk_codes:
            user32.keybd_event(vk, 0, 0, 0)
        time.sleep(hold_delay)
        # Release in reverse order
        for vk in reversed(vk_codes):
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

    @staticmethod
    def press(key_name: str, count: int = 1, delay: float = 0.05) -> None:
        """Press and release a single key by name."""
        attach_default_desktop()
        user32 = ctypes.windll.user32
        k_lower = key_name.lower().strip()
        vk = VK_MAP.get(k_lower, ord(k_lower[0].upper()) if len(k_lower) == 1 else 0)
        if not vk:
            return

        KEYEVENTF_KEYUP = 0x0002
        for _ in range(count):
            user32.keybd_event(vk, 0, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
            if delay:
                time.sleep(delay)

    @staticmethod
    def type_text(text: str, delay: float = 0.01) -> None:
        """Type characters sequentially using Windows SendInput Unicode events."""
        attach_default_desktop()
        user32 = ctypes.windll.user32
        KEYEVENTF_UNICODE = 0x0004
        KEYEVENTF_KEYUP = 0x0002

        for ch in text:
            code = ord(ch)
            user32.keybd_event(0, code, KEYEVENTF_UNICODE, 0)
            time.sleep(0.005)
            user32.keybd_event(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0)
            if delay:
                time.sleep(delay)

    @staticmethod
    def click(x: int, y: int, count: int = 1, button: str = "left", delay: float = 0.05) -> None:
        """Simulate hardware mouse clicks at (x, y) coordinates."""
        attach_default_desktop()
        user32 = ctypes.windll.user32
        user32.SetCursorPos(int(x), int(y))
        time.sleep(0.02)

        if button.lower() == "right":
            down_flag, up_flag = 0x0008, 0x0010  # RIGHTDOWN, RIGHTUP
        elif button.lower() == "middle":
            down_flag, up_flag = 0x0020, 0x0040  # MIDDLEDOWN, MIDDLEUP
        else:
            down_flag, up_flag = 0x0002, 0x0004  # LEFTDOWN, LEFTUP

        for _ in range(count):
            user32.mouse_event(down_flag, 0, 0, 0, 0)
            time.sleep(0.03)
            user32.mouse_event(up_flag, 0, 0, 0, 0)
            if delay:
                time.sleep(delay)

    @staticmethod
    def double_click(x: int, y: int) -> None:
        Input.click(x, y, count=2, delay=0.08)

    @staticmethod
    def right_click(x: int, y: int) -> None:
        Input.click(x, y, button="right")

    @staticmethod
    def get_cursor_pos() -> tuple[int, int]:
        attach_default_desktop()
        pt = win32api.GetCursorPos()
        return (pt[0], pt[1])
