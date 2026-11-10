# 节点图运行器：节点 = 一个画面（识别 + 动作），next = 有序候选列表。
# 节点字段与路由规则见 docs/task-yaml.md「节点图任务」一节。
# store：可选的共享状态仓（鸭子类型，只需 get(key, default) 与
# decrement(key, by) 两个方法），供 store_gate / store_end 节点字段读写
# 运行期变量（如剩余周回次数）

import time

from auto_chaldea.core.task_executor import (
    SKIP_RESULT,
    TIMEOUT_RESULT,
    execute_step,
    resolve_named_point,
    resolve_steps,
)
from auto_chaldea.core.task_schema import normalize_region
from auto_chaldea.utils.adb_device import click, get_size
from auto_chaldea.utils.paths import ADB_PATH, TEMPLATE_DIR
from auto_chaldea.utils.recognizer import find_all_matches
from auto_chaldea.utils.screen import get_screen

# 访问一轮（扫描全部候选）无命中时的重扫起始间隔 / 封顶 / 倍率
VISIT_RETRY_INTERVAL = 0.2
VISIT_MAX_RETRY_INTERVAL = 3.0
VISIT_BACKOFF_FACTOR = 2.0

# store_end 宽限期：等待无命中持续超过该秒数才视为"结算画面已点完、
# 画面回到了无候选的界面"，避免结算画面切换的瞬间误判收尾
STORE_END_GRACE = 2.0


# 任务图结构错误：加载时立即报错，不让坏图运行到一半才失败
class GraphValidationError(ValueError):
    pass


# 静态校验任务图：所有边引用的节点必须存在；
# 无条件节点（无 template，如命名坐标点）不能出现在候选列表中间——
# 它不识别就命中，放中间会短路后面的候选
def validate_graph(task):
    if not isinstance(task, dict):
        raise GraphValidationError("Task must be a dict")
    nodes = task.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        raise GraphValidationError("Graph task requires a non-empty 'nodes' mapping")
    entry = task.get("entry")
    if not isinstance(entry, list) or not entry:
        raise GraphValidationError("Graph task requires a non-empty 'entry' list")

    edges = [("entry", entry)]
    for name, node in nodes.items():
        if not isinstance(node, dict):
            raise GraphValidationError(f"Node {name!r} must be a mapping")
        for field in ("next", "on_error_next", "exceeded_next"):
            targets = node.get(field) or []
            if not isinstance(targets, list):
                raise GraphValidationError(
                    f"Node {name!r} field {field!r} must be a list"
                )
            edges.append((f"{name}.{field}", targets))

    for field, targets in edges:
        for target in targets:
            if target not in nodes:
                raise GraphValidationError(
                    f"{field} references undefined node: {target!r}"
                )
            if target in targets[:-1] and not nodes[target].get("template"):
                raise GraphValidationError(
                    f"{field} places unconditional node {target!r} (no template) at a "
                    f"non-final position; it would short-circuit later candidates"
                )

    # 从入口可达性检查：不可达节点通常是链接写错，提示但不阻止运行
    reachable = set()
    frontier = list(entry)
    while frontier:
        name = frontier.pop()
        if name in reachable:
            continue
        reachable.add(name)
        node = nodes[name]
        for field in ("next", "on_error_next", "exceeded_next"):
            frontier.extend(node.get(field) or [])
    for name in sorted(set(nodes) - reachable):
        print(f"[graph] warning: node {name!r} is unreachable from entry")


