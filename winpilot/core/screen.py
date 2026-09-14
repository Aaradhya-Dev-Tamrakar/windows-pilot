"""
Screen Capture & Recording Module: Silent window & desktop screenshot capture with video recording.
Direct, popup-free screen capture with verbose state reporting.
"""

from __future__ import annotations

import base64
import ctypes
import io
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from PIL import Image, ImageGrab

from winpilot.core.window import Window, attach_default_desktop

if sys.platform == "win32":
    import winreg


@dataclass
class CaptureMetadata:
    """Metadata detailing a screenshot or recording target and its properties."""

    target_type: Literal["desktop", "window"]
    target_name: str
    hwnd: int | None
    pid: int | None
    process_name: str | None
    bounds: tuple[int, int, int, int]
    dimensions: tuple[int, int]
    engine: str
    timestamp: str
    file_path: Path | None = None


def _get_virtual_screen_bounds() -> tuple[int, int, int, int]:
    """Retrieve virtual desktop bounds covering all displays (left, top, right, bottom)."""
    if sys.platform != "win32":
        return (0, 0, 1920, 1080)
    user32 = ctypes.windll.user32
    vx = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
    vy = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
    vw = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
    vh = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
    if vw == 0 or vh == 0:
        vx, vy = 0, 0
        vw = user32.GetSystemMetrics(0)
        vh = user32.GetSystemMetrics(1)
    return (vx, vy, vx + vw, vy + vh)


def _capture_gdi_rect(rect: tuple[int, int, int, int]) -> Image.Image | None:
    """
    Directly capture a screen rectangle using Win32 GDI BitBlt.
    100% silent, zero-popup, headless/interactive compatible.
    """
    if sys.platform != "win32":
        return None

    left, top, right, bottom = rect
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        return None

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    hdesktop = user32.GetDesktopWindow()
    desktop_dc = user32.GetWindowDC(hdesktop)
    mem_dc = gdi32.CreateCompatibleDC(desktop_dc)
    hbitmap = gdi32.CreateCompatibleBitmap(desktop_dc, width, height)
    old_bitmap = gdi32.SelectObject(mem_dc, hbitmap)

    # SRCCOPY (0x00CC0020) | CAPTUREBLT (0x40000000) for layered/translucent windows
    rop = 0x00CC0020 | 0x40000000
    try:
        gdi32.BitBlt(mem_dc, 0, 0, width, height, desktop_dc, left, top, rop)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD),
                ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD),
            ]

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = width
        bmi.biHeight = -height  # top-down DIB
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        buffer = ctypes.create_string_buffer(width * height * 4)
        lines = gdi32.GetDIBits(mem_dc, hbitmap, 0, height, buffer, ctypes.byref(bmi), 0)
        if lines > 0:
            return Image.frombuffer("RGB", (width, height), buffer, "raw", "BGRX", 0, 1)
        return None
    finally:
        # Mandatory Win32 cleanup
        gdi32.SelectObject(mem_dc, old_bitmap)
        gdi32.DeleteObject(hbitmap)
        gdi32.DeleteDC(mem_dc)
        user32.ReleaseDC(hdesktop, desktop_dc)


def _capture_print_window(hwnd: int) -> Image.Image | None:
    """Capture a specific window using PrintWindow (useful for occluded windows)."""
    if sys.platform != "win32" or not hwnd:
        return None

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    if width <= 0 or height <= 0:
        return None

    hdc_win = user32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_win)
    hbitmap = gdi32.CreateCompatibleBitmap(hdc_win, width, height)
    old_bm = gdi32.SelectObject(hdc_mem, hbitmap)

    try:
        # PW_RENDERFULLCONTENT = 2
        ok = user32.PrintWindow(hwnd, hdc_mem, 2)
        if not ok:
            # Fallback PW_DEFAULT = 0
            ok = user32.PrintWindow(hwnd, hdc_mem, 0)
        if not ok:
            return None

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD),
                ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD),
            ]

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = width
        bmi.biHeight = -height
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        buffer = ctypes.create_string_buffer(width * height * 4)
        lines = gdi32.GetDIBits(hdc_mem, hbitmap, 0, height, buffer, ctypes.byref(bmi), 0)
        if lines > 0:
            return Image.frombuffer("RGB", (width, height), buffer, "raw", "BGRX", 0, 1)
        return None
    finally:
        gdi32.SelectObject(hdc_mem, old_bm)
        gdi32.DeleteObject(hbitmap)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(hwnd, hdc_win)


