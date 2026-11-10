# 类 Pinia 的响应式状态仓：命名键值 + 变更信号，界面与执行引擎共用。
# 写入可在任意线程（引擎在工作线程递减剩余轮数，GIL 保证整型写原子）；
# 观察一律通过 Qt 信号——工作线程发出的信号自动排队投递到主线程，
# 界面无需自己处理跨线程回调。core 引擎不导入本模块，只依赖鸭子类型
# 的 get / decrement 两个方法（见 graph_runner 的 store 参数说明）

from PySide6.QtCore import QObject, Signal


class RunStateStore(QObject):
    # 任意键变更 (key, value)；界面借此刷新「第 X/Y 轮」前缀
    changed = Signal(str, object)
    # 新一轮周回开始：当前第几轮（从 1 起）。覆盖两种开始方式——
    # worker 进入图前的首轮，与结算中命中连续出击开启的后续轮
    run_started = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._values = {}

    # ---- 会话生命周期 ----

    # 开始一次执行会话：total = 计划周回轮数，remaining = 尚未开始的轮数。
    # 当前轮号 = total - remaining（递减后计算，无需额外状态）；
    # last_total 留作下次执行弹窗的初值，clear_session 不清除
    def begin_session(self, total):
        total = int(total)
        self._values["total"] = total
        self._values["remaining"] = total
        self._values["last_total"] = total
        self.changed.emit("total", total)
        self.changed.emit("remaining", total)

    # 会话结束 / 切换任务：清掉本轮计数，保留 last_total
    def clear_session(self):
        self._values.pop("total", None)
        self._values.pop("remaining", None)
        self.changed.emit("total", 0)

    # ---- 读写 ----

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value):
        self._values[key] = value
        self.changed.emit(key, value)

    # 递减并广播；key == "remaining" 时额外发 run_started（当前轮号）。
    # 返回递减后的值，供引擎日志打印剩余量
    def decrement(self, key, by=1):
        value = int(self._values.get(key, 0)) - int(by)
        self._values[key] = value
        self.changed.emit(key, value)
        if key == "remaining":
            self.run_started.emit(self.current_run)
        return value

    # ---- 只读视图 ----

    @property
    def remaining(self):
        return int(self._values.get("remaining", 0))

    @property
    def total(self):
        return int(self._values.get("total", 0))

    @property
    def current_run(self):
        return self.total - self.remaining


__all__ = ["RunStateStore"]
