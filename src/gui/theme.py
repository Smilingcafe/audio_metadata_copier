"""GUI 主题与样式定义 — 深蓝海洋暗色主题 + 毛玻璃效果

提供深蓝色系配色方案和毛玻璃风格的 Qt 样式表。
毛玻璃效果通过半透明背景 + 边框微光 + 渐变叠加模拟实现。
"""

from typing import Dict

# =====================================================================
# 深蓝海洋暗色主题 (Deep Ocean Blue)
# =====================================================================

DARK_THEME: Dict[str, str] = {
    # -- 背景层级 --
    "bg_primary": "#080f1e",
    "bg_secondary": "#0d1b33",
    "bg_tertiary": "#132544",
    "bg_input": "#162d52",
    "bg_hover": "#1e3d6e",
    "bg_selected": "#254d8a",

    # -- 文字层级 --
    "text_primary": "#dce6f5",
    "text_secondary": "#8fa8cc",
    "text_dimmed": "#5a7099",
    "text_accent": "#7aadff",

    # -- 强调色系 --
    "accent": "#4d7cff",
    "accent_hover": "#6b9bff",
    "accent_pressed": "#3a5ecc",

    # -- 语义色 --
    "success": "#3cb8a0",
    "warning": "#e6a04e",
    "error": "#e0556a",
    "info": "#6ba8e6",

    # -- 边框 --
    "border": "#1e3560",
    "border_focus": "#4d7cff",

    # -- 滚动条 --
    "scrollbar_bg": "#0d1b33",
    "scrollbar_handle": "#1e3560",
    "scrollbar_handle_hover": "#2a4d80",

    # -- 行交替 --
    "row_even": "#0d1b33",
    "row_odd": "#111f3a",
}


