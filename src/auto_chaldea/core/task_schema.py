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


def normalize_region(region):
    """将区域字段统一为坐标元组。"""
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


def valid_steps(task):
    """返回包含有效模板名的步骤。"""
    steps = task.get("steps", []) if isinstance(task, dict) else []
    return [step for step in steps if isinstance(step, dict) and step.get("template")]
