import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[3]
EXECUTABLE_ROOT = Path(sys.executable).resolve().parent
REPO_ROOT = EXECUTABLE_ROOT if (EXECUTABLE_ROOT / "assets").is_dir() else SOURCE_ROOT
ASSETS_DIR = REPO_ROOT / "assets"
ADB_PATH = ASSETS_DIR / "platform-tools" / "adb.exe"
TEMPLATE_DIR = ASSETS_DIR / "template"
TASK_DIR = ASSETS_DIR / "task"
QSS_DIR = ASSETS_DIR / "qss"
APP_QSS = QSS_DIR / "app.qss"


__all__ = [
    "ADB_PATH",
    "APP_QSS",
    "ASSETS_DIR",
    "QSS_DIR",
    "REPO_ROOT",
    "TASK_DIR",
    "TEMPLATE_DIR",
]
