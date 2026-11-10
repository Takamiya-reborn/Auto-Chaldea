# FGO 配色、调色板与外部 QSS 加载

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QPushButton,
    QProxyStyle,
    QStyle,
    QToolButton,
)

from auto_chaldea.utils.paths import APP_QSS

WIDGET_ANIMATION_MS = 200  # 部件动画时长（任务树展开 / 收起等）

FGO = {
    # -- 浅蓝基底 --
    "canvas": "#7ba9ba",  # 窗口画布兜底（实际背景由 QSS 渐变绘制）
    "surface": "#1a3049",  # 侧栏 / 活动栏 navy
    "overlay": "#23405c",  # 悬停高亮
    "selected": "#2c4160",  # 选中行 navy（金描边在 drawRow 里加）
    "border": "#0e1a28",
    "border_strong": "#8a744a",  # 哑金（空状态大图标）
    "text": "#e8e6df",  # 暖白（tooltip / 选中高亮文字等深底场景）
    "text_dark": "#16324a",  # 浅蓝底上的深藏青文字
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
    "text_on_cream": "#2c3a57",  # 白金底上的藏青文字
    "gold_text": "#eedb5a",  # 蓝底上的金色文字 / 图标
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
    "diamond_top": "#ffffff",  # 菱形底板白玉渐变（与胶囊按钮同款）
    "diamond_bottom": "#e3ddc8",
    "diamond_dim": "#6b7d90",  # 未选中灰版
    "pill_gold": "#dac254",  # 胶囊按钮 / 菱形金边
    "guide": "#4d647f",  # 树引导线（钢青，弱于 border_strong 的金）
}


# 读取 assets/qss 下的全局样式表
def build_stylesheet():
    return APP_QSS.read_text(encoding="utf-8")


# 收紧 Qt 内置部件动画时长（任务树展开 / 收起等）
class _AnimationProxyStyle(QProxyStyle):
    def styleHint(self, hint, option=None, widget=None, return_data=None):
        if hint == QStyle.SH_Widget_Animation_Duration:
            return WIDGET_ANIMATION_MS
        return super().styleHint(hint, option, widget, return_data)


# 游戏内按钮统一的投影参数：四周均匀扩散的正投影（无偏移）
_SHADOW_BLUR = 10
_SHADOW_OFFSET_X = 0
_SHADOW_OFFSET_Y = 0
_SHADOW_COLOR = QColor(18, 34, 54, 130)


# 应用级事件过滤器：任何按钮首次显示时自动挂上投影特效。
# QSS 不支持 box-shadow，只能用 QGraphicsDropShadowEffect 逐个部件实现；
# 走事件过滤器而不是逐处创建按钮时手挂，保证对话框等后建的按钮也生效。
class _ButtonShadowInstaller(QObject):
    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Show, QEvent.ShowToParent) and obj.isWidgetType():
            if isinstance(obj, (QPushButton, QToolButton)) and obj.graphicsEffect() is None:
                effect = QGraphicsDropShadowEffect(obj)
                effect.setBlurRadius(_SHADOW_BLUR)
                effect.setOffset(_SHADOW_OFFSET_X, _SHADOW_OFFSET_Y)
                effect.setColor(_SHADOW_COLOR)
                obj.setGraphicsEffect(effect)
        return False


# 应用 Fusion 风格 + FGO 调色板 + 全局样式表
def apply_theme(app):
    app.setStyle(_AnimationProxyStyle("fusion"))

    # 给每个按钮挂 FGO 风投影（过滤器存到 app 属性上防止被回收）
    shadow_installer = _ButtonShadowInstaller(app)
    app.setProperty("buttonShadowInstaller", shadow_installer)
    app.installEventFilter(shadow_installer)

    c = FGO
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(c["canvas"]))
    palette.setColor(QPalette.WindowText, QColor(c["gold_text"]))
    palette.setColor(QPalette.Base, QColor("#fffdf4"))
    palette.setColor(QPalette.AlternateBase, QColor("#f0e9d8"))
    palette.setColor(QPalette.Text, QColor(c["text_on_cream"]))
    palette.setColor(QPalette.Button, QColor("#e3ddc8"))
    palette.setColor(QPalette.ButtonText, QColor(c["text_on_cream"]))
    # 选中高亮使用 navy 色，避免部件（branch 区域、选中态图标）出现突兀的蓝
    palette.setColor(QPalette.Highlight, QColor("#2c4160"))
    palette.setColor(QPalette.HighlightedText, QColor("#eedb5a"))
    palette.setColor(QPalette.ToolTipBase, QColor("#10233a"))
    palette.setColor(QPalette.ToolTipText, QColor("#eedb5a"))
    palette.setColor(QPalette.PlaceholderText, QColor("#b3a254"))
    palette.setColor(QPalette.Link, QColor(c["gold_deep"]))
    app.setPalette(palette)

    app.setStyleSheet(build_stylesheet())
