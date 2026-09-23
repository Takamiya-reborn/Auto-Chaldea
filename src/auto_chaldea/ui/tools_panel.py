"""侧栏的辅助面板：模板库和设置占位。"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from auto_chaldea.utils.paths import TEMPLATE_DIR


class TemplatesPanel(QWidget):
    """列出 assets/template 中可用的图像模板。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidePanel")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(14, 10, 14, 10)
        title = QLabel("模板库")
        title.setObjectName("panelHeader")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        self._list = QListWidget(self)
        self._list.setSpacing(2)
        self._list.setIconSize(QSize(36, 36))
        layout.addWidget(self._list, 1)

        self.refresh_templates()

    def refresh_templates(self):
        self._list.clear()
        if not TEMPLATE_DIR.exists():
            return
        for path in sorted(TEMPLATE_DIR.rglob("*.png")):
            image = QImage(str(path))
            size_text = (
                f"{image.width()}×{image.height()}"
                if not image.isNull()
                else "未知尺寸"
            )
            item = QListWidgetItem(f"{path.stem}\n{size_text}")
            if not image.isNull():
                from PySide6.QtGui import QIcon

                item.setIcon(QIcon(str(path)))
            item.setSizeHint(QSize(0, 48))
            item.setToolTip(str(path))
            self._list.addItem(item)


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
