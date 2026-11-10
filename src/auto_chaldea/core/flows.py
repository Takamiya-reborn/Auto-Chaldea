# 内置标准流程图：把周回外壳（助战 → 开始 → 战斗 → 结算）沉淀为
# 代码内置的图模板，任务文件只写每回合脚本。DSL 规则见 docs/task-yaml.md「标准周回 flow」

FLOW_STANDARD_FARM = "标准周回"

# 结算链与战斗节点的公共模板路径
_T_TOUCH = "基本/请点击游戏界面"
_T_NEXT = "基本/下一步"
_T_ATTACK = "基本/attack"
_T_MASTER = "基本/御主技能"
_T_CONTINUOUS = "基本/连续出击"
# 选卡槽位间的点击间隔（秒）：选中动画较短，压到 0.5 加快选卡节奏
_CARD_STEP_INTERVAL = 0.5

# 选目标条目补第二击加速动画的延迟（秒）：第一击选中目标、动画开始后，
# 第二击落在动画播放中加速播放（内部延后双击，无需手写 Center 点击）
TARGET_DOUBLE_DELAY = 0.5


# 内置 flow → 构建函数；type: flow 时取用，返回 {"entry": [...], "nodes": {...}}
_FLOWS = {}


# 展开 flow 任务为图任务：type 为 'flow' 时用内置图模板构建节点图；
# type 为 'nodes' 或缺省时原样返回（手写 nodes 的逃生门）。
# 展开结果去掉 type 键保证幂等：任务在 loader 处展开一次，下游（UI、
# execute_graph）重复进入展开只是无害的空操作
def expand_flow(task):
    if not isinstance(task, dict) or not task.get("type"):
        return task
    kind = str(task["type"]).strip()
    if kind == "nodes":
        return task
    if kind != "flow":
        raise ValueError(f"Unknown type: {kind!r}, expected 'flow' or 'nodes'")
    if task.get("nodes"):
        # 手写节点优先：两者同时存在时以 nodes 为准
        print("[flow] task defines both 'type: flow' and 'nodes'; using 'nodes'")
        return task
    built = _FLOWS[FLOW_STANDARD_FARM](task)
    expanded = {key: value for key, value in task.items() if key != "type"}
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

    # 连刷次数由 UI 的执行次数输入驱动，存于共享状态仓（remaining = 尚未
    # 开始的轮数）。一次循环的边界：起始 = 选助战命中；结束 = 命中连续出击
    # （store_gate 消耗一次并回到选助战开启下一轮）或结算画面点完后经
    # store_end 结束本次图执行。worker 侧 while remaining > 0 决定是否
    # 继续下一轮，因此一轮图执行可覆盖多轮周回
    nodes = {
        "选助战": {
            "template": "助战池/选助战",
            "region": "右",
            "next": ["开始任务"],
            # 周回外壳节点标记：无子步骤，执行进度落在「准备」锚点行
            "_phase": "准备",
        },
        "开始任务": {
            "template": "基本/开始任务",
            "region": "右下",
            "timeout": 3,
            "next": [_battle_node(1)],
            "_phase": "准备",
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
            # 结算链 = 点屏 ⇄ 下一步 双节点互相/自环循环（下一步界面可能
            # 连续出现多个，如活动点数报酬），链尾不放选助战——它不会出现
            # 在结算画面里，只作为下一循环的入口由连续出击或 worker 路由。
            # store_end：结算画面点完、画面上不再有候选（持续超过宽限期）
            # 时正常结束本次图执行
            "结算点屏": {
                "template": _T_TOUCH,
                "region": "下",
                "store_end": "remaining",
                "next": ["结算点屏", "结算下一步", "连续出击"],
                # 周回外壳节点标记：无子步骤，执行进度落在「收尾」锚点行
                "_phase": "收尾",
            },
            "结算下一步": {
                "template": _T_NEXT,
                "region": "右下",
                "store_end": "remaining",
                "next": ["结算点屏", "结算下一步", "连续出击"],
                "_phase": "收尾",
            },
            # 连续出击：结算后出现且还有剩余轮数时点击 = 开启下一循环，
            # 随后尝试匹配选助战开始新一轮；次数耗尽时视为不存在不点击
            "连续出击": {
                "template": _T_CONTINUOUS,
                "store_gate": "remaining",
                "next": ["选助战"],
                "_phase": "收尾",
            },
        }
    )
    return {"entry": ["选助战"], "nodes": nodes}


def _battle_node(position):
    return f"战斗{position}"


