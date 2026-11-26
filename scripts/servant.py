# 从 Mooncell 生成从者档案骨架：python scripts/servant.py <Mooncell页面名>
# 参数即 https://fgo.wiki/w/<参数> 的页面名（支持重定向页，如 杀狐 → 光之高扬斯卡娅）。
# 自动字段：名称/别称/职介/灵基名单/技能名注释
# 人工字段：立绘/图标/模板 映射（骨架里全部 null，生成后按提示补截图归属）
#
#   python scripts/servant.py 光之高扬斯卡娅            # 生成档案
#   python scripts/servant.py 杀狐 --print              # 只打印不落盘
#   python scripts/servant.py 摩根 --force              # 已有档案时覆盖重建（丢手工编辑）

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVANT_DIR = REPO_ROOT / "data" / "servants"
TEMPLATE_DIR = REPO_ROOT / "assets" / "template"
WIKI_BASE = "https://fgo.wiki/"
API = WIKI_BASE + "api.php"

STAGE_CHARS = {"一": 1, "二": 2, "三": 3, "四": 4, "１": 1, "２": 2, "３": 3, "４": 4}
# Windows 文件名非法字符（从者名一般不含，出现时替换并提示）
ILLEGAL_FILENAME = re.compile(r'[\\/:*?"<>|]')

try:
    sys.stdout.reconfigure(errors="replace")
except (AttributeError, ValueError):
    pass


