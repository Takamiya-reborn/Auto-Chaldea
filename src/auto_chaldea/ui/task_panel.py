"""侧栏中的任务列表面板，加载 assets/task 下的 JSON 任务。"""

from PySide6.QtCore import QUrl, QSize, Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from auto_chaldea.core.paths import TASK_DIR
from auto_chaldea.core.task_repository import load_task_files, valid_steps
from auto_chaldea.ui.icons import refresh_icon
from auto_chaldea.ui.theme import GITHUB_DARK


class TaskPanel(QWidget):
    """展示所有可用的任务配置，选中后通知详情区域。"""

    task_selected = Signal(object, str)  # 参数：任务 dict、来源文件名（不含扩展名）

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidePanel")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(14, 10, 8, 10)
        title = QLabel("任务")
        title.setObjectName("panelHeader")
        header.addWidget(title)
        header.addStretch()

        refresh_button = QToolButton(self)
        refresh_button.setObjectName("panelHeaderButton")
        refresh_button.setToolTip("重新加载任务")
        refresh_button.setIcon(refresh_icon(GITHUB_DARK["muted"]))
        refresh_button.clicked.connect(self.refresh_tasks)
        header.addWidget(refresh_button)
        layout.addLayout(header)

        self._list = QListWidget(self)
        self._list.setSpacing(2)
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._show_context_menu)
        self._list.itemSelectionChanged.connect(self._emit_selection)
        layout.addWidget(self._list, 1)

        self.refresh_tasks()

    def refresh_tasks(self):
        """重新扫描任务目录并重建列表。"""
        self._list.blockSignals(True)
        self._list.clear()

        for filename, task in load_task_files():
            name = task.get("task_name") or task.get("name") or "未命名任务"
            step_count = len(valid_steps(task))
            item = QListWidgetItem(f"{name}\n{step_count} 个步骤 · {filename}")
            item.setSizeHint(QSize(0, 46))
            item.setToolTip(f"{name}（{filename}.json）")
            item.setData(Qt.UserRole, (task, filename))
            self._list.addItem(item)

        self._list.blockSignals(False)
        self._emit_selection()

    def _emit_selection(self):
        current = self._list.currentItem()
        if current is None:
            self.task_selected.emit(None, "")
            return
        task, filename = current.data(Qt.UserRole)
        self.task_selected.emit(task, filename)

    def _show_context_menu(self, pos):
        menu = QMenu(self._list)
        open_dir_action = menu.addAction("打开任务目录")
        if menu.exec(self._list.mapToGlobal(pos)) is open_dir_action:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(TASK_DIR)))
