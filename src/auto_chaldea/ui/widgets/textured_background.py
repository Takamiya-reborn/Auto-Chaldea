# FGO 风格的质感背景：横向渐变 + 低多边形三角面片 + 斜向光带 + 斜格子纹理
#
# QSS 的 background 只能画纯渐变，这里用 QPainter 在渐变上叠加
# 一层半透明的三角面片（jittered grid 拼成的无缝网格）、几道
# 斜向光带和细斜格子。几何用固定种子生成，同一尺寸下重绘结果
# 一致，不随每次 repaint 闪烁。

import random

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

# 与 app.qss 里 QMainWindow / centralCanvas 的渐变保持一致
GRADIENT_STOPS = [
    (0.0, "#7ba9ba"),
    (0.1, "#719bb0"),
    (0.2, "#688ea6"),
    (0.3, "#60839c"),
    (0.4, "#597994"),
    (0.5, "#54718d"),
    (0.6, "#50708f"),
    (0.7, "#4b7395"),
    (0.8, "#47769c"),
    (0.9, "#4279a0"),
    (1.0, "#3d76a2"),
]

_SEED = 2026  # 固定种子，保证同一尺寸下几何稳定
_CELL = 190  # 面片网格基准边长（px），越小面片越细密
_GRID_SPACING = 130  # 斜格子间距（px）


def _build_layers(width, height):
    rng = random.Random(_SEED)

    cols = max(2, round(width / _CELL) + 1)
    rows = max(2, round(height / _CELL) + 1)
    cell_w = width / (cols - 1)
    cell_h = height / (rows - 1)

    # jittered grid：相邻三角形共享顶点，拼接处无缝
    points = {}
    for row in range(rows):
        for col in range(cols):
            jitter_x = 0 if col in (0, cols - 1) else rng.uniform(-0.4, 0.4) * cell_w
            jitter_y = 0 if row in (0, rows - 1) else rng.uniform(-0.4, 0.4) * cell_h
            points[(col, row)] = QPointF(
                col * cell_w + jitter_x,
                row * cell_h + jitter_y,
            )

    facets = []
    for row in range(rows - 1):
        for col in range(cols - 1):
            tl = points[(col, row)]
            tr = points[(col + 1, row)]
            bl = points[(col, row + 1)]
            br = points[(col + 1, row + 1)]
            flip = rng.random() < 0.5
            triangles = (
                (tl, tr, br) if flip else (tl, tr, bl)
            ), ((tl, br, bl) if flip else (tr, br, bl))
            for triangle in triangles:
                facets.append((QPolygonF(triangle), _facet_color(rng)))

    return facets, _build_streaks(rng, width, height), _build_grid(rng, width, height)


# 面片颜色：大多数提亮，少数压暗，模拟玻璃碎面的明暗差
def _facet_color(rng):
    if rng.random() < 0.68:
        alpha = rng.uniform(6, 22)
        base = QColor(255, 255, 255)
    else:
        alpha = rng.uniform(4, 14)
        base = QColor(16, 35, 58)
    base.setAlpha(round(alpha))
    return base


# 斜向光带：从左上到右下的窄长四边形，两端羽化的白色渐变
def _build_streaks(rng, width, height):
    streaks = []
    for _ in range(3):
        center = rng.uniform(0.15, 0.85) * width
        band = rng.uniform(0.04, 0.1) * (width + height)
        slope = rng.uniform(0.35, 0.6) * height

        top = QPointF(center - band / 2 - slope, -band)
        bottom = QPointF(center + band / 2 + slope, height + band)
        polygon = QPolygonF(
            [
                QPointF(top.x() - band, top.y()),
                QPointF(top.x() + band * 0.4, top.y()),
                QPointF(bottom.x() + band * 1.4, bottom.y()),
                QPointF(bottom.x() - band * 0.2, bottom.y()),
            ]
        )
        gradient = QLinearGradient(
            polygon.boundingRect().topLeft(), polygon.boundingRect().bottomRight()
        )
        peak = rng.uniform(14, 30)
        gradient.setColorAt(0.0, QColor(255, 255, 255, 0))
        gradient.setColorAt(0.5, QColor(255, 255, 255, round(peak)))
        gradient.setColorAt(1.0, QColor(255, 255, 255, 0))
        streaks.append((polygon, gradient))
    return streaks


# 斜格子纹理：两组反向斜线（+45° 主格 + 反向弱格），极低透明度
def _build_grid(rng, width, height):
    lines = []
    span = width + height

    # 主格：同光带方向的斜线
    alpha = rng.uniform(9, 15)
    pen = QPen(QColor(255, 255, 255, round(alpha)), 1)
    for x in range(-height, width + height, _GRID_SPACING):
        lines.append((QLineF(x, 0, x + height, height), pen))

    # 反向弱格：稀疏一些、更淡
    alpha = rng.uniform(4, 8)
    pen = QPen(QColor(255, 255, 255, round(alpha)), 1)
    reverse_step = _GRID_SPACING * 2.2
    for x in range(-height, width + height, round(reverse_step)):
        lines.append((QLineF(x, height, x + height, 0), pen))
    return lines


# 中央画布：自绘 FGO 质感背景（替代 QSS 纯渐变）
class TexturedCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._cache_key = None
        self._facets = []
        self._streaks = []
        self._grid = []

    def resizeEvent(self, event):
        size = (self.width(), self.height())
        if size != self._cache_key:
            self._cache_key = size
            self._facets, self._streaks, self._grid = _build_layers(*size)
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        paint_background(self, painter)
        painter.end()


# 供任意控件在 paintEvent 里调用：按尺寸缓存并绘制完整质感背景
def paint_background(widget, painter):
    key = (widget.width(), widget.height())
    cache = getattr(widget, "_fgo_bg_cache", None)
    if cache is None or cache[0] != key:
        cache = (key, *_build_layers(*key))
        widget._fgo_bg_cache = cache
    _paint_layers(
        painter,
        QRectF(widget.rect()),
        facets=cache[1],
        streaks=cache[2],
        grid=cache[3],
    )


# 按渐变 → 面片 → 光带 → 格子的顺序绘制完整背景
def _paint_layers(painter, rect, facets=(), streaks=(), grid=()):
    gradient = QLinearGradient(0, 0, rect.width(), 0)
    for pos, color in GRADIENT_STOPS:
        gradient.setColorAt(pos, QColor(color))
    painter.fillRect(rect, gradient)
    painter.setRenderHint(QPainter.Antialiasing)

    painter.setPen(Qt.NoPen)
    for polygon, color in facets:
        painter.setBrush(color)
        painter.drawPolygon(polygon)
    for polygon, color in streaks:
        painter.setBrush(color)
        painter.drawPolygon(polygon)

    painter.setBrush(Qt.NoBrush)
    for line, pen in grid:
        painter.setPen(pen)
        painter.drawLine(line)
