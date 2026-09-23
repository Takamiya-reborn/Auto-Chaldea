import subprocess
import time

from auto_chaldea.utils.paths import ADB_PATH


def click(x, y, adb_path=ADB_PATH, device=None):
    cmd = [str(adb_path)]
    if device:
        cmd += ["-s", str(device)]
    cmd += ["shell", "input", "tap", str(int(x)), str(int(y))]
    result = subprocess.run(cmd, check=False)
    return result.returncode == 0


def double_click(x, y, interval=0.1, adb_path=ADB_PATH, device=None):
    """Click the same screen position twice with a short interval."""
    first_result = click(x, y, adb_path=adb_path, device=device)
    time.sleep(interval)
    second_result = click(x, y, adb_path=adb_path, device=device)
    return first_result and second_result


__all__ = ["click", "double_click"]
