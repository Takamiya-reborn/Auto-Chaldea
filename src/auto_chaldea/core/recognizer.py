import cv2
import numpy as np
import subprocess

from auto_chaldea.core.paths import ADB_PATH, TEMPLATE_DIR


def _prepare_match(template_path, adb_path, template_dir, region):
    """Capture the screen and prepare template-matching inputs."""
    cmd = [str(adb_path), "exec-out", "screencap", "-p"]
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0:
        return None

    img_array = np.frombuffer(res.stdout, dtype=np.uint8)
    screen = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if screen is None:
        return None

    search_area = screen
    offset_x, offset_y = 0, 0
    if region:
        x1, y1, x2, y2 = region
        search_area = screen[y1:y2, x1:x2]
        offset_x, offset_y = x1, y1

    template = cv2.imread(str(template_dir / template_path))
    if template is None:
        return None

    template_height, template_width = template.shape[:2]
    if search_area.shape[0] < template_height or search_area.shape[1] < template_width:
        return None

    match_result = cv2.matchTemplate(search_area, template, cv2.TM_CCOEFF_NORMED)
    return match_result, template_width, template_height, offset_x, offset_y


def find_all_matches(
    template_path,
    adb_path=ADB_PATH,
    template_dir=TEMPLATE_DIR,
    region=None,
    threshold=0.8,
):
    """Return all valid matches for the given template, sorted by screen position."""
    prepared = _prepare_match(template_path, adb_path, template_dir, region)
    if prepared is None:
        return []

    res_match, w, h, offset_x, offset_y = prepared

    matches = []
    while True:
        _, max_val, _, max_loc = cv2.minMaxLoc(res_match)
        if max_val < threshold:
            break

        matches.append(
            {
                "x": offset_x + max_loc[0] + w // 2,
                "y": offset_y + max_loc[1] + h // 2,
                "confidence": max_val,
            }
        )

        # Clear the matched area and nearby pixels to avoid duplicate hits.
        x1 = max(0, max_loc[0] - w // 2)
        y1 = max(0, max_loc[1] - h // 2)
        x2 = min(res_match.shape[1], max_loc[0] + w + w // 2)
        y2 = min(res_match.shape[0], max_loc[1] + h + h // 2)
        res_match[y1:y2, x1:x2] = 0.0

    matches.sort(key=lambda m: (m["y"], m["x"]))
    return matches


def find_best_match(
    template_path,
    adb_path=ADB_PATH,
    template_dir=TEMPLATE_DIR,
    region=None,
    threshold=0.8,
):
    """Return the highest-confidence match for the given template, if it exceeds the threshold."""
    prepared = _prepare_match(template_path, adb_path, template_dir, region)
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
