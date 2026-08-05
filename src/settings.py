"""设置面板：刷新间隔输入框 + 窗口缩放档位。"""
from __future__ import annotations

from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from . import skin
from .config import SCALE_OPTIONS


class SettingsDialog(QDialog):
    def __init__(self, cfg, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setModal(True)
        self.setMinimumWidth(260)
        self.setStyleSheet(f"""
QDialog {{ background-color: {skin.DIALOG_BG}; }}
QLabel {{ color: {skin.TEXT_LABEL}; }}
QLineEdit, QComboBox {{
    background-color: {skin.INPUT_BG};
    color: {skin.TEXT_STRONG};
    border: 1px solid {skin.BORDER_MED};
    border-radius: 4px;
    padding: 4px;
}}
QPushButton {{
    background-color: {skin.BTN_BG};
    color: {skin.TEXT_LABEL};
    border: 1px solid {skin.BORDER_MED};
    border-radius: 4px;
    padding: 4px 12px;
}}
QPushButton:hover {{ background-color: {skin.BTN_HOVER}; }}
""")
        self._result = (cfg.refresh_minutes, cfg.scale)

        lay = QVBoxLayout(self)
        lay.setSpacing(8)

        lay.addWidget(QLabel("刷新间隔（分钟）"))
        self.interval_edit = QLineEdit(str(cfg.refresh_minutes))
        self.interval_edit.setPlaceholderText("默认 10 分钟")
        self.interval_edit.setValidator(QIntValidator(1, 1440, self))
        lay.addWidget(self.interval_edit)

        lay.addWidget(QLabel("窗口缩放"))
        self.scale_combo = QComboBox()
        for s in SCALE_OPTIONS:
            self.scale_combo.addItem(f"{s}%", s)
        idx = self.scale_combo.findData(cfg.scale)
        self.scale_combo.setCurrentIndex(max(0, idx))
        lay.addWidget(self.scale_combo)

        btns = QHBoxLayout()
        ok = QPushButton("确定")
        cancel = QPushButton("取消")
        ok.clicked.connect(self._on_ok)
        cancel.clicked.connect(self.reject)
        btns.addStretch(1)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        lay.addLayout(btns)

    def _on_ok(self) -> None:
        try:
            minutes = int(self.interval_edit.text() or 10)
        except ValueError:
            minutes = 10
        minutes = max(1, min(1440, minutes))
        self._result = (minutes, int(self.scale_combo.currentData()))
        self.accept()

    def values(self):
        return self._result
