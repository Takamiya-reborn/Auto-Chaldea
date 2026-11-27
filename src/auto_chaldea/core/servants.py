# 从者档案：data/servants/<职介>/<名称>.yaml
# 为技能条目（skill）、选目标（target）、宝具（np）提供「角色引用 → 模板路径」的
# 解析；编写规则与档案字段说明见 docs/task-yail.md 的「从者档案」一节。
# null 字段 = 待截图登记：档案可以留空慢慢补，只有任务引用到时才会报错。

import re
from pathlib import Path

import yaml

from auto_chaldea.utils.paths import SERVANT_DIR

SKILL_SLOTS = ("1", "2", "3")

_DB = None


# 名称/昵称/引用的归一化：去空白、全角－转半角，匹配时忽略这两类书写差异
def normalize_name(value):
    return re.sub(r"\s+", "", str(value)).replace("－", "-")


def _icon_templates(value, context):
    # 技能图标值：技能池序号（int）或并列列表（同一技能的多个图标变体，任一命中）
    if value is None:
        return None
    numbers = [value] if isinstance(value, int) else value
    if not isinstance(numbers, list) or not numbers:
        raise ValueError(f"{context}: 技能图标须为技能池序号或序号列表，got {value!r}")
    templates = []
    for number in numbers:
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            raise ValueError(f"{context}: 非法技能池序号 {number!r}")
        templates.append(f"技能池/skill_{number}")
    return templates


def _portrait_names(value, context):
    # 立绘/模板值：null / 单文件名 / 文件名列表（多形态并列），统一为列表或 None；
    # 纯数字文件名（灵基阶段立绘）允许直接写数字
    if value is None:
        return None
    names = [value] if isinstance(value, (str, int)) else value
    if (
        not isinstance(names, list)
        or not names
        or not all(isinstance(name, (str, int)) and str(name).strip() for name in names)
    ):
        raise ValueError(f"{context}: 须为文件名或文件名列表，got {value!r}")
    return [str(name).strip() for name in names]


class Servant:
    # 单份档案：字段校验 + 技能组归一化（单技能组档案的组键固定为 None）
    def __init__(self, data, path):
        self.path = path
        self.name = str(data.get("名称") or "").strip()
        if not self.name:
            raise ValueError(f"{path}: 缺少 名称 字段")
        class_name = str(data.get("职介") or "").strip()
        if class_name != path.parent.name:
            raise ValueError(
                f"{path}: 职介 {class_name!r} 与目录名 {path.parent.name!r} 不一致"
            )
        self.class_name = class_name
        aliases = data.get("昵称") or []
        if isinstance(aliases, str):
            aliases = [aliases]
        self.aliases = [str(alias).strip() for alias in aliases if str(alias).strip()]
        self.portrait_dir = str(data.get("角色池目录") or self.name).strip()

        forms = data.get("灵基")
        if not isinstance(forms, list) or not forms:
            raise ValueError(f"{path}: 灵基 须为非空列表")
        self.forms = []
        for index, form in enumerate(forms, start=1):
            if not isinstance(form, dict) or not str(form.get("名称") or "").strip():
                raise ValueError(f"{path}: 灵基第{index}条缺少 名称")
            self.forms.append(
                {
                    "名称": str(form["名称"]).strip(),
                    "立绘": _portrait_names(form.get("立绘"), f"{path} 灵基第{index}条 立绘"),
                    "技能组": form.get("技能组"),
                }
            )

        self.skills = self._load_skills(data.get("技能"))
        self.np_templates = _portrait_names(data.get("宝具", {}).get("模板"), f"{path} 宝具 模板")

        # 分组技能时，每条灵基必须声明有效的 技能组；单技能组档案忽略该字段
        if None not in self.skills:
            for index, form in enumerate(self.forms, start=1):
                if form["技能组"] not in self.skills:
                    raise ValueError(
                        f"{path}: 灵基第{index}条的 技能组 {form['技能组']!r} 不存在，"
                        f"可用技能组：{list(self.skills)}"
                    )

    def _load_skills(self, value):
        if not isinstance(value, dict) or not value:
            raise ValueError(f"{self.path}: 技能 须为非空映射")
        # 顶层键全是 1/2/3 → 单技能组；否则键为技能组名
        groups = {None: value} if {str(key) for key in value} <= set(SKILL_SLOTS) else value
        parsed = {}
        for group, slots in groups.items():
            if not isinstance(slots, dict):
                raise ValueError(f"{self.path}: 技能组 {group!r} 须为映射")
            slots_parsed = {}
            for slot, icon in slots.items():
                if str(slot) not in SKILL_SLOTS:
                    raise ValueError(f"{self.path}: 技能序号须为 1/2/3，got {slot!r}")
                slots_parsed[str(slot)] = _icon_templates(
                    icon, f"{self.path} 技能{slot}"
                )
            parsed[group if group is None else str(group)] = slots_parsed
        return parsed

    def keys(self):
        return [self.name, *self.aliases]