def execute_graph(
    task,
    adb_path=ADB_PATH,
    template_dir=TEMPLATE_DIR,
    device=None,
    sleep_fn=time.sleep,
    should_stop=None,
    should_skip=None,
    screen=None,
    click_fn=None,
    store=None,
    progress=None,
):
    # 沿任务图行走：每轮访问取一帧截图，按序尝试候选节点，命中即执行其动作
    if not isinstance(task, dict):
        raise GraphValidationError("Task must be a dict")
    # flow 任务先展开为图（函数级导入避免模块循环：flows 只依赖 task_schema）
    from auto_chaldea.core.flows import expand_flow

    try:
        task = expand_flow(task)
    except ValueError as error:
        raise GraphValidationError(str(error)) from error
    validate_graph(task)

    if screen is None:
        screen = get_screen(adb_path=adb_path, device=device)
    nodes = task.get("nodes")
    entry = list(task.get("entry"))

    # 运行前解析：无条件节点（命名坐标点）与子步骤中的命名坐标点都需要屏幕尺寸
    width, height = get_size(adb_path=adb_path, device=device)
    fixed_clicks = {}
    for name, node in nodes.items():
        if not node.get("template") and node.get("click"):
            fixed_clicks[name] = resolve_named_point(node["click"], width, height)
    resolved_steps = {
        name: resolve_steps(node.get("steps") or [], adb_path=adb_path, device=device)
        for name, node in nodes.items()
        if node.get("steps")
    }

    raw_clicker = click_fn or (
        lambda x, y: click(x, y, adb_path=adb_path, device=device)
    )

    def clicker(x, y):
        result = raw_clicker(x, y)
        # 点击会改变画面：立即失效帧缓存，下一轮访问强制重新截屏
        if result and screen is not None:
            screen.invalidate()
        return result

    exec_times = {}
    # 收尾阶段标志（单元素列表以便 _visit 原位更新）：命中声明 store_end
    # 的结算链节点后置 True，命中任何其他节点即复位 False
    settled = [False]
    pending = entry
    while pending:
        if should_stop is not None and should_stop():
            return False
        outcome = _visit(
            pending,
            nodes,
            exec_times,
            adb_path=adb_path,
            template_dir=template_dir,
            device=device,
            sleep_fn=sleep_fn,
            should_stop=should_stop,
            should_skip=should_skip,
            screen=screen,
            clicker=clicker,
            fixed_clicks=fixed_clicks,
            resolved_steps=resolved_steps,
            store=store,
            settled=settled,
            progress=progress,
        )
        if outcome is None:
            # 等待超时且无法自救：图失败
            print(f"[graph] gave up waiting for candidates {pending}")
            return False
        pending = outcome
    return True


# 一轮访问：扫描 pending 候选直到命中，执行命中节点的动作并返回其路由。
# 返回下一候选列表；无法推进时返回 None
def _visit(
    pending,
    nodes,
    exec_times,
    adb_path,
    template_dir,
    device,
    sleep_fn,
    should_stop,
    should_skip,
    screen,
    clicker,
    fixed_clicks,
    resolved_steps,
    store=None,
    settled=None,
    progress=None,
):
    # 候选中声明了 timeout 的节点构成可选等待期限：超时视为已处理，
    # 取第一个可选节点直接前往其 next
    deadlines = [
        float(nodes[name]["timeout"])
        for name in pending
        if nodes[name].get("timeout") is not None
    ]
    deadline = time.monotonic() + min(deadlines) if deadlines else None

    interval = VISIT_RETRY_INTERVAL
    attempts = 0
    wait_started = time.monotonic()
    while True:
        attempts += 1
        # 每轮扫描用新帧：等待期间画面可能因动画/转场变化
        if screen is not None:
            screen.invalidate()
        hit = _scan_candidates(
            pending,
            nodes,
            exec_times,
            adb_path,
            template_dir,
            device,
            screen,
            store=store,
        )
        if hit is not None:
            break
        if attempts == 1:
            print(f"[graph] waiting for one of {pending} …")
        if should_stop is not None and should_stop():
            print(f"[graph] aborted while waiting for {pending}")
            return None
        if should_skip is not None and should_skip():
            # 跳过 = 推进图：与超时同路（可选节点优先，否则走自救边）；
            # 都没有时兜底前往第一个候选的 next——用户跳过只推进，不终止任务
            print(f"[graph] skip requested while waiting for {pending}")
            routed = _route_on_timeout(pending, nodes) or _route_on_skip(
                pending, nodes
            )
            if routed is not None:
                return routed
            print(f"[graph] skip with no route available from {pending}")
            return None
        if deadline is not None and time.monotonic() >= deadline:
            return _route_on_timeout(pending, nodes)
        # 状态仓收尾：仅在收尾阶段（收尾标志由 _visit 在命中节点时维护）
        # 等待无命中持续超过宽限期，视为"结算画面已点完"——本次图执行正
        # 常结束（次数是否耗尽由 worker 侧 while remaining > 0 决定是否继
        # 续）。回合操作与轮次衔接期间标志为 False，静默只是动画间隙，
        # 完全不做收尾判断
        if (
            settled is not None
            and settled[0]
            and store is not None
            and time.monotonic() - wait_started >= STORE_END_GRACE
        ):
            print("[graph] settlement store_end reached, graph pass complete")
            return []
        sleep_fn(interval)
        interval = min(interval * VISIT_BACKOFF_FACTOR, VISIT_MAX_RETRY_INTERVAL)

    name, matches, exceeded = hit
    node = nodes[name]
    if not exceeded:
        exec_times[name] = exec_times.get(name, 0) + 1
        # store_gate 命中即消耗一次状态仓键值（如连续出击命中 = 开启
        # 下一轮周回），与 exec_times 递增同点执行
        gate = node.get("store_gate")
        if gate is not None and store is not None:
            left = store.decrement(gate, 1)
            print(f"[graph] node {name!r} consumed store {gate!r}, remaining={left}")
    # 收尾阶段标志：命中结算链节点（声明 store_end）进入收尾，此后等待
    # 静默才计时判结束；命中任何其他节点（选助战、战斗、连续出击等）
    # 都离开收尾——阶段由图的走向显式声明，等待循环不做任何推断
    if settled is not None:
        settled[0] = node.get("store_end") is not None
    print(
        f"[graph] node {name!r} hit (times={exec_times.get(name, 0)}), "
        f"candidates were {pending}"
    )
    return _run_node(
        name,
        node,
        matches,
        exceeded,
        adb_path=adb_path,
        template_dir=template_dir,
        device=device,
        sleep_fn=sleep_fn,
        should_stop=should_stop,
        should_skip=should_skip,
        screen=screen,
        clicker=clicker,
        fixed_clicks=fixed_clicks,
        resolved_steps=resolved_steps,
        progress=progress,
    )


