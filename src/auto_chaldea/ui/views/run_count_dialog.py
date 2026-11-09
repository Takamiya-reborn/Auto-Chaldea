# 执行次数选择对话框：加减步进 + 常用轮数快捷键，FGO 弹窗风格

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIntValidator, QPainter
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
    QVBoxLayout,
)

from auto_chaldea.ui.common.icons import play_icon
from auto_chaldea.ui.common.theme import FGO
from auto_chaldea.ui.widgets.outlined_label import OutlinedLabel
from auto_chaldea.ui.widgets.textured_background import paint_background

MIN_COUNT = 1
MAX_COUNT = 9999
QUICK_COUNTS = (1, 3, 5, 10)


# 步进选择执行轮数；确认后通过 value() 取结果
class ExecutionCountDialog(QDialog):
    def __init__(self, initial=MIN_COUNT, parent=None):
        super().__init__(parent)
        self.setWindowTitle("执行次数 - Auto-Chaldea")
        self.setObjectName("runCountDialog")
        self.setFixedWidth(360)

        self._count = self._clamp(initial)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 30, 32, 26)
        layout.setSpacing(12)

        icon_button = QToolButton(self)
        icon_button.setIcon(play_icon(FGO["accent"]))
        icon_button.setIconSize(QSize(40, 40))
        icon_button.setFixedSize(52, 52)
        icon_button.setEnabled(False)
        icon_button.setStyleSheet(
            "QToolButton { background: transparent; border: none; }"
        )
        layout.addWidget(icon_button, alignment=Qt.AlignCenter)

        title = OutlinedLabel("执行次数", self)
        title.setObjectName("detailTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = OutlinedLabel("选择任务连续执行的轮数", self)
        subtitle.setObjectName("detailMeta")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        layout.addSpacing(6)

        layout.addLayout(self._build_stepper())
        layout.addSpacing(2)
        layout.addLayout(self._build_quick_buttons())
        layout.addSpacing(4)

        self._hint_label = QLabel(self._range_hint(), self)
        self._hint_label.setObjectName("statusLabel")
        self._hint_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._hint_label)
        layout.addSpacing(4)

        buttons = QHBoxLayout()
        buttons.setSpacing(14)

        self._confirm_button = QPushButton("开始执行", self)
        self._confirm_button.setProperty("pill", True)
        self._confirm_button.setCursor(Qt.PointingHandCursor)
        self._confirm_button.setMinimumHeight(38)
        self._confirm_button.setDefault(True)
        self._confirm_button.clicked.connect(self.accept)
        buttons.addWidget(self._confirm_button, 1)

        cancel_button = QPushButton("取消", self)
        cancel_button.setProperty("pill", True)
        cancel_button.setCursor(Qt.PointingHandCursor)
        cancel_button.setMinimumHeight(38)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(cancel_button, 1)
        layout.addLayout(buttons)

        self._sync_state()

    # 自绘与主窗口一致的 FGO 质感背景
    def paintEvent(self, event):
        painter = QPainter(self)
        paint_background(self, painter)
        painter.end()

    # 确认后的执行次数；输入框内容未提交时（如被清空）以旧值兜底
    def value(self):
        text = self._count_edit.text().strip()
        try:
            return self._clamp(int(text))
        except ValueError:
            return self._count

    # ---- 界面构建 ----

    def _build_stepper(self):
        row = QHBoxLayout()
        row.setSpacing(16)

        self._minus_button = QPushButton("−", self)
        self._minus_button.setProperty("pill", True)
        self._minus_button.setObjectName("stepperButton")
        self._minus_button.setCursor(Qt.PointingHandCursor)
        self._minus_button.setFixedSize(46, 46)
        self._minus_button.clicked.connect(lambda: self._set_count(self._count - 1))
        row.addWidget(self._minus_button, alignment=Qt.AlignVCenter)

        self._count_edit = QLineEdit(str(self._count), self)
        self._count_edit.setObjectName("countValue")
        self._count_edit.setAlignment(Qt.AlignCenter)
        self._count_edit.setFixedWidth(104)
        self._count_edit.setValidator(QIntValidator(MIN_COUNT, MAX_COUNT, self))
        self._count_edit.editingFinished.connect(self._apply_edit)
        row.addWidget(self._count_edit, alignment=Qt.AlignVCenter)

        self._plus_button = QPushButton("+", self)
        self._plus_button.setProperty("pill", True)
        self._plus_button.setObjectName("stepperButton")
        self._plus_button.setCursor(Qt.PointingHandCursor)
        self._plus_button.setFixedSize(46, 46)
        self._plus_button.clicked.connect(lambda: self._set_count(self._count + 1))
        row.addWidget(self._plus_button, alignment=Qt.AlignVCenter)
        return row

    def _build_quick_buttons(self):
        row = QHBoxLayout()
        row.setSpacing(10)
        for count in QUICK_COUNTS:
            button = QPushButton(f"{count} 轮", self)
            button.setProperty("pill", True)
            button.setObjectName("quickCountButton")
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(32)
            button.clicked.connect(lambda _=False, value=count: self._set_count(value))
            row.addWidget(button, 1)
        return row

    # ---- 数值状态 ----

    def _set_count(self, count):
        self._count = self._clamp(count)
        self._sync_state()

    def _clamp(self, count):
        return max(MIN_COUNT, min(MAX_COUNT, int(count)))

    # 编辑完成（回车或失焦）后把输入钳制进有效范围
    def _apply_edit(self):
        text = self._count_edit.text().strip()
        try:
            count = int(text)
        except ValueError:
            count = self._count
        self._set_count(count)

    def _range_hint(self):
        return f"范围 {MIN_COUNT} ~ {MAX_COUNT} 轮"

    # 数字显示与两端按钮的可用态同步
    def _sync_state(self):
        self._count_edit.setText(str(self._count))
        self._minus_button.setEnabled(self._count > MIN_COUNT)
        self._plus_button.setEnabled(self._count < MAX_COUNT)
