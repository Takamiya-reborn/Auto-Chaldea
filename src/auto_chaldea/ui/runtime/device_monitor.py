# 后台监控已连接设备的在线状态

import subprocess
import threading
import time

from PySide6.QtCore import QThread, Signal

from auto_chaldea.utils.paths import ADB_PATH
from auto_chaldea.utils.process import hidden_window_kwargs

# track-devices 流异常中断后的离线确认次数与间隔：
# adb 重启 / 管道抖动会导致流断开但设备实际在线，直接报断连会关掉
# 正在执行的任务窗口（历史 bug），确认期间设备恢复则重建流继续监控
OFFLINE_CONFIRM_ATTEMPTS = 3
OFFLINE_CONFIRM_INTERVAL = 2.0


# 后台监听设备是否从 ADB 在线列表中消失
class DeviceMonitor(QThread):
    disconnected = Signal()

    def __init__(self, port, adb_path=ADB_PATH, parent=None):
        super().__init__(parent)
        self._address = f"127.0.0.1:{int(port)}"
        self._adb_path = adb_path
        self._stop_requested = threading.Event()
        self._process = None
        self._process_lock = threading.Lock()

    # 请求监控线程退出
    def stop(self):
        self._stop_requested.set()
        with self._process_lock:
            process = self._process
        if process is not None and process.poll() is None:
            process.terminate()

    def run(self):
        while not self._stop_requested.is_set():
            process = self._start_track_stream()
            if process is None:
                # adb 无法启动：确认设备确实离线后才上报
                if self._confirm_offline():
                    self._report_disconnect("adb track-devices 启动失败")
                return

            device_online = False
            stream_broken = False
            try:
                while not self._stop_requested.is_set():
                    size_data = process.stdout.read(4)
                    if len(size_data) < 4:
                        stream_broken = True
                        break

                    try:
                        payload_size = int(size_data.decode("ascii"), 16)
                    except ValueError:
                        stream_broken = True
                        break

                    payload = process.stdout.read(payload_size)
                    if len(payload) < payload_size:
                        stream_broken = True
                        break

                    current_online = self._payload_has_device(payload)
                    if device_online and not current_online:
                        # 设备从在线列表消失：真断开，立即上报
                        self._report_disconnect("设备从 adb 在线列表消失")
                        return
                    device_online = current_online
            finally:
                with self._process_lock:
                    self._process = None
                if process.poll() is None:
                    process.terminate()
                    process.wait()

            if not stream_broken:
                return  # stop 请求退出

            # 流异常中断：设备可能仍在线，确认离线后才上报，否则重建流
            if self._confirm_offline():
                self._report_disconnect("track-devices 流中断且确认设备离线")
                return

    # 启动 track-devices 长流；失败返回 None
    def _start_track_stream(self):
        try:
            process = subprocess.Popen(
                [str(self._adb_path), "track-devices"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                **hidden_window_kwargs(),
            )
        except OSError:
            return None
        with self._process_lock:
            self._process = process
        return process

    # 流中断后的离线确认：轮询 adb devices，设备仍在线返回 False；
    # 连续确认失败（命令失败或设备不在列表）返回 True。可被 stop 打断
    def _confirm_offline(self):
        for attempt in range(OFFLINE_CONFIRM_ATTEMPTS):
            if self._stop_requested.is_set():
                return False
            if attempt:
                self._sleep_interruptible(OFFLINE_CONFIRM_INTERVAL)
                if self._stop_requested.is_set():
                    return False
            try:
                result = subprocess.run(
                    [str(self._adb_path), "devices"],
                    capture_output=True,
                    timeout=10,
                    **hidden_window_kwargs(),
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
            if result.returncode == 0 and self._payload_has_device(result.stdout):
                return False
        return True

    # 可被 stop 打断的等待
    def _sleep_interruptible(self, seconds):
        deadline = time.monotonic() + seconds
        while not self._stop_requested.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(0.2, remaining))

    # 统一的断连上报入口：打印来源便于排查，再发信号
    def _report_disconnect(self, reason):
        print(f"[device] {self._address} 判定断开：{reason}")
        self.disconnected.emit()

    # 判断设备状态更新中是否包含目标设备
    def _payload_has_device(self, payload):
        text = payload.decode("utf-8", errors="replace")
        for line in text.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == self._address:
                return parts[1] == "device"
        return False


__all__ = ["DeviceMonitor"]
