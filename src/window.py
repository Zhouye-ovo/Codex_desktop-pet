"""主窗口：DeepSeek 表盘风悬浮小窗。

全部图形由 QPainter 自绘，不依赖任何外部素材。
"""
from __future__ import annotations

import math

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QPointF,
    QRectF,
    QRunnable,
    Qt,
    QThreadPool,
    QTimer,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsOpacityEffect,
    QLabel,
    QPushButton,
    QWidget,
)

from . import providers, skin, usage
from .config import Config
from .settings import SettingsDialog

BASE_W = 320
BASE_H = 360
TOPBAR_H = 34
TOPBAR_MARGIN = 4
TOPBAR_BOTTOM = TOPBAR_H + TOPBAR_MARGIN
DIAL_D = 300
DRAG_THRESHOLD = 5
FONT_FAMILY = "Microsoft YaHei UI"
MONO_FONT = "Consolas"

# 5×7 点阵字形（自绘，通用数字/符号/自设计 ¥）
_DOT_5X7 = {
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "¥": ("10001", "10001", "01110", "11111", "00100", "00100", "00100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
}


class WorkerSignals(QObject):
    done = Signal(str, object)  # (model key, BalanceResult)


class BalanceWorker(QRunnable):
    def __init__(self, provider, key: str) -> None:
        super().__init__()
        self.provider = provider
        self.key = key
        self.signals = WorkerSignals()

    def run(self) -> None:
        self.signals.done.emit(self.key, self.provider.fetch())


class DotMatrixLabel(QWidget):
    """5×7 点阵 LED 标签：亮 #FFFFFF 微光 / 灭 10% 白。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._text = "--"
        self._error = False
        self.scale = 1.0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_text(self, text: str) -> None:
        self._text = text
        self.update()

    def set_error(self, on: bool) -> None:
        self._error = on
        self.update()

    def set_scale(self, s: float) -> None:
        self.scale = s
        self.update()

    def _pixel_size(self):
        s = self.scale
        pitch_x = max(3, round(5 * s))
        pitch_y = max(4, round(7 * s))
        gap_x = max(1, round(2 * s))
        w = len(self._text) * (5 * pitch_x) + max(0, len(self._text) - 1) * gap_x
        return w, 7 * pitch_y

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self.scale
        pitch_x = max(3, round(5 * s))
        pitch_y = max(4, round(7 * s))
        dot = max(2, round(3 * s))
        gap_x = max(1, round(2 * s))
        lit = QColor(skin.STATUS_RED) if self._error else QColor(255, 255, 255)
        glow = QColor(255, 59, 48, 70) if self._error else QColor(255, 255, 255, 70)
        off = QColor(255, 255, 255, 26)
        x = 0
        for ch in self._text:
            pat = _DOT_5X7.get(ch, _DOT_5X7[" "])
            for row in range(7):
                for col in range(5):
                    if pat[row][col] == "1":
                        p.fillRect(QRectF(x + col * pitch_x - 1, row * pitch_y - 1, dot + 2, dot + 2), glow)
                        p.fillRect(x + col * pitch_x, row * pitch_y, dot, dot, lit)
                    else:
                        p.fillRect(x + col * pitch_x, row * pitch_y, dot, dot, off)
            x += 5 * pitch_x + gap_x


class IconButton(QPushButton):
    """顶栏图标按钮：QPainter 线条自绘。"""

    def __init__(self, kind: str, tip: str, parent=None) -> None:
        super().__init__(parent)
        self.kind = kind
        self.setToolTip(tip)
        self.setCheckable(kind == "pin")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refreshing = False
        self.scale = 1.0

    def set_scale(self, s: float) -> None:
        self.scale = s
        self.setFixedSize(round(26 * s), round(26 * s))
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self.scale
        r = self.rect()
        if self.isDown():
            p.fillRect(r, QColor(skin.PRESS_BG))
        if self.underMouse():
            p.setPen(QPen(QColor(255, 255, 255, 90), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(r).adjusted(0.5, 0.5, -0.5, -0.5), 4, 4)

        color = QColor(skin.TEXT_LABEL)
        if self.kind == "pin" and self.isChecked():
            color = QColor(skin.STATUS_BLUE)
        elif self.kind == "refresh" and self.refreshing:
            color = QColor(skin.STATUS_GREEN)
        if self.underMouse():
            color = QColor(255, 255, 255)
        self._draw_icon(p, color, s)
        if self.kind == "pin" and self.isChecked():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(skin.STATUS_BLUE))
            p.drawEllipse(QPointF(r.center().x(), r.top() + round(4 * s)), max(1.5, 2 * s), max(1.5, 2 * s))

    def _draw_icon(self, p: QPainter, color: QColor, s: float) -> None:
        pen = QPen(color, max(1.0, 1.5 * s))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        cx, cy = self.width() / 2.0, self.height() / 2.0
        u = max(3.0, 8.0 * s)
        if self.kind == "refresh":
            rect = QRectF(cx - u, cy - u, 2 * u, 2 * u)
            p.drawArc(rect, 30 * 16, 270 * 16)
            ex = cx + u * math.cos(math.radians(30))
            ey = cy - u * math.sin(math.radians(30))
            p.drawLine(QPointF(ex, ey), QPointF(ex - 3 * s, ey - 3 * s))
            p.drawLine(QPointF(ex, ey), QPointF(ex + 1 * s, ey - 4 * s))
        elif self.kind == "settings":
            p.drawEllipse(QPointF(cx, cy), u * 0.55, u * 0.55)
            p.drawEllipse(QPointF(cx, cy), u * 0.22, u * 0.22)
            for i in range(8):
                a = math.radians(i * 45)
                x1 = cx + u * 0.62 * math.cos(a)
                y1 = cy - u * 0.62 * math.sin(a)
                x2 = cx + u * math.cos(a)
                y2 = cy - u * math.sin(a)
                p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        elif self.kind == "pin":
            p.drawLine(QPointF(cx, cy - u * 0.3), QPointF(cx, cy + u * 0.7))
            p.drawLine(QPointF(cx - u * 0.4, cy + u * 0.7), QPointF(cx + u * 0.4, cy + u * 0.7))
            p.setBrush(color)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy - u * 0.3), max(1.5, 1.8 * s), max(1.5, 1.8 * s))
        elif self.kind == "close":
            d = u * 0.75
            p.drawLine(QPointF(cx - d, cy - d), QPointF(cx + d, cy + d))
            p.drawLine(QPointF(cx + d, cy - d), QPointF(cx - d, cy + d))


class ModelState:
    def __init__(self, key: str, display: str) -> None:
        self.key = key
        self.display = display
        self.b0: float | None = None
        self.current: float | None = None
        self.last_error: str | None = None
        self.today_tokens: int = 0


class MainWindow(QWidget):
    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self.cfg = cfg
        self.scale = 1.0
        self._dragging = False
        self._press_global = None
        self._press_win = None
        self._hovered = False
        self._pending = 0
        self._lit_display = 0.0
        self._ratio = None
        self._model_phase = "idle"

        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if cfg.topmost:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)

        self.states = {
            "deepseek": ModelState("deepseek", "DEEPSEEK"),
            "vision": ModelState("vision", "识图"),
        }
        self.current_key = "deepseek"

        self._lit_anim = QVariantAnimation(self)
        self._lit_anim.setDuration(800)
        self._lit_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._lit_anim.valueChanged.connect(self._on_lit_anim)

        self._model_anim = QVariantAnimation(self)
        self._model_anim.setDuration(150)
        self._model_anim.valueChanged.connect(self._on_model_fade)
        self._model_anim.finished.connect(self._on_model_done)

        self._hover_anim = QVariantAnimation(self)
        self._hover_anim.setDuration(200)
        self._hover_anim.valueChanged.connect(self._on_hover_anim)

        self._build_ui()
        self._apply_scale()
        self._apply_pos()

        self.pool = QThreadPool()
        self.pool.setMaxThreadCount(4)
        self._workers = set()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_all)
        self._restart_timer()
        QTimer.singleShot(0, self.refresh_all)

    # ---------- UI ----------
    def _build_ui(self) -> None:
        self.btn_refresh = IconButton("refresh", "刷新余额", self)
        self.btn_settings = IconButton("settings", "设置", self)
        self.btn_pin = IconButton("pin", "置顶：开/关", self)
        self.btn_close = IconButton("close", "关闭", self)
        self.btn_refresh.clicked.connect(self.refresh_all)
        self.btn_settings.clicked.connect(self.open_settings)
        self.btn_pin.clicked.connect(self.toggle_topmost)
        self.btn_close.clicked.connect(self.close)
        self.btn_pin.setChecked(self.cfg.topmost)

        self.model_label = QLabel("DEEPSEEK", self)
        self.model_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.model_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.model_label.setStyleSheet(f"color: {skin.TEXT_WEAK2};")

        self.balance_label = DotMatrixLabel(self)
        self.balance_label.set_text("--")

        self.usage_overlay = QLabel("", self)
        self.usage_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.usage_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.usage_overlay.setStyleSheet(f"color: {skin.TEXT_MAIN};")

        self.balance_effect = QGraphicsOpacityEffect(self.balance_label)
        self.balance_label.setGraphicsEffect(self.balance_effect)
        self.usage_effect = QGraphicsOpacityEffect(self.usage_overlay)
        self.usage_overlay.setGraphicsEffect(self.usage_effect)
        self.usage_effect.setOpacity(0.0)

        self.model_effect = QGraphicsOpacityEffect(self.model_label)
        self.model_label.setGraphicsEffect(self.model_effect)

        self.today_label = QLabel("", self)
        self.session_label = QLabel("", self)
        self.open_label = QLabel("", self)
        self.v_label = QLabel("▼", self)
        for lbl in (self.today_label, self.session_label, self.open_label, self.v_label):
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.today_label.setStyleSheet(f"color: {skin.TEXT_LABEL};")
        self.session_label.setStyleSheet(f"color: {skin.TEXT_MID};")
        self.open_label.setStyleSheet(f"color: {skin.TEXT_WEAK};")
        self.v_label.setStyleSheet(f"color: {skin.TEXT_WEAK};")

        self._set_model_texts()

    def _apply_scale(self) -> None:
        s = self.cfg.scale / 100.0
        self.scale = s
        self.setFixedSize(round(BASE_W * s), round(BASE_H * s))
        W, H = self.width(), self.height()

        y_btn = round(TOPBAR_MARGIN * s) + round((TOPBAR_H * s - 26 * s) / 2)
        x = W - round(8 * s) - round(26 * s)
        for b in (self.btn_close, self.btn_pin, self.btn_settings, self.btn_refresh):
            b.set_scale(s)
            b.move(round(x), round(y_btn))
            x -= round(28 * s)

        top = round(TOPBAR_BOTTOM * s)
        cx = W / 2.0
        cy = top + (H - top) / 2.0
        r = round(DIAL_D * s) / 2.0
        face_r = r - round(40 * s) - max(1, round(2 * s))

        f_model = QFont(MONO_FONT, round(11 * s))
        f_model.setBold(True)
        f_model.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, round(2 * s))
        self.model_label.setFont(f_model)
        self.balance_label.set_scale(s)
        self.usage_overlay.setFont(QFont(FONT_FAMILY, round(11 * s), QFont.Weight.Bold))
        self.today_label.setFont(QFont(FONT_FAMILY, round(9 * s)))
        self.session_label.setFont(QFont(FONT_FAMILY, round(9 * s)))
        self.open_label.setFont(QFont(FONT_FAMILY, round(8 * s)))
        self.v_label.setFont(QFont(FONT_FAMILY, round(10 * s)))

        mw = round(180 * s)
        self.model_label.setGeometry(round(cx - mw / 2), round(cy - face_r * 0.62), mw, round(20 * s))
        bw, bh = self.balance_label._pixel_size()
        bx = round(cx - bw / 2)
        by = round(cy - face_r * 0.12 - bh / 2)
        self.balance_label.setGeometry(bx, by, bw, bh)
        self.usage_overlay.setGeometry(round(cx - max(bw, 190 * s) / 2), by, round(max(bw, 190 * s)), bh)
        self.today_label.setGeometry(round(cx - mw / 2), round(cy + face_r * 0.22), mw, round(18 * s))
        self.session_label.setGeometry(round(cx - mw / 2), round(cy + face_r * 0.38), mw, round(18 * s))
        self.open_label.setGeometry(round(cx - mw / 2), round(cy + face_r * 0.60), mw, round(16 * s))
        self.v_label.setGeometry(round(cx - mw / 2), round(cy + face_r * 0.78), mw, round(16 * s))

        self.update()

    def _apply_pos(self) -> None:
        if not self.cfg.pos:
            self._center_on_screen()
            return
        x, y = int(self.cfg.pos[0]), int(self.cfg.pos[1])
        screen = QApplication.primaryScreen().availableGeometry()
        w, h = self.width(), self.height()
        if x < screen.left() - w + 40 or x > screen.right() - 40 or y < screen.top() - 40 or y > screen.bottom() - 40:
            self._center_on_screen()
            return
        self.move(x, y)

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.left() + (screen.width() - self.width()) // 2, screen.top() + (screen.height() - self.height()) // 2)

    # ---------- 数据刷新 ----------
    def refresh_all(self) -> None:
        self.btn_refresh.refreshing = True
        self.btn_refresh.update()
        self._pending = 2
        self._start_worker(providers.DeepSeekProvider(), "deepseek")
        self._start_worker(providers.SiliconFlowProvider(), "vision")

    def _start_worker(self, provider, key: str) -> None:
        worker = BalanceWorker(provider, key)
        worker.signals.done.connect(lambda k, res: self._on_result(k, res))
        self._workers.add(worker)
        worker.signals.done.connect(lambda k, res, w=worker: self._workers.discard(w))
        self.pool.start(worker)

    def _on_result(self, key: str, res: providers.BalanceResult) -> None:
        st = self.states[key]
        if res.error:
            st.last_error = res.error
        else:
            st.last_error = None
            if st.b0 is None:
                st.b0 = res.amount
            st.current = res.amount
        st.today_tokens = usage.deepseek_today_tokens() if key == "deepseek" else usage.vision_today_tokens()
        self._pending -= 1
        if self._pending <= 0:
            self.btn_refresh.refreshing = False
            self.btn_refresh.update()
        if key == self.current_key:
            self._set_model_texts()
            self._update_dial_data(animate=True)

    # ---------- 盘面文字 ----------
    def _set_model_texts(self) -> None:
        st = self.states[self.current_key]
        self.model_label.setText(st.display)
        error = st.current is None and st.last_error is not None
        self.balance_label.set_error(error)
        self.balance_label.set_text("--" if st.current is None else f"¥{st.current:.2f}")
        self.usage_overlay.setText(f"{st.today_tokens:,} TOKENS")
        self.today_label.setText(f"TODAY {st.today_tokens:,} TOKENS")
        self.session_label.setText(self._fmt_session(st))
        self.open_label.setText(self._fmt_open(st))

    @staticmethod
    def _fmt_session(st: ModelState) -> str:
        if st.b0 is None or st.current is None:
            return "本次 --"
        diff = st.b0 - st.current
        sign = "-" if diff >= 0 else "+"
        return f"本次 {sign}¥{abs(diff):.2f}"

    @staticmethod
    def _fmt_open(st: ModelState) -> str:
        return f"OPEN ¥{st.b0:.2f}" if st.b0 is not None else "OPEN --"

    # ---------- 环 / 动画 ----------
    def _update_dial_data(self, animate: bool = True) -> None:
        st = self.states[self.current_key]
        if st.b0 is None or st.b0 <= 0 or st.current is None:
            target = 0.0
            self._ratio = None
        else:
            ratio = max(0.0, min(1.0, st.current / st.b0))
            self._ratio = ratio
            target = float(round(72 * ratio))
        if animate and abs(target - self._lit_display) > 0.01:
            self._lit_anim.stop()
            self._lit_anim.setStartValue(self._lit_display)
            self._lit_anim.setEndValue(target)
            self._lit_anim.start()
        else:
            self._lit_display = target
        self.update()

    def _on_lit_anim(self, v) -> None:
        self._lit_display = float(v)
        self.update()

    def _on_hover_anim(self, v) -> None:
        f = float(v)
        self.balance_effect.setOpacity(1.0 - f)
        self.usage_effect.setOpacity(f)

    def _set_hovered(self, on: bool) -> None:
        if on == self._hovered:
            return
        self._hovered = on
        self._hover_anim.stop()
        self._hover_anim.setStartValue(0.0 if on else 1.0)
        self._hover_anim.setEndValue(1.0 if on else 0.0)
        self._hover_anim.start()

    # ---------- 切模型 ----------
    def switch_model(self) -> None:
        if self._model_phase != "idle":
            return
        self._model_phase = "out"
        self._model_anim.stop()
        self._model_anim.setStartValue(1.0)
        self._model_anim.setEndValue(0.0)
        self._model_anim.setDuration(150)
        self._model_anim.start()

    def _on_model_fade(self, v) -> None:
        self.model_effect.setOpacity(float(v))

    def _on_model_done(self) -> None:
        if self._model_phase == "out":
            self._model_phase = "in"
            self.current_key = "vision" if self.current_key == "deepseek" else "deepseek"
            self._set_model_texts()
            self._update_dial_data(animate=True)
            self._model_anim.setStartValue(0.0)
            self._model_anim.setEndValue(1.0)
            self._model_anim.setDuration(150)
            self._model_anim.start()
        else:
            self._model_phase = "idle"

    # ---------- 设置 / 置顶 / 定时 ----------
    def open_settings(self) -> None:
        dlg = SettingsDialog(self.cfg, self)
        if dlg.exec():
            minutes, scale = dlg.values()
            self.cfg.refresh_minutes = minutes
            self.cfg.scale = scale
            self._apply_scale()
            self._restart_timer()
            self.cfg.save()
            self.refresh_all()

    def toggle_topmost(self) -> None:
        self.cfg.topmost = not self.cfg.topmost
        self.btn_pin.setChecked(self.cfg.topmost)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self.cfg.topmost)
        self.show()
        self.cfg.save()

    def _restart_timer(self) -> None:
        self.timer.stop()
        self.timer.start(max(1, self.cfg.refresh_minutes) * 60 * 1000)

    # ---------- 绘制 ----------
    def _dial_center(self):
        s = self.scale
        W, H = self.width(), self.height()
        top = round(TOPBAR_BOTTOM * s)
        cx = W / 2.0
        cy = top + (H - top) / 2.0
        r = round(DIAL_D * s) / 2.0
        return cx, cy, r

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self.scale
        rect = self.rect()
        radius = round(skin.BG_RADIUS * s)
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), radius, radius)
        p.setClipPath(path)
        p.fillRect(rect, QColor(0, 0, 0, skin.BG_ALPHA))
        self._draw_topbar(p, s, rect.width())
        self._draw_dial(p, s, rect.width(), rect.height())
        p.setClipping(False)

    def _draw_topbar(self, p: QPainter, s: float, W: int) -> None:
        x0 = round(8 * s)
        y0 = round(TOPBAR_MARGIN * s)
        w = W - round(16 * s)
        h = round(TOPBAR_H * s)
        p.fillRect(QRectF(x0 + 1, y0 + h, w - 2, max(1, round(2 * s))), QColor(0, 0, 0, 80))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(skin.TOPBAR_BG))
        p.drawRoundedRect(QRectF(x0, y0, w, h), 4, 4)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 46), 1))
        p.drawRoundedRect(QRectF(x0 + 0.5, y0 + 0.5, w - 1, h - 1), 4, 4)

    def _draw_dial(self, p: QPainter, s: float, W: int, H: int) -> None:
        cx, cy, r = self._dial_center()

        # 外圈浮雕：左上亮边 / 右下暗边 / 顶部偏左反光弧
        outer = QRectF(cx - r, cy - r, 2 * r, 2 * r)
        p.setPen(QPen(QColor(255, 255, 255, 32), max(1, round(2 * s))))
        p.drawArc(outer, 135 * 16, 90 * 16)
        p.setPen(QPen(QColor(0, 0, 0, 128), max(1, round(2 * s))))
        p.drawArc(outer, 315 * 16, 90 * 16)
        p.setPen(QPen(QColor(255, 255, 255, 40), max(1, round(1.5 * s))))
        p.drawArc(QRectF(cx - r * 0.55, cy - r * 0.55, r * 1.1, r * 1.1), 200 * 16, 40 * 16)

        # 三层压边
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(skin.BEZEL_OUTER), round(8 * s)))
        p.drawEllipse(QPointF(cx, cy), r - round(4 * s), r - round(4 * s))
        p.setPen(QPen(QColor(skin.BEZEL_MAIN), round(10 * s)))
        p.drawEllipse(QPointF(cx, cy), r - round(13 * s), r - round(13 * s))
        p.setPen(QPen(QColor(skin.BEZEL_BRIGHT), max(1, round(1 * s))))
        p.drawEllipse(QPointF(cx, cy), r - round(18.5 * s), r - round(18.5 * s))
        # 上半弧高光
        mr = r - round(13 * s)
        p.setPen(QPen(QColor(255, 255, 255, 18), max(1, round(4 * s))))
        p.drawArc(QRectF(cx - mr, cy - mr, 2 * mr, 2 * mr), 180 * 16, 180 * 16)

        # 120 根三级刻度（顶部起顺时针）
        tick_r0 = r - round(20 * s)
        for i in range(120):
            if i % 10 == 0:
                col, ln, wd = QColor(skin.TICK_MAJOR), round(12 * s), max(1.0, 1.5 * s)
            elif i % 5 == 0:
                col, ln, wd = QColor(skin.TICK_MID), round(9 * s), max(0.8, 0.9 * s)
            else:
                col, ln, wd = QColor(skin.TICK_MINOR), round(6 * s), max(0.5, 0.5 * s)
            a = math.radians(90 - i * 3)
            ca, sa = math.cos(a), math.sin(a)
            p.setPen(QPen(col, wd))
            p.drawLine(QPointF(cx + tick_r0 * ca, cy - tick_r0 * sa), QPointF(cx + (tick_r0 - ln) * ca, cy - (tick_r0 - ln) * sa))

        # 72 段油量环：轨道 → 亮格 → 径向切缝
        band_outer = r - round(24 * s)
        band_inner = r - round(40 * s)
        band_mid = (band_outer + band_inner) / 2.0
        band_w = band_outer - band_inner
        p.setPen(QPen(QColor(skin.TRACK), band_w))
        p.drawEllipse(QPointF(cx, cy), band_mid, band_mid)
        lit = max(0, min(72, int(round(self._lit_display))))
        seg = 5.0
        gap = 0.55
        p.setPen(QPen(QColor(skin.LIT), max(1, band_w - round(2 * s))))
        for i in range(lit):
            start = 90 - i * seg - gap / 2.0
            p.drawArc(QRectF(cx - band_mid, cy - band_mid, 2 * band_mid, 2 * band_mid), round(start * 16), round(-(seg - gap) * 16))
        p.setPen(QPen(QColor(skin.GAP), max(1.0, 1.8 * s)))
        for i in range(72):
            a = math.radians(90 - i * seg)
            ca, sa = math.cos(a), math.sin(a)
            p.drawLine(QPointF(cx + band_inner * ca, cy - band_inner * sa), QPointF(cx + band_outer * ca, cy - band_outer * sa))

        # 红色精度标记（比例位置短线 + 小圆）
        if self._ratio is not None:
            a = math.radians(90 - self._ratio * 360)
            ca, sa = math.cos(a), math.sin(a)
            x1, y1 = cx + band_inner * ca, cy - band_inner * sa
            x2, y2 = cx + band_outer * ca, cy - band_outer * sa
            p.setPen(QPen(QColor(skin.STATUS_RED), max(1.5, 2 * s)))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(skin.STATUS_RED))
            p.drawEllipse(QPointF(x2, y2), max(2, 2.5 * s), max(2, 2.5 * s))

        # 中心渐变盘面 + 暗角 + 同心细环
        face_r = band_inner - max(1, round(2 * s))
        face_rect = QRectF(cx - face_r, cy - face_r, 2 * face_r, 2 * face_r)
        grad = QRadialGradient(QPointF(cx, cy), face_r)
        grad.setColorAt(0.0, QColor(skin.BG_GRAD_TOP))
        grad.setColorAt(1.0, QColor(skin.BG_GRAD_BOTTOM))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(face_rect)
        vig = QRadialGradient(QPointF(cx, cy), face_r)
        vig.setColorAt(0.55, QColor(0, 0, 0, 0))
        vig.setColorAt(1.0, QColor(0, 0, 0, 140))
        p.setBrush(QBrush(vig))
        p.drawEllipse(face_rect)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(skin.INNER_RING), 1))
        p.drawEllipse(QPointF(cx, cy), face_r - round(2 * s), face_r - round(2 * s))
        p.setPen(QPen(QColor(255, 255, 255, 20), 1))
        p.drawEllipse(QPointF(cx, cy), face_r * 0.82, face_r * 0.82)

    # ---------- 鼠标：悬停（限表盘圆内）/ 拖拽 ----------
    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            if self.model_label.geometry().contains(e.position().toPoint()):
                self.switch_model()
            else:
                self._press_global = e.globalPosition().toPoint()
                self._press_win = self.pos()
                self._dragging = False
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e) -> None:
        cx, cy, r = self._dial_center()
        dx = e.position().x() - cx
        dy = e.position().y() - cy
        self._set_hovered(dx * dx + dy * dy <= r * r)
        if self._press_global is not None and e.buttons() & Qt.MouseButton.LeftButton:
            delta = e.globalPosition().toPoint() - self._press_global
            if not self._dragging:
                if delta.manhattanLength() >= DRAG_THRESHOLD * max(1.0, self.scale):
                    self._dragging = True
            if self._dragging:
                self.move(self._press_win + delta)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            if self._dragging:
                self.cfg.pos = [self.x(), self.y()]
                self.cfg.save()
            self._dragging = False
            self._press_global = None
            self._press_win = None
        super().mouseReleaseEvent(e)

    def leaveEvent(self, e) -> None:
        self._set_hovered(False)
        super().leaveEvent(e)

    def closeEvent(self, e) -> None:
        self.cfg.pos = [self.x(), self.y()]
        self.cfg.save()
        super().closeEvent(e)