"""侧栏中的任务树面板，按目录结构加载 assets/task 下的 YAML 任务。"""

from pathlib import Path

from PySide6.QtCore import QPointF, QUrl, QSize, Qt, Signal
from PySide6.QtGui import QColor, QDesktopServices, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QProxyStyle,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from auto_chaldea.utils.paths import TASK_DIR
from auto_chaldea.core.task_loader import load_task_file
from auto_chaldea.ui.icons import dir_node_icon, refresh_icon, task_node_icon
from auto_chaldea.ui.theme import GITHUB_DARK


class FastTreeStyle(QProxyStyle):
    """缩短任务树展开和收起的动画时长。"""

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == self.StyleHint.SH_Widget_Animation_Duration:
            return 120
        return super().styleHint(hint, option, widget, returnData)


class TaskTreeWidget(QTreeWidget):
    """带层级引导线的任务树：在子项的每个缩进层级绘制连接线。"""

    def drawRow(self, painter, option, index):
        super().drawRow(painter, option, index)

        depth = 0
        parent = index.parent()
        while parent.isValid():
            depth += 1
            parent = parent.parent()
        if depth == 0:
            return

        rect = self.visualRect(index)
        indent = self.indentation()
        painter.save()
        painter.fillRect(
            rect.left() - depth * indent,
            rect.top(),
            depth * indent,
            rect.height(),
            QColor(GITHUB_DARK["surface"]),
        )
        painter.setPen(QPen(QColor(GITHUB_DARK["border_strong"]), 1))
        half = indent / 2
        for level in range(depth):
            # visualRect 的 left 是内容区起点（已含 depth 层缩进），引导线要回退到行首
            x = rect.left() + (level - depth) * indent + half
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
        connector_x = rect.left() + (depth - 1 - depth) * indent + half
        painter.drawLine(
            QPointF(connector_x, rect.center().y()),
            QPointF(rect.left() + half, rect.center().y()),
        )
        painter.restore()


class TaskPanel(QWidget):
    """以目录树展示任务配置，选中任务文件后通知详情区域。"""

    task_selected = Signal(
        object, str
    )  # 参数：任务 dict、来源文件相对路径（不含扩展名）

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidePanel")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(14, 10, 8, 10)
        title = QLabel("任务")
        title.setObjectName("panelHeader")
        header.addWidget(title)
        header.addStretch()

        refresh_button = QToolButton(self)
        refresh_button.setObjectName("panelHeaderButton")
        refresh_button.setToolTip("重新加载任务")
        refresh_button.setIcon(refresh_icon(GITHUB_DARK["muted"]))
        refresh_button.clicked.connect(self.refresh_tasks)
        header.addWidget(refresh_button)
        layout.addLayout(header)

        self._tree = TaskTreeWidget(self)
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(False)  # 隐藏默认分支箭头，改用自绘组合图标
        self._tree.setIndentation(18)
        self._tree.setIconSize(QSize(24, 24))
        self._tree.setTextElideMode(Qt.ElideRight)
        self._tree.setUniformRowHeights(True)
        self._tree.setContentsMargins(8, 6, 8, 8)
        self._tree.setStyle(FastTreeStyle(self._tree.style()))
        self._tree.setAnimated(True)  # 展开 / 收起时的滑动动画
        self._tree.setExpandsOnDoubleClick(False)  # 展开收起统一由单击触发
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.itemSelectionChanged.connect(self._emit_selection)
        self._tree.itemClicked.connect(self._toggle_dir_item)
        self._tree.itemExpanded.connect(self._expand_dir_item)
        self._tree.itemCollapsed.connect(lambda item: self._set_dir_icon(item, False))
        layout.addWidget(self._tree, 1)

        self.refresh_tasks()

    def refresh_tasks(self):
        """重新扫描任务目录，任务内容在选中时按需加载。"""
        self._tree.blockSignals(True)
        self._tree.clear()

        self._fill_branch(self._tree.invisibleRootItem(), TASK_DIR)

        self._tree.blockSignals(False)
        self._emit_selection()

    def _fill_branch(self, parent_item, dir_path):
        """填充目录的一层内容，不读取 YAML 文件。"""
        if not dir_path.exists():
            return

        entries = sorted(
            dir_path.iterdir(), key=lambda path: (path.is_file(), path.name)
        )
        for path in entries:
            if path.is_dir():
                child = self._make_dir_item(path)
                parent_item.addChild(child)
                if self._has_directory_entries(path):
                    child.addChild(self._make_placeholder_item())
            elif path.suffix.lower() in (".yaml", ".yml"):
                relpath = path.relative_to(TASK_DIR).with_suffix("").as_posix()
                parent_item.addChild(self._make_task_item(path, relpath))

    def _has_directory_entries(self, dir_path):
        return any(dir_path.iterdir())

    def _make_dir_item(self, dir_path):
        item = QTreeWidgetItem()
        item.setText(0, dir_path.name)
        item.setTextAlignment(0, Qt.AlignLeft | Qt.AlignVCenter)
        item.setSizeHint(0, QSize(0, 29))
        item.setFlags(Qt.ItemIsEnabled)  # 目录不可选中，点击仅展开 / 收起
        item.setData(0, Qt.UserRole + 1, dir_path)
        self._set_dir_icon(item, False)
        return item

    def _make_placeholder_item(self):
        item = QTreeWidgetItem([""])
        item.setData(0, Qt.UserRole + 3, True)
        item.setFlags(Qt.NoItemFlags)
        return item

    def _make_task_item(self, path, relpath):
        item = QTreeWidgetItem()
        item.setText(0, path.stem)
        item.setTextAlignment(0, Qt.AlignLeft | Qt.AlignVCenter)
        item.setIcon(0, task_node_icon(GITHUB_DARK["muted"]))
        item.setSizeHint(0, QSize(0, 29))
        item.setToolTip(0, path.name)
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        item.setData(0, Qt.UserRole, path)
        item.setData(0, Qt.UserRole + 1, relpath)
        return item

    def _emit_selection(self):
        current = self._tree.currentItem()
        path = current.data(0, Qt.UserRole) if current is not None else None
        if not isinstance(path, Path) or path.is_dir():
            self.task_selected.emit(None, "")
            return

        task = load_task_file(path)
        if task is None:
            self.task_selected.emit(None, "")
            return
        self.task_selected.emit(task, current.data(0, Qt.UserRole + 1))

    def _toggle_dir_item(self, item, _column):
        """点击目录节点时展开 / 收起；文件节点交给默认的选择行为。"""
        if item.flags() & Qt.ItemIsSelectable:
            return
        item.setExpanded(not item.isExpanded())

    def _expand_dir_item(self, item):
        """目录首次展开时只加载它的直接子项。"""
        self._set_dir_icon(item, True)
        if item.childCount() == 1 and item.child(0).data(0, Qt.UserRole + 3):
            item.takeChildren()
            self._fill_branch(item, item.data(0, Qt.UserRole + 1))

    # ---- 展开状态图标 ----

    def _set_dir_icon(self, item, expanded):
        item.setIcon(
            0,
            dir_node_icon(
                GITHUB_DARK["accent"], GITHUB_DARK["muted"], 90 if expanded else 0
            ),
        )

    # ---- 右键菜单 ----

    def _show_context_menu(self, pos):
        menu = QMenu(self._tree)
        open_dir_action = menu.addAction("打开所在目录")
        if menu.exec(self._tree.mapToGlobal(pos)) is open_dir_action:
            item = self._tree.itemAt(pos)
            target = item.data(0, Qt.UserRole + 1) if item is not None else None
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target or TASK_DIR)))
