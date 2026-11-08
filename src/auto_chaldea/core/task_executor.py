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
# 手动跳过当前步骤，继续下一步。
SKIP_RESULT = "skip"

# 命名坐标点：template 字段可直接使用这些名称，无需模板识别，直接点击对应位置。
# 坐标以 NAMED_POINT_BASE_SIZE 为基准填写（像素），执行时按实际屏幕尺寸等比缩放；
# Center 特殊处理为屏幕中心，不在此表中。
# 坐标为 (x, y) 元组，单个轴可以是 None 表示尚未测量，使用时会报错并指出缺哪个轴。
NAMED_POINT_BASE_SIZE = (1280, 720)
NAMED_POINTS = {
    # 三个敌人在同一行，y 均为 45
    "enemy1": (45, 45),
    "enemy2": (298, 45),
    "enemy3": (545, 45),
}


def is_named_point(name):
    """判断 template 字段是否为内置命名坐标点（Center、Enemy1 等）。"""
    key = str(name).strip().casefold()
    return key == "center" or key in NAMED_POINTS


def resolve_named_point(name, width, height):
    """把命名坐标点解析为当前屏幕尺寸下的实际坐标 (x, y)。"""
    key = str(name).strip().casefold()
    if key == "center":
        return (width // 2, height // 2)
    if key not in NAMED_POINTS:
        return None
    point = NAMED_POINTS[key]
    base_x, base_y = point
    if base_x is None or base_y is None:
        missing = "x" if base_x is None else "y"
        raise ValueError(
            f"Named point {name!r} has no {missing} coordinate configured yet, "
            f"fill it in NAMED_POINTS of task_executor.py"
        )
    base_width, base_height = NAMED_POINT_BASE_SIZE
    return (
        round(base_x * width / base_width),
        round(base_y * height / base_height),
    )


def expand_named_steps(steps):
    """结构解析（无需设备）：把命名坐标点步骤展开为统一的点击步骤形态。

    - single 模式的命名点 → 含 `click: None` 占位的点击步骤，template 保留原名用于显示
    - multi 模式列表中的命名点拆分为独立点击步骤，置于识别步骤之前
    - 其余步骤原样保留
    展开只依赖步骤本身，可在无设备时用于界面展示，保证展示行数与
    运行时步骤一一对应；坐标由运行前的 resolve_steps 解析。
    """
    expanded = []
    for step in steps:
        template_path = step.get("template")
        if not template_path:
            continue
        mode = str(step.get("mode") or "single").strip().lower()
        if mode == "multi":
            named, normal = _split_named_points(template_path)
            for name in named:
                expanded.append({**step, "template": name, "click": None})
            if normal:
                expanded.append({**step, "template": ",".join(normal)})
        elif is_named_point(template_path):
            expanded.append({**step, "click": None})
        else:
            expanded.append(step)
    return expanded


def resolve_steps(steps, adb_path=ADB_PATH, device=None):
    """运行前解析：展开命名坐标点并把占位坐标换算为实际屏幕坐标。

    坐标换算需要屏幕尺寸，须在设备连接后调用；未配置坐标的命名点
    在此报错，任务不会开始执行。
    """
    expanded = expand_named_steps(steps)
    width, height = get_size(adb_path=adb_path, device=device)
    resolved = []
    for step in expanded:
        if "click" not in step:
            resolved.append(step)
            continue
        mode = str(step.get("mode") or "single").strip().lower()
        if mode == "none":
            raise ValueError(
                f"Step with mode 'none' cannot use named point {step.get('template')!r}"
            )
        x, y = resolve_named_point(step["template"], width, height)
        resolved.append({**step, "click": [x, y]})
    return resolved


def _split_named_points(template_path):
    """把逗号分隔的 template 拆成 (命名坐标点列表, 普通模板列表)。"""
    named, normal = [], []
    for part in str(template_path).split(","):
        part = part.strip()
        if not part:
            continue
        (named if is_named_point(part) else normal).append(part)
    return named, normal


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
    should_skip=None,
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
        if should_skip is not None and should_skip():
            print(f"[task] skipped while waiting for {describe}")
            return SKIP_RESULT
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
    should_skip=None,
):
    """执行一步任务，识别失败时按退避间隔重试。"""
    if not isinstance(step, dict):
        raise ValueError(f"Step must be a dict, got {type(step).__name__}")

    recognizer = recognizer_fn or _build_recognizer(adb_path, template_dir, device)
    multi_recognizer = multi_recognizer_fn or _build_multi_recognizer(
        adb_path, template_dir, device
    )
    clicker = click_fn or _build_clicker(adb_path, device)

    # 除 template 外全部字段可省略：mode 默认 single，index 默认 0，region 默认全屏
    mode = str(step.get("mode") or "single").strip().lower()
    if mode not in ("single", "multi", "none"):
        raise ValueError(
            f"Invalid mode value: {mode!r}, expected 'single', 'multi' or 'none'"
        )

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

    template_path = step.get("template")

    # 解析阶段（resolve_steps）产出的固定坐标点击步骤：click 为坐标 [x, y]，
    # 无需模板识别。直接调用 execute_step 时也在此兜底解析命名坐标点。
    click_target = step.get("click")
    if click_target is None and template_path and is_named_point(template_path):
        if mode == "none":
            raise ValueError(
                f"Step with mode 'none' cannot use named point {template_path!r}"
            )
        if mode == "multi":
            raise ValueError(
                f"Named point {template_path!r} must be resolved by resolve_steps() "
                f"before execute_step (named points in multi lists are split there)"
            )
        width, height = get_size(adb_path=adb_path, device=device)
        click_target = resolve_named_point(template_path, width, height)

    if click_target is not None:
        x, y = int(click_target[0]), int(click_target[1])
        label = f"template={template_path}, " if template_path else ""
        print(f"[task] step {label}click=({x}, {y})")
        result = clicker(x, y)
        if result and step_interval:
            sleep_fn(step_interval)
        return result

    if not template_path:
        return False

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
        if any(is_named_point(t) for t in template_paths):
            raise ValueError(
                f"Named point in a multi list must be resolved by resolve_steps() "
                f"first: {template_path!r}"
            )

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
            should_skip=should_skip,
        )
        if matches == SKIP_RESULT:
            return SKIP_RESULT
        if matches is None:
            return TIMEOUT_RESULT
        result = False
        for target in matches:
            if clicker(target["x"], target["y"]):
                result = True
        if result and step_interval:
            sleep_fn(step_interval)
        return result

    # single/none 模式：单个模板，index 默认 0（第一个匹配）
    index = int(step.get("index") or 0)

    action = "recognize only" if mode == "none" else "click"
    print(
        f"[task] step template={template_path}, mode={mode}, action={action}, "
        f"index={index}, region={region}"
    )

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
        should_skip=should_skip,
    )
    if matches == SKIP_RESULT:
        return SKIP_RESULT
    if matches is None:
        return TIMEOUT_RESULT
    if mode == "none":
        if step_interval:
            sleep_fn(step_interval)
        return True
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

    for step in resolve_steps(valid_steps(task), adb_path=adb_path, device=device):
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
