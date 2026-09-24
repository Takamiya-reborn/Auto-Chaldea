from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class SettingsPanel(QWidget):
    """设置占位面板。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidePanel")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(0)

        title = QLabel("设置")
        title.setObjectName("panelHeader")
        layout.addWidget(title)
        layout.addStretch()

        hint = QLabel("设置功能开发中")
        hint.setObjectName("emptySubHint")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
        layout.addStretch()