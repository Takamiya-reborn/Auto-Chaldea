"""FGO 游戏风配色、调色板和外部 QSS 加载。"""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QProxyStyle, QStyle

from auto_chaldea.utils.paths import APP_QSS

WIDGET_ANIMATION_MS = 200  # 部件动画时长（任务树展开 / 收起等）

FGO = {
    # -- 深蓝基底 --
    "canvas": "#142438",  # 窗口画布兜底（实际背景由 QSS 渐变绘制）
    "surface": "#1a3049",  # 侧栏 / 活动栏 navy
    "overlay": "#23405c",  # 悬停高亮
    "selected": "#2c4160",  # 选中行 navy（金描边在 drawRow 里加）
    "border": "#0e1a28",
    "border_strong": "#8a744a",  # 哑金（空状态大图标）
    "text": "#e8e6df",  # 暖白
    "muted": "#9aa7b5",  # 钢青灰
    "accent": "#d4b06a",  # 金 accent
    "accent_emphasis": "#b8935a",
    "brand": "#d4b06a",  # 活动栏选中指示条
    "success": "#5cbf6e",
    "success_emphasis": "#3f9e56",
    "success_hover": "#4aab5f",
    "danger": "#e0564e",
    "attention": "#d4a13f",  # 琥珀金
    "timeout": "#7fa8c9",  # 冷蓝（超时 = 停滞）
    # -- 奶油面板 / 金 --
    "text_on_cream": "#2a3240",  # 奶油底上的深藏青文字
    "cream_top": "#f7f2e4",  # 列表卡片奶油渐变
    "cream_bottom": "#eee5cd",
    "cream_hover_top": "#fdfaf0",
    "cream_hover_bottom": "#f4ecd8",
    "cream_selected_top": "#fffdf4",
    "cream_selected_bottom": "#f6edd6",
    "gold": "#d4b06a",
    "gold_border": "#b89a5e",
    "gold_deep": "#8a6f3c",
    # -- 渐变端点（QSS 写字面值，QPainter 读这些键）--
    "run_top": "#e8c97e",  # 执行按钮金琥珀渐变
    "run_bottom": "#c99b3f",
    "stop_top": "#a63a3a",  # 停止按钮绯红渐变
    "stop_bottom": "#7c2430",
    "diamond_top": "#5b93d6",  # 菱形底板蓝宝石渐变
    "diamond_bottom": "#1f3f66",
    "diamond_dim": "#3a5578",  # 未选中暗版
    "guide": "#4d647f",  # 树引导线（钢青，弱于 border_strong 的金）
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
    """为 QApplication 应用 Fusion 风格、FGO 调色板和样式表。"""
    app.setStyle(_AnimationProxyStyle("fusion"))

    c = FGO
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(c["canvas"]))
    palette.setColor(QPalette.WindowText, QColor(c["text"]))
    palette.setColor(QPalette.Base, QColor(c["canvas"]))
    palette.setColor(QPalette.AlternateBase, QColor(c["surface"]))
    palette.setColor(QPalette.Text, QColor(c["text"]))
    palette.setColor(QPalette.Button, QColor(c["surface"]))
    palette.setColor(QPalette.ButtonText, QColor(c["text"]))
    # 选中高亮使用 navy 色，避免部件（branch 区域、选中态图标）出现突兀的蓝
    palette.setColor(QPalette.Highlight, QColor(c["selected"]))
    palette.setColor(QPalette.HighlightedText, QColor(c["text"]))
    palette.setColor(QPalette.ToolTipBase, QColor(c["canvas"]))
    palette.setColor(QPalette.ToolTipText, QColor(c["text"]))
    palette.setColor(QPalette.PlaceholderText, QColor(c["muted"]))
    palette.setColor(QPalette.Link, QColor(c["accent"]))
    app.setPalette(palette)

    app.setStyleSheet(build_stylesheet())
