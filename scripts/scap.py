import argparse
from datetime import datetime
from pathlib import Path
import re
import subprocess


def parse_port(value):
    try:
        port = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "端口号必须是 1 到 65535 之间的整数"
        ) from error
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("端口号必须是 1 到 65535 之间的整数")
    return port


def find_single_tcp_device(adb):
    result = subprocess.run(
        [str(adb), "devices"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    devices = []
    for line in (result.stdout or "").splitlines():
        parts = line.split()
        if (
            len(parts) >= 2
            and parts[1] == "device"
            and re.fullmatch(r"127\.0\.0\.1:\d+", parts[0])
        ):
            devices.append(parts[0])

    if len(devices) == 1:
        return devices[0]
    if not devices:
        print("未找到已连接的本地 TCP ADB 设备，请指定端口号。")
    else:
        print("检测到多个本地 TCP ADB 设备，请指定端口号：")
        print("、".join(devices))
    return None


def main():
    parser = argparse.ArgumentParser(description="从指定的本地 TCP ADB 设备截图")
    parser.add_argument(
        "port", nargs="?", type=parse_port, help="模拟器的 ADB TCP 端口，例如 5555"
    )
    args = parser.parse_args()

    adb = Path(__file__).resolve().parents[1] / "assets" / "platform-tools" / "adb.exe"
    device = f"127.0.0.1:{args.port}" if args.port else find_single_tcp_device(adb)
    if device is None:
        return 1
    connection = subprocess.run(
        [str(adb), "connect", device],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    connection_output = f"{connection.stdout}\n{connection.stderr}".lower()
    if connection.returncode != 0 or "connected to" not in connection_output:
        print(f"无法连接 ADB 设备：{device}")
        print((connection.stdout or connection.stderr).strip())
        return 1

    output_dir = Path(__file__).resolve().parents[1] / "assets" / "template"
    output_dir.mkdir(exist_ok=True)
    output = output_dir / datetime.now().strftime("%Y%m%d_%H%M%S.png")

    with output.open("wb") as file:
        screenshot = subprocess.run(
            [str(adb), "-s", device, "exec-out", "screencap", "-p"],
            stdout=file,
            check=False,
        )

    if screenshot.returncode != 0:
        output.unlink(missing_ok=True)
        print(f"设备截图失败：{device}")
        return screenshot.returncode

    print(f"截图已保存：{output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
