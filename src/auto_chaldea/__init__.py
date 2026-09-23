from auto_chaldea.utils.connector import connect_to_device
from auto_chaldea.utils.paths import (
    ADB_PATH,
    ASSETS_DIR,
    REPO_ROOT,
    TASK_DIR,
    TEMPLATE_DIR,
)
from auto_chaldea.core.task_executor import execute_step, execute_task
from auto_chaldea.core.task_repository import load_tasks


def main():
    """Start the Auto-Chaldea desktop application."""
    from auto_chaldea.ui import main as gui_main

    return gui_main()


__all__ = [
    "REPO_ROOT",
    "ASSETS_DIR",
    "ADB_PATH",
    "TEMPLATE_DIR",
    "TASK_DIR",
    "connect_to_device",
    "load_tasks",
    "execute_step",
    "execute_task",
    "main",
]
