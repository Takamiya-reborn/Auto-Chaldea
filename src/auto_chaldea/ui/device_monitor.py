"""后台监控已连接设备的在线状态。"""

import threading
import subprocess

from PySide6.QtCore import QThread, Signal

from auto_chaldea.utils.paths import ADB_PATH


class DeviceMonitor(QThread):
    """在后台监听设备是否从 ADB 在线列表中消失。"""

    disconnected = Signal()

    def __init__(self, port, adb_path=ADB_PATH, parent=None):
        super().__init__(parent)
        self._address = f"127.0.0.1:{int(port)}"
        self._adb_path = adb_path
        self._stop_requested = threading.Event()
        self._process = None
        self._process_lock = threading.Lock()

    def stop(self):
        """请求监控线程退出。"""
        self._stop_requested.set()
        with self._process_lock:
            process = self._process
        if process is not None and process.poll() is None:
            process.terminate()

    def run(self):
        command = [str(self._adb_path), "track-devices"]
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            if not self._stop_requested.is_set():
                self.disconnected.emit()
            return

        with self._process_lock:
            self._process = process

        device_online = False
        try:
            while not self._stop_requested.is_set():
                size_data = process.stdout.read(4)
                if len(size_data) < 4:
                    break

                try:
                    payload_size = int(size_data.decode("ascii"), 16)
                except ValueError:
                    break

                payload = process.stdout.read(payload_size)
                if len(payload) < payload_size:
                    break

                current_online = self._payload_has_device(payload)
                if device_online and not current_online:
                    self.disconnected.emit()
                    return
                device_online = current_online

        finally:
            with self._process_lock:
                self._process = None
            if process.poll() is None:
                process.terminate()
                process.wait()

        if device_online and not self._stop_requested.is_set():
            self.disconnected.emit()

    def _payload_has_device(self, payload):
        """判断设备状态更新中是否包含目标设备。"""
        text = payload.decode("utf-8", errors="replace")
        for line in text.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == self._address:
                return parts[1] == "device"
        return False


__all__ = ["DeviceMonitor"]