class Screen:
    """Provides silent screenshot and visual capture utilities with metadata."""

    @staticmethod
    def get_default_screenshots_dir() -> Path:
        """
        Locates the standard Windows Screenshots folder (analogous to Win+PrtScn).
        Checks Windows Shell Folders in registry, OneDrive redirection, or ~/Pictures/Screenshots.
        """
        if sys.platform == "win32":
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
                ) as key:
                    # Check known folder GUID for Screenshots or My Pictures
                    for guid in (
                        "{B7BEDE81-DF94-4782-A1A4-47730846E97E}",
                        "{B7BEDE81-DF94-4682-A7D8-57A52620B86F}",
                        "My Pictures",
                    ):
                        try:
                            val, _ = winreg.QueryValueEx(key, guid)
                            expanded = Path(os.path.expandvars(val))
                            if guid == "My Pictures":
                                expanded = expanded / "Screenshots"
                            expanded.mkdir(parents=True, exist_ok=True)
                            return expanded
                        except FileNotFoundError:
                            continue
            except Exception:
                pass

        # Fallback to user home
        fallback = Path.home() / "Pictures" / "Screenshots"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback

    @staticmethod
    def capture_desktop(
        bbox: tuple[int, int, int, int] | None = None,
    ) -> tuple[Image.Image | None, CaptureMetadata]:
        """
        Capture the full virtual desktop or a specific bounding box silently.
        Uses native Win32 GDI BitBlt first; falls back to PIL.ImageGrab.
        """
        attach_default_desktop()
        effective_bbox = bbox or _get_virtual_screen_bounds()
        engine = "Win32 GDI BitBlt"

        img = _capture_gdi_rect(effective_bbox)
        if img is None:
            engine = "Pillow ImageGrab Fallback"
            try:
                img = ImageGrab.grab(bbox=effective_bbox, all_screens=True)
            except Exception:
                img = None

        width = (effective_bbox[2] - effective_bbox[0]) if img else 0
        height = (effective_bbox[3] - effective_bbox[1]) if img else 0
        if img:
            width, height = img.size

        meta = CaptureMetadata(
            target_type="desktop",
            target_name="Full Desktop (All Screens)" if not bbox else f"Region {bbox}",
            hwnd=None,
            pid=None,
            process_name=None,
            bounds=effective_bbox,
            dimensions=(width, height),
            engine=engine,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        return img, meta

    @staticmethod
    def capture_window(
        window_or_hwnd: Window | int,
    ) -> tuple[Image.Image | None, CaptureMetadata]:
        """
        Capture the visual rectangle of a specific window silently without any popup.
        """
        attach_default_desktop()
        w = window_or_hwnd if isinstance(window_or_hwnd, Window) else Window(window_or_hwnd)
        if not w.is_valid:
            meta = CaptureMetadata(
                target_type="window",
                target_name=f"Invalid HWND {window_or_hwnd}",
                hwnd=int(window_or_hwnd) if isinstance(window_or_hwnd, int) else w.hwnd,
                pid=None,
                process_name=None,
                bounds=(0, 0, 0, 0),
                dimensions=(0, 0),
                engine="None (Invalid Window)",
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            return None, meta

        rect = w.rect
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]

        # 1. First attempt: Direct GDI screen crop from window rect
        engine = "Win32 GDI BitBlt"
        img = _capture_gdi_rect(rect)

        # 2. Second attempt: PrintWindow (for occluded or offscreen window contents)
        if img is None:
            engine = "Win32 PrintWindow"
            img = _capture_print_window(w.hwnd)

        # 3. Third attempt: ImageGrab fallback
        if img is None:
            engine = "Pillow ImageGrab Fallback"
            try:
                img = ImageGrab.grab(bbox=rect, all_screens=True)
            except Exception:
                img = None

        actual_dims = img.size if img else (max(0, width), max(0, height))

        meta = CaptureMetadata(
            target_type="window",
            target_name=w.title or f"Window (HWND: {w.hwnd})",
            hwnd=w.hwnd,
            pid=w.pid,
            process_name=w.process_name,
            bounds=rect,
            dimensions=actual_dims,
            engine=engine,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        return img, meta

    @staticmethod
    def save(
        image: Image.Image,
        dest_path: str | Path,
        format: str = "PNG",
    ) -> Path:
        """Save a PIL Image to disk."""
        p = Path(dest_path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        image.save(str(p), format=format)
        return p

    @staticmethod
    def capture_to_file(
        window_or_hwnd: Window | int | None = None,
        dest_path: str | Path | None = None,
    ) -> tuple[Path | None, CaptureMetadata]:
        """
        Captures a silent screenshot directly to a file (Win+PrtScn style).
        Defaults to the Windows Screenshots directory with timestamped filename.
        """
        if window_or_hwnd:
            img, meta = Screen.capture_window(window_or_hwnd)
        else:
            img, meta = Screen.capture_desktop()

        if img is None:
            return None, meta

        if dest_path:
            out_file = Path(dest_path).resolve()
        else:
            ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            prefix = "Screenshot"
            if meta.process_name:
                clean_proc = Path(meta.process_name).stem
                prefix = f"Screenshot_{clean_proc}"
            out_file = Screen.get_default_screenshots_dir() / f"{prefix}_{ts}.png"

        saved = Screen.save(img, out_file)
        meta.file_path = saved
        return saved, meta

    @staticmethod
    def to_base64(image: Image.Image, format: str = "PNG") -> str:
        """Convert a PIL Image to a base64 encoded string (for MCP vision tools)."""
        buffered = io.BytesIO()
        image.save(buffered, format=format)
        return base64.b64encode(buffered.getvalue()).decode("utf-8")


class ScreenRecorder:
    """
    Background screen & window video recorder with real-time telemetry.
    Supports capturing full desktop or tracking a specific target window HWND.
    Exports to MP4 (via ffmpeg) or high-quality animated GIF (via Pillow).
    """

    def __init__(
        self,
        target_window: Window | int | None = None,
        fps: int = 15,
        on_status_change: Callable[[str], None] | None = None,
        on_frame: Callable[[int, float], None] | None = None,
    ):
        self.target_window = (
            target_window if isinstance(target_window, Window)
            else Window(target_window) if target_window
            else None
        )
        self.fps = max(1, min(fps, 60))
        self.on_status_change = on_status_change
        self.on_frame = on_frame

        self._frames: list[Image.Image] = []
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._start_time: float = 0.0
        self._end_time: float = 0.0
        self._lock = threading.Lock()

    @property
    def is_recording(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def frame_count(self) -> int:
        with self._lock:
            return len(self._frames)

    @property
    def elapsed_seconds(self) -> float:
        if not self._start_time:
            return 0.0
        end = self._end_time if self._end_time else time.time()
        return max(0.0, end - self._start_time)

    @property
    def current_fps(self) -> float:
        el = self.elapsed_seconds
        fc = self.frame_count
        return (fc / el) if el > 0.5 else float(self.fps)

    def start(self) -> None:
        """Start background frame capture loop."""
        if self.is_recording:
            return

        self._frames.clear()
        self._stop_event.clear()
        self._start_time = time.time()
        self._end_time = 0.0

        if self.on_status_change:
            self.on_status_change("started")

        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _capture_loop(self) -> None:
        frame_interval = 1.0 / self.fps
        while not self._stop_event.is_set():
            t0 = time.perf_counter()

            if self.target_window:
                img, _ = Screen.capture_window(self.target_window)
            else:
                img, _ = Screen.capture_desktop()

            if img is not None:
                with self._lock:
                    self._frames.append(img)
                    count = len(self._frames)

                if self.on_frame:
                    self.on_frame(count, self.elapsed_seconds)

            delta = time.perf_counter() - t0
            sleep_time = max(0.0, frame_interval - delta)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def stop(self) -> int:
        """Stop recording and return captured frame count."""
        if not self.is_recording:
            return len(self._frames)

        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
        self._end_time = time.time()

        if self.on_status_change:
            self.on_status_change("stopped")

        return len(self._frames)

    def save(self, dest_path: str | Path, format: str | None = None) -> Path:
        """
        Save captured frames to MP4 or GIF.
        Auto-detects format from file extension if format is None.
        """
        dest = Path(dest_path).resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)
        fmt = (format or dest.suffix.lstrip(".").lower() or "mp4").lower()

        with self._lock:
            if not self._frames:
                raise RuntimeError("No frames captured during recording.")
            frames_copy = list(self._frames)

        effective_fps = self.fps

        # Format 1: MP4 via ffmpeg
        if fmt in ("mp4", "webm", "mkv", "avi") and shutil.which("ffmpeg"):
            temp_dir = tempfile.mkdtemp(prefix="winpilot_rec_")
            try:
                first_frame = frames_copy[0]
                w, h = first_frame.size
                if w % 2 != 0:
                    w -= 1
                if h % 2 != 0:
                    h -= 1

                for idx, frame in enumerate(frames_copy):
                    resized = frame.crop((0, 0, w, h)) if frame.size != (w, h) else frame
                    resized.save(os.path.join(temp_dir, f"frame_{idx:05d}.png"))

                input_pattern = os.path.join(temp_dir, "frame_%05d.png")
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-framerate",
                    str(effective_fps),
                    "-i",
                    input_pattern,
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-crf",
                    "23",
                    str(dest),
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if res.returncode == 0 and dest.exists():
                    return dest
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        # Format 2: High-Quality Animated GIF (Pure Pillow fallback)
        gif_dest = dest if dest.suffix.lower() == ".gif" else dest.with_suffix(".gif")
        frame_dur_ms = int(1000 / effective_fps)
        frames_copy[0].save(
            str(gif_dest),
            format="GIF",
            save_all=True,
            append_images=frames_copy[1:],
            duration=frame_dur_ms,
            loop=0,
            optimize=True,
        )
        return gif_dest

