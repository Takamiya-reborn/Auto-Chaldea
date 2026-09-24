"""任务步骤和执行结果表格。"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from auto_chaldea.ui.theme import GITHUB_DARK

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

    def set_steps(self, steps):
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
                    item.setForeground(QColor(GITHUB_DARK["muted"]))
                self.setItem(row, column, item)

        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

    def set_result(self, row, text, color):
        item = self.item(row, len(HEADERS) - 1)
        if item is not None:
            item.setText(text)
            item.setForeground(QColor(color))

    def clear_results(self):
        for row in range(self.rowCount()):
            self.set_result(row, "—", GITHUB_DARK["muted"])
