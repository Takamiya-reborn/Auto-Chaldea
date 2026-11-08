import subprocess
import sys


# Windows 下防止 subprocess 弹出控制台窗口
def hidden_window_kwargs():
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


__all__ = ["hidden_window_kwargs"]
