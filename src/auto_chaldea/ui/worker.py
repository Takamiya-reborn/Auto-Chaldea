"""后台任务执行线程，支持暂停、继续和停止。"""

import threading
import time

from PySide6.QtCore import QThread, Signal

from auto_chaldea.utils.adb_device import DeviceDisconnectedError, connect_to_device
from auto_chaldea.utils.paths import ADB_PATH, TEMPLATE_DIR
from auto_chaldea.core.task_executor import TIMEOUT_RESULT, execute_step
from auto_chaldea.core.task_schema import valid_steps


class TaskWorker(QThread):
    """在独立线程中顺序执行任务步骤。

    通过 :meth:`pause` / :meth:`resume` / :meth:`stop` 从主线程控制执行，
    所有信号都会排队投递到主线程，可安全地更新界面。
    """

    step_started = Signal(int)  # 参数：步骤序号（从 0 开始）
    step_finished = Signal(int, str)  # 参数：步骤序号、结果状态
    execution_started = Signal(int)  # 参数：执行次数（从 1 开始）
    log_message = Signal(str)
    device_disconnected = Signal()
    finished_run = Signal(bool)  # 参数：任务是否完整跑完（未被停止）

    def __init__(self, task, port=None, execution_total=1, parent=None):
        super().__init__(parent)
        self._task = task
        self._port = port
        self._execution_total = execution_total
        self._resume_event = threading.Event()
        self._resume_event.set()
        self._stop_requested = threading.Event()
        self._is_paused = False

    # ---- 线程控制 ----

    def pause(self):
        if self.isRunning() and not self._is_paused:
            self._is_paused = True
            self._resume_event.clear()

    def resume(self):
        if self.isRunning() and self._is_paused:
            self._is_paused = False
            self._resume_event.set()

    def stop(self):
        self._stop_requested.set()
        self._resume_event.set()  # 唤醒暂停中的线程以便退出

    @property
    def is_paused(self):
        return self._is_paused

    # ---- 内部辅助 ----

    def _wait_while_paused(self):
        """暂停期间阻塞，直到恢复或请求停止。"""
        while not self._resume_event.wait(0.1):
            if self._stop_requested.is_set():
                return

    def _interruptible_sleep(self, seconds):
        """可被暂停/停止打断的等待，用作 execute_step 的 sleep_fn。"""
        deadline = time.monotonic() + seconds
        while True:
            self._wait_while_paused()
            if self._stop_requested.is_set():
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(0.1, remaining))

    # ---- 线程主体 ----

    def run(self):
        try:
            if self._port:
                self.log_message.emit(f"正在连接设备 127.0.0.1:{self._port} …")
                if not connect_to_device(self._port, adb_path=ADB_PATH):
                    self.log_message.emit("模拟器已断开，请重新连接。")
                    self.device_disconnected.emit()
                    self.finished_run.emit(False)
                    return
                self.log_message.emit("设备连接成功。")

            steps = valid_steps(self._task)
            completed = True
            for execution in range(1, self._execution_total + 1):
                if self._stop_requested.is_set():
                    break
                self.execution_started.emit(execution)
                for position, step in enumerate(steps):
                    if self._stop_requested.is_set():
                        break
                    self._wait_while_paused()
                    if self._stop_requested.is_set():
                        break

                    self.step_started.emit(position)
                    clicked = execute_step(
                        step,
                        adb_path=ADB_PATH,
                        template_dir=TEMPLATE_DIR,
                        sleep_fn=self._interruptible_sleep,
                        device=f"127.0.0.1:{self._port}" if self._port else None,
                        should_stop=self._stop_requested.is_set,
                    )
                    if clicked == TIMEOUT_RESULT:
                        result = "timeout"
                    elif clicked:
                        result = "executed"
                    else:
                        result = "failed"
                    self.step_finished.emit(position, result)

                    if self._stop_requested.is_set():
                        break
                    if not clicked:
                        self.log_message.emit(
                            f"步骤 {position + 1} 未等到目标（超时或识别失败），任务终止。"
                        )
                        completed = False
                        break
                if not completed:
                    break

            self.finished_run.emit(completed and not self._stop_requested.is_set())
        except DeviceDisconnectedError as error:
            self.log_message.emit(f"模拟器已断开：{error}")
            self.device_disconnected.emit()
            self.finished_run.emit(False)
        except Exception as error:  # noqa: BLE001 - 后台线程需要兜底并回报界面
            self.log_message.emit(f"任务异常终止：{error}")
            self.finished_run.emit(False)
