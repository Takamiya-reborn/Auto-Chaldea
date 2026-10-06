"""FGO 奶油卡片式树组件，供任务树 / 模板树等目录树复用。"""

import subprocess
import sys

from PySide6.QtCore import QEvent, QModelIndex, QPersistentModelIndex, QRectF, QUrl, Qt
from PySide6.QtGui import QColor, QDesktopServices, QLinearGradient, QPainter, QPalette, QPen
from PySide6.QtWidgets import QProxyStyle, QStyle, QTreeWidget

from auto_chaldea.ui.theme import FGO

# 卡片与视口边缘的留白（setContentsMargins 对滚动区视口无效）
VIEWPORT_MARGINS = (8, 6, 8, 8)


class FastTreeStyle(QProxyStyle):
    """缩短树展开和收起的动画时长。"""

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == self.StyleHint.SH_Widget_Animation_Duration:
            return 120
        return super().styleHint(hint, option, widget, returnData)


class CardTreeWidget(QTreeWidget):
    """FGO 卡片式树，每行为常驻金边的奶油卡片。

    卡片背景整行自绘，并随层级右移缩进表达嵌套关系；选中态查
    selectionModel，悬停态自行跟踪。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover_index = QPersistentModelIndex()
        # Qt 会在选中行（含缩进槽）上用调色板 Highlight 再画一层底色，
        # 盖掉卡片金边（表现为选中后边框"消失"）；置为透明后该底色不可见。
        # 选中行文字也会被换成 HighlightedText，需配回奶油底上的深色
        palette = self.palette()
        palette.setColor(QPalette.Highlight, QColor(0, 0, 0, 0))
        palette.setColor(QPalette.HighlightedText, QColor(FGO["text_on_cream"]))
        self.setPalette(palette)
        # 视口默认不接收悬停事件，打开后才能跟踪悬停行
        self.viewport().setAttribute(Qt.WA_Hover, True)

    def viewportEvent(self, event):
        kind = event.type()
        if kind in (QEvent.HoverMove, QEvent.HoverEnter):
            self._set_hover_index(self.indexAt(event.position().toPoint()))
        elif kind == QEvent.HoverLeave:
            self._set_hover_index(QModelIndex())
        return super().viewportEvent(event)

    def mouseMoveEvent(self, event):
        self._set_hover_index(self.indexAt(event.position().toPoint()))
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._set_hover_index(QModelIndex())
        super().leaveEvent(event)

    def _set_hover_index(self, index):
        """切换悬停行并重绘受影响的两行。"""
        if index == self._hover_index:
            return
        old = QModelIndex(self._hover_index)
        self._hover_index = QPersistentModelIndex(index)
        for changed in (old, QModelIndex(self._hover_index)):
            if changed.isValid():
                self.update(self.visualRect(changed))

    def drawRow(self, painter, option, index):
        # 剥离选中 / 悬停态：否则 Qt 会用调色板 Highlight 在选中行的缩进区
        # 再画一层 navy 底色，盖掉卡片左缘金边（表现为选中后边框"消失"）
        option.state &= ~QStyle.State_Selected
        option.state &= ~QStyle.State_MouseOver

        rect = self.visualRect(index)
        depth = 0
        parent = index.parent()
        while parent.isValid():
            depth += 1
            parent = parent.parent()

        # 浅色引导线：每个祖先层级一条竖线，最后一级出水平肘线连到卡片，
        # 画在卡片之前，被卡片覆盖的部分不会显示
        if depth:
            indent = self.indentation()
            guide = QColor(FGO["muted"])
            guide.setAlpha(60)
            painter.save()
            painter.setPen(QPen(guide, 1))
            half = round(indent / 2)
            for level in range(depth):
                x = rect.left() + (level - depth) * indent + half
                painter.drawLine(x, rect.top(), x, rect.bottom())
            painter.drawLine(
                rect.left() - indent + half,
                rect.center().y(),
                rect.left(),
                rect.center().y(),
            )
            painter.restore()

        # visualRect 的 left 已含 depth 层缩进，卡片随之右移表达层级嵌套
        card_left = rect.left() + 1

        if index.flags() & Qt.ItemIsEnabled:
            selection_model = self.selectionModel()
            hovered = self._hover_index.isValid() and self._hover_index == index
            selected = selection_model is not None and selection_model.isSelected(index)
            if selected:
                top, bottom = FGO["cream_selected_top"], FGO["cream_selected_bottom"]
                pen = QPen(QColor(FGO["gold"]), 2)
            elif hovered:
                top, bottom = FGO["cream_hover_top"], FGO["cream_hover_bottom"]
                pen = QPen(QColor(FGO["gold_border"]), 1)
            else:
                top, bottom = FGO["cream_top"], FGO["cream_bottom"]
                pen = QPen(QColor(FGO["gold_border"]), 1)

            # FGO 风：每行都是常驻金边的奶油卡片，边框不再依赖悬停 / 选中
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)
            card = QRectF(
                card_left,
                rect.top() + 1,
                self.viewport().width() - 8 - card_left,
                rect.height() - 2,
            )
            gradient = QLinearGradient(card.topLeft(), card.bottomLeft())
            gradient.setColorAt(0.0, QColor(top))
            gradient.setColorAt(1.0, QColor(bottom))
            painter.setPen(pen)
            painter.setBrush(gradient)
            painter.drawRoundedRect(card, 6, 6)
            painter.restore()

        # 选中 / 悬停底色已剥离，这里只画文字和图标
        super().drawRow(painter, option, index)


def open_directory(path):
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def reveal_file(path):
    """在资源管理器中选中文件；非 Windows 平退化为打开所在目录。"""
    if sys.platform == "win32":
        # explorer 的 /select 参数不支持 list 形式的自动引号，需手工拼接
        subprocess.run(f'explorer /select,"{path}"', check=False)
    else:
        open_directory(path.parent)
