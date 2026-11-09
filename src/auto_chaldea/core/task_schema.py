DEFAULT_SCREEN_WIDTH = 1280
DEFAULT_SCREEN_HEIGHT = 720

REGION_ALIASES = {
    "左": (0, 0, DEFAULT_SCREEN_WIDTH // 2, DEFAULT_SCREEN_HEIGHT),
    "右": (DEFAULT_SCREEN_WIDTH // 2, 0, DEFAULT_SCREEN_WIDTH, DEFAULT_SCREEN_HEIGHT),
    "上": (0, 0, DEFAULT_SCREEN_WIDTH, DEFAULT_SCREEN_HEIGHT // 2),
    "下": (0, DEFAULT_SCREEN_HEIGHT // 2, DEFAULT_SCREEN_WIDTH, DEFAULT_SCREEN_HEIGHT),
    "左上": (0, 0, DEFAULT_SCREEN_WIDTH // 2, DEFAULT_SCREEN_HEIGHT // 2),
    "右上": (
        DEFAULT_SCREEN_WIDTH // 2,
        0,
        DEFAULT_SCREEN_WIDTH,
        DEFAULT_SCREEN_HEIGHT // 2,
    ),
    "左下": (
        0,
        DEFAULT_SCREEN_HEIGHT // 2,
        DEFAULT_SCREEN_WIDTH // 2,
        DEFAULT_SCREEN_HEIGHT,
    ),
    "右下": (
        DEFAULT_SCREEN_WIDTH // 2,
        DEFAULT_SCREEN_HEIGHT // 2,
        DEFAULT_SCREEN_WIDTH,
        DEFAULT_SCREEN_HEIGHT,
    ),
}


# 区域字段统一为坐标元组
def normalize_region(region):
    if region in (None, "", [], (), {}):
        return None

    if isinstance(region, str):
        region = region.strip()
        if not region:
            return None
        if region in REGION_ALIASES:
            return REGION_ALIASES[region]
        values = [item.strip() for item in region.split(",")]
        if len(values) != 4:
            raise ValueError(f"Invalid region value: {region!r}")
        return tuple(int(value) for value in values)

    if isinstance(region, (list, tuple)) and len(region) == 4:
        return tuple(int(value) for value in region)

    return region


# 返回图任务（flow 展开后或手写 nodes）各节点子步骤的有效模板步骤，
# 按节点定义顺序拉平，供 UI 表格展示
def valid_steps(task):
    if not isinstance(task, dict):
        return []
    steps = []
    for node in (task.get("nodes") or {}).values():
        if not isinstance(node, dict):
            continue
        steps.extend(
            step
            for step in node.get("steps") or []
            if isinstance(step, dict) and step.get("template")
        )
    return steps


# 节点子步骤 → 拉平步骤表的行号映射：{节点名: [每个子步骤对应的表格行号]}。
# 展开规则与 valid_steps + expand_named_steps 一致（同序过滤、命名坐标点
# 拆分同样占行），保证运行时子步骤与表格行一一对应，供执行进度高亮使用
def node_step_rows(task):
    if not isinstance(task, dict):
        return {}
    # 函数级导入避免模块循环（task_executor 依赖本模块的 normalize_region）
    from auto_chaldea.core.task_executor import expand_named_steps

    rows = {}
    offset = 0
    for name, node in (task.get("nodes") or {}).items():
        if not isinstance(node, dict):
            continue
        spans = []
        for step in node.get("steps") or []:
            if not isinstance(step, dict) or not step.get("template"):
                continue
            count = len(expand_named_steps([step]))
            spans.extend(range(offset, offset + count))
            offset += count
        if spans:
            rows[name] = spans
    return rows
