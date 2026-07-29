"""自定义标题栏组件

使用 PyQt6 自绘风格替代 Windows 原生标题栏，
使窗口边框、按钮与暗色主题保持一致。
"""

from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal, QEvent
from PyQt6.QtGui import QMouseEvent, QAction
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy
)


# ── 按钮基础样式 (融合理暗色主题) ──
_BUTTON_BASE = """
    QPushButton {{
        border: none;
        border-radius: 0;
        min-width: 46px;
        min-height: 32px;
        max-width: 46px;
        max-height: 32px;
        font-size: 14px;
        font-family: "Segoe MDL2 Assets", "Microsoft YaHei";
    }}
"""

_CLOSE_STYLE = _BUTTON_BASE + """
    QPushButton {{
        color: #e0e0f0;
        background: transparent;
    }}
    QPushButton:hover {{
        background: #e81123;
        color: white;
    }}
"""

_MINMAX_STYLE = _BUTTON_BASE + """
    QPushButton {{
        color: #b0b0c8;
        background: transparent;
    }}
    QPushButton:hover {{
        background: #454575;
        color: #e0e0f0;
    }}
"""


class TitleBar(QWidget):
    """自定义标题栏 — 拖拽移动、最大化、PyQt 风格按钮"""

    # 当用户点击关闭按钮时发出
    close_clicked = pyqtSignal()
    # 当用户点击最小化按钮时发出
    minimize_clicked = pyqtSignal()
    # 当用户点击最大化/还原按钮时发出
    maximize_clicked = pyqtSignal()

    def __init__(self, parent: QWidget, title: str = ""):
        super().__init__(parent)
        self._parent = parent
        self._dragging = False
        self._drag_start = QPoint()

        self.setFixedHeight(36)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setObjectName("titleBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(0)

        # ── 应用图标 + 标题 ──
        self._icon_label = QLabel("🎵")
        self._icon_label.setFixedWidth(28)
        self._icon_label.setStyleSheet("font-size: 16px; background: transparent; color: #7eb8ff;")
        layout.addWidget(self._icon_label)

        self._title_label = QLabel(title)
        self._title_label.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #e0e0f0;"
            "background: transparent; padding-left: 4px;"
        )
        layout.addWidget(self._title_label)

        layout.addStretch()

        # ── 最小化按钮 ──
        self._btn_min = QPushButton("\u2014")  # em-dash
        self._btn_min.setStyleSheet(_MINMAX_STYLE)
        self._btn_min.setToolTip("最小化")
        self._btn_min.clicked.connect(self.minimize_clicked)
        layout.addWidget(self._btn_min)

        # ── 最大化/还原按钮 ──
        self._btn_max = QPushButton("\u25A1")  # □ (square)
        self._btn_max.setStyleSheet(_MINMAX_STYLE)
        self._btn_max.setToolTip("最大化")
        self._btn_max.clicked.connect(self.maximize_clicked)
        layout.addWidget(self._btn_max)

        # ── 关闭按钮 ──
        self._btn_close = QPushButton("\u2716")  # ✖
        self._btn_close.setStyleSheet(_CLOSE_STYLE)
        self._btn_close.setToolTip("关闭")
        self._btn_close.clicked.connect(self.close_clicked)
        layout.addWidget(self._btn_close)

        # 整栏可拖拽
        self.setMouseTracking(True)

    def set_title(self, title: str):
        self._title_label.setText(title)

    def set_maximized_icon(self, maximized: bool):
        """最大化时切为还原图标"""
        self._btn_max.setText("\u2750" if maximized else "\u25A1")  # ❐ or □

    # ── 拖拽移动 ──
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging:
            delta = event.globalPosition().toPoint() - self._drag_start
            new_pos = self._parent.pos() + delta
            self._parent.move(new_pos)
            self._drag_start = event.globalPosition().toPoint()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._dragging = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """双击标题栏 => 最大化 / 还原"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_clicked.emit()
        super().mouseDoubleClickEvent(event)
