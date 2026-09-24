"""VSCode 风格主窗口：活动栏 + 侧栏面板 + 任务详情。"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QSplitter,
    QStackedWidget,
    QWidget,
)

from auto_chaldea.ui.activity_bar import ActivityBar
from auto_chaldea.ui.device_monitor import DeviceMonitor
from auto_chaldea.ui.task_detail import TaskDetailView
from auto_chaldea.ui.task_panel import TaskPanel
from auto_chaldea.ui.settings_panel import SettingsPanel
from auto_chaldea.ui.templates_panel import TemplatesPanel

PANEL_TASKS = 0
PANEL_TEMPLATES = 1
PANEL_SETTINGS = 2


class MainWindow(QMainWindow):
    """组装三栏布局并协调面板切换与任务选择。"""

    device_disconnected = Signal(int)

    def __init__(self, device_port=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Auto-Chaldea")
        self.resize(1120, 720)

        self._panel_index = PANEL_TASKS
        self._panel_visible = True
        self._device_port = int(device_port) if device_port is not None else None
        self._disconnecting = False
        self._device_monitor = None

        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.activity_bar = ActivityBar(self)

        self._panel_stack = QStackedWidget(self)
        self.task_panel = TaskPanel(self)
        self.templates_panel = TemplatesPanel(self)
        self.settings_panel = SettingsPanel(self)
        self._panel_stack.addWidget(self.task_panel)
        self._panel_stack.addWidget(self.templates_panel)
        self._panel_stack.addWidget(self.settings_panel)

        self.detail_view = TaskDetailView(self)

        splitter = QSplitter(Qt.Horizontal, self)
        splitter.addWidget(self._panel_stack)
        splitter.addWidget(self.detail_view)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setSizes([300, 820])

        layout.addWidget(self.activity_bar)
        layout.addWidget(splitter, 1)

        self.activity_bar.set_checked(PANEL_TASKS)
        self.activity_bar.panel_requested.connect(self._show_panel)
        self.task_panel.task_selected.connect(self.detail_view.set_task)
        self.detail_view.device_disconnected.connect(self._handle_device_disconnected)

        if device_port is not None:
            self.detail_view.set_device_port(device_port)
            self._device_monitor = DeviceMonitor(device_port, parent=self)
            self._device_monitor.disconnected.connect(self._handle_device_disconnected)
            self._device_monitor.start()

    def _show_panel(self, index):
        """点击活动栏图标：切换面板；点击当前面板图标则收起侧栏。"""
        if self._panel_visible and index == self._panel_index:
            self._panel_stack.hide()
            self._panel_visible = False
            self.activity_bar.clear_checked()
            return

        self._panel_stack.show()
        self._panel_visible = True
        self._panel_index = index
        self._panel_stack.setCurrentIndex(index)
        self.activity_bar.set_checked(index)

    def _handle_device_disconnected(self, _port=None):
        """统一处理主动监控和任务执行中发现的设备断开。"""
        if self._disconnecting or self._device_port is None:
            return
        self._disconnecting = True
        self.device_disconnected.emit(self._device_port)

    def _stop_device_monitor(self):
        if self._device_monitor is None:
            return
        self._device_monitor.stop()
        self._device_monitor.wait()
        self._device_monitor = None

    def closeEvent(self, event):
        self._stop_device_monitor()
        self.detail_view.shutdown()
        super().closeEvent(event)
