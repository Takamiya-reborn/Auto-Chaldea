"""Execution of task definitions against ADB and screen recognition."""

import time

from auto_chaldea.utils.adb_click import click
from auto_chaldea.utils.adb_get_size import get_size
from auto_chaldea.utils.paths import ADB_PATH, TEMPLATE_DIR
from auto_chaldea.utils.recognizer import find_all_matches, find_all_matches_multi
from auto_chaldea.core.task_repository import normalize_region, valid_steps


def execute_step(
    step,
    adb_path=ADB_PATH,
    template_dir=TEMPLATE_DIR,
    recognizer_fn=None,
    multi_recognizer_fn=None,
    click_fn=None,
    sleep_fn=time.sleep,
    device=None,
):
    """Execute one task step by locating the target and clicking it if present."""
    if not isinstance(step, dict):
        raise ValueError(f"Step must be a dict, got {type(step).__name__}")

    recognizer = recognizer_fn or _build_recognizer(adb_path, template_dir, device)
    multi_recognizer = multi_recognizer_fn or _build_multi_recognizer(
        adb_path, template_dir, device
    )
    clicker = click_fn or _build_clicker(adb_path, device)

    template_path = step.get("template")
    if not template_path:
        return False

    # 除 template 外全部字段可省略：mode 默认 single，index 默认 0，region 默认全屏
    mode = str(step.get("mode") or "single").strip().lower()
    if mode not in ("single", "multi"):
        raise ValueError(f"Invalid mode value: {mode!r}, expected 'single' or 'multi'")

    region = normalize_region(step.get("region"))
    wait_value = step.get("wait_after")
    wait_after = 1.0 if wait_value in (None, "") else float(wait_value)
    if wait_after < 0:
        raise ValueError(f"Invalid wait_after value: {wait_after}, must be at least 0")

    if str(template_path).strip().casefold() == "center":
        width, height = get_size(adb_path=adb_path, device=device)
        print(
            f"[task] step template=Center, click=({width // 2}, {height // 2}), "
            f"wait_after={wait_after}"
        )
        result = clicker(width // 2, height // 2)
        if wait_after > 0:
            sleep_fn(wait_after)
        return result

    if mode == "multi":
        # multi 模式：template 为逗号分隔的多个模板，必须提供 count，取 TOP count 逐个点击
        count = step.get("count")
        if count is None:
            raise ValueError(
                f"Step with mode 'multi' requires a 'count' field, template={template_path}"
            )
        count = int(count)
        if count <= 0:
            raise ValueError(
                f"Invalid count value: {count}, must be a positive integer"
            )

        template_paths = [t.strip() for t in str(template_path).split(",") if t.strip()]
        if not template_paths:
            return False

        print(
            f"[task] step templates={template_paths}, mode=multi, count={count}, "
            f"region={region}, wait_after={wait_after}"
        )
        matches = multi_recognizer(template_paths, top_n=count, region=region)
        result = False
        for target in matches:
            if clicker(target["x"], target["y"]):
                result = True
        if wait_after > 0:
            sleep_fn(wait_after)
        return result

    # single 模式：单个模板，index 默认 0（第一个匹配）
    index = int(step.get("index") or 0)

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
    multi_recognizer_fn=None,
    click_fn=None,
    sleep_fn=time.sleep,
    device=None,
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
            multi_recognizer_fn=multi_recognizer_fn,
            click_fn=click_fn,
            sleep_fn=sleep_fn,
            device=device,
        )
    return True


def _build_recognizer(adb_path, template_dir, device=None):
    return lambda template_path, region: find_all_matches(
        template_path,
        adb_path=adb_path,
        template_dir=template_dir,
        region=region,
        device=device,
    )


def _build_multi_recognizer(adb_path, template_dir, device=None):
    return lambda template_paths, top_n, region: find_all_matches_multi(
        template_paths,
        top_n=top_n,
        adb_path=adb_path,
        template_dir=template_dir,
        region=region,
        device=device,
    )


def _build_clicker(adb_path, device=None):
    return lambda x, y: click(x, y, adb_path=adb_path, device=device)
