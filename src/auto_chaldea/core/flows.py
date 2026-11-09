# 内置标准流程图：把周回外壳（助战 → 开始 → 战斗 → 结算）沉淀为
# 代码内置的图模板，任务文件只写每回合脚本。DSL 规则见 README「标准周回 flow」

FLOW_STANDARD_FARM = "标准周回"

# 结算链与战斗节点的公共模板路径
_T_TOUCH = "基本/请点击游戏界面"
_T_NEXT = "基本/下一步"
_T_ATTACK = "基本/attack"
_T_MASTER = "基本/御主技能"


# flow 名 → 构建函数；返回 {"entry": [...], "nodes": {...}}
_FLOWS = {}


# 展开 flow 任务为图任务：无 flow 字段时原样返回（手写 nodes 的逃生门）。
# 展开结果去掉 flow 键保证幂等：任务在 loader 处展开一次，下游（UI、
# execute_graph）重复进入展开只是无害的空操作
def expand_flow(task):
    if not isinstance(task, dict) or not task.get("flow"):
        return task
    if task.get("nodes"):
        # 手写节点优先：两者同时存在时以 nodes 为准
        print(f"[flow] task defines both 'flow' and 'nodes'; using 'nodes'")
        return task
    name = str(task["flow"]).strip()
    builder = _FLOWS.get(name)
    if builder is None:
        raise ValueError(
            f"Unknown flow: {name!r}, available flows: {sorted(_FLOWS)}"
        )
    built = builder(task)
    expanded = {key: value for key, value in task.items() if key != "flow"}
    expanded.update({"entry": built["entry"], "nodes": built["nodes"]})
    return expanded


# ---- 标准周回 ----

def _build_standard_farm(task):
    turn_map = task.get("turns")
    if not isinstance(turn_map, dict) or not turn_map:
        raise ValueError(f"Flow {FLOW_STANDARD_FARM!r} requires a non-empty 'turns' mapping")
    try:
        turns = sorted(int(turn) for turn in turn_map)
    except (TypeError, ValueError) as error:
        raise ValueError(f"'turns' keys must be turn numbers: {turn_map!r}") from error
    if turns != list(range(1, len(turns) + 1)):
        raise ValueError(
            f"'turns' keys must be consecutive turns starting at 1: {turns}"
        )

    # 连刷次数由 UI 的执行次数输入驱动：一次图执行 = 一轮完整周回。
    # 选助战 max_times=1：结算回到选关界面后命中即超限，本轮结束
    nodes = {
        "选助战": {
            "template": "助战池/选助战",
            "region": "右",
            "max_times": 1,
            "exceeded_next": [],
            "next": ["开始任务"],
        },
        "开始任务": {
            "template": "基本/开始任务",
            "region": "右下",
            "timeout": 3,
            "next": [_battle_node(1)],
        },
    }
    for position, turn in enumerate(turns):
        battle = _battle_node(position + 1)
        if position + 1 < len(turns):
            next_candidates = [_battle_node(position + 2), "结算点屏"]
        else:
            next_candidates = ["结算点屏"]
        nodes[battle] = {
            "template": _T_ATTACK,
            "region": "右下",
            "action": "none",
            "steps": _battle_steps(turn_map[turn]),
            "next": next_candidates,
        }
    nodes.update(
        {
            "结算点屏": {
                "template": _T_TOUCH,
                "region": "下",
                "next": ["结算点屏", "结算下一步"],
            },
            "结算下一步": {
                "template": _T_NEXT,
                "region": "右下",
                "next": ["结算点屏", "选助战"],
            },
        }
    )
    return {"entry": ["选助战"], "nodes": nodes}


def _battle_node(position):
    return f"战斗{position}"


