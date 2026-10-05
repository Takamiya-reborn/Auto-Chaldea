import subprocess
import sys


def hidden_window_kwargs():
    """Return subprocess options that prevent console windows on Windows."""
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


__all__ = ["hidden_window_kwargs"]