class ServantDB:
    # 名称 + 昵称 → 档案；键冲突即失败（引用歧义在加载期暴露）
    def __init__(self, servants):
        self._by_key = {}
        for servant in servants:
            for key in servant.keys():
                normalized = normalize_name(key)
                if not normalized:
                    continue
                existing = self._by_key.get(normalized)
                if existing is not None and existing is not servant:
                    raise ValueError(
                        f"角色键 {key!r} 同时出现在 {existing.path.name} 与 "
                        f"{servant.path.name}，请改用不同昵称"
                    )
                self._by_key[normalized] = servant

    def resolve(self, name):
        return self._by_key.get(normalize_name(name))

    def registered_keys(self):
        return sorted(self._by_key)


def load_servants(force=False):
    # 加载并缓存全部档案；force=True 用于档案修改后的强制重载
    global _DB
    if _DB is None or force:
        if not SERVANT_DIR.exists():
            raise ValueError(f"从者档案目录不存在：{SERVANT_DIR}")
        servants = []
        for path in sorted(SERVANT_DIR.rglob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError(f"{path}: 档案须为映射")
            servants.append(Servant(data, path))
        _DB = ServantDB(servants)
    return _DB


def resolve_skill(ref):
    # "名字/技能号" 或 "名字/技能组/技能号" →
    # {"templates": [...], "label": 原文, "servant": 角色名}
    db = load_servants()
    parts = [part.strip() for part in str(ref).split("/")]
    if len(parts) == 2:
        name, slot = parts
        group_name = None
    elif len(parts) == 3:
        name, group_name, slot = parts
    else:
        raise ValueError(
            f"skill 引用 {ref!r} 须为 名字/技能号 或 名字/技能组/技能号"
        )
    if slot not in SKILL_SLOTS:
        raise ValueError(f"skill 引用 {ref!r} 的技能号须为 1/2/3，got {slot!r}")
    servant = db.resolve(name)
    if servant is None:
        raise ValueError(
            f"skill 引用 {ref!r}：未登记的角色 {name!r}，已登记：{db.registered_keys()}"
        )
    if None in servant.skills:
        if group_name is not None:
            raise ValueError(
                f"skill 引用 {ref!r}：{servant.name} 是单技能组档案，不需要写技能组"
            )
        group = servant.skills[None]
    else:
        group_names = list(servant.skills)
        if group_name is None:
            # 多技能组省略组名：仅当各组该技能的图标完全一致时才允许（组切换不影响引用）
            candidates = [servant.skills[group][slot] for group in group_names]
            if any(candidate != candidates[0] for candidate in candidates[1:]):
                raise ValueError(
                    f"skill 引用 {ref!r}：{servant.name} 有多个技能组 {group_names} "
                    f"且技能{slot}图标不同，请写 名字/技能组/技能号 消歧"
                )
            group = servant.skills[group_names[0]]
        elif group_name not in servant.skills:
            raise ValueError(
                f"skill 引用 {ref!r}：{servant.name} 没有技能组 {group_name!r}，"
                f"可用：{group_names}"
            )
        else:
            group = servant.skills[group_name]
    templates = group[slot]
    if not templates:
        raise ValueError(
            f"skill 引用 {ref!r}：{servant.name} 的技能{slot}图标未登记"
            f"（{servant.path.name}），请先补 技能池 截图并填入档案"
        )
    return {"templates": templates, "label": str(ref).strip(), "servant": servant.name}


def resolve_troop(entries):
    # troop 字段 → 归一化名/昵称 → 位次列表（1 起）。
    # 位次 = 队伍顺序（1-3 人），决定技能栏分区（1/2/3号位）；同名多副本
    # （自出 + 助战）合法，此时一个名字对应多个位次，
    # 引用其技能时须写 "N号位名字/技能号" 前缀消歧
    if not isinstance(entries, list) or not 1 <= len(entries) <= 3:
        raise ValueError(
            f"troop 须为位次顺序的从者名列表（1-3 人）: {entries!r}"
        )
    db = load_servants()
    positions = {}
    for position, entry in enumerate(entries, 1):
        if not isinstance(entry, str) or not entry.strip():
            raise ValueError(f"troop 第{position}位须为从者名: {entry!r}")
        servant = db.resolve(entry)
        if servant is None:
            raise ValueError(
                f"troop 第{position}位 {entry!r}：未登记的角色，"
                f"已登记：{db.registered_keys()}"
            )
        for key in servant.keys():
            positions.setdefault(normalize_name(key), []).append(position)
    return positions


def resolve_target(ref):
    # 角色引用 → 角色池模板列表；非角色引用返回 None（调用方按原始模板路径处理）
    # 名字            → 该角色全部已登记立绘（多形态并列，任一命中）
    # 名字/立绘编号    → 指定立绘编号
    # 名字/形态名      → 按灵基显示名或立绘文件名过滤（如 摩根/冬之女王）
    db = load_servants()
    parts = [part.strip() for part in str(ref).split("/")]
    if len(parts) > 2:
        raise ValueError(f"target {ref!r} 段数过多，须为 名字 或 名字/形态")
    servant = db.resolve(parts[0])
    if servant is None:
        return None
    directory = servant.portrait_dir
    if len(parts) == 1:
        names = []
        for form in servant.forms:
            for portrait in form["立绘"] or []:
                if portrait not in names:
                    names.append(portrait)
        if not names:
            raise ValueError(
                f"target {ref!r}：{servant.name} 的灵基立绘均未登记"
                f"（{servant.path.name}），请先补 角色池 截图并填入档案"
            )
    else:
        selector = parts[1]
        if selector.isdigit():
            registered = sorted(
                {
                    portrait
                    for form in servant.forms
                    for portrait in form["立绘"] or []
                }
            )
            if selector not in registered:
                raise ValueError(
                    f"target {ref!r}：{servant.name} 未登记立绘 {selector}，"
                    f"已登记：{registered}"
                )
            names = [selector]
        else:
            matched = []
            for form in servant.forms:
                portraits = form["立绘"] or []
                if normalize_name(selector) == normalize_name(form["名称"]) or selector in portraits:
                    for portrait in portraits:
                        if portrait not in matched:
                            matched.append(portrait)
            if not matched:
                raise ValueError(
                    f"target {ref!r}：{servant.name} 没有形态或立绘 {selector!r}，"
                    f"可用形态：{sorted({form['名称'] for form in servant.forms})}"
                )
            names = matched
    return [f"角色池/{directory}/{name}" for name in names]


def resolve_np(name):
    # 角色引用 → 宝具模板列表（强化改名并列，任一命中）；非角色引用返回 None
    db = load_servants()
    servant = db.resolve(name)
    if servant is None:
        return None
    if not servant.np_templates:
        raise ValueError(
            f"np {name!r}：{servant.name} 的宝具模板未登记"
            f"（{servant.path.name}），请先补 宝具 截图并填入档案"
        )
    return [f"宝具/{template}" for template in servant.np_templates]
