"""侧栏中的任务树面板，按目录结构加载 assets/task 下的 YAML 任务。"""

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QToolButton,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from auto_chaldea.utils.paths import TASK_DIR
from auto_chaldea.core.task_loader import load_task_file
from auto_chaldea.ui.card_tree import (
    CardTreeWidget,
    FastTreeStyle,
    VIEWPORT_MARGINS as _VIEWPORT_MARGINS,
    open_directory as _open_directory,
    reveal_file as _reveal_file,
)
from auto_chaldea.ui.icons import dir_node_icon, refresh_icon, task_node_icon
from auto_chaldea.ui.theme import FGO


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
        header.setContentsMargins(16, 12, 10, 12)
        title = QLabel("任务")
        title.setObjectName("panelHeader")
        header.addWidget(title)
        header.addStretch()

        refresh_button = QToolButton(self)
        refresh_button.setObjectName("panelHeaderButton")
        refresh_button.setToolTip("重新加载任务")
        refresh_button.setIcon(refresh_icon(FGO["muted"]))
        refresh_button.clicked.connect(self.refresh_tasks)
        header.addWidget(refresh_button)
        layout.addLayout(header)

        self._tree = CardTreeWidget(self)
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(False)  # 隐藏默认分支箭头，改用自绘组合图标
        self._tree.setIndentation(18)
        self._tree.setIconSize(QSize(24, 24))
        self._tree.setTextElideMode(Qt.ElideRight)
        self._tree.setUniformRowHeights(True)
        self._tree.setViewportMargins(*_VIEWPORT_MARGINS)
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
        """重新扫描任务目录构建整棵树；任务内容在选中时按需加载。

        目录项建树时递归预填充（只做目录扫描，不读 YAML），避免展开时
        先出现空容器、再突然渲染出子项的观感。
        """
        self._tree.blockSignals(True)
        self._tree.clear()

        self._fill_branch(self._tree.invisibleRootItem(), TASK_DIR)

        self._tree.blockSignals(False)
        self._emit_selection()

    def _fill_branch(self, parent_item, dir_path):
        """递归填充目录内容，不读取 YAML 文件。"""
        if not dir_path.exists():
            return

        entries = sorted(
            dir_path.iterdir(), key=lambda path: (path.is_file(), path.name)
        )
        for path in entries:
            if path.is_dir():
                child = self._make_dir_item(path)
                parent_item.addChild(child)
                self._fill_branch(child, path)
            elif path.suffix.lower() in (".yaml", ".yml"):
                relpath = path.relative_to(TASK_DIR).with_suffix("").as_posix()
                parent_item.addChild(self._make_task_item(path, relpath))

    def _make_dir_item(self, dir_path):
        item = QTreeWidgetItem()
        item.setText(0, dir_path.name)
        item.setTextAlignment(0, Qt.AlignLeft | Qt.AlignVCenter)
        item.setSizeHint(0, QSize(0, 32))
        item.setFlags(Qt.ItemIsEnabled)  # 目录不可选中，点击仅展开 / 收起
        item.setData(0, Qt.UserRole + 1, dir_path)
        self._set_dir_icon(item, False)
        return item

    def _make_task_item(self, path, relpath):
        item = QTreeWidgetItem()
        item.setText(0, path.stem)
        item.setTextAlignment(0, Qt.AlignLeft | Qt.AlignVCenter)
        item.setIcon(0, task_node_icon(FGO["muted"]))
        item.setSizeHint(0, QSize(0, 32))
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
        """目录展开时把图标切换为打开状态。"""
        self._set_dir_icon(item, True)

    # ---- 展开状态图标 ----

    def _set_dir_icon(self, item, expanded):
        item.setIcon(
            0,
            dir_node_icon(
                FGO["gold"], FGO["muted"], 90 if expanded else 0
            ),
        )

    # ---- 右键菜单 ----

    def _show_context_menu(self, pos):
        menu = QMenu(self._tree)
        reveal_action = menu.addAction("在资源管理器中显示")
        if menu.exec(self._tree.mapToGlobal(pos)) is reveal_action:
            self._reveal_in_explorer(self._tree.itemAt(pos))

    def _reveal_in_explorer(self, item):
        """在系统文件管理器中定位右键的节点；空白处显示任务根目录。"""
        if item is None:
            _open_directory(TASK_DIR)
            return

        # 目录节点在 UserRole+1 存绝对 Path；任务文件节点在 UserRole 存绝对 Path
        target = item.data(0, Qt.UserRole + 1)
        if isinstance(target, Path):
            _open_directory(target)
            return

        file_path = item.data(0, Qt.UserRole)
        if isinstance(file_path, Path):
            _reveal_file(file_path)
        else:
            _open_directory(TASK_DIR)