def api(params):
    query = urllib.parse.urlencode({**params, "format": "json"})
    request = urllib.request.Request(
        f"{API}?{query}", headers={"User-Agent": "auto-chaldea-servant/0.1"}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except (OSError, ValueError) as error:
        raise SystemExit(f"Mooncell 请求失败：{error}")


def fetch_wikitext(page):
    # 参数 = /w/<页面名>；redirects=1 使命名页（杀狐等别称页）落到正式从者页
    data = api({"action": "parse", "page": page, "prop": "wikitext", "redirects": "1"})
    parse = data.get("parse") or {}
    text = (parse.get("wikitext") or {}).get("*") or ""
    if data.get("error") or not text:
        raise SystemExit(f"页面不存在或拉取失败：{WIKI_BASE}{urllib.parse.quote(page)}")
    return parse.get("title") or page, text


def template_blocks(text, head):
    # 抓取以 head（如 "{{宝具\n"）开头的完整模板块，花括号配对支持嵌套子模板
    blocks, start = [], text.find(head)
    while start != -1:
        depth, end = 0, start
        while end < len(text):
            if text.startswith("{{", end):
                depth += 1
                end += 2
            elif text.startswith("}}", end):
                depth -= 1
                end += 2
                if depth == 0:
                    break
            else:
                end += 1
        if depth == 0:
            blocks.append(text[start:end])
        start = text.find(head, end)
    return blocks


def block_params(block):
    # 模板块首行之后的 |key=value → dict（跨行值/嵌套子模板忽略，字段逐行书写）
    params = {}
    for line in block.splitlines()[1:]:
        if line.startswith("|"):
            key, _, value = line[1:].partition("=")
            params[key.strip()] = value.strip()
    return params


def parse_skill_names(text):
    # '''技能N（开放条件）''' 标记槽位；{{持有技能|分类|中文名|...}} 收集中文名，
    # 同槽位多个 = 强化链（含 Mooncell tabber 分形态描述）
    slots, current = {}, None
    pattern = re.compile(r"'''\s*技能(\d)（|\{\{持有技能\|([^|\n]*)\|([^|\n]*)\|")
    for match in pattern.finditer(text):
        if match.group(2) is None:
            current = match.group(1)
            slots.setdefault(current, [])
        elif current:
            name = match.group(3).strip()
            if name and name not in slots[current]:
                slots[current].append(name)
    return slots


def parse_servant(title, text):
    base_blocks = template_blocks(text, "{{基础数值\n")
    base = block_params(base_blocks[0]) if base_blocks else {}
    if not base:
        raise SystemExit(f"页面 {title!r} 不是从者页面（没有 基础数值 模板）")

    name = (base.get("中文名") or title).strip()
    class_name = (base.get("职阶") or "").strip()
    if not class_name:
        raise SystemExit(f"页面 {title!r} 缺少 职阶 字段")
    aliases = [
        a.strip() for a in re.split(r"[,，、]", base.get("昵称") or "") if a.strip()
    ]

    # 各阶段显示名：优先中文卡面名N（不同阶段不同名字的从者，如 U－奥尔加玛丽）
    battle_name = base.get("中文战斗名") or name
    stage_names = {
        1: base.get("中文卡面名") or battle_name,
        2: base.get("中文卡面名") or battle_name,
        3: base.get("中文卡面名3") or battle_name,
        4: base.get("中文卡面名4") or battle_name,
    }

    # 立绘N：第N阶段 → 灵基条目；其余标签（简易灵衣：X、扩大版等）→ 灵衣/变体条目
    stage_numbers, extras = [], []
    for key, label in base.items():
        if not re.fullmatch(r"立绘\d+", key) or not label:
            continue
        match = re.fullmatch(r"第([一二三四１-４])阶段", label)
        number = STAGE_CHARS.get(match.group(1)) if match else None
        if number:
            stage_numbers.append(number)
        else:
            extras.append(label)

    stages = [
        {"阶段": number, "名称": stage_names[number].strip()}
        for number in sorted(set(stage_numbers))
    ]
    if not stages:
        stages = [{"阶段": None, "名称": battle_name.strip()}]

    return {
        "name": name,
        "class": class_name,
        "aliases": aliases,
        "stages": stages,
        "extras": extras,
        "skills": parse_skill_names(text),
    }


def build_yaml(info):
    lines = [
        f"# 从者档案：{info['name']}（由 scripts/servant.py 生成，截图归属待人工登记）",
        "",
        f"名称: {info['name']}",
    ]
    if info["aliases"]:
        lines.append(f"别称: [{', '.join(info['aliases'])}]")
    lines.append(f"职介: {info['class']}")
    lines.append("")
    lines.append(f"角色池目录: {info['name']}")
    lines.append("")
    lines.append("灵基:")
    for stage in info["stages"]:
        lines.append(f"  - {{ 名称: {stage['名称']}, 立绘: null }}")
    for label in info["extras"]:
        lines.append(
            f"  - {{ 名称: {info['stages'][0]['名称']}, 立绘: null }}"
            f"   # 灵衣/变体：{label}"
        )
    lines.append("")
    lines.append("技能:")
    for slot in ("1", "2", "3"):
        names = info["skills"].get(slot) or []
        comment = f"   # {'，'.join(names)}" if names else ""
        lines.append(f"  {slot}: null{comment}")
    lines.append("")
    lines.append("宝具:")
    lines.append("  模板: null")
    return "\n".join(lines) + "\n"


def scan_local_templates():
    # 扫描本地模板库存，提示可归属的截图；归属判断仍需人工
    print()
    print("本地模板库存（归属需人工确认后填入档案）：")
    pool = sorted((TEMPLATE_DIR / "技能池").glob("skill_*.png"))
    numbers = [p.stem for p in pool]
    print(f"  技能池: {', '.join(numbers) if numbers else '（空）'}")
    portrait_dir = TEMPLATE_DIR / "角色池"
    if portrait_dir.is_dir():
        for directory in sorted(portrait_dir.iterdir()):
            if directory.is_dir():
                files = [p.stem for p in sorted(directory.glob("*.png"))]
                if files:
                    print(f"  角色池/{directory.name}: {', '.join(files)}")
    np_dir = TEMPLATE_DIR / "宝具"
    nps = [p.stem for p in sorted(np_dir.glob("*.png"))] if np_dir.is_dir() else []
    print(f"  宝具: {', '.join(nps) if nps else '（空）'}")


def main():
    parser = argparse.ArgumentParser(
        description="从 Mooncell 页面生成 data/servants/<职介>/<名称>.yaml 档案骨架"
    )
    parser.add_argument("page", help="Mooncell 页面名（https://fgo.wiki/w/<页面名>）")
    parser.add_argument("--force", action="store_true", help="已有档案时覆盖重建")
    parser.add_argument("--print", action="store_true", help="只打印骨架，不写文件")
    args = parser.parse_args()

    title, text = fetch_wikitext(args.page)
    info = parse_servant(title, text)

    filename = ILLEGAL_FILENAME.sub("＿", info["name"])
    if filename != info["name"]:
        print(f"提示：名称含非法文件名字符，文件名已替换为 {filename!r}")
    target = SERVANT_DIR / info["class"] / f"{filename}.yaml"
    yaml_text = build_yaml(info)

    if args.print:
        print(f"---- {target.relative_to(REPO_ROOT)} ----")
        print(yaml_text, end="")
    else:
        if target.exists() and not args.force:
            raise SystemExit(
                f"档案已存在：{target.relative_to(REPO_ROOT)}（--force 覆盖重建会丢失手工编辑）"
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml_text, encoding="utf-8")
        print(f"已生成：{target.relative_to(REPO_ROOT)}")

    print()
    print(f"名称={info['name']}  职介={info['class']}  别称={info['aliases'] or '无'}")
    print(f"灵基形态 {len(info['stages'])} 个 + 灵衣/变体 {len(info['extras'])} 个")
    print("待人工登记：立绘 / 技能图标 / 宝具模板（骨架中均为 null）")
    scan_local_templates()

    if not args.print:
        # 生成后立即用档案加载器校验，结构问题当场暴露
        sys.path.insert(0, str(REPO_ROOT / "src"))
        try:
            from auto_chaldea.core.servants import load_servants

            load_servants(force=True)
            print()
            print("档案校验通过 ✓")
        except Exception as error:  # noqa: BLE001 — 校验失败原样报告
            print()
            print(f"档案校验失败：{error}")


if __name__ == "__main__":
    main()
