from pathlib import Path

import cv2
import numpy as np

from auto_chaldea.utils.paths import ADB_PATH, TEMPLATE_DIR
from auto_chaldea.utils.screen import get_screen

DEFAULT_TEMPLATE_SUFFIX = ".png"


# 读取模板图像，缺少后缀时默认使用 PNG
def _load_template(template_dir, template_path):
    path = Path(str(template_path))
    if not path.suffix:
        path = path.with_suffix(DEFAULT_TEMPLATE_SUFFIX)
    template_file = template_dir / path
    try:
        image_data = np.fromfile(template_file, dtype=np.uint8)
    except OSError:
        return None
    return cv2.imdecode(image_data, cv2.IMREAD_COLOR)


# 在 frame 的 rect 区域 (x1, y1, x2, y2) 内做模板匹配，
# 返回带全屏坐标的匹配列表
def _match_in_region(template, frame, rect, threshold):
    x1, y1, x2, y2 = rect
    search_area = frame[y1:y2, x1:x2]
    template_height, template_width = template.shape[:2]
    if search_area.shape[0] < template_height or search_area.shape[1] < template_width:
        return []

    res_match = cv2.matchTemplate(search_area, template, cv2.TM_CCOEFF_NORMED)
    return _extract_matches(
        res_match, template_width, template_height, x1, y1, threshold
    )


# 提取阈值以上且互不重叠的匹配结果（坐标已加回全屏偏移）
def _extract_matches(
    res_match, template_width, template_height, offset_x, offset_y, threshold
):
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


# 只保留调用方需要的字段并按屏幕位置排序
def _compact_matches(matches):
    matches = [
        {"x": m["x"], "y": m["y"], "confidence": m["confidence"]} for m in matches
    ]
    matches.sort(key=lambda m: (m["y"], m["x"]))
    return matches


# 判断两个匹配区域是否重叠
def _rects_overlap(a, b):
    return (
        a["left"] < b["left"] + b["width"]
        and b["left"] < a["left"] + a["width"]
        and a["top"] < b["top"] + b["height"]
        and b["top"] < a["top"] + a["height"]
    )


# 区域裁剪到帧范围内，返回 (search_area, offset_x, offset_y)
def _crop_frame(frame, region):
    if region is None:
        return frame, 0, 0
    x1, y1, x2, y2 = region
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2 = min(frame.shape[1], int(x2))
    y2 = min(frame.shape[0], int(y2))
    return frame[y1:y2, x1:x2], x1, y1


def find_all_matches(
    template_path,
    adb_path=ADB_PATH,
    template_dir=TEMPLATE_DIR,
    region=None,
    threshold=0.7,
    device=None,
    screen=None,
):
    # 查找模板的全部匹配，并按屏幕位置排序。
    # 每次都在声明区域内全量搜索：同一模板在屏上可能有多个实例，
    # 且目标实例会随回合变化，缓存上次命中位置会锁死搜索范围
    if screen is None:
        screen = get_screen(adb_path=adb_path, device=device)

    template = _load_template(template_dir, template_path)
    if template is None:
        return []

    frame = screen.capture()
    frame_width, frame_height = frame.shape[1], frame.shape[0]
    if region is None:
        region = (0, 0, frame_width, frame_height)

    matches = _match_in_region(template, frame, region, threshold)
    return _compact_matches(matches)


def find_all_matches_multi(
    template_paths,
    top_n=None,
    adb_path=ADB_PATH,
    template_dir=TEMPLATE_DIR,
    region=None,
    threshold=0.7,
    device=None,
    screen=None,
):
    # 在同一帧截图中匹配多个模板并返回前 N 个结果
    if isinstance(template_paths, str):
        template_paths = [template_paths]

    if screen is None:
        screen = get_screen(adb_path=adb_path, device=device)

    frame = screen.capture()
    search_area, offset_x, offset_y = _crop_frame(frame, region)

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
    screen=None,
):
    # 返回超过阈值的最高置信度结果
    if screen is None:
        screen = get_screen(adb_path=adb_path, device=device)

    template = _load_template(template_dir, template_path)
    if template is None:
        return None

    frame = screen.capture()
    search_area, offset_x, offset_y = _crop_frame(frame, region)

    template_height, template_width = template.shape[:2]
    if search_area.shape[0] < template_height or search_area.shape[1] < template_width:
        return None

    res_match = cv2.matchTemplate(search_area, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res_match)
    if max_val < threshold:
        return None

    return {
        "x": offset_x + max_loc[0] + template_width // 2,
        "y": offset_y + max_loc[1] + template_height // 2,
        "confidence": max_val,
    }
