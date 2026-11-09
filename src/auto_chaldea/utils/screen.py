# 屏幕帧来源：统一截屏 + 最近一帧缓存（原始格式优先、点击后失效、ROI 缓存）。
# 缓存语义见 README「屏幕帧复用」一节

import struct
import subprocess
import threading

import cv2
import numpy as np

from auto_chaldea.utils.adb_device import DeviceDisconnectedError
from auto_chaldea.utils.paths import ADB_PATH
from auto_chaldea.utils.process import hidden_window_kwargs

# screencap 原始输出头部：uint32（小端）宽、高、格式，新系统多一个色彩空间字段
# 因此头部长度可能是 12 或 16 字节，两种都尝试解析
_RAW_CANDIDATE_HEADERS = (16, 12)
# 像素格式常量（android graphics PixelFormat）
_RAW_FORMAT_RGBA = 1
_RAW_FORMAT_BGRA = 5
# 解析出的宽高超出该范围视为格式不符，走 PNG 兜底
_MAX_CAPTURE_DIM = 8192


class ScreenSource:
    # 单个设备的帧来源；capture() 返回缓存帧，调用方不得修改返回的数组
    def __init__(self, adb_path=ADB_PATH, device=None):
        self._adb_path = adb_path
        self._device = device
        self._lock = threading.Lock()
        self._frame = None
        self._raw_disabled = False
        # 模板标识 → 最近命中矩形 (x1, y1, x2, y2)，全屏坐标系
        self._roi_cache = {}

    # ---- 帧缓存 ----

    # 清空帧缓存：点击等输入操作后、重试下一轮前调用
    def invalidate(self):
        with self._lock:
            self._frame = None

    # 返回最近一帧（BGR）；缓存失效时重新截屏
    def capture(self):
        with self._lock:
            if self._frame is None:
                self._frame = self._screencap()
            return self._frame

    # 整帧 + 区域裁剪，返回 (裁剪图, 偏移 x, 偏移 y)；region 为全屏坐标
    def crop(self, region):
        frame = self.capture()
        if not region:
            return frame, 0, 0
        x1, y1, x2, y2 = region
        return frame[y1:y2, x1:x2], x1, y1

    # ---- ROI 缓存 ----

    def get_cached_roi(self, template_key):
        return self._roi_cache.get(str(template_key))

    # 记录模板最近命中位置（含余量），下次小范围搜索
    def set_cached_roi(self, template_key, rect):
        self._roi_cache[str(template_key)] = tuple(int(value) for value in rect)

    def clear_cached_roi(self, template_key):
        self._roi_cache.pop(str(template_key), None)

    # ---- 截屏实现 ----

    def _screencap(self):
        if not self._raw_disabled:
            frame = self._screencap_raw()
            if frame is not None:
                return frame
            # 原始格式解析失败：记住并改走 PNG，避免每次都双倍开销
            self._raw_disabled = True
        return self._screencap_png()

    def _run_screencap(self, png):
        command = [str(self._adb_path)]
        if self._device:
            command += ["-s", str(self._device)]
        command += ["exec-out", "screencap"]
        if png:
            command.append("-p")
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                timeout=15,
                **hidden_window_kwargs(),
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise DeviceDisconnectedError("无法读取模拟器屏幕") from error
        if result.returncode != 0:
            raise DeviceDisconnectedError("模拟器已断开")
        return result.stdout

    def _screencap_raw(self):
        return _decode_raw_screencap(self._run_screencap(png=False))

    def _screencap_png(self):
        data = self._run_screencap(png=True)
        frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise DeviceDisconnectedError("无法解析模拟器屏幕")
        return frame


# 解析 screencap 原始输出为 BGR 帧；格式不符返回 None（交给 PNG 兜底）
def _decode_raw_screencap(data):
    if not data:
        return None
    for header_size in _RAW_CANDIDATE_HEADERS:
        if len(data) <= header_size:
            continue
        width, height, pixel_format = struct.unpack_from("<III", data, 0)
        if not (
            0 < width <= _MAX_CAPTURE_DIM
            and 0 < height <= _MAX_CAPTURE_DIM
            and pixel_format in (_RAW_FORMAT_RGBA, _RAW_FORMAT_BGRA)
        ):
            continue
        expected = header_size + width * height * 4
        if len(data) < expected:
            continue
        pixels = np.frombuffer(
            data, dtype=np.uint8, count=width * height * 4, offset=header_size
        ).reshape(height, width, 4)
        code = (
            cv2.COLOR_RGBA2BGR
            if pixel_format == _RAW_FORMAT_RGBA
            else cv2.COLOR_BGRA2BGR
        )
        return cv2.cvtColor(pixels, code)
    return None


# 按设备复用的帧来源注册表：任务执行与界面共用同一实例，
# 点击失效与帧缓存的语义才能跨调用保持
_SCREENS = {}
_SCREENS_LOCK = threading.Lock()


def get_screen(adb_path=ADB_PATH, device=None):
    key = (str(adb_path), str(device) if device else None)
    with _SCREENS_LOCK:
        screen = _SCREENS.get(key)
        if screen is None:
            screen = ScreenSource(adb_path=adb_path, device=device)
            _SCREENS[key] = screen
        return screen


__all__ = ["ScreenSource", "get_screen"]
