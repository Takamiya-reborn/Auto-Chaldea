"""GitHub Dark 配色、调色板和外部 QSS 加载。"""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QProxyStyle, QStyle

from auto_chaldea.utils.paths import APP_QSS

WIDGET_ANIMATION_MS = 200  # 部件动画时长（任务树展开 / 收起等）

GITHUB_DARK = {
    "canvas": "#0d1117",  # 主背景（编辑区）
    "surface": "#161b22",  # 侧栏 / 活动栏
    "overlay": "#1c2128",  # 悬停高亮
    "selected": "#2d333b",  # 选中行（灰度色，避免过于突兀）
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
    "timeout": "#d2a8ff",
}


def build_stylesheet():
    """读取 assets/qss 下的全局样式表。"""
    return APP_QSS.read_text(encoding="utf-8")


class _AnimationProxyStyle(QProxyStyle):
    """收紧 Qt 内置部件动画时长，例如任务树的展开 / 收起动画。"""

    def styleHint(self, hint, option=None, widget=None, return_data=None):
        if hint == QStyle.SH_Widget_Animation_Duration:
            return WIDGET_ANIMATION_MS
        return super().styleHint(hint, option, widget, return_data)


def apply_theme(app):
    """为 QApplication 应用 Fusion 风格、GitHub Dark 调色板和样式表。"""
    app.setStyle(_AnimationProxyStyle("fusion"))

    c = GITHUB_DARK
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(c["canvas"]))
    palette.setColor(QPalette.WindowText, QColor(c["text"]))
    palette.setColor(QPalette.Base, QColor(c["canvas"]))
    palette.setColor(QPalette.AlternateBase, QColor(c["surface"]))
    palette.setColor(QPalette.Text, QColor(c["text"]))
    palette.setColor(QPalette.Button, QColor(c["surface"]))
    palette.setColor(QPalette.ButtonText, QColor(c["text"]))
    # 选中高亮统一使用灰度色，避免部件（branch 区域、选中态图标）出现突兀的蓝色
    palette.setColor(QPalette.Highlight, QColor(c["selected"]))
    palette.setColor(QPalette.HighlightedText, QColor(c["text"]))
    palette.setColor(QPalette.ToolTipBase, QColor(c["surface"]))
    palette.setColor(QPalette.ToolTipText, QColor(c["text"]))
    palette.setColor(QPalette.PlaceholderText, QColor(c["muted"]))
    palette.setColor(QPalette.Link, QColor(c["accent"]))
    app.setPalette(palette)

    app.setStyleSheet(build_stylesheet())
