"""通过 ADB 执行任务步骤。"""

import time

from auto_chaldea.utils.adb_device import click, get_size
from auto_chaldea.utils.paths import ADB_PATH, TEMPLATE_DIR
from auto_chaldea.utils.recognizer import find_all_matches, find_all_matches_multi
from auto_chaldea.core.task_schema import normalize_region, valid_steps

# 识别不到目标时的默认重试间隔（秒），也是退避的起始间隔
DEFAULT_RETRY_INTERVAL = 0.2
# 退避间隔的封顶值（秒）：间隔翻倍增长到该值后不再增长，之后一直以该值重试
DEFAULT_MAX_RETRY_INTERVAL = 3.0
# 每次识别失败后间隔的放大倍数
RETRY_BACKOFF_FACTOR = 2.0
# 点击成功后、推进到下一步前的默认等待间隔（秒）
DEFAULT_STEP_INTERVAL = 1.0
# 超时视为已处理，继续下一步。
TIMEOUT_RESULT = "timeout"


def _step_float(step, key, default):
    """读取步骤中的数值字段。"""
    value = step.get(key)
    return default if value in (None, "") else float(value)


def _recognize_with_retry(
    recognize,
    describe,
    retry_interval,
    max_retry_interval,
    timeout,
    sleep_fn,
    should_stop=None,
):
    """反复识别直到出现匹配；超时返回 None，外部请求停止时返回空列表。

    recognize 为无参回调，返回匹配列表（非空视为匹配成功）；
    识别失败时重试间隔从 retry_interval 起按倍数退避，封顶于
    max_retry_interval 后不再增长；should_stop 为可选回调，每次
    重试前调用，返回 True 时放弃等待。
    """
    deadline = time.monotonic() + timeout if timeout is not None else None
    interval = retry_interval
    attempts = 0
    while True:
        attempts += 1
        matches = recognize()
        if matches:
            if attempts > 1:
                print(f"[task] {describe} matched after {attempts} attempts")
            return matches
        if attempts == 1:
            timeout_note = f", timeout={timeout}s" if timeout is not None else ""
            print(
                f"[task] waiting for {describe}: no match yet, "
                f"retrying with backoff from {retry_interval}s"
                f"{timeout_note}"
            )
        if should_stop is not None and should_stop():
            print(f"[task] aborted while waiting for {describe}")
            return []
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                print(f"[task] timed out waiting for {describe} after {timeout}s")
                return None
            print(f"[task] retrying {describe} in {min(interval, remaining):.3g}s")
            sleep_fn(min(interval, remaining))
        else:
            print(f"[task] retrying {describe} in {interval:.3g}s")
            sleep_fn(interval)
        # 未识别到则退避：间隔按倍数增长，封顶于 max_retry_interval
        interval = min(interval * RETRY_BACKOFF_FACTOR, max_retry_interval)


def execute_step(
    step,
    adb_path=ADB_PATH,
    template_dir=TEMPLATE_DIR,
    recognizer_fn=None,
    multi_recognizer_fn=None,
    click_fn=None,
    sleep_fn=time.sleep,
    device=None,
    should_stop=None,
):
    """执行一步任务，识别失败时按退避间隔重试。"""
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

    # 除 template 外全部字段可省略：retry_interval 默认 0.2s（退避起始值），
    # max_retry_interval 默认 3s（退避封顶值），timeout 默认不超时（一直重试）
    retry_interval = _step_float(step, "retry_interval", DEFAULT_RETRY_INTERVAL)
    if retry_interval <= 0:
        raise ValueError(
            f"Invalid retry_interval value: {retry_interval}, must be positive"
        )
    max_retry_interval = _step_float(
        step, "max_retry_interval", DEFAULT_MAX_RETRY_INTERVAL
    )
    if max_retry_interval <= 0:
        raise ValueError(
            f"Invalid max_retry_interval value: {max_retry_interval}, must be positive"
        )
    # 封顶值不低于起始值：低于时相当于不退避，按固定间隔重试
    max_retry_interval = max(max_retry_interval, retry_interval)
    timeout = _step_float(step, "timeout", None)
    if timeout is not None and timeout <= 0:
        raise ValueError(f"Invalid timeout value: {timeout}, must be positive")
    step_interval = _step_float(step, "step_interval", DEFAULT_STEP_INTERVAL)
    if step_interval < 0:
        raise ValueError(
            f"Invalid step_interval value: {step_interval}, must be non-negative"
        )

    if str(template_path).strip().casefold() == "center":
        width, height = get_size(adb_path=adb_path, device=device)
        print(f"[task] step template=Center, click=({width // 2}, {height // 2})")
        result = clicker(width // 2, height // 2)
        if result and step_interval:
            sleep_fn(step_interval)
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
            f"region={region}"
        )
        matches = _recognize_with_retry(
            lambda: multi_recognizer(template_paths, top_n=count, region=region),
            describe=f"templates={template_paths}",
            retry_interval=retry_interval,
            max_retry_interval=max_retry_interval,
            timeout=timeout,
            sleep_fn=sleep_fn,
            should_stop=should_stop,
        )
        if matches is None:
            return TIMEOUT_RESULT
        result = False
        for target in matches:
            if clicker(target["x"], target["y"]):
                result = True
        if result and step_interval:
            sleep_fn(step_interval)
        return result

    # single 模式：单个模板，index 默认 0（第一个匹配）
    index = int(step.get("index") or 0)

    print(f"[task] step template={template_path}, index={index}, region={region}")

    def _recognize_single():
        found = recognizer(template_path, region=region)
        # 匹配数量须多于 index 才算识别成功（index: 1 要求至少 2 个匹配）
        return found if len(found) > index else []

    matches = _recognize_with_retry(
        _recognize_single,
        describe=f"template={template_path} (index={index})",
        retry_interval=retry_interval,
        max_retry_interval=max_retry_interval,
        timeout=timeout,
        sleep_fn=sleep_fn,
        should_stop=should_stop,
    )
    if matches is None:
        return TIMEOUT_RESULT
    result = False
    if len(matches) > index:
        target = matches[index]
        result = clicker(target["x"], target["y"])
    if result and step_interval:
        sleep_fn(step_interval)
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
    should_stop=None,
):
    """按顺序执行任务中的有效步骤。"""
    if not isinstance(task, dict):
        raise ValueError(f"Task must be a dict, got {type(task).__name__}")

    for step in valid_steps(task):
        if should_stop is not None and should_stop():
            return False
        result = execute_step(
            step,
            adb_path=adb_path,
            template_dir=template_dir,
            recognizer_fn=recognizer_fn,
            multi_recognizer_fn=multi_recognizer_fn,
            click_fn=click_fn,
            sleep_fn=sleep_fn,
            device=device,
            should_stop=should_stop,
        )
        if not result:
            return False
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
