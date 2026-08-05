"""Windows 真模糊（Acrylic / 云母）封装。

优先 Win11：DwmSetWindowAttribute(DWMWA_SYSTEMBACKDROP_TYPE=38, DWMSBT_TRANSIENTWINDOW=3)
+ DWMWA_USE_IMMERSIVE_DARK_MODE=20；
其次 Win10：SetWindowCompositionAttribute(ACCENT_ENABLE_ACRYLICBLURBEHIND)。
任何失败静默返回 False，由界面层维持假玻璃（半透明渐变 + 高光）。
只依赖 ctypes / winreg，不写 C 盘。
"""
from __future__ import annotations

import ctypes
import winreg
from ctypes import wintypes

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMSBT_TRANSIENTWINDOW = 3

WCA_ACCENT_POLICY = 19
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4

_WIN11_BACKDROP_BUILD = 22621


class _ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_uint),
        ("AccentFlags", ctypes.c_uint),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_uint),
    ]


class _WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.c_void_p),
        ("SizeOfData", ctypes.c_size_t),
    ]


def _win_build() -> int:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as k:
            return int(winreg.QueryValueEx(k, "CurrentBuildNumber")[0])
    except Exception:
        return 0


def _apply_win11(hwnd: int) -> bool:
    try:
        dwm = ctypes.windll.dwmapi
        backdrop = ctypes.c_int(DWMSBT_TRANSIENTWINDOW)
        dark = ctypes.c_int(1)
        r1 = dwm.DwmSetWindowAttribute(
            wintypes.HWND(hwnd), DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(backdrop), ctypes.sizeof(backdrop))
        dwm.DwmSetWindowAttribute(
            wintypes.HWND(hwnd), DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(dark), ctypes.sizeof(dark))
        return r1 == 0
    except Exception:
        return False


def _apply_win10(hwnd: int) -> bool:
    try:
        user32 = ctypes.windll.user32
        policy = _ACCENT_POLICY()
        policy.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
        policy.AccentFlags = 2
        # GradientColor 为 ABGR：alpha 160 + 深蓝 (10,16,42)
        policy.GradientColor = (160 << 24) | (42 << 16) | (16 << 8) | 10
        data = _WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = WCA_ACCENT_POLICY
        data.Data = ctypes.cast(ctypes.pointer(policy), ctypes.c_void_p)
        data.SizeOfData = ctypes.sizeof(policy)
        return bool(user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data)))
    except Exception:
        return False


def apply_real_blur(hwnd: int) -> bool:
    if not hwnd:
        return False
    try:
        build = _win_build()
        if build >= _WIN11_BACKDROP_BUILD:
            if _apply_win11(hwnd):
                return True
        return _apply_win10(hwnd)
    except Exception:
        return False