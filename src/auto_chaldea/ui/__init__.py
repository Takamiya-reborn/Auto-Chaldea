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

    dialog = ConnectDialog()
    if dialog.exec() != ConnectDialog.Accepted:
        return 0

    window = MainWindow(device_port=dialog.port())
    window.show()

    return app.exec()


__all__ = ["main", "MainWindow", "ConnectDialog"]