# 按序扫描候选：返回 (节点名, 匹配列表, 是否已达 max_times)，无命中返回 None。
# 共用同一帧截图——这就是图模型"一个节点试多个候选只截一次屏"的收益点
def _scan_candidates(
    pending, nodes, exec_times, adb_path, template_dir, device, screen, store=None
):
    for name in pending:
        node = nodes[name]
        template_path = node.get("template")
        if not template_path:
            # 无条件节点（已校验只能处于末位）：直接命中
            return name, None, False

        matches = find_all_matches(
            template_path,
            adb_path=adb_path,
            template_dir=template_dir,
            region=normalize_region(node.get("region")),
            threshold=float(node.get("threshold") or 0.7),
            device=device,
            screen=screen,
        )
        index = int(node.get("index") or 0)
        if len(matches) <= index:
            continue

        # 达到 max_times 的节点不再执行：有 exceeded_next 则走超限路由，否则当它不存在
        max_times = node.get("max_times")
        if max_times is not None and exec_times.get(name, 0) >= int(max_times):
            if node.get("exceeded_next") is not None:
                print(
                    f"[graph] node {name!r} reached max_times={max_times}, "
                    f"routing to exceeded_next {node['exceeded_next']}"
                )
                return name, matches, True
            continue

        # store_gate：状态仓键值 < 1（次数耗尽）或无状态仓时视为不存在，
        # 同帧继续扫描后续候选，路由不受阻
        gate = node.get("store_gate")
        if gate is not None and (store is None or _store_value(store, gate) < 1):
            continue
        return name, matches, False
    return None


