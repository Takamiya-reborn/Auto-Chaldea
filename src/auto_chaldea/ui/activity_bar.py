"""VSCode 风格的最左侧活动栏：工具/项目入口。"""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QToolButton, QVBoxLayout, QWidget

from auto_chaldea.ui.icons import settings_icon, tasks_icon, templates_icon
from auto_chaldea.ui.theme import GITHUB_DARK


class ActivityBar(QWidget):
    """窄图标栏，点击图标切换侧栏面板，再次点击收起侧栏。"""

    panel_requested = Signal(int)  # 参数：面板序号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("activityBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(48)

        self._icon_factories = [tasks_icon, templates_icon, settings_icon]
        self._buttons = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignTop)

        tooltips = ["任务", "模板库", "设置"]
        for index, tooltip in enumerate(tooltips):
            button = self._create_button(index, tooltip)
            self._buttons.append(button)
            layout.addWidget(button)

    def _create_button(self, index, tooltip):
        button = QToolButton(self)
        button.setObjectName("activityButton")
        button.setToolTip(tooltip)
        button.setIcon(self._icon_factories[index](GITHUB_DARK["muted"]))
        button.setIconSize(QSize(24, 24))
        button.setCheckable(True)
        button.setAutoExclusive(True)
        button.setCursor(Qt.PointingHandCursor)
        button.setFixedHeight(44)
        button.clicked.connect(
            lambda _checked=False, idx=index: self.panel_requested.emit(idx)
        )
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
            color = (
                GITHUB_DARK["text"] if i == active_index else GITHUB_DARK["muted"]
            )
            button.setIcon(self._icon_factories[i](color))
