"""GitHub Dark 配色常量和全局样式表。"""

from PySide6.QtGui import QColor, QPalette

GITHUB_DARK = {
    "canvas": "#0d1117",  # 主背景（编辑区）
    "surface": "#161b22",  # 侧栏 / 活动栏
    "overlay": "#1c2128",  # 悬停高亮
    "border": "#21262d",
    "border_strong": "#30363d",
    "text": "#e6edf3",
    "muted": "#8b949e",
    "accent": "#58a6ff",
    "accent_emphasis": "#1f6feb",
    "brand": "#f78166",  # 活动栏选中指示条
    "success": "#3fb950",
    "success_emphasis": "#238636",
    "success_hover": "#2ea043",
    "danger": "#f85149",
    "attention": "#d29922",
}


def build_stylesheet():
    """返回 GitHub Dark 风格的全局 QSS。"""
    c = GITHUB_DARK
    return f"""
    * {{
        font-family: "Segoe UI", "Microsoft YaHei UI", "PingFang SC", sans-serif;
        font-size: 13px;
    }}

    QWidget {{ color: {c["text"]}; }}

    QMainWindow {{ background-color: {c["canvas"]}; }}

    QToolTip {{
        background-color: {c["surface"]};
        color: {c["text"]};
        border: 1px solid {c["border_strong"]};
        padding: 4px 8px;
    }}

    /* ---- 活动栏（最左列） ---- */
    #activityBar {{
        background-color: {c["surface"]};
        border-right: 1px solid {c["border"]};
    }}
    QToolButton#activityButton {{
        background: transparent;
        border: none;
        border-left: 2px solid transparent;
        border-top-right-radius: 6px;
        border-bottom-right-radius: 6px;
        padding: 0 11px;
    }}
    QToolButton#activityButton:hover {{ background-color: {c["overlay"]}; }}
    QToolButton#activityButton:checked {{ border-left: 2px solid {c["brand"]}; }}

    /* ---- 侧栏面板（第二列） ---- */
    #sidePanel {{
        background-color: {c["surface"]};
        border-right: 1px solid {c["border"]};
    }}
    QLabel#panelHeader {{
        color: {c["muted"]};
        font-size: 11px;
        font-weight: 700;
    }}
    QToolButton#panelHeaderButton {{
        background: transparent;
        border: none;
        border-radius: 6px;
        padding: 4px;
    }}
    QToolButton#panelHeaderButton:hover {{ background-color: {c["overlay"]}; }}

    QListWidget {{
        background: transparent;
        border: none;
        outline: none;
    }}
    QListWidget::item {{
        padding: 8px 10px;
        border-radius: 6px;
    }}
    QListWidget::item:hover {{ background-color: {c["overlay"]}; }}
    QListWidget::item:selected {{ background-color: rgba(56, 139, 253, 0.22); }}

    /* ---- 任务详情（右侧区域） ---- */
    QLabel#detailTitle {{ font-size: 17px; font-weight: 600; }}
    QLabel#detailMeta {{ color: {c["muted"]}; font-size: 12px; }}
    QLabel#detailDesc {{ color: {c["text"]}; }}
    QLabel#emptyHint {{ color: {c["muted"]}; font-size: 22px; font-weight: 600; }}
    QLabel#emptySubHint {{ color: {c["muted"]}; font-size: 13px; }}
    QLabel#statusLabel {{ color: {c["muted"]}; font-size: 12px; }}
    QLabel#portLabel {{ color: {c["muted"]}; font-size: 12px; }}

    QTableWidget {{
        background-color: {c["canvas"]};
        border: 1px solid {c["border"]};
        border-radius: 6px;
        gridline-color: {c["border"]};
        selection-background-color: rgba(56, 139, 253, 0.25);
        selection-color: {c["text"]};
        outline: none;
    }}
    QTableWidget::item {{ padding: 4px 8px; border: none; }}
    QHeaderView::section {{
        background-color: {c["surface"]};
        color: {c["muted"]};
        border: none;
        border-bottom: 1px solid {c["border_strong"]};
        border-right: 1px solid {c["border"]};
        padding: 6px 8px;
        font-weight: 600;
    }}

    /* ---- 底部操作栏 ---- */
    #actionBar {{
        background-color: {c["canvas"]};
        border-top: 1px solid {c["border"]};
    }}

    QLineEdit {{
        background-color: {c["canvas"]};
        color: {c["text"]};
        border: 1px solid {c["border_strong"]};
        border-radius: 6px;
        padding: 5px 8px;
        selection-background-color: {c["accent_emphasis"]};
    }}
    QLineEdit:focus {{ border-color: {c["accent"]}; }}

    QPushButton {{
        background-color: {c["surface"]};
        color: {c["text"]};
        border: 1px solid {c["border_strong"]};
        border-radius: 6px;
        padding: 5px 14px;
    }}
    QPushButton:hover {{ background-color: {c["overlay"]}; border-color: #3d444d; }}
    QPushButton:pressed {{ background-color: {c["border"]}; }}
    QPushButton:disabled {{
        color: {c["muted"]};
        background-color: {c["surface"]};
        border-color: {c["border"]};
    }}

    QPushButton#runButton {{
        background-color: {c["success_emphasis"]};
        border: 1px solid rgba(240, 246, 252, 0.1);
        color: #ffffff;
        font-weight: 600;
        padding: 6px 18px;
    }}
    QPushButton#runButton:hover {{ background-color: {c["success_hover"]}; }}
    QPushButton#runButton:disabled {{
        background-color: rgba(46, 160, 67, 0.35);
        border-color: rgba(240, 246, 252, 0.05);
        color: rgba(255, 255, 255, 0.75);
    }}

    QPushButton#stopButton {{
        background: transparent;
        color: {c["danger"]};
        border: 1px solid {c["border_strong"]};
    }}
    QPushButton#stopButton:hover {{
        background-color: rgba(248, 81, 73, 0.1);
        border-color: {c["danger"]};
    }}
    QPushButton#stopButton:disabled {{ color: {c["muted"]}; }}

    /* ---- 布局部件 ---- */
    QSplitter::handle {{ background-color: {c["border"]}; }}
    QSplitter::handle:hover {{ background-color: {c["accent"]}; }}
    QStackedWidget {{ background: transparent; }}

    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
    QScrollBar::handle:vertical {{
        background-color: #3d444d;
        border-radius: 5px;
        min-height: 24px;
        margin: 2px 3px;
    }}
    QScrollBar::handle:vertical:hover {{ background-color: {c["muted"]}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

    QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 0; }}
    QScrollBar::handle:horizontal {{
        background-color: #3d444d;
        border-radius: 5px;
        min-width: 24px;
        margin: 3px 2px;
    }}
    QScrollBar::handle:horizontal:hover {{ background-color: {c["muted"]}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}
    """


def apply_theme(app):
    """为 QApplication 应用 Fusion 风格、GitHub Dark 调色板和样式表。"""
    app.setStyle("Fusion")

    c = GITHUB_DARK
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(c["canvas"]))
    palette.setColor(QPalette.WindowText, QColor(c["text"]))
    palette.setColor(QPalette.Base, QColor(c["canvas"]))
    palette.setColor(QPalette.AlternateBase, QColor(c["surface"]))
    palette.setColor(QPalette.Text, QColor(c["text"]))
    palette.setColor(QPalette.Button, QColor(c["surface"]))
    palette.setColor(QPalette.ButtonText, QColor(c["text"]))
    palette.setColor(QPalette.Highlight, QColor(c["accent_emphasis"]))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ToolTipBase, QColor(c["surface"]))
    palette.setColor(QPalette.ToolTipText, QColor(c["text"]))
    palette.setColor(QPalette.PlaceholderText, QColor(c["muted"]))
    palette.setColor(QPalette.Link, QColor(c["accent"]))
    app.setPalette(palette)

    app.setStyleSheet(build_stylesheet())
