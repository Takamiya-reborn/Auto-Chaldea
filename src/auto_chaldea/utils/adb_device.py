import re
import subprocess
import time

from auto_chaldea.utils.paths import ADB_PATH


class DeviceDisconnectedError(RuntimeError):
    """ADB 操作无法访问设备。"""


def connect_to_device(port, adb_path=ADB_PATH):
    """连接本机回环地址上的 Android 设备。"""
    address = _device_address(port)
    try:
        result = subprocess.run(
            [str(adb_path), "connect", address],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=15,
        )
    except OSError as error:
        print(f"Failed to run ADB executable {adb_path}: {error}")
        return False
    except subprocess.TimeoutExpired:
        print(f"ADB connection timed out: {address}")
        return False

    output = (result.stdout or result.stderr).strip()
    if output:
        print(output)
    if result.returncode != 0 or "connected to" not in output.lower():
        print(f"ADB connection failed: {address}")
        return False
    if not _device_is_online(address, adb_path):
        print(f"ADB connection failed: {address} (device offline)")
        return False
    print(f"ADB connection succeeded: {address}")
    return True


def disconnect_device(port, adb_path=ADB_PATH):
    """断开本机回环地址上的 Android 设备。"""
    address = _device_address(port)
    try:
        result = subprocess.run(
            [str(adb_path), "disconnect", address],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=15,
        )
    except OSError as error:
        print(f"Failed to run ADB executable {adb_path}: {error}")
        return False
    except subprocess.TimeoutExpired:
        print(f"ADB disconnection timed out: {address}")
        return False

    output = (result.stdout or result.stderr).strip()
    if output:
        print(output)
    if result.returncode != 0:
        print(f"ADB disconnection failed: {address}")
        return False
    print(f"ADB disconnected: {address}")
    return True


def click(x, y, adb_path=ADB_PATH, device=None):
    """点击设备屏幕坐标。"""
    command = _device_command(adb_path, device, "shell", "input", "tap", int(x), int(y))
    try:
        result = subprocess.run(command, check=False, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DeviceDisconnectedError("无法操作模拟器") from error
    if result.returncode != 0:
        raise DeviceDisconnectedError("模拟器已断开")
    return True


def double_click(x, y, interval=0.1, adb_path=ADB_PATH, device=None):
    """连续点击两次。"""
    first_result = click(x, y, adb_path=adb_path, device=device)
    time.sleep(interval)
    second_result = click(x, y, adb_path=adb_path, device=device)
    return first_result and second_result


def get_size(adb_path=ADB_PATH, device=None):
    """读取设备屏幕尺寸。"""
    command = _device_command(adb_path, device, "shell", "wm", "size")
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DeviceDisconnectedError("无法读取模拟器屏幕尺寸") from error
    if result.returncode != 0:
        raise DeviceDisconnectedError("模拟器已断开")

    match = re.search(r"Override size:\s*(\d+)x(\d+)", result.stdout or "")
    if match is None:
        match = re.search(r"Physical size:\s*(\d+)x(\d+)", result.stdout or "")
    if match is None:
        raise DeviceDisconnectedError("无法读取模拟器屏幕尺寸")
    return int(match.group(1)), int(match.group(2))


def _device_address(port):
    try:
        port = int(port)
    except (TypeError, ValueError) as error:
        raise ValueError("Port must be an integer between 1 and 65535.") from error
    if not 1 <= port <= 65535:
        raise ValueError("Port must be an integer between 1 and 65535.")
    return f"127.0.0.1:{port}"


def _device_command(adb_path, device, *arguments):
    command = [str(adb_path)]
    if device:
        command += ["-s", str(device)]
    return command + [str(argument) for argument in arguments]


def _device_is_online(address, adb_path=ADB_PATH, timeout=15):
    try:
        result = subprocess.run(
            [str(adb_path), "devices"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

    for line in (result.stdout or "").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == address:
            return parts[1] == "device"
    return False


__all__ = [
    "DeviceDisconnectedError",
    "click",
    "connect_to_device",
    "disconnect_device",
    "double_click",
    "get_size",
]
