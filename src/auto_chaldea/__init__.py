import json
import time
from pathlib import Path

from auto_chaldea.core.connector import connect_to_device
from auto_chaldea.core.paths import (
    ADB_PATH,
    ASSETS_DIR,
    REPO_ROOT,
    TASK_DIR,
    TEMPLATE_DIR,
)


def _normalize_region(region):
    """Normalize task-region input into a 4-item tuple when possible."""
    if region in (None, "", [], (), {}):
        return None

    if isinstance(region, str):
        region_text = region.strip()
        if not region_text:
            return None
        parts = [item.strip() for item in region_text.split(",")]
        if len(parts) != 4:
            raise ValueError(f"Invalid region value: {region!r}")
        return tuple(int(value) for value in parts)

    if isinstance(region, (list, tuple)) and len(region) == 4:
        return tuple(int(value) for value in region)

    return region


def load_tasks(task_dir=None):
    """Load all task JSON files from the configured task directory."""
    base_dir = Path(task_dir) if task_dir is not None else TASK_DIR
    if not base_dir.exists():
        return []

    tasks = []
    for json_path in sorted(base_dir.glob("*.json")):
        with json_path.open("r", encoding="utf-8") as file:
            task = json.load(file)
        if isinstance(task, dict):
            tasks.append(task)
    return tasks


def execute_step(
    step,
    adb_path=ADB_PATH,
    template_dir=TEMPLATE_DIR,
    recognizer_fn=None,
    click_fn=None,
    sleep_fn=time.sleep,
):
    """Execute one task step by locating the target and clicking it if present."""
    if recognizer_fn is None:
        from auto_chaldea.core.recognizer import find_all_matches

        def recognizer_fn(template_path, region):
            return find_all_matches(
                template_path,
                adb_path=adb_path,
                template_dir=template_dir,
                region=region,
            )

    if click_fn is None:
        from auto_chaldea.core.adb_click import click

        def click_fn(x, y):
            return click(x, y, adb_path=adb_path)

    if not isinstance(step, dict):
        raise ValueError(f"Step must be a dict, got {type(step).__name__}")

    template_path = step.get("template")
    if not template_path:
        return False

    index = step.get("index", step.get("indexi", 0))
    region = _normalize_region(step.get("region"))
    wait_after = float(step.get("wait_after", 0) or 0)

    print(
        f"[task] step template={template_path}, index={index}, region={region}, wait_after={wait_after}"
    )
    matches = recognizer_fn(template_path, region=region)
    result = False
    target_index = int(index)
    if len(matches) > target_index:
        target = matches[target_index]
        result = click_fn(target["x"], target["y"])
    if wait_after > 0:
        sleep_fn(wait_after)
    return result


def execute_task(
    task,
    adb_path=ADB_PATH,
    template_dir=TEMPLATE_DIR,
    recognizer_fn=None,
    click_fn=None,
    sleep_fn=time.sleep,
):
    """Run every step in a task definition sequentially."""
    if not isinstance(task, dict):
        raise ValueError(f"Task must be a dict, got {type(task).__name__}")

    steps = task.get("steps", [])
    for step in steps:
        if not isinstance(step, dict):
            continue
        execute_step(
            step,
            adb_path=adb_path,
            template_dir=template_dir,
            recognizer_fn=recognizer_fn,
            click_fn=click_fn,
            sleep_fn=sleep_fn,
        )

    return True


def _prompt_choose_task(tasks):
    """Ask the user to pick a task from the available list."""
    if not tasks:
        print("No JSON tasks found in assets/task.")
        return None

    print("Available tasks:")
    for idx, task in enumerate(tasks, start=1):
        task_name = task.get("task_name") or task.get("name") or f"task_{idx}"
        print(f"  {idx}. {task_name}")

    while True:
        choice = input("Please choose a task number: ").strip()
        if not choice:
            print("Please enter a valid task number.")
            continue
        if not choice.isdigit():
            print("Please enter a number.")
            continue

        selected = int(choice)
        if 1 <= selected <= len(tasks):
            return tasks[selected - 1]
        print(f"Please choose a number between 1 and {len(tasks)}.")


def main():
    """Start the interactive device connection and task-execution flow."""
    while True:
        port = input("Please enter the device port: ").strip()
        try:
            if connect_to_device(port, adb_path=ADB_PATH):
                break
        except ValueError as error:
            print(error)

    tasks = load_tasks()
    chosen_task = _prompt_choose_task(tasks)
    if chosen_task is None:
        return

    print(
        f"Running task: {chosen_task.get('task_name') or chosen_task.get('name', 'Untitled task')}"
    )
    execute_task(chosen_task, adb_path=ADB_PATH, template_dir=TEMPLATE_DIR)
    print("Task finished.")


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
