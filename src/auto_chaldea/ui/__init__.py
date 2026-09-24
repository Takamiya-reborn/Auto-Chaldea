"""Auto-Chaldea 桌面界面（PySide6）。"""

import sys

from PySide6.QtWidgets import QApplication

from auto_chaldea.ui.connect_dialog import ConnectDialog
from auto_chaldea.ui.main_window import MainWindow
from auto_chaldea.ui.theme import apply_theme


def main():
    """启动图形界面：先连接设备，连接成功后进入主界面。"""
    app = QApplication(sys.argv)
    app.setApplicationName("Auto-Chaldea")
    apply_theme(app)

    reconnect_port = None
    while True:
        dialog = ConnectDialog(
            initial_port=reconnect_port,
            notice="模拟器已断开，请重新连接" if reconnect_port else None,
        )
        if dialog.exec() != ConnectDialog.Accepted:
            return 0

        window = MainWindow(device_port=dialog.port())
        disconnected_port = []

        def reopen_connection(port):
            disconnected_port.append(port)
            window.close()

        window.device_disconnected.connect(reopen_connection)
        window.show()
        app.exec()

        if not disconnected_port:
            return 0
        reconnect_port = disconnected_port[0]


__all__ = ["main", "MainWindow", "ConnectDialog"]
