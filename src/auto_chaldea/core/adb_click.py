import subprocess

from auto_chaldea.core.paths import ADB_PATH


def click(x, y, adb_path=ADB_PATH):
    result = subprocess.run(
        [str(adb_path), "shell", "input", "tap", str(int(x)), str(int(y))],
        check=False,
    )
    return result.returncode == 0


__all__ = ["click"]
