"""任务步骤和执行结果表格。"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from auto_chaldea.ui.theme import FGO

HEADERS = ("#", "模板", "匹配序号", "区域", "模式", "结果")


class TaskStepTable(QTableWidget):
    """显示步骤并提供结果更新接口。"""

    def __init__(self, parent=None):
        super().__init__(0, len(HEADERS), parent)
        self.setHorizontalHeaderLabels(list(HEADERS))
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self._running_row = None

    def set_steps(self, steps):
        self._running_row = None
        self.setRowCount(len(steps))
        for row, step in enumerate(steps):
            region = step.get("region") or "全屏"
            mode = step.get("mode") or "single"
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
                    item.setForeground(QColor(FGO["muted"]))
                self.setItem(row, column, item)

        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

    def set_result(self, row, text, color):
        item = self.item(row, len(HEADERS) - 1)
        if item is not None:
            item.setText(text)
            item.setForeground(QColor(color))

    def set_running_row(self, row):
        """金琥珀底高亮正在执行的步骤行，并滚动到可见位置。

        独立于选中态：新 QSS 下选中底色与表格奶油底几乎同色，无法
        起到指示作用；直接写 BackgroundRole 不受选中样式影响。
        """
        if row == self._running_row:
            return
        self._clear_running_row()
        self._running_row = row
        if row is None or not 0 <= row < self.rowCount():
            return

        highlight = QColor(FGO["run_top"])
        for column in range(self.columnCount()):
            item = self.item(row, column)
            if item is None:
                continue
            item.setBackground(highlight)
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        first = self.item(row, 0)
        if first is not None:
            self.scrollToItem(first, QAbstractItemView.EnsureVisible)

    def clear_running_row(self):
        """移除执行中高亮（结果列文字保留）。"""
        self._clear_running_row()

    def _clear_running_row(self):
        if self._running_row is None:
            return
        for column in range(self.columnCount()):
            item = self.item(self._running_row, column)
            if item is None:
                continue
            item.setData(Qt.BackgroundRole, None)
            font = item.font()
            font.setBold(False)
            item.setFont(font)
        self._running_row = None

    def clear_results(self):
        self._clear_running_row()
        for row in range(self.rowCount()):
            self.set_result(row, "—", FGO["muted"])
