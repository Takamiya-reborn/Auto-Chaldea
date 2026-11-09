# FGO 奶油卡片式树，供任务树 / 模板树等目录树复用

import subprocess
import sys

from PySide6.QtCore import QEvent, QModelIndex, QPersistentModelIndex, QRectF, Qt, QUrl
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QIcon,
    QLinearGradient,
    QPainter,
    QPalette,
    QPen,
)
from PySide6.QtWidgets import (
    QApplication,
    QStyle,
    QStyleOptionViewItem,
    QStyledItemDelegate,
    QTreeWidget,
)

from auto_chaldea.ui.common.theme import FGO
from auto_chaldea.ui.widgets.hex_scrollbar import install_hex_scrollbars

# 卡片与视口边缘的留白（setContentsMargins 对滚动区视口无效）
VIEWPORT_MARGINS = (8, 6, 8, 8)


# 行内容委托：只画图标与文字，绝不画任何样式底色。
# Fusion / QSS 会以"带透明度的 Highlight"填充条目矩形——若 Highlight 配成
# 透明黑，点击行后就表现为卡片上的灰色遮罩。这里直接跳过全部背景原语，
# 从根上杜绝该类填充；几何沿用样式自身的 subElementRect，保证与原版一致。
#
# 注意：CardTreeWidget 不能再挂 QProxyStyle（如曾经的 FastTreeStyle）——
# PySide6 6.11.2 下"代理样式 + Python 重写的 paint"组合会触发原生段错误；
# 动画时长已由 app 级 _AnimationProxyStyle 全局收紧，树级无需重复设置。
class CardRowDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # 原生 paint 流程里 initStyleOption 由 Qt 内部先调用，从模型填
        # text / icon / font / palette；这里自绘必须显式补上，否则全空。
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        widget = opt.widget
        style = widget.style() if widget is not None else QApplication.style()
        enabled = bool(opt.state & QStyle.State_Enabled)
        # 图标
        icon = opt.icon
        if not icon.isNull():
            deco = style.subElementRect(QStyle.SE_ItemViewItemDecoration, opt, widget)
            if deco.isValid():
                mode = QIcon.Normal if enabled else QIcon.Disabled
                state = QIcon.On if opt.state & QStyle.State_Open else QIcon.Off
                icon.paint(painter, deco, Qt.AlignCenter, mode, state)
        # 文字（超宽省略，禁用行用禁用色）
        text = opt.text
        if text:
            text_rect = style.subElementRect(QStyle.SE_ItemViewItemText, opt, widget)
            if text_rect.isValid():
                fm = opt.fontMetrics
                elided = fm.elidedText(text, Qt.ElideRight, text_rect.width())
                group = QPalette.Normal if enabled else QPalette.Disabled
                painter.save()
                painter.setFont(opt.font)
                painter.setPen(opt.palette.color(group, QPalette.Text))
                flags = (opt.displayAlignment & ~Qt.AlignVertical_Mask) | Qt.AlignVCenter
                painter.drawText(text_rect, flags, elided)
                painter.restore()


# 卡片式树：每行为常驻金边的奶油卡片，整行自绘并随层级缩进；
# 选中态查 selectionModel，悬停态自行跟踪
class CardTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        install_hex_scrollbars(self)
        self.setItemDelegate(CardRowDelegate(self))
        self._hover_index = QPersistentModelIndex()
        # Qt 会在选中行（含缩进槽）上用调色板 Highlight 再画一层底色，
        # 盖掉卡片金边（表现为选中后边框"消失"）；且 Fusion 会以带透明度的
        # Highlight 填充条目矩形——置为透明黑会表现为点击后的灰色遮罩，
        # 故改为奶油色：无论样式何时叠这层填充，都是奶油底上画奶油，不可见。
        # 选中行文字也会被换成 HighlightedText，需配回奶油底上的深色
        palette = self.palette()
        palette.setColor(QPalette.Highlight, QColor(FGO["cream_selected_bottom"]))
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

    # 切换悬停行并重绘受影响的两行
    def _set_hover_index(self, index):
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
            guide = QColor(FGO["gold_border"])
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

        # 内容交给 CardRowDelegate：只画图标与文字。不再调用
        # QTreeView::drawRow——它会让样式以"带透明度的 Highlight"填充行
        # 矩形（Highlight 配透明黑时表现为点击后的灰色遮罩），彻底绕开。
        # 委托的 rect 必须用 visualRect（已含层级缩进）：原生 drawRow 内部
        # 会按深度调整委托矩形，绕开后需自行补偿，否则文字不随卡片缩进。
        opt = QStyleOptionViewItem(option)
        opt.rect = self.visualRect(index)
        self.itemDelegate().paint(painter, opt, index)


def open_directory(path):
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


# 在资源管理器中选中文件；非 Windows 退化为打开所在目录
def reveal_file(path):
    if sys.platform == "win32":
        # explorer 的 /select 参数不支持 list 形式的自动引号，需手工拼接
        subprocess.run(f'explorer /select,"{path}"', check=False)
    else:
        open_directory(path.parent)