# 回合脚本条目 → 线性步骤列表（复用 task_executor 的步骤语法）
def _battle_steps(battle):
    if not isinstance(battle, dict):
        raise ValueError(f"Battle entry must be a mapping, got {battle!r}")
    if battle.get("attack") is not None:
        # 攻击按钮点击已内置到 cards：解析到选卡自动先点右下攻击
        raise ValueError(
            f"'attack' is built into 'cards' now; remove the field: {battle!r}"
        )
    if battle.get("count") is not None:
        # 每个选卡槽位就是一次识别点击，不再需要 count
        raise ValueError(
            f"'count' is no longer used; each cards entry is one pick: {battle!r}"
        )
    skills = battle.get("skills") or []
    steps = []
    for position, skill in enumerate(skills):
        following = skills[position + 1] if position + 1 < len(skills) else None
        mode = _center_mode(skill, following)
        step = _skill_step(skill)
        if mode == "double":
            # 第一击触发技能，第二击跳过动画：省掉单独的中央点击
            step["double"] = True
        steps.append(step)
        if mode == "tap":
            steps.append({"template": "Center"})

    cards = battle.get("cards")
    if cards:
        if not isinstance(cards, list) or not cards:
            raise ValueError(f"'cards' must be a non-empty list: {cards!r}")
        if len(cards) > 3:
            raise ValueError(
                f"a FGO turn selects at most 3 cards (NP included), got {len(cards)}: {cards!r}"
            )
        # 攻击按钮固定在屏幕右下：解析到选卡即自动先点攻击，无需显式配置；
        # 个别界面差异用 attack_region 覆盖
        attack_step = {"template": _T_ATTACK, "region": "右下"}
        if battle.get("attack_region"):
            attack_step["region"] = battle["attack_region"]
        steps.append(attack_step)

        # cards = 选卡槽位序列，每个槽位一次识别点击：
        #   字符串 → 单一目标；数组 → 目标范围（multi 取最靠前的一个命中）；
        #   {np: 名} → 宝具。已选中的卡会出现选中标记，置信度下降不再命中，
        #   因此相邻槽位的候选范围可以安全重叠
        for entry in cards:
            if isinstance(entry, dict) and entry.get("np"):
                # 宝具点击后紧接选卡，无需中央点击
                steps.append({"template": f"宝具/{entry['np']}"})
                continue
            names = [entry] if isinstance(entry, str) else entry
            if (
                not isinstance(names, list)
                or not names
                or not all(isinstance(name, str) and name.strip() for name in names)
            ):
                raise ValueError(
                    f"cards entry must be a card name, a list of names, "
                    f"or a mapping with 'np': {entry!r}"
                )
            templates = ",".join(f"基本/{name.strip()}" for name in names)
            if len(names) == 1:
                steps.append({"template": templates})
            else:
                steps.append({"template": templates, "mode": "multi", "count": 1})
    return steps


# 技能条目 → 单个点击步骤
def _skill_step(skill):
    if isinstance(skill, str):
        # 简写：字符串视为角色池技能或原始模板路径
        skill = {"target": skill} if "/" in skill else {"template": skill}
    if not isinstance(skill, dict):
        raise ValueError(f"Skill entry must be a mapping, got {skill!r}")

    step = {}
    if skill.get("pool") is not None:
        step["template"] = f"技能池/skill_{skill['pool']}"
        # 技能池图标固定在屏幕底部，缺省 region 下；个别技能在左侧时条目覆盖
        step.setdefault("region", "下")
    elif skill.get("target"):
        step["template"] = f"角色池/{skill['target']}"
    elif skill.get("master"):
        step["template"] = _T_MASTER
        # 御主技能菜单在右侧
        step.setdefault("region", "右")
    elif skill.get("template"):
        step["template"] = skill["template"]
    else:
        raise ValueError(f"Skill entry needs one of pool/target/master/template: {skill!r}")

    for field in ("index", "region", "threshold"):
        if skill.get(field) is not None:
            step[field] = skill[field]
    return step


# 动画跳过方式分派（默认规则见 README「标准周回 flow」）：
#   "double" — 双击该条目，第二击跳过动画；"tap" — 单击后补屏幕中央点击；
#   "none" — 都不要。显式 center 字段覆盖默认
def _center_mode(skill, following=None):
    if not isinstance(skill, dict):
        # 字符串简写与 _skill_step 同规则：带 / 视为目标头像，否则为原始模板
        skill = {"target": skill} if "/" in skill else {"template": skill}
    center = skill.get("center")
    if center is None:
        if skill.get("master"):
            return "none"
        if skill.get("target"):
            return "tap"
        if _is_target_selection(following):
            return "none"
        if skill.get("template"):
            return "none"
        return "double"
    if center in ("double", "tap", "none"):
        return center
    return "tap" if center else "none"


# 下一个条目是否为目标选择（target 条目意味着当前技能需要选目标）
def _is_target_selection(following):
    return isinstance(following, dict) and bool(following.get("target"))


_FLOWS[FLOW_STANDARD_FARM] = _build_standard_farm


__all__ = ["FLOW_STANDARD_FARM", "expand_flow"]
