# 后台任务执行线程，支持暂停、继续和停止

import threading
import time

from PySide6.QtCore import QThread, Signal

from auto_chaldea.core.graph_runner import execute_graph
from auto_chaldea.utils.adb_device import DeviceDisconnectedError, connect_to_device
from auto_chaldea.utils.paths import ADB_PATH, TEMPLATE_DIR


# 在独立线程中顺序执行任务步骤，通过 pause / resume / stop 从主线程
# 控制；所有信号排队投递到主线程，可安全更新界面。
# 周回轮数由注入的 store（RunStateStore）驱动：进入图前消耗一次开启
# 第 1 轮，图内连续出击命中继续消耗并开启后续轮；store 剩余为 0 时停
class TaskWorker(QThread):
    node_step = Signal(str, int, str)  # 参数：节点名、子步骤序号、状态
    skip_consumed = Signal()  # 一次"下一步"请求已被执行端消费（跳过生效）
    log_message = Signal(str)
    device_disconnected = Signal()
    finished_run = Signal(bool)  # 参数：任务是否完整跑完（未被停止）

    def __init__(self, task, port=None, store=None, parent=None):
        super().__init__(parent)
        self._task = task
        self._port = port
        self._store = store
        self._resume_event = threading.Event()
        self._resume_event.set()
        self._stop_requested = threading.Event()
        self._skip_requested = threading.Event()
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

    # 请求跳过当前正在等待识别的步骤
    def skip_step(self):
        if self.isRunning():
            self._skip_requested.set()

    # 跳过谓词：读取即消费，一次"下一步"只跳过一次等待，
    # 避免标志残留导致后续所有等待被连续跳过、级联终止任务
    def _consume_skip(self):
        if self._skip_requested.is_set():
            self._skip_requested.clear()
            # 消费即生效（路由推进或跳过子步骤），通知界面刷新状态栏
            self.skip_consumed.emit()
            return True
        return False

    @property
    def is_paused(self):
        return self._is_paused

    # ---- 内部辅助 ----

    # 暂停期间阻塞，直到恢复或请求停止
    def _wait_while_paused(self):
        while not self._resume_event.wait(0.1):
            if self._stop_requested.is_set():
                return

    # 可被暂停 / 停止 / 跳过打断的等待，用作 execute_step 的 sleep_fn
    def _interruptible_sleep(self, seconds):
        deadline = time.monotonic() + seconds
        while True:
            self._wait_while_paused()
            if self._stop_requested.is_set() or self._skip_requested.is_set():
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(0.1, remaining))

    # ---- 线程主体 ----

    # 节点图任务执行：while remaining > 0 驱动——每次进入图前消耗一次
    # 开启新一轮，图内连续出击命中可在同一轮图执行里继续开启后续轮；
    # 节点进度通过信号投递到界面
    def _run_graph(self, device):
        completed = True
        try:
            while not self._stop_requested.is_set() and self._store.remaining > 0:
                # 本轮开始：消耗一次剩余次数，run_started 随之发出
                self._store.decrement("remaining")
                self._skip_requested.clear()
                self._wait_while_paused()
                if self._stop_requested.is_set():
                    break

                # 子步骤进度回调：转发为界面信号，由详情页映射到表格行高亮
                def progress(node, position, status):
                    self.node_step.emit(node, position, status)

                result = execute_graph(
                    self._task,
                    adb_path=ADB_PATH,
                    template_dir=TEMPLATE_DIR,
                    device=device,
                    sleep_fn=self._interruptible_sleep,
                    should_stop=self._stop_requested.is_set,
                    should_skip=self._consume_skip,
                    store=self._store,
                    progress=progress,
                )
                if result is False:
                    self.log_message.emit(
                        f"第 {self._store.current_run} 轮执行未走完任务图"
                        f"（等待超时或步骤失败），任务终止。"
                    )
                    completed = False
                    break
            self.finished_run.emit(completed and not self._stop_requested.is_set())
        except DeviceDisconnectedError as error:
            self.log_message.emit(f"模拟器已断开：{error}")
            self.device_disconnected.emit()
            self.finished_run.emit(False)
        except Exception as error:  # noqa: BLE001 - 后台线程需要兜底并回报界面
            self.log_message.emit(f"任务异常终止：{error}")
            self.finished_run.emit(False)

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

            device = f"127.0.0.1:{self._port}" if self._port else None
            if not self._task.get("nodes"):
                self.log_message.emit("任务缺少 'nodes'，不是节点图任务，无法执行。")
                self.finished_run.emit(False)
                return
            self._run_graph(device)
        except DeviceDisconnectedError as error:
            self.log_message.emit(f"模拟器已断开：{error}")
            self.device_disconnected.emit()
            self.finished_run.emit(False)
        except Exception as error:  # noqa: BLE001 - 后台线程需要兜底并回报界面
            self.log_message.emit(f"任务异常终止：{error}")
            self.finished_run.emit(False)
