# FGO 风格滚动条：轨道完全透明，手柄是白底金边的细长六边形
#
# QSS 画不了六边形，这里继承 QScrollBar 全自绘。用
# install_hex_scrollbars(view) 装到 QAbstractScrollArea 上即可
# 同时替换横竖两条滚动条。

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QAbstractScrollArea, QHBoxLayout, QScrollBar, QWidget

_GOLD = "#dac254"
_TOP = "#ffffff"
_BOTTOM = "#e3ddc8"
_TRACK = "#3c3c3c"  # 轨道背景色（半透明灰）
_THICKNESS = 20  # 滚动条粗细
_MIN_LENGTH = 30  # 手柄最短长度
_TIP = 9  # 六边形尖端长度
_MARGIN = 1  # 手柄留白
_PROTRUDE = 3  # 手柄单侧超出轨道的量，制造层次感
_TRACK_ALPHA = 128  # 轨道不透明度（50%）
# 手柄正投影：与按钮同色的暗影。QPainter 没有高斯模糊，
# 用由内到外逐层变淡的同形描边模拟四周均匀扩散的软阴影
_SHADOW_COLOR = (18, 34, 54)  # 与 theme.py 按钮投影同色
_SHADOW_LAYERS = ((2, 100), (4, 70), (6, 40))  # (描边宽度, 不透明度)


class HexScrollBar(QScrollBar):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        if orientation == Qt.Vertical:
            self.setFixedWidth(_THICKNESS)
        else:
            self.setFixedHeight(_THICKNESS)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.maximum() > self.minimum():
            self._draw_track(painter)
            self._draw_handle(painter)
        painter.end()

    # 半透明灰色方形轨道，比手柄窄，让手柄凸出来
    def _draw_track(self, painter):
        vertical = self.orientation() == Qt.Vertical
        track = self.height() if vertical else self.width()
        cross = self.width() if vertical else self.height()

        color = QColor(_TRACK)
        color.setAlpha(_TRACK_ALPHA)
        width = max(4, cross - 2 * _PROTRUDE)
        pos = round((cross - width) / 2)
        if vertical:
            painter.fillRect(pos, 0, width, track, color)
        else:
            painter.fillRect(0, pos, track, width, color)

    # 六边形手柄横跨整个控件宽度，两侧盖在轨道上；不可用时整体压暗
    def _draw_handle(self, painter):
        vertical = self.orientation() == Qt.Vertical
        track = self.height() if vertical else self.width()
        cross = self.width() if vertical else self.height()

        span = self.maximum() - self.minimum()
        length = max(_MIN_LENGTH, round(track * self.pageStep() / (span + self.pageStep())))
        travel = track - length
        offset = round(travel * self.value() / span) if span > 0 else 0

        margin = _MARGIN
        tip = min(_TIP, max(5, length * 0.22))
        body = length - 2 * tip

        if vertical:
            x0, x1, xc = margin, cross - margin, cross / 2
            top, bottom = offset, offset + length
            points = [
                QPointF(xc, top),
                QPointF(x1, top + tip),
                QPointF(x1, bottom - tip),
                QPointF(xc, bottom),
                QPointF(x0, bottom - tip),
                QPointF(x0, top + tip),
            ]
            gradient = QLinearGradient(0, top, 0, bottom)
        else:
            y0, y1, yc = margin, cross - margin, cross / 2
            left, right = offset, offset + length
            points = [
                QPointF(left, yc),
                QPointF(left + tip, y1),
                QPointF(right - tip, y1),
                QPointF(right, yc),
                QPointF(right - tip, y0),
                QPointF(left + tip, y0),
            ]
            gradient = QLinearGradient(left, 0, right, 0)

        gradient.setColorAt(0.0, QColor(_TOP))
        gradient.setColorAt(1.0, QColor(_BOTTOM))

        path = QPainterPath()
        path.addPolygon(QPolygonF(points))
        path.closeSubpath()

        if self.isEnabled():
            self._draw_shadow(painter, path)
        painter.setPen(QPen(QColor(_GOLD), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(gradient)
        if not self.isEnabled():
            painter.setOpacity(0.4)
        painter.drawPath(path)

    # 手柄四周的正投影：逐层加宽描边、逐层变淡，外层被手柄填充盖住，
    # 只露出均匀的暗影边缘
    def _draw_shadow(self, painter, path):
        painter.setBrush(Qt.NoBrush)
        for width, alpha in _SHADOW_LAYERS:
            color = QColor(*_SHADOW_COLOR, alpha)
            painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPath(path)


# 把六边形滚动条装到滚动区域（同时替换横竖两条）
def install_hex_scrollbars(view):
    view.setVerticalScrollBar(HexScrollBar(Qt.Vertical, view))
    view.setHorizontalScrollBar(HexScrollBar(Qt.Horizontal, view))


# 仿游戏的独立滚动条：视图与滚动条并排成兄弟控件，内部竖向滚动条
# 隐藏（内容区不再被挤占），右侧立一根六边形进度条双向同步。
# 滚轮 / 键盘仍由视图内部处理，拖动外置手柄则回写内部滚动条。
class ScrollBox(QWidget):
    def __init__(self, view, parent=None):
        super().__init__(parent)
        self._view = view
        internal = view.verticalScrollBar()
        # 必须关掉策略而不是 setVisible：滚动区域布局每次重算都会按
        # ScrollBarAsNeeded 把隐藏的内部滚动条重新弹出来，叠在列表上
        view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._bar = HexScrollBar(Qt.Vertical, self)
        self._sync_steps()
        self._bar.setRange(internal.minimum(), internal.maximum())
        internal.valueChanged.connect(self._bar.setValue)
        self._bar.valueChanged.connect(internal.setValue)
        internal.rangeChanged.connect(self._sync_range)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(view, 1)
        layout.addWidget(self._bar)

    def _sync_steps(self):
        internal = self._view.verticalScrollBar()
        self._bar.setPageStep(internal.pageStep())
        self._bar.setSingleStep(internal.singleStep())

    def _sync_range(self, minimum, maximum):
        self._sync_steps()
        self._bar.setRange(minimum, maximum)
