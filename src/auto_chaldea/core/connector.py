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
    except FileNotFoundError:
        print(f"ADB executable not found: {adb_path}")
        return False
    except subprocess.TimeoutExpired:
        print(f"ADB connection timed out: {address}")
        return False

    output = (result.stdout or result.stderr).strip()
    if output:
        print(output)
    if result.returncode == 0:
        print(f"ADB connection succeeded: {address}")
        return True

    print(f"ADB connection failed: {address}")
    return False
