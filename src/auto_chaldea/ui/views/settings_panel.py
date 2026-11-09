from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from auto_chaldea.ui.widgets.outlined_label import OutlinedLabel


# 设置占位面板
class SettingsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidePanel")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(0)

        title = OutlinedLabel("设置")
        title.setObjectName("panelHeader")
        layout.addWidget(title)
        layout.addStretch()

        hint = OutlinedLabel("设置功能开发中")
        hint.setObjectName("emptySubHint")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
        layout.addStretch()
