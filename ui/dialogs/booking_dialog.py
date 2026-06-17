from PyQt6.QtWidgets import (QDialog, QFormLayout, QLineEdit, QSpinBox, QComboBox, 
                             QTextEdit, QPushButton, QHBoxLayout, QMessageBox, QDialogButtonBox,
                             QDateEdit, QTimeEdit, QLabel)
from PyQt6.QtCore import QDate, QTime, Qt
from datetime import datetime, date
from models.cage import Cage
from models.user import User
from services.booking_service import BookingService
from services.conflict_service import ConflictService

class BookingDialog(QDialog):
    def __init__(self, parent=None, cage: Cage = None, user: User = None, selected_date: date = None):
        super().__init__(parent)
        self.cage = cage
        self.user = user
        self.selected_date = selected_date or date.today()
        self.setWindowTitle('新建预约')
        self.setFixedWidth(450)
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        cage_info = QLabel(f'笼位：<b>{self.cage.cage_code}</b> ({self.cage.room} - {self.cage.animal_type})')
        cage_info.setStyleSheet('font-size: 14px;')
        layout.addRow(cage_info)

        researcher_info = QLabel(f'申请人：<b>{self.user.name}</b>')
        researcher_info.setStyleSheet('font-size: 14px;')
        layout.addRow(researcher_info)

        self.project_name_edit = QLineEdit()
        self.project_name_edit.setPlaceholderText('请输入项目名称')
        layout.addRow('项目名称：', self.project_name_edit)

        self.animal_count_spin = QSpinBox()
        self.animal_count_spin.setRange(1, self.cage.capacity)
        self.animal_count_spin.setValue(1)
        layout.addRow(f'动物数量（最多{self.cage.capacity}）：', self.animal_count_spin)

        self.date_edit = QDateEdit(QDate(self.selected_date.year, self.selected_date.month, self.selected_date.day))
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setMinimumDate(QDate.currentDate())
        layout.addRow('预约日期：', self.date_edit)

        time_layout = QHBoxLayout()
        self.start_time_edit = QTimeEdit(QTime(9, 0))
        self.start_time_edit.setDisplayFormat('HH:mm')
        self.end_time_edit = QTimeEdit(QTime(12, 0))
        self.end_time_edit.setDisplayFormat('HH:mm')
        time_layout.addWidget(self.start_time_edit)
        time_layout.addWidget(QLabel('  至  '))
        time_layout.addWidget(self.end_time_edit)
        time_layout.addStretch()

        self.check_conflict_btn = QPushButton('🔍 检测冲突')
        self.check_conflict_btn.clicked.connect(self._check_conflict)
        time_layout.addWidget(self.check_conflict_btn)
        layout.addRow('预约时段：', time_layout)

        self.conflict_label = QLabel('')
        self.conflict_label.setWordWrap(True)
        layout.addRow('', self.conflict_label)

        self.purpose_edit = QTextEdit()
        self.purpose_edit.setPlaceholderText('请详细描述实验目的和动物使用方案...')
        self.purpose_edit.setFixedHeight(100)
        layout.addRow('实验目的：', self.purpose_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _check_conflict(self):
        start_dt, end_dt = self._get_datetimes()
        if not start_dt or not end_dt:
            return

        is_valid, conflicts, message = ConflictService.validate_booking(
            self.cage.id, start_dt, end_dt
        )

        if is_valid:
            self.conflict_label.setText(f'<span style="color: #67c23a;">✓ {message}</span>')
        else:
            self.conflict_label.setText(f'<span style="color: #f56c6c;">✗ {message}</span>')

        return is_valid

    def _get_datetimes(self):
        qdate = self.date_edit.date()
        qstart = self.start_time_edit.time()
        qend = self.end_time_edit.time()

        start_dt = datetime(qdate.year(), qdate.month(), qdate.day(), 
                           qstart.hour(), qstart.minute())
        end_dt = datetime(qdate.year(), qdate.month(), qdate.day(), 
                         qend.hour(), qend.minute())

        if start_dt >= end_dt:
            QMessageBox.warning(self, '提示', '结束时间必须晚于开始时间')
            return None, None

        return start_dt, end_dt

    def _on_ok(self):
        project_name = self.project_name_edit.text().strip()
        animal_count = self.animal_count_spin.value()
        purpose = self.purpose_edit.toPlainText().strip()

        if not all([project_name, purpose]):
            QMessageBox.warning(self, '提示', '请填写完整信息')
            return

        start_dt, end_dt = self._get_datetimes()
        if not start_dt or not end_dt:
            return

        if not self._check_conflict():
            QMessageBox.warning(self, '时段冲突', '当前选择的时段存在冲突，请重新选择')
            return

        success, message, booking = BookingService.create_booking(
            cage_id=self.cage.id,
            researcher_id=self.user.id,
            project_name=project_name,
            animal_count=animal_count,
            start_time=start_dt,
            end_time=end_dt,
            purpose=purpose
        )

        if success:
            QMessageBox.information(self, '成功', f'{message}\n\n预约编号：#{booking.id}\n当前状态：草稿\n\n您可以在"我的预约"中提交审批')
            self.accept()
        else:
            QMessageBox.critical(self, '失败', message)
