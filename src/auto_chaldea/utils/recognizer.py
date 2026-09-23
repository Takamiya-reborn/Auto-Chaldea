import cv2
import numpy as np
import subprocess
from pathlib import Path

from auto_chaldea.utils.paths import ADB_PATH, TEMPLATE_DIR

DEFAULT_TEMPLATE_SUFFIX = ".png"


def _load_template(template_dir, template_path):
    """Load a template image, appending the default suffix when none is given."""
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
    """Capture the device screen and return the (possibly cropped) search area."""
    cmd = [str(adb_path)]
    if device:
        cmd += ["-s", str(device)]
    cmd += ["exec-out", "screencap", "-p"]
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

    return search_area, offset_x, offset_y


def _prepare_match(template_path, adb_path, template_dir, region, device=None):
    """Capture the screen and prepare template-matching inputs."""
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


def _extract_matches(res_match, template_width, template_height, offset_x, offset_y, threshold):
    """Greedily extract non-overlapping matches above the threshold from a match result."""
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
        y2 = min(res_match.shape[0], max_loc[1] + template_height + template_height // 2)
        res_match[y1:y2, x1:x2] = 0.0

    return matches


def _rects_overlap(a, b):
    """Return True if two matches (with left/top/width/height) cover overlapping areas."""
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
    threshold=0.8,
    device=None,
):
    """Return all valid matches for the given template, sorted by screen position."""
    prepared = _prepare_match(template_path, adb_path, template_dir, region, device)
    if prepared is None:
        return []

    res_match, w, h, offset_x, offset_y = prepared

    matches = _extract_matches(res_match, w, h, offset_x, offset_y, threshold)
    matches.sort(key=lambda m: (m["y"], m["x"]))
    return [
        {"x": m["x"], "y": m["y"], "confidence": m["confidence"]} for m in matches
    ]


def find_all_matches_multi(
    template_paths,
    top_n=None,
    adb_path=ADB_PATH,
    template_dir=TEMPLATE_DIR,
    region=None,
    threshold=0.8,
    device=None,
):
    """Match multiple templates against one screenshot and return the top N matches.

    Each template is matched against a single screen capture; overlapping hits from
    different templates are deduplicated (higher confidence wins). Results are sorted
    top-to-bottom, then left-to-right, and truncated to ``top_n`` (all if None).
    """
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
        if search_area.shape[0] < template_height or search_area.shape[1] < template_width:
            continue

        res_match = cv2.matchTemplate(search_area, template, cv2.TM_CCOEFF_NORMED)
        for match in _extract_matches(res_match, template_width, template_height, offset_x, offset_y, threshold):
            match["template"] = str(template_path)
            candidates.append(match)

    # Deduplicate across templates: keep the higher-confidence match when hits overlap.
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
    """Return the highest-confidence match for the given template, if it exceeds the threshold."""
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
