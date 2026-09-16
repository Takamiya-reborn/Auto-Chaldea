from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ASSETS_DIR = REPO_ROOT / "assets"
ADB_PATH = ASSETS_DIR / "platform-tools" / "adb.exe"
TEMPLATE_DIR = ASSETS_DIR / "template"
TASK_DIR = ASSETS_DIR / "task"


__all__ = [
    "REPO_ROOT",
    "ASSETS_DIR",
    "ADB_PATH",
    "TEMPLATE_DIR",
    "TASK_DIR",
]