def generate_stylesheet(theme: Dict[str, str]) -> str:
    """根据主题字典生成 Qt 样式表。

    所有毛玻璃效果通过半透明 rgba 背景 + 微光边框模拟实现。
    """
    t = theme
    return f"""
/* =====================================================================
   全局样式 -- 深蓝海洋暗色主题 + 毛玻璃质感
   ===================================================================== */

QWidget {{
    background-color: {t['bg_primary']};
    color: {t['text_primary']};
    font-family: "Microsoft YaHei", "Segoe UI", "Noto Sans CJK SC", sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {t['bg_primary']};
}}

/* -- 毛玻璃分组框 -- */
QGroupBox {{
    background: rgba(13, 27, 51, 0.62);
    border: 1px solid rgba(37, 77, 138, 0.28);
    border-radius: 10px;
    margin-top: 12px;
    padding: 14px 12px 10px 12px;
    font-weight: bold;
    font-size: 13px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 18px;
    padding: 0 10px;
    color: {t['text_accent']};
    background: transparent;
}}

/* -- 毛玻璃按钮 -- */
QPushButton {{
    background: rgba(19, 37, 68, 0.58);
    border: 1px solid rgba(37, 77, 138, 0.28);
    border-radius: 8px;
    padding: 8px 18px;
    color: {t['text_primary']};
    font-weight: bold;
    min-width: 80px;
}}
QPushButton:hover {{
    background: rgba(30, 61, 110, 0.70);
    border-color: rgba(77, 124, 255, 0.50);
    color: #ffffff;
}}
QPushButton:pressed {{
    background: rgba(37, 77, 138, 0.78);
    border-color: {t['accent']};
}}
QPushButton:disabled {{
    background: rgba(19, 37, 68, 0.22);
    color: {t['text_dimmed']};
    border-color: rgba(30, 53, 96, 0.12);
}}

/* -- 主要操作按钮 (发光强调) -- */
QPushButton#primaryBtn {{
    background: rgba(77, 124, 255, 0.72);
    border: 1px solid rgba(77, 124, 255, 0.55);
    border-radius: 10px;
    color: #ffffff;
    font-weight: bold;
    padding: 10px 28px;
}}
QPushButton#primaryBtn:hover {{
    background: rgba(107, 155, 255, 0.82);
    border-color: rgba(107, 155, 255, 0.70);
}}
QPushButton#primaryBtn:pressed {{
    background: rgba(58, 94, 204, 0.88);
    border-color: {t['accent']};
}}
QPushButton#primaryBtn:disabled {{
    background: rgba(19, 37, 68, 0.22);
    color: {t['text_dimmed']};
    border-color: rgba(30, 53, 96, 0.12);
}}

/* -- 毛玻璃输入框 -- */
QLineEdit {{
    background: rgba(22, 45, 82, 0.55);
    border: 1px solid rgba(37, 77, 138, 0.28);
    border-radius: 8px;
    padding: 9px 14px;
    color: {t['text_primary']};
    selection-background-color: {t['accent']};
    selection-color: #ffffff;
}}
QLineEdit:focus {{
    border-color: rgba(77, 124, 255, 0.55);
    background: rgba(22, 45, 82, 0.75);
}}
QLineEdit::placeholder {{
    color: {t['text_dimmed']};
}}

/* -- 毛玻璃复选框 -- */
QCheckBox {{
    spacing: 8px;
    color: {t['text_secondary']};
    padding: 4px 0;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid rgba(37, 77, 138, 0.35);
    border-radius: 5px;
    background: rgba(22, 45, 82, 0.50);
}}
QCheckBox::indicator:checked {{
    background: rgba(77, 124, 255, 0.70);
    border-color: {t['accent']};
}}
QCheckBox::indicator:checked:hover {{
    background: rgba(107, 155, 255, 0.80);
}}
QCheckBox::indicator:hover {{
    border-color: rgba(77, 124, 255, 0.55);
}}

/* -- 毛玻璃树形列表 -- */
QTreeWidget, QTableWidget {{
    background: rgba(13, 27, 51, 0.52);
    border: 1px solid rgba(37, 77, 138, 0.28);
    border-radius: 8px;
    color: {t['text_primary']};
    gridline-color: rgba(30, 53, 96, 0.18);
    outline: none;
}}
QTreeWidget::item, QTableWidget::item {{
    padding: 4px 6px;
    border: none;
    background: transparent;
}}
QTreeWidget::item:selected, QTableWidget::item:selected {{
    background: rgba(37, 77, 138, 0.58);
    color: {t['text_primary']};
}}
QTreeWidget::item:hover, QTableWidget::item:hover {{
    background: rgba(30, 61, 110, 0.52);
}}
QTreeWidget::item:alternate, QTableWidget::item:alternate {{
    background: rgba(17, 31, 58, 0.38);
}}
QTreeWidget::item:!alternate, QTableWidget::item:!alternate {{
    background: rgba(13, 27, 51, 0.22);
}}
QHeaderView::section {{
    background: rgba(19, 37, 68, 0.62);
    color: {t['text_secondary']};
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid rgba(37, 77, 138, 0.25);
    font-weight: bold;
}}

/* -- 毛玻璃进度条 -- */
QProgressBar {{
    border: 1px solid rgba(37, 77, 138, 0.28);
    border-radius: 8px;
    background: rgba(13, 27, 51, 0.42);
    text-align: center;
    height: 24px;
    color: {t['text_primary']};
    font-weight: bold;
}}
QProgressBar::chunk {{
    background: rgba(77, 124, 255, 0.65);
    border-radius: 6px;
}}

/* -- 毛玻璃日志区域 -- */
QTextEdit, QPlainTextEdit {{
    background: rgba(13, 27, 51, 0.52);
    border: 1px solid rgba(37, 77, 138, 0.28);
    border-radius: 8px;
    padding: 10px;
    color: {t['text_secondary']};
    font-family: "Consolas", "Cascadia Code", "Fira Code", monospace;
    font-size: 12px;
}}

/* -- 滚动条 -- */
QScrollBar:vertical {{
    border: none;
    background: {t['scrollbar_bg']};
    width: 10px;
    margin: 0;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: {t['scrollbar_handle']};
    min-height: 30px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background: {t['scrollbar_handle_hover']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    border: none;
    background: {t['scrollbar_bg']};
    height: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: {t['scrollbar_handle']};
    min-width: 30px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {t['scrollbar_handle_hover']};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* -- 标签 -- */
QLabel {{
    color: {t['text_secondary']};
    background: transparent;
}}
QLabel#titleLabel {{
    color: {t['text_primary']};
    font-size: 18px;
    font-weight: bold;
    background: transparent;
}}
QLabel#statusLabel {{
    color: {t['text_dimmed']};
    font-size: 12px;
    background: transparent;
}}

/* -- 毛玻璃菜单 -- */
QMenu {{
    background: rgba(13, 27, 51, 0.92);
    border: 1px solid rgba(37, 77, 138, 0.35);
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 8px 36px 8px 18px;
    border-radius: 6px;
    background: transparent;
}}
QMenu::item:selected {{
    background: rgba(30, 61, 110, 0.65);
}}
QMenu::separator {{
    height: 1px;
    background: rgba(37, 77, 138, 0.25);
    margin: 4px 10px;
}}

/* -- 毛玻璃工具提示 -- */
QToolTip {{
    background: rgba(13, 27, 51, 0.92);
    color: {t['text_primary']};
    border: 1px solid rgba(37, 77, 138, 0.35);
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
}}

/* -- 分割线 -- */
QFrame#separator {{
    color: {t['border']};
    background-color: {t['border']};
    height: 1px;
}}

/* -- 状态栏 -- */
QStatusBar {{
    background: rgba(13, 27, 51, 0.70);
    color: {t['text_dimmed']};
    border-top: 1px solid rgba(37, 77, 138, 0.25);
    padding: 4px;
}}
"""
