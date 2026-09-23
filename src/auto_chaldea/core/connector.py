import subprocess

from auto_chaldea.core.paths import ADB_PATH


def connect_to_device(port, adb_path=ADB_PATH):
    """Connect to an Android device through the local loopback address.

    Args:
        port: Device port number in the range 1 to 65535.
        adb_path: Path to the ADB executable.

    Returns:
        True if the connection succeeds; otherwise False.
    """
    try:
        port = int(port)
    except (TypeError, ValueError) as error:
        raise ValueError("Port must be an integer between 1 and 65535.") from error

    if not 1 <= port <= 65535:
        raise ValueError("Port must be an integer between 1 and 65535.")

    address = f"127.0.0.1:{port}"
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

    # adb connect 在连接失败时也可能返回退出码 0（例如端口上没有进程监听），
    # 因此必须根据输出内容判断是否真正建立了连接。
    if result.returncode != 0 or "connected to" not in output.lower():
        print(f"ADB connection failed: {address}")
        return False

    if not _device_is_online(address, adb_path):
        print(f"ADB connection failed: {address} (device offline)")
        return False

    print(f"ADB connection succeeded: {address}")
    return True


def disconnect_device(port, adb_path=ADB_PATH):
    """Disconnect a previously connected Android device.

    Args:
        port: Device port number in the range 1 to 65535.
        adb_path: Path to the ADB executable.

    Returns:
        True if the disconnection succeeds; otherwise False.
    """
    try:
        port = int(port)
    except (TypeError, ValueError) as error:
        raise ValueError("Port must be an integer between 1 and 65535.") from error

    if not 1 <= port <= 65535:
        raise ValueError("Port must be an integer between 1 and 65535.")

    address = f"127.0.0.1:{port}"
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


def _device_is_online(address, adb_path=ADB_PATH):
    """Check that the device appears in ``adb devices`` with online state."""
    try:
        result = subprocess.run(
            [str(adb_path), "devices"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

    for line in (result.stdout or "").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == address:
            return parts[1] == "device"
    return False
