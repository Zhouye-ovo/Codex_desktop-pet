"""主窗口：无边框透明悬浮窗，固定画布 + 四按钮顶栏 + 两行余额 + 悬停切换今日用量。"""
from __future__ import annotations

import os

from PySide6.QtCore import QRectF, Qt, QThreadPool, QTimer, QRunnable, QObject, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import providers, usage
from .config import Config
from .settings import SettingsDialog

BASE_W = 320
BASE_H = 400
RADIUS = 16
DRAG_THRESHOLD = 5
FONT_FAMILY = "Microsoft YaHei UI"

BTN_QSS = """
QPushButton {
    background: transparent;
    color: rgba(255,255,255,200);
    border: none;
    border-radius: 6px;
}
QPushButton:hover { background: rgba(255,255,255,40); color: white; }
QPushButton:pressed { background: rgba(255,255,255,70); }
QPushButton:checked { color: #ffd76a; }
"""


class WorkerSignals(QObject):
    done = Signal(object)  # BalanceResult


class BalanceWorker(QRunnable):
    def __init__(self, provider) -> None:
        super().__init__()
        self.provider = provider
        self.signals = WorkerSignals()

    def run(self) -> None:
        self.signals.done.emit(self.provider.fetch())


class RowWidget(QWidget):
    """单行：默认显示余额，悬停时临时切换为今日用量。"""

    def __init__(self, title: str, scale: float, parent=None) -> None:
        super().__init__(parent)
        self.scale = scale
        self.balance_text = "读取中…"
        self.usage_text = "今日 —"
        self._hover = False

        lay = QHBoxLayout(self)
        self.title_label = QLabel(title)
        self.value_label = QLabel(self.balance_text)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.value_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.title_label.setStyleSheet("color: rgba(255,255,255,220);")
        self.value_label.setStyleSheet("color: white;")
        lay.addWidget(self.title_label)
        lay.addStretch(1)
        lay.addWidget(self.value_label)
        self.set_scale(scale)

    def set_scale(self, s: float) -> None:
        self.scale = s
        self.title_label.setFont(QFont(FONT_FAMILY, round(11 * s)))
        self.value_label.setFont(QFont(FONT_FAMILY, round(12 * s), QFont.Weight.Bold))
        self.layout().setContentsMargins(round(14 * s), round(6 * s), round(14 * s), round(6 * s))

    def set_balance(self, text: str) -> None:
        self.balance_text = text
        if not self._hover:
            self.value_label.setText(text)

    def set_usage(self, text: str) -> None:
        self.usage_text = text
        if self._hover:
            self.value_label.setText(text)

    def enterEvent(self, event) -> None:
        self._hover = True
        self.value_label.setText(self.usage_text)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.value_label.setText(self.balance_text)
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(round(6 * self.scale), 1, round(-6 * self.scale), -1)
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 10, 10)
        p.fillPath(path, QColor(0, 0, 0, 70))
        super().paintEvent(event)


