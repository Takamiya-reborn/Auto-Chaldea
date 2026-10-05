import argparse
import subprocess
from pathlib import Path

import cv2
import numpy as np

IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}


def find_device(adb_path):
    result = subprocess.run(
        [str(adb_path), "devices"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "无法执行 adb devices").strip())

    devices = [
        line.split()[0]
        for line in (result.stdout or "").splitlines()
        if len(line.split()) >= 2 and line.split()[1] == "device"
    ]
    if len(devices) != 1:
        if not devices:
            raise RuntimeError("未找到在线 ADB 设备")
        raise RuntimeError(
            f"检测到多个在线 ADB 设备，请使用 --device 指定：{', '.join(devices)}"
        )
    return devices[0]


def capture_screen(adb_path, device):
    result = subprocess.run(
        [str(adb_path), "-s", device, "exec-out", "screencap", "-p"],
        capture_output=True,
        check=False,
        timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "设备截图失败：" + (result.stderr or b"").decode(errors="replace")
        )

    screen = cv2.imdecode(
        np.frombuffer(result.stdout, dtype=np.uint8), cv2.IMREAD_COLOR
    )
    if screen is None:
        raise RuntimeError("无法解析设备截图")
    return screen


def load_image(path):
    data = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def main():
    parser = argparse.ArgumentParser(description="检查设备屏幕与模板的最高矩阵匹配度")
    parser.add_argument("template_path", type=Path, help="模板图像路径")
    parser.add_argument("--device", help="ADB 设备序列号；未指定时要求恰好一个在线设备")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    adb_path = repo_root / "assets" / "platform-tools" / "adb.exe"
    template_path = args.template_path.resolve()
    if not template_path.is_file():
        parser.error(f"模板图像不存在：{template_path}")
    if template_path.suffix.lower() not in IMAGE_SUFFIXES:
        parser.error(f"不支持的模板图像格式：{template_path.suffix}")

    try:
        device = args.device or find_device(adb_path)
        screen = capture_screen(adb_path, device)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        parser.error(str(error))

    template = load_image(template_path)
    if template is None:
        parser.error(f"无法读取模板图像：{template_path}")
    if template.shape[0] > screen.shape[0] or template.shape[1] > screen.shape[1]:
        parser.error("模板图像尺寸大于设备屏幕")

    match = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, confidence, _, location = cv2.minMaxLoc(match)
    print(f"设备：{device}")
    print(f"模板：{template_path}")
    print(f"匹配度：{confidence:.6f}  位置=({location[0]}, {location[1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
