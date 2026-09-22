"""Task configuration loading and validation helpers."""

import json
from pathlib import Path

from auto_chaldea.core.paths import TASK_DIR


def normalize_region(region):
    """Normalize a task region into a four-item tuple when possible."""
    if region in (None, "", [], (), {}):
        return None

    if isinstance(region, str):
        region = region.strip()
        if not region:
            return None
        values = [item.strip() for item in region.split(",")]
        if len(values) != 4:
            raise ValueError(f"Invalid region value: {region!r}")
        return tuple(int(value) for value in values)

    if isinstance(region, (list, tuple)) and len(region) == 4:
        return tuple(int(value) for value in region)

    return region


def load_tasks(task_dir=None):
    """Load task dictionaries from a directory, ignoring invalid files."""
    base_dir = Path(task_dir) if task_dir is not None else TASK_DIR
    if not base_dir.exists():
        return []

    return [task for _, task in _iter_task_files(base_dir)]


def load_task_files(task_dir=None):
    """Load task dictionaries together with their source file stems."""
    base_dir = Path(task_dir) if task_dir is not None else TASK_DIR
    if not base_dir.exists():
        return []

    return list(_iter_task_files(base_dir))


def _iter_task_files(base_dir):
    for json_path in sorted(base_dir.glob("*.json")):
        try:
            with json_path.open("r", encoding="utf-8") as file:
                task = json.load(file)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(task, dict):
            yield json_path.stem, task


def valid_steps(task):
    """Return task steps that contain a usable template name."""
    steps = task.get("steps", []) if isinstance(task, dict) else []
    return [step for step in steps if isinstance(step, dict) and step.get("template")]
