from pathlib import Path

import yaml

from auto_chaldea.core.flows import expand_flow
from auto_chaldea.utils.paths import TASK_DIR


def load_tasks(task_dir=None):
    return [task for _, task in load_task_files(task_dir)]


# 加载任务配置及其相对路径
def load_task_files(task_dir=None):
    base_dir = Path(task_dir) if task_dir is not None else TASK_DIR
    if not base_dir.exists():
        return []
    return list(_iter_task_files(base_dir))


# 按需加载单个任务文件，解析失败时返回 None。
# 任务必须是图（手写 nodes 或 flow 展开得到），没有 'nodes' 的文件会被跳过
def load_task_file(task_path):
    try:
        with Path(task_path).open("r", encoding="utf-8") as file:
            task = yaml.safe_load(file)
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(task, dict):
        return None
    # flow 任务在此统一展开为图任务，UI 与执行器拿到的都是展开后的形态
    try:
        task = expand_flow(task)
    except ValueError as error:
        print(f"[task] flow expansion failed: {error}")
        return None
    if not task.get("nodes"):
        print(
            f"[task] {Path(task_path).name}: no 'nodes' after flow expansion; "
            f"only graph tasks are supported, skipped"
        )
        return None
    return task


def _iter_task_files(base_dir):
    yaml_files = sorted([*base_dir.rglob("*.yaml"), *base_dir.rglob("*.yml")])
    for yaml_path in yaml_files:
        task = load_task_file(yaml_path)
        if task is not None:
            yield yaml_path.relative_to(base_dir).with_suffix("").as_posix(), task
