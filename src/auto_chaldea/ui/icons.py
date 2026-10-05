"""基于 QtAwesome 的统一图标入口，含 FGO 风菱形底板绘制。"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

import qtawesome as qta

from auto_chaldea.ui.theme import FGO

# 菱形底板像素图缓存：(size, lit, dpr) -> QPixmap
_DIAMOND_CACHE = {}


def _font_icon(name, color):
    """按名称和颜色返回 QtAwesome 字体图标。"""
    return qta.icon(name, color=color)


def tasks_icon(color):
    return _font_icon("fa6s.list-ul", color)


def templates_icon(color):
    return _font_icon("fa6s.images", color)


def settings_icon(color):
    return _font_icon("fa6s.gear", color)


def refresh_icon(color):
    return _font_icon("fa6s.rotate", color)


def play_icon(color):
    return _font_icon("fa6s.play", color)


def pause_icon(color):
    return _font_icon("fa6s.pause", color)


def stop_icon(color):
    return _font_icon("fa6s.stop", color)


def next_icon(color):
    return _font_icon("fa6s.forward", color)


def device_icon(color):
    return _font_icon("fa6s.mobile-screen", color)


def disconnect_icon(color):
    return _font_icon("fa6s.plug-circle-xmark", color)


def folder_icon(color, opened=False):
    name = "fa6s.folder-open" if opened else "fa6s.folder"
    return _font_icon(name, color)


def dir_node_icon(folder_color, _chevron_color, angle=0.0):
    """按展开状态返回文件夹图标，不创建合成像素图。"""
    return folder_icon(folder_color, opened=angle >= 45.0)


def task_node_icon(color):
    return _font_icon("fa6s.file-lines", color)


def _diamond_pixmap(size, lit, dpr):
    """绘制 FGO 蓝宝石菱形底板像素图（不包含字形）。"""
    key = (size, lit, dpr)
    cached = _DIAMOND_CACHE.get(key)
    if cached is not None:
        return cached

    pm = QPixmap(QSize(size, size) * dpr)
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)

    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.translate(size / 2.0, size / 2.0)
    painter.rotate(45)

    side = size * 0.68
    radius = size * 0.08
    half = side / 2.0
    path = QPainterPath()
    path.addRoundedRect(-half, -half, side, side, radius, radius)

    if lit:
        gradient = QLinearGradient(0, -half, 0, half)
        gradient.setColorAt(0.0, QColor(FGO["diamond_top"]))
        gradient.setColorAt(1.0, QColor(FGO["diamond_bottom"]))
        painter.fillPath(path, QBrush(gradient))
        edge = QColor(FGO["gold"])
    else:
        painter.fillPath(path, QBrush(QColor(FGO["diamond_dim"])))
        edge = QColor("#5b7391")

    # 上半部高光，模拟 FGO 菱形的玻璃光泽
    painter.save()
    painter.setClipRect(-half, -half, side, half)
    gloss = QLinearGradient(0, -half, 0, 0)
    gloss.setColorAt(0.0, QColor(255, 255, 255, 80))
    gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
    painter.fillPath(path, QBrush(gloss))
    painter.restore()

    painter.setPen(QPen(edge, 1))
    painter.drawPath(path)
    painter.end()

    _DIAMOND_CACHE[key] = pm
    return pm


def diamond_icon(glyph_name, size=24, lit=True, dpr=1.0):
    """FGO 蓝宝石菱形底板 + 白色字形图标。lit=False 为未选中暗版。"""
    plate = _diamond_pixmap(size, lit, dpr)

    glyph_color = "#ffffff" if lit else "#c3d0de"
    glyph_size = round(size * 0.52)
    glyph = qta.icon(glyph_name, color=glyph_color).pixmap(glyph_size, glyph_size)

    pm = QPixmap(plate)
    painter = QPainter(pm)
    x = round((pm.width() / dpr - glyph_size) / 2.0)
    y = round((pm.height() / dpr - glyph_size) / 2.0)
    painter.drawPixmap(x, y, glyph)
    painter.end()
    return QIcon(pm)
