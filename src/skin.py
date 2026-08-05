"""皮肤常量：DeepSeek 表盘风配色集中地，换肤只改本文件。"""
from __future__ import annotations

# ---------- 真模糊（禁用） ----------
REAL_BLUR_ENABLED = False

# ---------- 背景 ----------
BG_ALPHA = 51                       # 20% 黑色底盘
BG_RADIUS = 16
BG_GRAD_TOP = "#080808"
BG_GRAD_BOTTOM = "#0D0D0D"
VIGNETTE = "rgba(0,0,0,0.55)"

# ---------- 压边 ----------
BEZEL_OUTER = "#0A0A0A"
BEZEL_MAIN = "#1C1C1C"
BEZEL_BRIGHT = "#2A2A2A"
BEZEL_HIGHLIGHT = "rgba(255,255,255,0.07)"

# ---------- 刻度 / 内圈 ----------
TICK_MAJOR = "#4A4A4A"
TICK_MID = "#2E2E2E"
TICK_MINOR = "#1E1E1E"
INNER_RING = "#242424"

# ---------- 油量环 ----------
TRACK = "#151515"
GAP = "#080808"
LIT = "#F4F4F0"

# ---------- 文字 ----------
TEXT_STRONG = "#FFFFFF"
TEXT_MAIN = "#F4F4F0"
TEXT_LABEL = "#D4D4CE"
TEXT_MID = "#A1A19A"
TEXT_WEAK2 = "#B2B2AC"
TEXT_WEAK = "#7A7A74"

# ---------- 状态色 ----------
STATUS_BLUE = "#4EA3FF"
STATUS_RED = "#FF3B30"
STATUS_GREEN = "#00D084"

# ---------- 顶栏 ----------
TOPBAR_BG = "#0E0E0E"
BORDER_STRONG = "rgba(255,255,255,0.35)"
BORDER_MED = "rgba(255,255,255,0.18)"
BORDER_WEAK = "rgba(255,255,255,0.08)"
PRESS_BG = "#151515"

# ---------- 点阵 ----------
DOT_LIT = "#FFFFFF"
DOT_OFF = "rgba(255,255,255,0.10)"

# ---------- 设置面板 ----------
DIALOG_BG = TOPBAR_BG
INPUT_BG = TRACK
BTN_BG = TRACK
BTN_HOVER = BEZEL_MAIN