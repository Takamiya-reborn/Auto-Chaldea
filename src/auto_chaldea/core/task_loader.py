from pathlib import Path

import yaml

from auto_chaldea.utils.paths import TASK_DIR


def load_tasks(task_dir=None):
    """加载任务配置，跳过无法解析的文件。"""
    return [task for _, task in load_task_files(task_dir)]


def load_task_files(task_dir=None):
    """加载任务配置及其相对路径。"""
    base_dir = Path(task_dir) if task_dir is not None else TASK_DIR
    if not base_dir.exists():
        return []
    return list(_iter_task_files(base_dir))


def load_task_file(task_path):
    """按需加载单个任务文件，解析失败时返回 None。"""
    try:
        with Path(task_path).open("r", encoding="utf-8") as file:
            task = yaml.safe_load(file)
    except (OSError, yaml.YAMLError):
        return None
    return task if isinstance(task, dict) else None


def _iter_task_files(base_dir):
    yaml_files = sorted([*base_dir.rglob("*.yaml"), *base_dir.rglob("*.yml")])
    for yaml_path in yaml_files:
        try:
            with yaml_path.open("r", encoding="utf-8") as file:
                task = yaml.safe_load(file)
        except (OSError, yaml.YAMLError):
            continue
        if isinstance(task, dict):
            yield yaml_path.relative_to(base_dir).with_suffix("").as_posix(), task