class MainWindow(QWidget):
    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self.cfg = cfg
        self.scale = 1.0
        self._dragging = False
        self._press_global = None
        self._press_win = None

        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if cfg.topmost:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.bg_pixmap = self._load_bg()
        self._build_ui()
        self._apply_scale()
        self._apply_pos()

        self.pool = QThreadPool()
        self.pool.setMaxThreadCount(4)
        self._workers = set()  # 持有 worker 引用，防止被 GC 导致信号丢失
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_all)
        self._restart_timer()

        QTimer.singleShot(0, self.refresh_all)

    # ---------- UI ----------
    def _build_ui(self) -> None:
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(0)

        self.bar = QHBoxLayout()
        self.bar.addStretch(1)
        self.btn_refresh = self._make_button("⟳", "刷新余额")
        self.btn_settings = self._make_button("⚙", "设置")
        self.btn_pin = self._make_button("📌", "置顶：开/关")
        self.btn_close = self._make_button("✕", "关闭")
        for b in (self.btn_refresh, self.btn_settings, self.btn_pin, self.btn_close):
            self.bar.addWidget(b)
        self.root.addLayout(self.bar)

        self.root.addStretch(1)

        self.row_deepseek = RowWidget("DeepSeek", self.scale, self)
        self.row_vision = RowWidget("识图", self.scale, self)
        self.root.addWidget(self.row_deepseek)
        self.root.addWidget(self.row_vision)
        self.root.addSpacing(round(16 * self.scale))

        self.btn_refresh.clicked.connect(self.refresh_all)
        self.btn_settings.clicked.connect(self.open_settings)
        self.btn_pin.clicked.connect(self.toggle_topmost)
        self.btn_close.clicked.connect(self.close)

    def _make_button(self, text: str, tip: str) -> QPushButton:
        b = QPushButton(text)
        b.setToolTip(tip)
        b.setCheckable(text == "📌")
        b.setStyleSheet(BTN_QSS)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        return b

    def _apply_scale(self) -> None:
        s = self.cfg.scale / 100.0
        self.scale = s
        w, h = round(BASE_W * s), round(BASE_H * s)
        self.setFixedSize(w, h)
        self.bar.setContentsMargins(round(8 * s), round(8 * s), round(8 * s), 0)
        self.bar.setSpacing(round(4 * s))
        for b in (self.btn_refresh, self.btn_settings, self.btn_pin, self.btn_close):
            b.setFixedSize(round(30 * s), round(26 * s))
            b.setFont(QFont(FONT_FAMILY, round(11 * s)))
        self.row_deepseek.set_scale(s)
        self.row_vision.set_scale(s)
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
        self.bg_pixmap = self._load_bg()
        self.update()
        self.row_deepseek.set_usage(self._fmt_usage(usage.deepseek_today_tokens()))
        self.row_vision.set_usage(self._fmt_usage(usage.vision_today_tokens()))
        self._start_worker(providers.DeepSeekProvider(), self.row_deepseek)
        self._start_worker(providers.SiliconFlowProvider(), self.row_vision)

    def _start_worker(self, provider, row: RowWidget) -> None:
        worker = BalanceWorker(provider)
        worker.signals.done.connect(lambda res, r=row: self._on_result(r, res))
        self._workers.add(worker)
        worker.signals.done.connect(lambda res, w=worker: self._workers.discard(w))
        self.pool.start(worker)

    def _on_result(self, row: RowWidget, res: providers.BalanceResult) -> None:
        if res.error:
            row.set_balance("读取失败")
            row.setToolTip(res.error)
        else:
            row.set_balance(self._fmt_money(res.amount, res.currency))
            row.setToolTip("")

    @staticmethod
    def _fmt_money(amount, currency: str) -> str:
        try:
            amt = float(amount)
        except (TypeError, ValueError):
            return "—"
        if currency and currency.upper() != "CNY":
            return f"{amt:,.2f} {currency}"
        return f"¥{amt:,.2f}"

    @staticmethod
    def _fmt_usage(n: int) -> str:
        return f"今日: {n:,} tokens"

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

    # ---------- 背景 / 绘制 ----------
    def _load_bg(self):
        path = self.cfg.bg_abs()
        if os.path.isfile(path):
            pm = QPixmap(path)
            if not pm.isNull():
                return pm
        return None

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = self.rect()
        radius = round(RADIUS * self.scale)
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), radius, radius)
        p.setClipPath(path)
        if self.bg_pixmap is not None:
            p.drawPixmap(rect, self.bg_pixmap)
        else:
            grad = QLinearGradient(0, 0, 0, rect.height())
            grad.setColorAt(0, QColor(32, 42, 68, 245))
            grad.setColorAt(1, QColor(16, 20, 36, 245))
            p.fillPath(path, QBrush(grad))
            p.setPen(QColor(255, 255, 255, 150))
            p.setFont(QFont(FONT_FAMILY, round(13 * self.scale)))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "将底图放到 assets/bg.png")
        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 36), 1))
        p.drawRoundedRect(QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)

    # ---------- 拖拽 ----------
    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._press_global = e.globalPosition().toPoint()
            self._press_win = self.pos()
            self._dragging = False
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e) -> None:
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

    def closeEvent(self, e) -> None:
        self.cfg.pos = [self.x(), self.y()]
        self.cfg.save()
        super().closeEvent(e)
