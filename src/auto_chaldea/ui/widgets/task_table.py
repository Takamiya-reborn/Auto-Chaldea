# 任务步骤和执行结果表格

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
)

from auto_chaldea.ui.common.theme import FGO
from auto_chaldea.ui.widgets.hex_scrollbar import install_hex_scrollbars

HEADERS = ("#", "步骤", "匹配序号", "区域", "模式", "结果")

_RUNNING_BG = QColor(FGO["attention"])  # 执行中行底的琥珀金


# 执行中行的底色由委托自绘。QSS 存在 QTableWidget::item 规则时
# QStyleSheetStyle 会忽略 item 的 BackgroundRole，setBackground 无效
class _RunningRowDelegate(QStyledItemDelegate):
    def __init__(self, table):
        super().__init__(table)
        self._table = table

    def paint(self, painter, option, index):
        if index.row() == self._table._running_row:
            brush = QBrush(_RUNNING_BG)
            painter.fillRect(option.rect, brush)
            option.backgroundBrush = brush
        super().paint(painter, option, index)


# 显示步骤并提供结果更新接口
class TaskStepTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(0, len(HEADERS), parent)
        self.setHorizontalHeaderLabels(list(HEADERS))
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setItemDelegate(_RunningRowDelegate(self))
        install_hex_scrollbars(self)
        self._running_row = None

    def set_steps(self, steps):
        self._running_row = None
        self.setRowCount(len(steps))
        for row, step in enumerate(steps):
            region = step.get("region") or "全屏"
            # 命名坐标点解析出的固定点击步骤没有识别模式，显示为“点击”
            mode = "点击" if "click" in step else (step.get("mode") or "single")
            values = (
                str(row + 1),
                str(step.get("template", "")),
                str(step.get("index", 0)),
                str(region),
                str(mode),
                "—",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(
                    Qt.AlignCenter if column != 1 else (Qt.AlignLeft | Qt.AlignVCenter)
                )
                if column == len(values) - 1:
                    item.setForeground(QColor("#8a97b5"))  # 奶油底上的弱化藏青
                self.setItem(row, column, item)

        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

    def set_result(self, row, text, color):
        item = self.item(row, len(HEADERS) - 1)
        if item is not None:
            item.setText(text)
            item.setForeground(QColor(color))

    # 高亮执行中的行并滚动到可见位置。行底色由 _RunningRowDelegate 自绘
    # （琥珀金，与奶油表格底拉开差距）；这里只管字重和结果列文字颜色
    def set_running_row(self, row):
        if row == self._running_row:
            return
        self._clear_running_row()
        self._running_row = row
        if row is None or not 0 <= row < self.rowCount():
            return

        text = QColor(FGO["text_on_cream"])
        for column in range(self.columnCount()):
            item = self.item(row, column)
            if item is None:
                continue
            # 结果列默认是弱化灰，压在琥珀底上含糊不清，高亮期间一并转藏青
            item.setForeground(text)
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        first = self.item(row, 0)
        if first is not None:
            self.scrollToItem(first, QAbstractItemView.EnsureVisible)
        first = self.item(row, 0)
        if first is not None:
            self.scrollToItem(first, QAbstractItemView.EnsureVisible)

    # 移除执行中高亮（结果列文字保留）
    def clear_running_row(self):
        self._clear_running_row()

    def _clear_running_row(self):
        if self._running_row is None:
            return
        for column in range(self.columnCount()):
            item = self.item(self._running_row, column)
            if item is None:
                continue
            # 高亮时把结果列转成了藏青，取消高亮后还原弱化灰
            if column == len(HEADERS) - 1 and item.text() == "—":
                item.setForeground(QColor("#8a97b5"))
            font = item.font()
            font.setBold(False)
            item.setFont(font)
        self._running_row = None

    def clear_results(self):
        self._clear_running_row()
        for row in range(self.rowCount()):
            self.set_result(row, "—", "#8a97b5")
