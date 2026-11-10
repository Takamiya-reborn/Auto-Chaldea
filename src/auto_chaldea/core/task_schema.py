import re

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


# 模板路径片段 → 表格友好名：技能/选卡/宝具步骤按 DSL 语义显示，
# 未识别的模板原样返回
def _label_part(part):
    key = part.strip()
    if not key:
        return key
    if key.startswith("技能池/skill_"):
        return f"技能{key[len('技能池/skill_'):]}"
    if key == "基本/御主技能":
        return "御主技能"
    match = re.fullmatch(r"(?i)master([1-3])", key)
    if match:
        return f"御主技能{match.group(1)}"
    if key.startswith("角色池/"):
        return key[len("角色池/"):]
    colors = {"基本/buster": "红", "基本/quick": "绿", "基本/arts": "蓝"}
    if key in colors:
        return colors[key]
    if key.startswith("宝具/"):
        return "宝"
    if key == "基本/attack":
        return "攻击"
    return key


# template 字段 → 表格友好名；multi 模式的逗号列表逐段翻译后以 "/" 连接
def _step_label(template):
    return "/".join(
        _label_part(part) for part in str(template).split(",") if part.strip()
    )


# 图任务（flow 展开后或手写 nodes）→ 表格显示行与节点行号映射。
# 返回 (rows, node_rows)：
#   rows — 显示行列表，与运行时步骤（展开命名坐标点后）一一对应，
#     模板列换成友好名；首尾固定加「准备」「收尾」锚点行，对应周回外壳
#   node_rows — {节点名: [该节点子步骤对应的表格行号]}，执行进度高亮用；
#     无子步骤的外壳节点由 flows 标记的 _phase（准备/收尾）落到锚点行
def task_step_view(task):
    if not isinstance(task, dict):
        return [], {}
    # 函数级导入避免模块循环（task_executor 依赖本模块的 normalize_region）
    from auto_chaldea.core.task_executor import expand_named_steps

    def anchor(name):
        return {"template": name, "index": "—", "region": "—", "mode": "—"}

    rows = [anchor("准备")]
    spans = {}
    offset = 1
    for name, node in (task.get("nodes") or {}).items():
        if not isinstance(node, dict):
            continue
        node_spans = []
        for step in node.get("steps") or []:
            if not isinstance(step, dict) or not step.get("template"):
                continue
            for expanded in expand_named_steps([step]):
                row = dict(expanded)
                row["template"] = _step_label(expanded.get("template"))
                rows.append(row)
                node_spans.append(offset)
                offset += 1
        if node_spans:
            spans[name] = node_spans
    rows.append(anchor("收尾"))

    node_rows = dict(spans)
    phase_rows = {"准备": 0, "收尾": len(rows) - 1}
    for name, node in (task.get("nodes") or {}).items():
        if not isinstance(node, dict) or name in node_rows:
            continue
        phase = node.get("_phase")
        if phase in phase_rows:
            node_rows[name] = [phase_rows[phase]]
    return rows, node_rows


# Center 是内部保留的位置常量（屏幕中心点击），yaml 中不允许编写：
# flow 任务不再生成，手写节点与子步骤中出现时加载即拒绝
def reject_center(task):
    if not isinstance(task, dict):
        return
    for name, node in (task.get("nodes") or {}).items():
        if not isinstance(node, dict):
            continue
        for field in ("template", "click"):
            if _contains_center(node.get(field)):
                raise ValueError(
                    f"node {name!r}: 'Center' is a reserved internal constant "
                    f"and cannot be written in yaml ({field} field)"
                )
        for step in node.get("steps") or []:
            if isinstance(step, dict) and _contains_center(step.get("template")):
                raise ValueError(
                    f"node {name!r}: 'Center' is a reserved internal constant "
                    f"and cannot be written in yaml (step template)"
                )


def _contains_center(value):
    if not isinstance(value, str):
        return False
    return any(part.strip().casefold() == "center" for part in value.split(","))
