"""FGO 风格的最左侧活动栏：菱形底板图标 + 金色选中指示。"""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QToolButton, QVBoxLayout, QWidget

from auto_chaldea.ui.icons import diamond_icon

_GLYPHS = ["fa6s.list-ul", "fa6s.images", "fa6s.gear"]
_DISCONNECT_GLYPH = "fa6s.plug-circle-xmark"
_DIAMOND_SIZE = 34  # 菱形底板边长（按钮高 46，留少量呼吸感）


class ActivityBar(QWidget):
    """窄图标栏，点击图标切换侧栏面板，再次点击收起侧栏。"""

    panel_requested = Signal(int)  # 参数：面板序号
    disconnect_requested = Signal()  # 手动断开当前设备

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("activityBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(52)

        self._buttons = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(6)

        tooltips = ["任务", "模板库"]
        for index, tooltip in enumerate(tooltips):
            button = self._create_button(index, tooltip)
            self._buttons.append(button)
            layout.addWidget(button)

        layout.addStretch()
        layout.addWidget(self._create_disconnect_button())

        # 设置固定在最底部，但面板序号仍与 MainWindow 的 PANEL_SETTINGS 对应
        settings_button = self._create_button(2, "设置")
        self._buttons.append(settings_button)
        layout.addWidget(settings_button)

    def _apply_icon(self, button, glyph, lit):
        button.setIcon(
            diamond_icon(glyph, size=_DIAMOND_SIZE, lit=lit, dpr=button.devicePixelRatioF())
        )

    def _create_button(self, index, tooltip):
        button = QToolButton(self)
        button.setObjectName("activityButton")
        button.setToolTip(tooltip)
        self._apply_icon(button, _GLYPHS[index], lit=False)
        button.setIconSize(QSize(_DIAMOND_SIZE, _DIAMOND_SIZE))
        button.setCheckable(True)
        button.setAutoExclusive(True)
        button.setCursor(Qt.PointingHandCursor)
        button.setFixedHeight(46)
        button.clicked.connect(
            lambda _checked=False, idx=index: self.panel_requested.emit(idx)
        )
        return button

    def _create_disconnect_button(self):
        button = QToolButton(self)
        button.setObjectName("activityButton")
        button.setToolTip("断开设备")
        self._apply_icon(button, _DISCONNECT_GLYPH, lit=False)
        button.setIconSize(QSize(_DIAMOND_SIZE, _DIAMOND_SIZE))
        button.setCursor(Qt.PointingHandCursor)
        button.setFixedHeight(46)
        button.clicked.connect(lambda: self.disconnect_requested.emit())
        return button

    def set_checked(self, index):
        """高亮指定面板的图标。"""
        for i, button in enumerate(self._buttons):
            button.setChecked(i == index)
        self._update_icons(index)

    def clear_checked(self):
        """取消所有图标的高亮（侧栏被收起时）。"""
        for button in self._buttons:
            button.setChecked(False)
        self._update_icons(-1)

    def _update_icons(self, active_index):
        for i, button in enumerate(self._buttons):
            self._apply_icon(button, _GLYPHS[i], lit=(i == active_index))
