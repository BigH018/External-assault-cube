"""ctypes wrappers around the Win32 API. The ONLY module that makes ctypes Win32 calls.

Covers: global key state, DPI awareness, finding a process's main window, window/client rects,
foreground control (including the AttachThreadInput trick) and reading an exe's file version.
Overlay window styles (WS_EX_LAYERED | WS_EX_TRANSPARENT) are added in Phase 9.
"""

from __future__ import annotations

import ctypes
import logging
from collections.abc import Iterable
from ctypes import wintypes

log = logging.getLogger(__name__)

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_shcore = None  # loaded lazily (Windows 8.1+)
_version = ctypes.WinDLL("version", use_last_error=True)

# --- prototypes (declaring argtypes/restype stops ctypes truncating 64-bit handles) ---

_user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
_user32.GetAsyncKeyState.restype = ctypes.c_short

_WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
_user32.EnumWindows.argtypes = [_WNDENUMPROC, wintypes.LPARAM]
_user32.EnumWindows.restype = wintypes.BOOL
_user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_user32.GetWindowThreadProcessId.restype = wintypes.DWORD
_user32.IsWindowVisible.argtypes = [wintypes.HWND]
_user32.IsWindowVisible.restype = wintypes.BOOL
_user32.IsWindow.argtypes = [wintypes.HWND]
_user32.IsWindow.restype = wintypes.BOOL
_user32.IsIconic.argtypes = [wintypes.HWND]
_user32.IsIconic.restype = wintypes.BOOL
_user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
_user32.GetWindow.restype = wintypes.HWND
_user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
_user32.GetWindowTextLengthW.restype = ctypes.c_int
_user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
_user32.GetClientRect.restype = wintypes.BOOL
_user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
_user32.GetWindowRect.restype = wintypes.BOOL
_user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
_user32.ClientToScreen.restype = wintypes.BOOL
_user32.GetForegroundWindow.argtypes = []
_user32.GetForegroundWindow.restype = wintypes.HWND
_user32.SetForegroundWindow.argtypes = [wintypes.HWND]
_user32.SetForegroundWindow.restype = wintypes.BOOL
_user32.BringWindowToTop.argtypes = [wintypes.HWND]
_user32.BringWindowToTop.restype = wintypes.BOOL
_user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.ShowWindow.restype = wintypes.BOOL
_user32.SetFocus.argtypes = [wintypes.HWND]
_user32.SetFocus.restype = wintypes.HWND
_user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
_user32.AttachThreadInput.restype = wintypes.BOOL
_kernel32.GetCurrentThreadId.argtypes = []
_kernel32.GetCurrentThreadId.restype = wintypes.DWORD

_kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_kernel32.OpenProcess.restype = wintypes.HANDLE
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.restype = wintypes.BOOL
_kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                 ctypes.POINTER(wintypes.DWORD)]
_kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL

_version.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
_version.GetFileVersionInfoSizeW.restype = wintypes.DWORD
_version.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
_version.GetFileVersionInfoW.restype = wintypes.BOOL
_version.VerQueryValueW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p),
                                    ctypes.POINTER(wintypes.UINT)]
_version.VerQueryValueW.restype = wintypes.BOOL

# --- constants ------------------------------------------------------------------------

_KEY_DOWN_MASK = 0x8000           # GetAsyncKeyState: high bit set while the key is held
_GW_OWNER = 4                     # GetWindow: owner window (top-level "main" windows have none)
_SW_SHOW = 5
_SW_RESTORE = 9
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_MAX_PATH_CHARS = 1024
_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)
_PROCESS_PER_MONITOR_DPI_AWARE = 2


class _VS_FIXEDFILEINFO(ctypes.Structure):
    _fields_ = [(name, wintypes.DWORD) for name in (
        "dwSignature", "dwStrucVersion", "dwFileVersionMS", "dwFileVersionLS",
        "dwProductVersionMS", "dwProductVersionLS", "dwFileFlagsMask", "dwFileFlags",
        "dwFileOS", "dwFileType", "dwFileSubtype", "dwFileDateMS", "dwFileDateLS")]


# --- keys -------------------------------------------------------------------------------

def is_key_down(vk: int) -> bool:
    """True if the key/mouse button with virtual-key code `vk` is held right now.

    Works globally, even while the game window has focus. That's why hotkeys poll this
    instead of using Qt key events.
    """
    return bool(_user32.GetAsyncKeyState(vk) & _KEY_DOWN_MASK)


def get_pressed_keys(vks: Iterable[int]) -> set[int]:
    """The subset of `vks` currently held down. Feeds the keybind engine each tick."""
    return {vk for vk in vks if is_key_down(vk)}


# --- DPI --------------------------------------------------------------------------------

