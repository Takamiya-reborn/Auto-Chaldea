"""使用 QPainter 绘制的矢量图标，避免依赖外部图片资源。

所有图标在 24x24 的逻辑坐标内绘制，通过缩放支持任意尺寸。
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)


def _render(draw, color, size=24):
    """在透明画布上按指定颜色渲染图标并返回 QPixmap。"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    scale = size / 24
    painter.scale(scale, scale)
    pen = QPen(QColor(color), 1.7)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    draw(painter)
    painter.end()
    return pixmap


def _icon(draw, color, size=24):
    return QIcon(_render(draw, color, size))


def _pixmap(draw, color, size=24):
    return _render(draw, color, size)


# ---- 绘制函数（24x24 逻辑坐标） ----


def _draw_tasks(painter):
    """任务列表图标：三个圆点加横线。"""
    color = painter.pen().color()
    painter.setBrush(QBrush(color))
    for row in range(3):
        y = 7.5 + row * 4.5
        painter.drawEllipse(QPointF(7, y), 1.2, 1.2)
    painter.setBrush(Qt.NoBrush)
    for row in range(3):
        y = 7.5 + row * 4.5
        painter.drawLine(QPointF(10.5, y), QPointF(18.5, y))


def _draw_templates(painter):
    """模板库图标：相框加山形。"""
    painter.drawRoundedRect(QRectF(4.5, 5, 15, 14), 2, 2)
    color = painter.pen().color()
    painter.setBrush(QBrush(color))
    painter.drawEllipse(QPointF(9.2, 9.6), 1.5, 1.5)
    painter.setBrush(Qt.NoBrush)
    path = QPainterPath(QPointF(6, 16.5))
    path.lineTo(QPointF(10.3, 11.8))
    path.lineTo(QPointF(12.8, 14.3))
    path.lineTo(QPointF(15.2, 11.9))
    path.lineTo(QPointF(18, 14.7))
    painter.drawPath(path)


def _draw_settings(painter):
    """设置图标：三行滑杆。"""
    color = painter.pen().color()
    for y, knob_x in ((7.5, 9), (12, 15), (16.5, 7.5)):
        painter.drawLine(QPointF(5, y), QPointF(19, y))
    painter.setBrush(QBrush(color))
    for y, knob_x in ((7.5, 9), (12, 15), (16.5, 7.5)):
        painter.drawEllipse(QPointF(knob_x, y), 2.4, 2.4)


def _draw_refresh(painter):
    """刷新图标：圆弧加箭头。"""
    rect = QRectF(5.2, 5.2, 13.6, 13.6)
    path = QPainterPath()
    path.arcMoveTo(rect, 40)
    path.arcTo(rect, 40, 280)
    painter.drawPath(path)
    color = painter.pen().color()
    painter.setBrush(QBrush(color))
    painter.drawPolygon(
        QPolygonF([QPointF(18.6, 4.6), QPointF(14.4, 5.4), QPointF(17.3, 8.9)])
    )


def _draw_play(painter):
    """播放图标：实心三角。"""
    color = painter.pen().color()
    painter.setBrush(QBrush(color))
    path = QPainterPath(QPointF(8, 5.5))
    path.lineTo(QPointF(8, 18.5))
    path.lineTo(QPointF(19, 12))
    path.closeSubpath()
    painter.drawPath(path)


def _draw_pause(painter):
    """暂停图标：两根竖条。"""
    color = painter.pen().color()
    painter.setBrush(QBrush(color))
    painter.drawRoundedRect(QRectF(7, 6, 3.4, 12), 1.2, 1.2)
    painter.drawRoundedRect(QRectF(13.6, 6, 3.4, 12), 1.2, 1.2)


def _draw_stop(painter):
    """停止图标：实心方块。"""
    color = painter.pen().color()
    painter.setBrush(QBrush(color))
    painter.drawRoundedRect(QRectF(7, 7, 10, 10), 1.5, 1.5)


def _draw_device(painter):
    """设备图标：竖置手机轮廓。"""
    painter.drawRoundedRect(QRectF(8, 4.5, 8, 15), 2, 2)
    painter.drawLine(QPointF(10.8, 16.6), QPointF(13.2, 16.6))


# ---- 对外接口 ----


def tasks_icon(color, size=24):
    return _icon(_draw_tasks, color, size)


def tasks_pixmap(color, size=24):
    return _pixmap(_draw_tasks, color, size)


def templates_icon(color, size=24):
    return _icon(_draw_templates, color, size)


def settings_icon(color, size=24):
    return _icon(_draw_settings, color, size)


def refresh_icon(color, size=24):
    return _icon(_draw_refresh, color, size)


def play_icon(color, size=24):
    return _icon(_draw_play, color, size)


def pause_icon(color, size=24):
    return _icon(_draw_pause, color, size)


def stop_icon(color, size=24):
    return _icon(_draw_stop, color, size)


def device_icon(color, size=24):
    return _icon(_draw_device, color, size)


def device_pixmap(color, size=24):
    return _pixmap(_draw_device, color, size)