# store 键值 → int：容忍非数值与缺键，缺省视为耗尽（0）
def _store_value(store, key):
    try:
        return int(store.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0


# 超时/跳过时的路由：优先"可选节点超时视为已处理"——取第一个声明了
# timeout 的候选直接前往其 next；否则取第一个候选的 on_error_next 自救
def _route_on_timeout(pending, nodes):
    for name in pending:
        if nodes[name].get("timeout") is not None:
            nxt = nodes[name].get("next") or []
            print(f"[graph] optional node {name!r} timed out, continuing to {nxt}")
            return list(nxt)
    for name in pending:
        on_error = nodes[name].get("on_error_next")
        if on_error:
            print(
                f"[graph] waiting timed out, routing {pending} -> on_error_next {on_error}"
            )
            return list(on_error)
    return None


# 用户跳过且无可选节点与自救边时的兜底：视为第一个有出边的候选已被
# 手动处理，直接前往其 next——保证"下一步"始终推进图而不终止任务
def _route_on_skip(pending, nodes):
    for name in pending:
        nxt = nodes[name].get("next") or []
        if nxt:
            print(
                f"[graph] skip fallback: treating {name!r} as handled, "
                f"continuing to {nxt}"
            )
            return list(nxt)
    return None


# 执行命中节点：前置等待 → 动作（点击/命名点/子步骤）→ 后置等待 → 路由。
# 返回下一候选列表；无法推进时返回 None
def _run_node(
    name,
    node,
    matches,
    exceeded,
    adb_path,
    template_dir,
    device,
    sleep_fn,
    should_stop,
    should_skip,
    screen,
    clicker,
    fixed_clicks,
    resolved_steps,
    progress=None,
):
    # 已达 max_times 的超限命中：不执行动作，直接走超限路由
    if exceeded:
        return list(node.get("exceeded_next") or [])

    steps = resolved_steps.get(name) or []
    # 无子步骤的节点（周回外壳：选助战、开始任务、结算等）也回报进度，
    # 供界面在「准备」/「收尾」锚点行上高亮
    if not steps and progress is not None:
        progress(name, 0, "running")

    pre_delay = _node_float(node, "pre_delay")
    if pre_delay:
        sleep_fn(pre_delay)

    failed = False
    if name in fixed_clicks:
        x, y = fixed_clicks[name]
        print(f"[graph] node {name!r} click=({x}, {y})")
        clicker(int(x), int(y))
    elif matches is not None:
        action = str(node.get("action") or "click").strip().lower()
        if action not in ("click", "none"):
            raise GraphValidationError(
                f"Node {name!r} has invalid action {action!r}, expected 'click' or 'none'"
            )
        if action == "click":
            index = int(node.get("index") or 0)
            target = matches[index]
            print(
                f"[graph] node {name!r} click template={node.get('template')} "
                f"at=({target['x']}, {target['y']}) confidence={target['confidence']:.3f}"
            )
            clicker(int(target["x"]), int(target["y"]))

    for position, step in enumerate(steps):
        if should_stop is not None and should_stop():
            return None
        # 进度回报：子步骤开始前 "running"，结束后归一为
        # executed / failed / skipped / timeout，供界面高亮对应表格行
        if progress is not None:
            progress(name, position, "running")
        result = execute_step(
            step,
            adb_path=adb_path,
            template_dir=template_dir,
            sleep_fn=sleep_fn,
            device=device,
            should_stop=should_stop,
            should_skip=should_skip,
            screen=screen,
            click_fn=clicker,
        )
        if progress is not None:
            if result == SKIP_RESULT:
                status = "skipped"
            elif result == TIMEOUT_RESULT:
                status = "timeout"
            elif result:
                status = "executed"
            else:
                status = "failed"
            progress(name, position, status)
        if result in (SKIP_RESULT, TIMEOUT_RESULT):
            # skip / timeout 视为已处理，继续子步骤
            continue
        if not result:
            print(f"[graph] node {name!r} step {position + 1} failed")
            failed = True
            break

    post_delay = _node_float(node, "post_delay")
    if post_delay:
        sleep_fn(post_delay)

    if not steps and progress is not None:
        progress(name, 0, "executed")

    if failed:
        on_error = node.get("on_error_next")
        if not on_error:
            return None
        print(f"[graph] node {name!r} routing on_error_next {on_error}")
        return list(on_error)

    return list(node.get("next") or [])


def _node_float(node, key):
    value = node.get(key)
    return 0.0 if value in (None, "") else float(value)


__all__ = [
    "GraphValidationError",
    "execute_graph",
    "validate_graph",
]
