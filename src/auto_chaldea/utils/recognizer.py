import cv2
import numpy as np
import subprocess
from pathlib import Path

from auto_chaldea.utils.adb_device import DeviceDisconnectedError
from auto_chaldea.utils.paths import ADB_PATH, TEMPLATE_DIR

DEFAULT_TEMPLATE_SUFFIX = ".png"


def _load_template(template_dir, template_path):
    """读取模板图像，缺少后缀时默认使用 PNG。"""
    path = Path(str(template_path))
    if not path.suffix:
        path = path.with_suffix(DEFAULT_TEMPLATE_SUFFIX)
    template_file = template_dir / path
    try:
        image_data = np.fromfile(template_file, dtype=np.uint8)
    except OSError:
        return None
    return cv2.imdecode(image_data, cv2.IMREAD_COLOR)


def _capture_screen(adb_path, region, device=None):
    """截取设备屏幕，并按区域裁剪。"""
    cmd = [str(adb_path)]
    if device:
        cmd += ["-s", str(device)]
    cmd += ["exec-out", "screencap", "-p"]
    try:
        res = subprocess.run(cmd, capture_output=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DeviceDisconnectedError("无法读取模拟器屏幕") from error
    if res.returncode != 0:
        raise DeviceDisconnectedError("模拟器已断开")

    img_array = np.frombuffer(res.stdout, dtype=np.uint8)
    screen = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if screen is None:
        raise DeviceDisconnectedError("无法解析模拟器屏幕")

    search_area = screen
    offset_x, offset_y = 0, 0
    if region:
        x1, y1, x2, y2 = region
        search_area = screen[y1:y2, x1:x2]
        offset_x, offset_y = x1, y1

    return search_area, offset_x, offset_y


def _prepare_match(template_path, adb_path, template_dir, region, device=None):
    """准备模板匹配所需的数据。"""
    captured = _capture_screen(adb_path, region, device)
    if captured is None:
        return None
    search_area, offset_x, offset_y = captured

    template = _load_template(template_dir, template_path)
    if template is None:
        return None

    template_height, template_width = template.shape[:2]
    if search_area.shape[0] < template_height or search_area.shape[1] < template_width:
        return None

    match_result = cv2.matchTemplate(search_area, template, cv2.TM_CCOEFF_NORMED)
    return match_result, template_width, template_height, offset_x, offset_y


def _extract_matches(
    res_match, template_width, template_height, offset_x, offset_y, threshold
):
    """提取阈值以上且互不重叠的匹配结果。"""
    matches = []
    while True:
        _, max_val, _, max_loc = cv2.minMaxLoc(res_match)
        if max_val < threshold:
            break

        left = offset_x + max_loc[0]
        top = offset_y + max_loc[1]
        matches.append(
            {
                "x": left + template_width // 2,
                "y": top + template_height // 2,
                "confidence": max_val,
                "left": left,
                "top": top,
                "width": template_width,
                "height": template_height,
            }
        )

        x1 = max(0, max_loc[0] - template_width // 2)
        y1 = max(0, max_loc[1] - template_height // 2)
        x2 = min(res_match.shape[1], max_loc[0] + template_width + template_width // 2)
        y2 = min(
            res_match.shape[0], max_loc[1] + template_height + template_height // 2
        )
        res_match[y1:y2, x1:x2] = 0.0

    return matches


def _rects_overlap(a, b):
    """判断两个匹配区域是否重叠。"""
    return (
        a["left"] < b["left"] + b["width"]
        and b["left"] < a["left"] + a["width"]
        and a["top"] < b["top"] + b["height"]
        and b["top"] < a["top"] + a["height"]
    )


def find_all_matches(
    template_path,
    adb_path=ADB_PATH,
    template_dir=TEMPLATE_DIR,
    region=None,
    threshold=0.7,
    device=None,
):
    """查找模板的全部匹配，并按屏幕位置排序。"""
    prepared = _prepare_match(template_path, adb_path, template_dir, region, device)
    if prepared is None:
        return []

    res_match, w, h, offset_x, offset_y = prepared

    matches = _extract_matches(res_match, w, h, offset_x, offset_y, threshold)
    matches.sort(key=lambda m: (m["y"], m["x"]))
    return [{"x": m["x"], "y": m["y"], "confidence": m["confidence"]} for m in matches]


def find_all_matches_multi(
    template_paths,
    top_n=None,
    adb_path=ADB_PATH,
    template_dir=TEMPLATE_DIR,
    region=None,
    threshold=0.7,
    device=None,
):
    """在同一张截图中匹配多个模板并返回前 N 个结果。"""
    if isinstance(template_paths, str):
        template_paths = [template_paths]

    captured = _capture_screen(adb_path, region, device)
    if captured is None:
        return []
    search_area, offset_x, offset_y = captured

    candidates = []
    for template_path in template_paths:
        template = _load_template(template_dir, template_path)
        if template is None:
            continue

        template_height, template_width = template.shape[:2]
        if (
            search_area.shape[0] < template_height
            or search_area.shape[1] < template_width
        ):
            continue

        res_match = cv2.matchTemplate(search_area, template, cv2.TM_CCOEFF_NORMED)
        for match in _extract_matches(
            res_match, template_width, template_height, offset_x, offset_y, threshold
        ):
            match["template"] = str(template_path)
            candidates.append(match)

    # 重叠时保留置信度更高的结果。
    candidates.sort(key=lambda m: m["confidence"], reverse=True)
    accepted = []
    for candidate in candidates:
        if any(_rects_overlap(candidate, kept) for kept in accepted):
            continue
        accepted.append(candidate)

    accepted.sort(key=lambda m: (m["y"], m["x"]))
    if top_n is not None:
        accepted = accepted[:top_n]

    return [
        {
            "x": m["x"],
            "y": m["y"],
            "confidence": m["confidence"],
            "template": m["template"],
        }
        for m in accepted
    ]


def find_best_match(
    template_path,
    adb_path=ADB_PATH,
    template_dir=TEMPLATE_DIR,
    region=None,
    threshold=0.8,
    device=None,
):
    """返回超过阈值的最高置信度结果。"""
    prepared = _prepare_match(template_path, adb_path, template_dir, region, device)
    if prepared is None:
        return None

    res_match, template_width, template_height, offset_x, offset_y = prepared
    _, max_val, _, max_loc = cv2.minMaxLoc(res_match)
    if max_val < threshold:
        return None

    return {
        "x": offset_x + max_loc[0] + template_width // 2,
        "y": offset_y + max_loc[1] + template_height // 2,
        "confidence": max_val,
    }
