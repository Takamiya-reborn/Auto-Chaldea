"""启动时的设备连接对话框：输入模拟器端口，连接成功后进入主界面。"""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
    QVBoxLayout,
)

from auto_chaldea.utils.connector import connect_to_device
from auto_chaldea.utils.paths import ADB_PATH
from auto_chaldea.ui.icons import device_icon
from auto_chaldea.ui.theme import GITHUB_DARK


class ConnectDialog(QDialog):
    """输入模拟器的 ADB 端口号并连接设备。"""

    connected = Signal(int)  # 参数：连接成功的端口号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("连接设备 - Auto-Chaldea")
        self.setFixedWidth(380)

        self._port = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 24)
        layout.setSpacing(10)

        icon_button = QToolButton(self)
        icon_button.setIcon(device_icon(GITHUB_DARK["accent"]))
        icon_button.setIconSize(QSize(44, 44))
        icon_button.setFixedSize(56, 56)
        icon_button.setEnabled(False)
        icon_button.setStyleSheet(
            "QToolButton { background: transparent; border: none; }"
        )
        layout.addWidget(icon_button, alignment=Qt.AlignCenter)

        title = QLabel("Auto-Chaldea", self)
        title.setObjectName("detailTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("输入模拟器的 ADB 端口号以连接设备", self)
        subtitle.setObjectName("detailMeta")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        layout.addSpacing(8)

        self._port_edit = QLineEdit(self)
        self._port_edit.setPlaceholderText("例如 5555")
        self._port_edit.setValidator(QIntValidator(1, 65535, self))
        self._port_edit.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._port_edit)

        self._status_label = QLabel(" ", self)
        self._status_label.setObjectName("statusLabel")
        self._status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._status_label)
        layout.addSpacing(6)

        buttons = QHBoxLayout()
        buttons.addStretch()

        quit_button = QPushButton("退出", self)
        quit_button.setCursor(Qt.PointingHandCursor)
        quit_button.clicked.connect(self.reject)
        buttons.addWidget(quit_button)

        self._connect_button = QPushButton("连接", self)
        self._connect_button.setObjectName("runButton")
        self._connect_button.setCursor(Qt.PointingHandCursor)
        self._connect_button.setDefault(True)
        self._connect_button.clicked.connect(self._try_connect)
        buttons.addWidget(self._connect_button)
        layout.addLayout(buttons)

    def port(self):
        """返回连接成功的端口号；未连接时为 None。"""
        return self._port

    def _try_connect(self):
        text = self._port_edit.text().strip()
        if not text:
            self._set_status("请输入端口号", GITHUB_DARK["attention"])
            return

        try:
            port = int(text)
        except ValueError:
            port = 0
        if not 1 <= port <= 65535:
            self._set_status(
                "端口必须是 1 到 65535 之间的整数", GITHUB_DARK["attention"]
            )
            return

        self._connect_button.setEnabled(False)
        self._port_edit.setEnabled(False)
        self._set_status("连接中…")
        QApplication.processEvents()  # 先刷新界面再执行阻塞的连接调用

        try:
            ok = connect_to_device(port, adb_path=ADB_PATH)
        except (
            Exception
        ) as error:  # noqa: BLE001 - 连接出错不允许卡死对话框，必须可以重试
            message = f"连接出错：{error}"
            self._set_status(message, GITHUB_DARK["danger"])
            self._port_edit.setFocus()
            return
        finally:
            self._connect_button.setEnabled(True)
            self._port_edit.setEnabled(True)

        if ok:
            self._port = port
            self.connected.emit(port)
            self.accept()
        else:
            message = "连接失败，请确认模拟器已启动并允许 ADB 调试"
            self._set_status(message, GITHUB_DARK["danger"])
            self._port_edit.setFocus()

    def _set_status(self, text, color=None):
        if color:
            self._status_label.setText(f'<span style="color:{color};">●</span> {text}')
        else:
            self._status_label.setText(text)
