"""皮肤常量：颜色 / 透明度 / 开关集中在这里，换肤只改本文件。"""
from __future__ import annotations

# ---------- 背景（高透明深色渐变） ----------
BG_ALPHA = 160                      # 背景整体不透明度（150–170，可读性优先可调高）
BG_TOP = (10, 16, 42)               # 渐变上部：近黑深蓝
BG_BOTTOM = (28, 40, 78)            # 渐变下部：略浅
BG_RADIUS = 16                      # 圆角半径 px（×缩放）

# ---------- 玻璃效果 ----------
REAL_BLUR_ENABLED = True            # 真模糊总开关（失败自动回退假玻璃）
GLASS_HIGHLIGHT_ENABLED = True      # 顶部高光细线（玻璃反光）
GLASS_HIGHLIGHT_ALPHA = 90
GLASS_HIGHLIGHT_HEIGHT = 2          # px（×缩放）

# ---------- 霓虹描边 ----------
NEON_CYAN = "#00E5FF"
NEON_CYAN_RGB = (0, 229, 255)
NEON_MAGENTA = "#FF2BD6"
NEON_MAGENTA_RGB = (255, 43, 214)
BORDER_GLOW_ENABLED = True          # 外圈光晕
BORDER_ALPHA_OUTER = 55
BORDER_ALPHA_INNER = 170
BORDER_WIDTH = 2                    # 内圈描边宽度 px（×缩放）

# ---------- 扫描线纹理 ----------
SCANLINE_ENABLED = True             # 极淡扫描线（默认开，可关）
SCANLINE_ALPHA = 10
SCANLINE_SPACING = 6                # px（×缩放）
SCANLINE_WIDTH = 1

# ---------- 行面板 / 文字 ----------
ROW_BG_RGB = (6, 10, 22)
ROW_BG_ALPHA = 95                   # 行面板深色底
ROW_BORDER_ALPHA = 120              # 行面板霓虹描边
TITLE_COLOR = "rgba(255,255,255,235)"
TITLE_TEXT_SIZE = 11
ROW_TEXT_SIZE = 12