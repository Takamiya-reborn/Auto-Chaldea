# 带描边的文字标签：FGO 风格的金色字配藏青描边
#
# QSS 不支持文字描边，这里在 paintEvent 里先画出藏青描边层，
# 再叠加正常颜色的文字。填充色不读调色板（QSS 的 color 属性
# 不会写进 palette），而是显式传入，默认金色 #eedb5a。

import re

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen, QTextDocument
from PySide6.QtWidgets import QLabel

from auto_chaldea.ui.common.theme import FGO

# 8 方向描边偏移系数（跳过中心）
_OUTLINE_OFFSETS = [
    (dx, dy)
    for dx in (-1, 0, 1)
    for dy in (-1, 0, 1)
    if (dx, dy) != (0, 0)
]


class OutlinedLabel(QLabel):
    def __init__(
        self,
        text="",
        parent=None,
        outline_color="#2c3a57",
        outline_width=2,
        fill_color=None,
    ):
        super().__init__(text, parent)
        self._outline_color = QColor(outline_color)
        self._outline_width = outline_width
        self._fill_color = QColor(fill_color or FGO["gold_text"])

    def paintEvent(self, event):
        text = self.text()
        if not text:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        if Qt.mightBeRichText(text):
            self._paint_rich_text(painter, text)
        else:
            self._paint_plain_text(painter, text)
        painter.end()

    # ---- 纯文本：描边层用路径偏移垫底，金字用原生 drawText 保证清晰 ----

    def _paint_plain_text(self, painter, text):
        path = QPainterPath()
        path.addText(0, 0, self.font(), text)
        bounds = path.boundingRect()

        rect = self.rect()
        fm = QFontMetrics(self.font())
        alignment = self.alignment()
        if alignment & Qt.AlignHCenter:
            x = (rect.width() - bounds.width()) / 2 - bounds.left()
        elif alignment & Qt.AlignRight:
            x = rect.width() - fm.horizontalAdvance(text) - bounds.left()
        else:
            x = -bounds.left()
        if alignment & Qt.AlignVCenter:
            y = (rect.height() - bounds.height()) / 2 - bounds.top()
        elif alignment & Qt.AlignBottom:
            y = rect.height() - bounds.height() - bounds.top()
        else:
            y = fm.ascent()

        # 全部取整，避免亚像素渲染导致文字发糊
        x, y = round(x), round(y)

        # 描边层：8 方向整数偏移副本，全部垫在金字下方
        radius = max(1, round(self._outline_width / 2.0))
        pen = self._outline_pen()
        for dx, dy in _OUTLINE_OFFSETS:
            painter.strokePath(
                path.translated(x + dx * radius, y + dy * radius), pen
            )

        # 正文层：原生 drawText，走字体 hinting，与普通 QLabel 一样清晰
        pen = painter.pen()
        painter.setPen(QPen(self._fill_color, 1))
        painter.drawText(QPointF(x, y), text)
        painter.setPen(pen)

    def _outline_pen(self):
        return QPen(
            self._outline_color,
            self._outline_width,
            Qt.SolidLine,
            Qt.RoundCap,
            Qt.RoundJoin,
        )

    # ---- 富文本（状态栏的彩色圆点等）：QTextDocument 多层偏移叠加 ----

    def _paint_rich_text(self, painter, text):
        # 描边层：把 HTML 里的颜色统一换成描边色，逐方向偏移绘制
        outline_html = re.sub(
            r"(color\s*:\s*)[^;\"'}]+",
            rf"\g<1>{self._outline_color.name()}",
            text,
        )
        origin = self._content_origin(outline_html)
        doc = self._build_document(outline_html, outline=True)
        radius = max(1, round(self._outline_width / 2.0))
        for dx, dy in _OUTLINE_OFFSETS:
            painter.save()
            painter.translate(
                origin.x() + dx * radius, origin.y() + dy * radius
            )
            doc.drawContents(painter)
            painter.restore()

        # 正文层：原文内容，默认色为填充色（内层 span 仍可自带颜色）
        origin = self._content_origin(text)
        painter.translate(round(origin.x()), round(origin.y()))
        doc = self._build_document(text)
        doc.drawContents(painter)

    def _build_document(self, html, outline=False):
        doc = QTextDocument(self)
        if outline:
            # 描边层用加粗字体，保证藏青轮廓比金字宽出一圈
            bold = QFont(self.font())
            bold.setBold(True)
            doc.setDefaultFont(bold)
        else:
            doc.setDefaultFont(self.font())
        doc.setDocumentMargin(0)
        if self.wordWrap():
            doc.setTextWidth(self.width())
        align = "center"
        if self.alignment() & Qt.AlignLeft:
            align = "left"
        elif self.alignment() & Qt.AlignRight:
            align = "right"
        wrapped = f'<span style="color:{self._fill_color.name()};">{html}</span>'
        doc.setHtml(f'<div align="{align}">{wrapped}</div>')
        return doc

    # 富文本按标签对齐方式与控件高度垂直居中
    def _content_origin(self, html):
        doc = self._build_document(html)
        x = 0.0
        if self.alignment() & Qt.AlignRight:
            x = self.width() - doc.size().width()
        y = max(0.0, (self.height() - doc.size().height()) / 2)
        return QPointF(x, y)
