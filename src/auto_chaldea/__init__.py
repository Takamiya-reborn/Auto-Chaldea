from auto_chaldea.core.task_executor import (
    execute_step,
    execute_task,
    expand_named_steps,
    resolve_steps,
)
from auto_chaldea.core.task_loader import load_tasks
from auto_chaldea.utils.adb_device import connect_to_device
from auto_chaldea.utils.paths import (
    ADB_PATH,
    ASSETS_DIR,
    REPO_ROOT,
    TASK_DIR,
    TEMPLATE_DIR,
)


def main():
    # 延迟导入：import auto_chaldea 本身不拉起 Qt
    from auto_chaldea.ui import main as gui_main

    return gui_main()


__all__ = [
    "ADB_PATH",
    "ASSETS_DIR",
    "REPO_ROOT",
    "TASK_DIR",
    "TEMPLATE_DIR",
    "connect_to_device",
    "execute_step",
    "execute_task",
    "expand_named_steps",
    "load_tasks",
    "main",
    "resolve_steps",
]