# 回合脚本条目 → 节点子步骤列表（复用 task_executor 的步骤语法）
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
    for skill in skills:
        steps.extend(_skill_steps(skill))

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
        #   因此相邻槽位的候选范围可以安全重叠。槽位间隔压到 0.5 秒
        #   （默认 1.0）；攻击按钮不在此列，点击后保留完整间隔等发牌动画
        for entry in cards:
            if isinstance(entry, dict) and entry.get("np"):
                # 宝具点击后紧接选卡，无需中央点击
                steps.append(
                    {"template": f"宝具/{entry['np']}", "step_interval": _CARD_STEP_INTERVAL}
                )
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
                steps.append(
                    {"template": templates, "step_interval": _CARD_STEP_INTERVAL}
                )
            else:
                steps.append(
                    {
                        "template": templates,
                        "mode": "multi",
                        "count": 1,
                        "step_interval": _CARD_STEP_INTERVAL,
                    }
                )
    return steps


# 技能条目 → 子步骤列表：本体点击 + 可选 target 子步骤（选目标 + 延后双击）。
# 技能条目只支持 pool / master / const；target 不是独立条目，而是挂在条目上的子步骤字段。
# 动画加速内化为双击 / 延后双击，不再生成显式的 Center 点击步骤
def _skill_steps(skill):
    if not isinstance(skill, dict):
        raise ValueError(f"Skill entry must be a mapping, got {skill!r}")
    if skill.get("center") is not None:
        raise ValueError(
            f"'center' field is removed; animation acceleration is applied "
            f"automatically (double / delayed double): {skill!r}"
        )

    # const：常量基础步骤——无识别的固定点击（命名坐标点等），原样透传，
    # 不参与动画加速分派
    if skill.get("const") is not None:
        value = skill["const"]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Skill entry 'const' must be a non-empty value: {skill!r}")
        if value.strip().casefold() == "center":
            raise ValueError(
                f"'Center' is a reserved internal constant and cannot be "
                f"written in yaml: {skill!r}"
            )
        return [{"template": value.strip()}]

    step = {}
    master_number = None
    if skill.get("pool") is not None:
        step["template"] = f"技能池/skill_{skill['pool']}"
        # 技能池图标固定在屏幕底部，缺省 region 下；个别技能在左侧时条目覆盖
        step.setdefault("region", "下")
    elif skill.get("master") is not None:
        master_number = _master_number(skill)
        step["template"] = _T_MASTER
        # 御主技能图标固定在右侧：单击打开御主菜单
        step.setdefault("region", "右")
    else:
        raise ValueError(
            f"Skill entry needs 'pool', 'master' or 'const' "
            f"(target is a sub-step field on the entry): {skill!r}"
        )

    for field in ("index", "region", "threshold"):
        if skill.get(field) is not None:
            step[field] = skill[field]

    steps = [step]
    body = step
    if master_number is not None:
        # 技能本体在御主菜单里位置固定：Master<N> 命名坐标点直接点击，
        # 不走模板识别
        body = {"template": f"Master{master_number}"}
        steps.append(body)

    target = skill.get("target")
    if target:
        # target 支持单个名字或名字列表：列表时 multi 模式取屏幕最靠前的
        # 一个命中（与 cards 数组槽位语义一致），可兼容不同灵基立绘
        if isinstance(target, str):
            names = [target.strip()]
        elif isinstance(target, list):
            names = [name.strip() if isinstance(name, str) else "" for name in target]
        else:
            names = []
        if not names or not all(names):
            raise ValueError(
                f"Skill entry 'target' must be a non-empty name or a list "
                f"of names: {skill!r}"
            )
        # target 子步骤：单击选目标，动画在选完后才开始播，
        # 延后补第二击加速播放（延后双击）
        target_step = {
            "template": ",".join(f"角色池/{name}" for name in names),
            "double": TARGET_DOUBLE_DELAY,
        }
        if len(names) > 1:
            target_step["mode"] = "multi"
            target_step["count"] = 1
        steps.append(target_step)
    else:
        # 无 target：双击本体——第一击触发技能，第二击加速动画播放
        body["double"] = True
    return steps


# master 条目取值校验：只能是御主菜单里的技能序号 1/2/3
def _master_number(skill):
    value = skill.get("master")
    if isinstance(value, bool):
        raise ValueError(
            f"Skill entry 'master' must be 1, 2 or 3 (the Nth master skill "
            f"in the master menu), got {value!r}: {skill!r}"
        )
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = None
    if number not in (1, 2, 3):
        raise ValueError(
            f"Skill entry 'master' must be 1, 2 or 3 (the Nth master skill "
            f"in the master menu), got {value!r}: {skill!r}"
        )
    return number


_FLOWS[FLOW_STANDARD_FARM] = _build_standard_farm


__all__ = ["FLOW_STANDARD_FARM", "expand_flow"]
