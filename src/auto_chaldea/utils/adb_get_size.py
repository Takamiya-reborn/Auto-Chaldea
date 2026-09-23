import re
import subprocess

from auto_chaldea.utils.paths import ADB_PATH


def get_size(adb_path=ADB_PATH, device=None):
    """Return the connected Android device's screen size as ``(width, height)``."""
    cmd = [str(adb_path)]
    if device:
        cmd += ["-s", str(device)]
    cmd += ["shell", "wm", "size"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = result.stdout or ""
    match = re.search(r"Override size:\s*(\d+)x(\d+)", output)
    if match is None:
        match = re.search(r"Physical size:\s*(\d+)x(\d+)", output)
    if match is None:
        raise RuntimeError(f"Could not determine device screen size: {output!r}")
    return int(match.group(1)), int(match.group(2))


__all__ = ["get_size"]