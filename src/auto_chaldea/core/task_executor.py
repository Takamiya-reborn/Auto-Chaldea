"""Execution of task definitions against ADB and screen recognition."""

import time

from auto_chaldea.core.adb_click import click
from auto_chaldea.core.paths import ADB_PATH, TEMPLATE_DIR
from auto_chaldea.core.recognizer import find_all_matches
from auto_chaldea.core.task_repository import normalize_region, valid_steps


def execute_step(
    step,
    adb_path=ADB_PATH,
    template_dir=TEMPLATE_DIR,
    recognizer_fn=None,
    click_fn=None,
    sleep_fn=time.sleep,
):
    """Execute one task step by locating the target and clicking it if present."""
    if not isinstance(step, dict):
        raise ValueError(f"Step must be a dict, got {type(step).__name__}")

    recognizer = recognizer_fn or _build_recognizer(adb_path, template_dir)
    clicker = click_fn or _build_clicker(adb_path)

    template_path = step.get("template")
    if not template_path:
        return False

    index = int(step.get("index", step.get("indexi", 0)))
    region = normalize_region(step.get("region"))
    wait_after = float(step.get("wait_after", 0) or 0)

    print(
        f"[task] step template={template_path}, index={index}, "
        f"region={region}, wait_after={wait_after}"
    )
    matches = recognizer(template_path, region=region)
    result = False
    if len(matches) > index:
        target = matches[index]
        result = clicker(target["x"], target["y"])
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
    """Run every valid step in a task definition sequentially."""
    if not isinstance(task, dict):
        raise ValueError(f"Task must be a dict, got {type(task).__name__}")

    for step in valid_steps(task):
        execute_step(
            step,
            adb_path=adb_path,
            template_dir=template_dir,
            recognizer_fn=recognizer_fn,
            click_fn=click_fn,
            sleep_fn=sleep_fn,
        )
    return True


def _build_recognizer(adb_path, template_dir):
    return lambda template_path, region: find_all_matches(
        template_path,
        adb_path=adb_path,
        template_dir=template_dir,
        region=region,
    )


def _build_clicker(adb_path):
    return lambda x, y: click(x, y, adb_path=adb_path)