def set_dpi_aware() -> bool:
    """Make this process per-monitor DPI aware. Must run BEFORE QApplication is created.

    Without it, Windows scales our windows on high-DPI displays and every overlay drawing ends up
    offset from the game. Tries the newest API first and falls back for older Windows versions.
    Returns True if any call succeeded.
    """
    global _shcore
    try:
        if _user32.SetProcessDpiAwarenessContext(_DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2):
            return True
    except AttributeError:
        pass  # Windows < 10 1703
    try:
        _shcore = ctypes.WinDLL("shcore")
        if _shcore.SetProcessDpiAwareness(_PROCESS_PER_MONITOR_DPI_AWARE) == 0:  # S_OK
            return True
    except (AttributeError, OSError):
        pass
    try:
        return bool(_user32.SetProcessDPIAware())
    except AttributeError:
        return False


# --- windows ----------------------------------------------------------------------------

def find_main_window(pid: int) -> int | None:
    """Handle of the visible, unowned, titled top-level window belonging to process `pid`."""
    found: list[int] = []

    @_WNDENUMPROC
    def callback(hwnd: int, _lparam: int) -> bool:
        owner_pid = wintypes.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner_pid))
        if (owner_pid.value == pid and _user32.IsWindowVisible(hwnd)
                and not _user32.GetWindow(hwnd, _GW_OWNER) and _user32.GetWindowTextLengthW(hwnd) > 0):
            found.append(hwnd)
            return False  # stop enumerating
        return True

    _user32.EnumWindows(callback, 0)
    return found[0] if found else None


def is_window(hwnd: int | None) -> bool:
    """True if `hwnd` still refers to an existing window."""
    return bool(hwnd) and bool(_user32.IsWindow(hwnd))


def is_minimized(hwnd: int) -> bool:
    return bool(_user32.IsIconic(hwnd))


def get_client_rect_on_screen(hwnd: int) -> tuple[int, int, int, int] | None:
    """(x, y, width, height) of the window's CLIENT area (the drawable part, no frame) in screen pixels."""
    rect = wintypes.RECT()
    if not _user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None
    origin = wintypes.POINT(0, 0)
    if not _user32.ClientToScreen(hwnd, ctypes.byref(origin)):  # client (0,0) -> screen coordinates
        return None
    return origin.x, origin.y, rect.right - rect.left, rect.bottom - rect.top


def get_window_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    """(x, y, width, height) of the whole window including its frame, in screen pixels."""
    rect = wintypes.RECT()
    if not _user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


def get_foreground_window() -> int | None:
    return _user32.GetForegroundWindow() or None


def force_foreground(hwnd: int) -> bool:
    """Bring `hwnd` to the foreground with keyboard focus, even when another app is focused.

    Windows' "foreground lock" normally stops a background process from stealing focus. The usual
    workaround: temporarily attach our thread's input queue to the current foreground thread.
    Windows then treats us as part of that thread and allows SetForegroundWindow.
    When AssaultCube loses focus it should release its mouse grab, so the menu becomes clickable.
    Returns True if `hwnd` ended up in the foreground.
    """
    foreground = _user32.GetForegroundWindow()
    if foreground == hwnd:
        return True
    our_thread = _kernel32.GetCurrentThreadId()
    fg_thread = _user32.GetWindowThreadProcessId(foreground, None) if foreground else 0
    attached = bool(fg_thread and fg_thread != our_thread and _user32.AttachThreadInput(our_thread, fg_thread, True))
    try:
        _user32.ShowWindow(hwnd, _SW_RESTORE if _user32.IsIconic(hwnd) else _SW_SHOW)
        _user32.BringWindowToTop(hwnd)
        _user32.SetForegroundWindow(hwnd)
        _user32.SetFocus(hwnd)
    finally:
        if attached:
            _user32.AttachThreadInput(our_thread, fg_thread, False)
    ok = _user32.GetForegroundWindow() == hwnd
    if not ok:
        log.debug("force_foreground(0x%X) did not take effect", hwnd)
    return ok


# --- process info -------------------------------------------------------------------------

def get_process_image_path(pid: int) -> str | None:
    """Full path of the process's executable, or None if it can't be queried."""
    handle = _kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        size = wintypes.DWORD(_MAX_PATH_CHARS)
        buf = ctypes.create_unicode_buffer(_MAX_PATH_CHARS)
        if not _kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return None
        return buf.value
    finally:
        _kernel32.CloseHandle(handle)


def get_file_version(path: str) -> str | None:
    """File version of an exe/dll as "a.b.c.d", or None if it has no version resource."""
    size = _version.GetFileVersionInfoSizeW(path, None)
    if not size:
        return None
    data = ctypes.create_string_buffer(size)
    if not _version.GetFileVersionInfoW(path, 0, size, data):
        return None
    ptr = ctypes.c_void_p()
    length = wintypes.UINT()
    if not _version.VerQueryValueW(data, "\\", ctypes.byref(ptr), ctypes.byref(length)) or not ptr.value:
        return None
    info = ctypes.cast(ptr, ctypes.POINTER(_VS_FIXEDFILEINFO)).contents
    # Each DWORD holds two 16-bit parts: MS = major.minor, LS = build.revision.
    return (f"{info.dwFileVersionMS >> 16}.{info.dwFileVersionMS & 0xFFFF}."
            f"{info.dwFileVersionLS >> 16}.{info.dwFileVersionLS & 0xFFFF}")
