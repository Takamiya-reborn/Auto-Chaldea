from datetime import datetime
from pathlib import Path
import subprocess

adb = Path(__file__).resolve().parents[1] / "assets" / "platform-tools" / "adb.exe"
output_dir = Path(__file__).resolve().parent[1] / "assets" / "template"
output_dir.mkdir(exist_ok=True)
output = output_dir / datetime.now().strftime("%Y%m%d_%H%M%S.png")

with output.open("wb") as file:
    subprocess.run([str(adb), "exec-out", "screencap", "-p"], stdout=file, check=True)
