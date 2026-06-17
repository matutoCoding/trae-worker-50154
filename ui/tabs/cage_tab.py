from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QLineEdit,
                             QSpinBox, QComboBox, QTextEdit, QMessageBox, QLabel, QSplitter,
                             QDateEdit, QTimeEdit, QGroupBox, QListWidget, QListWidgetItem)
from PyQt6.QtCore import QDate, QTime, Qt
from datetime import datetime, date, timedelta, time
from models.user import User, UserRole
from models.cage import Cage, CageStatus
from models.booking import Booking, BookingStatus
from services.cage_service import CageService
from services.booking_service import BookingService
from services.conflict_service import ConflictService
from services.user_service import UserService
from ui.dialogs.cage_dialog import CageDialog
from ui.dialogs.booking_dialog import BookingDialog

class CageTab(QWidget):
    def __init__(self, current_user: User):
        super().__init__()
        self.current_user = current_user
        self.selected_cage: Cage = None
        self.selected_date = date.today()
        self._init_ui()
        self._load_cages()
        self._load_schedule()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = self._create_left_panel()
        right_panel = self._create_right_panel()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter)

    def _create_left_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        cage_group = QGroupBox('笼位列表')
        cage_layout = QVBoxLayout(cage_group)

        btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton('🔄 刷新')
        self.refresh_btn.clicked.connect(self._load_cages)
        btn_layout.addWidget(self.refresh_btn)

        if self.current_user.role in [UserRole.FACILITY_MANAGER]:
            self.add_cage_btn = QPushButton('➕ 新增笼位')
            self.add_cage_btn.clicked.connect(self._add_cage)
            btn_layout.addWidget(self.add_cage_btn)

        cage_layout.addLayout(btn_layout)

        self.cage_list = QListWidget()
        self.cage_list.itemClicked.connect(self._on_cage_selected)
        self.cage_list.setStyleSheet('''
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background: #409eff;
                color: white;
            }
        ''')
        cage_layout.addWidget(self.cage_list)

        layout.addWidget(cage_group)

        if self.selected_cage:
            info_group = QGroupBox('笼位信息')
            info_layout = QFormLayout(info_group)
            self.info_labels = {}
            for field in ['编号', '房间', '容量', '动物类型', '状态']:
                label = QLabel('-')
                self.info_labels[field] = label
                info_layout.addRow(f'{field}：', label)
            layout.addWidget(info_group)

        layout.addStretch()
        return widget

    def _create_right_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        control_layout = QHBoxLayout()
        
        date_label = QLabel('选择日期：')
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.dateChanged.connect(self._on_date_changed)
        control_layout.addWidget(date_label)
        control_layout.addWidget(self.date_edit)

        self.prev_day_btn = QPushButton('◀ 前一天')
        self.prev_day_btn.clicked.connect(lambda: self.date_edit.setDate(self.date_edit.date().addDays(-1)))
        control_layout.addWidget(self.prev_day_btn)

        self.next_day_btn = QPushButton('后一天 ▶')
        self.next_day_btn.clicked.connect(lambda: self.date_edit.setDate(self.date_edit.date().addDays(1)))
        control_layout.addWidget(self.next_day_btn)

        self.today_btn = QPushButton('今天')
        self.today_btn.clicked.connect(lambda: self.date_edit.setDate(QDate.currentDate()))
        control_layout.addWidget(self.today_btn)

        control_layout.addStretch()

        if self.current_user.role == UserRole.RESEARCHER:
            self.new_booking_btn = QPushButton('📅 新建预约')
            self.new_booking_btn.clicked.connect(self._create_booking)
            self.new_booking_btn.setStyleSheet('''
                QPushButton {
                    background: #67c23a;
                    color: white;
                    padding: 8px 16px;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #5daf34;
                }
                QPushButton:disabled {
                    background: #c0c4cc;
                }
            ''')
            self.new_booking_btn.setEnabled(False)
            control_layout.addWidget(self.new_booking_btn)

        layout.addLayout(control_layout)

        schedule_group = QGroupBox('时段排期表')
        schedule_layout = QVBoxLayout(schedule_group)

        self.schedule_table = QTableWidget()
        self.schedule_table.setColumnCount(3)
        self.schedule_table.setHorizontalHeaderLabels(['时段', '预约信息', '状态'])
        self.schedule_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.schedule_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.schedule_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.schedule_table.setColumnWidth(0, 120)
        self.schedule_table.setColumnWidth(2, 100)
        self.schedule_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.schedule_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.schedule_table.verticalHeader().setVisible(False)
        self.schedule_table.setStyleSheet('''
            QTableWidget {
                gridline-color: #e4e7ed;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background: #f5f7fa;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #e4e7ed;
                font-weight: bold;
            }
        ''')
        schedule_layout.addWidget(self.schedule_table)

        layout.addWidget(schedule_group)

        return widget

    def _load_cages(self):
        self.cage_list.clear()
        cages = CageService.get_all_cages()
        for cage in cages:
            item = QListWidgetItem(f'[{cage.cage_code}] {cage.room} - {cage.animal_type}')
            item.setData(Qt.ItemDataRole.UserRole, cage)
            status_text = {CageStatus.AVAILABLE: '🟢', CageStatus.OCCUPIED: '🔴', CageStatus.MAINTENANCE: '🟡'}.get(cage.status, '⚪')
            item.setText(f'{status_text} {item.text()}')
            self.cage_list.addItem(item)

    def _on_cage_selected(self, item):
        self.selected_cage = item.data(Qt.ItemDataRole.UserRole)
        if hasattr(self, 'new_booking_btn'):
            self.new_booking_btn.setEnabled(True)
        self._update_cage_info()
        self._load_schedule()

    def _update_cage_info(self):
        if not self.selected_cage:
            return
        if hasattr(self, 'info_labels'):
            status_map = {CageStatus.AVAILABLE: '可用', CageStatus.OCCUPIED: '占用', CageStatus.MAINTENANCE: '维护中'}
            self.info_labels['编号'].setText(self.selected_cage.cage_code)
            self.info_labels['房间'].setText(self.selected_cage.room)
            self.info_labels['容量'].setText(str(self.selected_cage.capacity))
            self.info_labels['动物类型'].setText(self.selected_cage.animal_type)
            self.info_labels['状态'].setText(status_map.get(self.selected_cage.status, self.selected_cage.status.value))

    def _on_date_changed(self):
        self.selected_date = self.date_edit.date().toPyDate()
        self._load_schedule()

    def _load_schedule(self):
        self.schedule_table.setRowCount(0)
        if not self.selected_cage:
            return

        start_datetime = datetime.combine(self.selected_date, datetime.min.time())
        end_datetime = datetime.combine(self.selected_date + timedelta(days=1), datetime.min.time())

        bookings = ConflictService.get_cage_bookings_in_range(
            self.selected_cage.id, start_datetime, end_datetime
        )

        time_slots = []
        for hour in range(8, 20):
            slot_start = datetime.combine(self.selected_date, time(hour, 0))
            slot_end = datetime.combine(self.selected_date, time(hour + 1, 0))
            time_slots.append((slot_start, slot_end))

        for slot_start, slot_end in time_slots:
            row = self.schedule_table.rowCount()
            self.schedule_table.insertRow(row)

            time_text = f'{slot_start.strftime("%H:%M")} - {slot_end.strftime("%H:%M")}'
            self.schedule_table.setItem(row, 0, QTableWidgetItem(time_text))

            booking_info = ''
            status_text = '空闲'
            status_color = '#67c23a'

            for booking in bookings:
                if ConflictService.check_time_overlap(slot_start, slot_end, booking.start_time, booking.end_time):
                    if booking.status in [BookingStatus.APPROVED, BookingStatus.PENDING_ADVISOR, 
                                          BookingStatus.PENDING_FACILITY, BookingStatus.PENDING_ETHICS]:
                        booking_info = (f'预约#{booking.id} | {booking.project_name}\n'
                                        f'申请人：{booking.researcher.name}\n'
                                        f'{booking.start_time.strftime("%H:%M")} - {booking.end_time.strftime("%H:%M")}')
                        status_text = BookingService.get_booking_status_text(booking.status)
                        status_color = '#e6a23c' if booking.status != BookingStatus.APPROVED else '#f56c6c'
                        break

            info_item = QTableWidgetItem(booking_info if booking_info else '可预约')
            self.schedule_table.setItem(row, 1, info_item)

            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(Qt.GlobalColor.white if status_color != '#67c23a' else Qt.GlobalColor.black)
            status_item.setBackground(Qt.GlobalColor.white)
            status_item.setForeground(Qt.GlobalColor.darkGreen if status_color == '#67c23a' else 
                                      Qt.GlobalColor.darkYellow if status_color == '#e6a23c' else Qt.GlobalColor.red)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.schedule_table.setItem(row, 2, status_item)

    def _add_cage(self):
        dialog = CageDialog(self)
        if dialog.exec():
            self._load_cages()

    def _create_booking(self):
        if not self.selected_cage:
            QMessageBox.warning(self, '提示', '请先选择一个笼位')
            return
        dialog = BookingDialog(self, self.selected_cage, self.current_user, self.selected_date)
        if dialog.exec():
            self._load_schedule()
