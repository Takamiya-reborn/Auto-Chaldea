"""基于 QtAwesome 的统一图标入口。"""

import qtawesome as qta


def _font_icon(name, color):
    """按名称和颜色返回 QtAwesome 字体图标。"""
    return qta.icon(name, color=color)


def tasks_icon(color):
    return _font_icon("fa6s.list-ul", color)


def templates_icon(color):
    return _font_icon("fa6s.images", color)


def settings_icon(color):
    return _font_icon("fa6s.sliders", color)


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


def folder_icon(color, opened=False):
    name = "fa6s.folder-open" if opened else "fa6s.folder"
    return _font_icon(name, color)


def dir_node_icon(folder_color, _chevron_color, angle=0.0):
    """按展开状态返回文件夹图标，不创建合成像素图。"""
    return folder_icon(folder_color, opened=angle >= 45.0)


def task_node_icon(color):
    return _font_icon("fa6s.file-lines", color)
