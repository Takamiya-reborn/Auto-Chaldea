"""右侧任务详情区域：描述、步骤表格和执行控制。"""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from auto_chaldea.ui.icons import (
    next_icon,
    pause_icon,
    play_icon,
    stop_icon,
    tasks_icon,
)
from auto_chaldea.ui.theme import GITHUB_DARK
from auto_chaldea.utils.adb_device import disconnect_device
from auto_chaldea.core.task_schema import valid_steps
from auto_chaldea.ui.task_table import TaskStepTable
from auto_chaldea.ui.worker import TaskWorker


class TaskDetailView(QWidget):
    """显示当前选中任务的描述；未选中时显示空状态提示。

    底部操作栏提供设备端口输入和执行 / 暂停 / 停止按钮。
    """

    device_disconnected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._task = None
        self._filename = ""
        self._worker = None
        self._execution_total = 0
        self._execution_current = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stack = QStackedWidget(self)
        self._stack.addWidget(self._build_empty_page())
        self._stack.addWidget(self._build_detail_page())
        layout.addWidget(self._stack, 1)

    # ---- 界面构建 ----

    def _build_empty_page(self):
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        icon_button = QToolButton(page)
        icon_button.setIcon(tasks_icon(GITHUB_DARK["border_strong"]))
        icon_button.setIconSize(QSize(56, 56))
        icon_button.setFixedSize(64, 64)
        icon_button.setEnabled(False)
        icon_button.setStyleSheet(
            "QToolButton { background: transparent; border: none; }"
        )
        layout.addWidget(icon_button, alignment=Qt.AlignCenter)

        hint = QLabel("请选择任务")
        hint.setObjectName("emptyHint")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        sub_hint = QLabel("从左侧任务列表中选择一个任务查看详情")
        sub_hint.setObjectName("emptySubHint")
        sub_hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub_hint)
        return page

    def _build_detail_page(self):
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        self._title_label = QLabel(page)
        self._title_label.setObjectName("detailTitle")
        layout.addWidget(self._title_label)

        self._meta_label = QLabel(page)
        self._meta_label.setObjectName("detailMeta")
        layout.addWidget(self._meta_label)

        self._desc_label = QLabel(page)
        self._desc_label.setObjectName("detailDesc")
        self._desc_label.setWordWrap(True)
        layout.addWidget(self._desc_label)

        self._table = TaskStepTable(page)
        layout.addWidget(self._table, 1)

        layout.addLayout(self._build_action_bar())
        return page

    def _build_action_bar(self):
        bar = QHBoxLayout()
        bar.setSpacing(8)

        port_label = QLabel("设备端口")
        port_label.setObjectName("portLabel")
        port_label.setVisible(False)
        bar.addWidget(port_label)

        self._port_edit = QLineEdit(self)
        self._port_edit.setPlaceholderText("例如 5555，留空则跳过连接")
        self._port_edit.setValidator(QIntValidator(1, 65535, self))
        self._port_edit.setFixedWidth(190)
        self._port_edit.setVisible(False)
        bar.addWidget(self._port_edit)

        self._status_label = QLabel("就绪", self)
        self._status_label.setObjectName("statusLabel")
        bar.addSpacing(10)
        bar.addWidget(self._status_label)
        bar.addStretch()

        self._run_button = QPushButton("执行", self)
        self._run_button.setObjectName("runButton")
        self._run_button.setIcon(play_icon("#ffffff"))
        self._run_button.setCursor(Qt.PointingHandCursor)
        self._run_button.clicked.connect(self._start_run)
        bar.addWidget(self._run_button)

        self._pause_button = QPushButton("暂停", self)
        self._pause_button.setCursor(Qt.PointingHandCursor)
        self._pause_button.setIcon(pause_icon(GITHUB_DARK["text"]))
        self._pause_button.clicked.connect(self._toggle_pause)
        bar.addWidget(self._pause_button)

        self._next_button = QPushButton("下一步", self)
        self._next_button.setIcon(next_icon(GITHUB_DARK["text"]))
        self._next_button.setCursor(Qt.PointingHandCursor)
        self._next_button.clicked.connect(self._skip_step)
        bar.addWidget(self._next_button)

        self._stop_button = QPushButton("停止", self)
        self._stop_button.setObjectName("stopButton")
        self._stop_button.setIcon(stop_icon(GITHUB_DARK["danger"]))
        self._stop_button.setCursor(Qt.PointingHandCursor)
        self._stop_button.clicked.connect(self._stop_run)
        bar.addWidget(self._stop_button)

        self._set_running_state(running=False)
        return bar

    # ---- 公开接口 ----

    def set_task(self, task, filename=""):
        """切换当前展示的任务；task 为 None 时回到空状态。"""
        self._task = task
        self._filename = filename
        self._execution_total = 0
        self._execution_current = 0

        if task is None:
            self._stack.setCurrentIndex(0)
            return

        name = task.get("task_name") or task.get("name") or "未命名任务"
        steps = valid_steps(task)
        self._title_label.setText(name)
        self._meta_label.setText(f"来源 {filename}.yaml · 共 {len(steps)} 个步骤")

        prerequisite = task.get("prerequisite") or task.get("description")
        self._desc_label.setText(f"执行要求：{prerequisite}" if prerequisite else "")
        self._desc_label.setVisible(bool(prerequisite))

        self._table.set_steps(steps)
        self._stack.setCurrentIndex(1)

    def shutdown(self):
        """窗口关闭前停止后台任务并断开 ADB 连接。"""
        if self._worker is not None:
            self._worker.stop()
            self._worker.wait()

        port = self._port_edit.text().strip()
        if port:
            try:
                disconnect_device(int(port))
            except ValueError:
                pass

    def set_device_port(self, port):
        """记录启动时已连接的设备端口并更新状态提示。"""
        self._port_edit.setText(str(port))
        self._set_status(f"已连接 127.0.0.1:{port}", GITHUB_DARK["success"])

    # ---- 任务执行 ----

    def _start_run(self):
        if self._worker is not None or self._task is None:
            return

        steps = valid_steps(self._task)
        if not steps:
            self._set_status("任务没有可执行的步骤", GITHUB_DARK["attention"])
            return

        execution_total, accepted = QInputDialog.getInt(
            self,
            "执行次数",
            "请输入执行次数：",
            1,
            1,
            9999,
            1,
        )
        if not accepted:
            return

        port = self._port_edit.text().strip()
        if port:
            try:
                port_value = int(port)
            except ValueError:
                port_value = 0
            if not 1 <= port_value <= 65535:
                self._set_status(
                    "设备端口必须是 1 到 65535 之间的整数",
                    GITHUB_DARK["attention"],
                )
                return

        self._table.clear_results()
        self._execution_total = execution_total
        self._execution_current = 1
        self._worker = TaskWorker(self._task, port or None, execution_total)
        self._worker.execution_started.connect(self._on_execution_started)
        self._worker.step_started.connect(self._on_step_started)
        self._worker.step_finished.connect(self._on_step_finished)
        self._worker.device_disconnected.connect(self._on_device_disconnected)
        self._worker.log_message.connect(
            lambda message: self._set_status(message, GITHUB_DARK["muted"])
        )
        self._worker.finished_run.connect(self._on_finished)
        self._worker.start()

        self._set_running_state(running=True)
        self._set_status(f"运行中 · 共 {len(steps)} 个步骤", GITHUB_DARK["accent"])

    def _toggle_pause(self):
        worker = self._worker
        if worker is None:
            return
        if worker.is_paused:
            worker.resume()
            self._pause_button.setText("暂停")
            self._pause_button.setIcon(pause_icon(GITHUB_DARK["text"]))
            self._set_status("运行中", GITHUB_DARK["accent"])
        else:
            worker.pause()
            self._pause_button.setText("继续")
            self._pause_button.setIcon(play_icon(GITHUB_DARK["text"]))
            self._set_status("已暂停", GITHUB_DARK["attention"])

    def _stop_run(self):
        if self._worker is None:
            return
        self._worker.stop()
        self._set_status("正在停止…", GITHUB_DARK["attention"])

    def _skip_step(self):
        if self._worker is None:
            return
        self._worker.skip_step()
        self._set_status("正在跳过当前步骤…", GITHUB_DARK["attention"])

    def _on_step_started(self, position):
        total = self._table.rowCount()
        self._table.selectRow(position)
        self._set_status(f"运行中 · 步骤 {position + 1}/{total}", GITHUB_DARK["accent"])

    def _on_execution_started(self, execution):
        self._execution_current = execution
        self._set_status("运行中", GITHUB_DARK["accent"])

    def _on_step_finished(self, position, result):
        if result == "timeout":
            self._table.set_result(position, "超时", GITHUB_DARK["timeout"])
        elif result == "skipped":
            self._table.set_result(position, "已跳过", GITHUB_DARK["attention"])
        elif result == "executed":
            self._table.set_result(position, "已执行", GITHUB_DARK["success"])
        else:
            self._table.set_result(position, "未匹配", GITHUB_DARK["danger"])

    def _on_device_disconnected(self):
        port = self._port_edit.text().strip()
        if port:
            self.device_disconnected.emit(int(port))

    def _on_finished(self, completed):
        if self._worker is not None:
            self._worker.wait()
            self._worker.deleteLater()
            self._worker = None

        self._set_running_state(running=False)
        if completed:
            self._set_status("已完成", GITHUB_DARK["success"])
        else:
            self._table.clear_results()
            self._set_status("已停止", GITHUB_DARK["danger"])

    # ---- 状态与按钮 ----

    def _set_running_state(self, running):
        self._run_button.setEnabled(not running)
        self._pause_button.setEnabled(running)
        self._next_button.setEnabled(running)
        self._stop_button.setEnabled(running)
        if running:
            self._pause_button.setText("暂停")
            self._pause_button.setIcon(pause_icon(GITHUB_DARK["text"]))
        self._port_edit.setEnabled(not running)

    def _set_status(self, text, color=None):
        if self._execution_total:
            text = (
                f"当前执行：{self._execution_current}/{self._execution_total} · {text}"
            )
        if color:
            self._status_label.setText(f'<span style="color:{color};">●</span> {text}')
        else:
            self._status_label.setText(text)
