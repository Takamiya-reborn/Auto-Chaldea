"""侧栏中的模板库面板，按目录结构展示 assets/template 下的模板图像。"""

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QToolButton,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from auto_chaldea.utils.paths import TEMPLATE_DIR
from auto_chaldea.ui.card_tree import (
    CardTreeWidget,
    FastTreeStyle,
    VIEWPORT_MARGINS,
    open_directory,
    reveal_file,
)
from auto_chaldea.ui.icons import dir_node_icon, refresh_icon
from auto_chaldea.ui.theme import FGO

_PREVIEW_MARGIN = 16  # 预览图四周留白
_CHECKER_SIZE = 10  # 透明区棋盘格边长
_CHECKER_LIGHT = QColor("#22384f")
_CHECKER_DARK = QColor("#1a3049")


class _PreviewCanvas(QLabel):
    """保持宽高比缩放显示模板大图，透明区域绘制棋盘格。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self._original = QPixmap()

    def set_image(self, pixmap):
        self._original = pixmap
        self._update_scaled()

    def _update_scaled(self):
        if self._original.isNull():
            self.clear()
            return
        avail = (self.size() - QSize(_PREVIEW_MARGIN * 2, _PREVIEW_MARGIN * 2)).expandedTo(
            QSize(1, 1)
        )
        scaled = self._original.scaled(
            avail, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        # 叠一层棋盘格底，让透明 PNG 的边界可辨认
        board = QPixmap(scaled.size())
        painter = QPainter(board)
        painter.drawTiledPixmap(board.rect(), self._checker_tile())
        painter.drawPixmap(0, 0, scaled)
        painter.end()
        self.setPixmap(board)

    @staticmethod
    def _checker_tile():
        tile = QPixmap(_CHECKER_SIZE * 2, _CHECKER_SIZE * 2)
        tile.fill(_CHECKER_LIGHT)
        painter = QPainter(tile)
        painter.fillRect(0, 0, _CHECKER_SIZE, _CHECKER_SIZE, _CHECKER_DARK)
        painter.fillRect(_CHECKER_SIZE, _CHECKER_SIZE, _CHECKER_SIZE, _CHECKER_SIZE, _CHECKER_DARK)
        painter.end()
        return tile

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_scaled()


class TemplatesPanel(QWidget):
    """以目录树展示模板图像；选中项通过信号交给详情区放大显示。"""

    template_selected = Signal(object)  # 选中的模板 Path，取消选择时为 None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidePanel")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(16, 12, 10, 12)
        title = QLabel("模板库")
        title.setObjectName("panelHeader")
        header.addWidget(title)
        header.addStretch()

        refresh_button = QToolButton(self)
        refresh_button.setObjectName("panelHeaderButton")
        refresh_button.setToolTip("重新扫描模板")
        refresh_button.setIcon(refresh_icon(FGO["muted"]))
        refresh_button.clicked.connect(self.refresh_templates)
        header.addWidget(refresh_button)
        layout.addLayout(header)

        self._tree = CardTreeWidget(self)
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(False)  # 隐藏默认分支箭头，改用自绘组合图标
        self._tree.setIndentation(18)
        self._tree.setIconSize(QSize(24, 24))
        self._tree.setTextElideMode(Qt.ElideRight)
        self._tree.setUniformRowHeights(True)
        self._tree.setViewportMargins(*VIEWPORT_MARGINS)
        self._tree.setStyle(FastTreeStyle(self._tree.style()))
        self._tree.setAnimated(True)
        self._tree.setExpandsOnDoubleClick(False)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.itemSelectionChanged.connect(self._emit_selection)
        self._tree.itemClicked.connect(self._toggle_dir_item)
        self._tree.itemExpanded.connect(self._expand_dir_item)
        self._tree.itemCollapsed.connect(lambda item: self._set_dir_icon(item, False))
        layout.addWidget(self._tree, 1)

        self.refresh_templates()

    def refresh_templates(self):
        """重新扫描模板目录构建整棵树，默认收起目录。"""
        self._tree.blockSignals(True)
        self._tree.clear()

        self._fill_branch(self._tree.invisibleRootItem(), TEMPLATE_DIR)

        self._tree.blockSignals(False)
        self._emit_selection()

    def _fill_branch(self, parent_item, dir_path):
        """递归填充目录内容；目录在前、图像在后，各自按名称排序。"""
        if not dir_path.exists():
            return

        entries = sorted(dir_path.iterdir(), key=lambda path: (path.is_file(), path.name))
        for path in entries:
            if path.is_dir():
                child = self._make_dir_item(path)
                parent_item.addChild(child)
                self._fill_branch(child, path)
            elif path.suffix.lower() == ".png":
                parent_item.addChild(self._make_image_item(path))

    def _make_dir_item(self, dir_path):
        item = QTreeWidgetItem()
        item.setText(0, dir_path.name)
        item.setTextAlignment(0, Qt.AlignLeft | Qt.AlignVCenter)
        item.setSizeHint(0, QSize(0, 32))
        item.setFlags(Qt.ItemIsEnabled)  # 目录不可选中，点击仅展开 / 收起
        item.setData(0, Qt.UserRole + 1, dir_path)
        self._set_dir_icon(item, False)
        return item

    def _make_image_item(self, path):
        image = QImage(str(path))
        size_text = f"{image.width()}×{image.height()}" if not image.isNull() else "未知尺寸"
        item = QTreeWidgetItem()
        item.setText(0, path.stem)
        item.setTextAlignment(0, Qt.AlignLeft | Qt.AlignVCenter)
        if not image.isNull():
            item.setIcon(0, QIcon(str(path)))
        item.setSizeHint(0, QSize(0, 32))
        item.setToolTip(0, f"{path}\n{size_text}")
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        item.setData(0, Qt.UserRole, path)
        return item

    def _emit_selection(self):
        current = self._tree.currentItem()
        path = current.data(0, Qt.UserRole) if current is not None else None
        if not isinstance(path, Path):
            self.template_selected.emit(None)
            return
        self.template_selected.emit(path)

    def _toggle_dir_item(self, item, _column):
        """点击目录节点时展开 / 收起；图像节点交给默认的选择行为。"""
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
            dir_node_icon(FGO["gold"], FGO["muted"], 90 if expanded else 0),
        )

    # ---- 右键菜单 ----

    def _show_context_menu(self, pos):
        menu = QMenu(self._tree)
        reveal_action = menu.addAction("在资源管理器中显示")
        if menu.exec(self._tree.mapToGlobal(pos)) is reveal_action:
            self._reveal_in_explorer(self._tree.itemAt(pos))

    def _reveal_in_explorer(self, item):
        """在系统文件管理器中定位右键的节点；空白处显示模板根目录。"""
        if item is None:
            open_directory(TEMPLATE_DIR)
            return

        # 目录节点在 UserRole+1 存绝对 Path；图像节点在 UserRole 存绝对 Path
        target = item.data(0, Qt.UserRole + 1)
        if isinstance(target, Path):
            open_directory(target)
            return

        file_path = item.data(0, Qt.UserRole)
        if isinstance(file_path, Path):
            reveal_file(file_path)
        else:
            open_directory(TEMPLATE_DIR)


class TemplateDetailView(QWidget):
    """占据任务详情位置的模板放大预览。"""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(6)

        self._preview = _PreviewCanvas(self)
        self._preview_name = QLabel(self)
        self._preview_name.setObjectName("previewName")
        self._preview_info = QLabel(self)
        self._preview_info.setObjectName("previewInfo")
        layout.addStretch()
        layout.addWidget(self._preview, 1)
        layout.addWidget(self._preview_name)
        layout.addWidget(self._preview_info)
        layout.addStretch()
        self._show_empty()

    def set_template(self, path):
        if path is None:
            self._show_empty()
            return
        pixmap = QPixmap(str(path))
        self._preview.set_image(pixmap)
        self._preview_name.setText(path.stem)
        self._preview_info.setText(f"{path} · {pixmap.width()}×{pixmap.height()}")

    def _show_empty(self):
        self._preview.set_image(QPixmap())
        self._preview_name.setText("未选择模板")
        self._preview_info.setText("在左侧模板库中点击一个模板查看大图")
