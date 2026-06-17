from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QMessageBox, QLabel, QLineEdit,
                             QGroupBox, QTabWidget, QFormLayout, QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt, QTimer
from models.user import User, UserRole
from models.booking import BookingStatus
from services.access_service import AccessService
from services.booking_service import BookingService
from services.user_service import UserService
from datetime import datetime

class AccessTab(QWidget):
    def __init__(self, current_user: User):
        super().__init__()
        self.current_user = current_user
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        title = QLabel('🔐 准入登记管理')
        title.setStyleSheet('font-size: 16px; font-weight: bold; color: #2c3e50;')
        layout.addWidget(title)

        if self.current_user.role == UserRole.FACILITY_MANAGER:
            entry_group = QGroupBox('快速登记')
            entry_layout = QHBoxLayout(entry_group)

            self.access_code_edit = QLineEdit()
            self.access_code_edit.setPlaceholderText('请扫描或输入准入码...')
            self.access_code_edit.returnPressed.connect(self._on_access_code_submit)
            entry_layout.addWidget(self.access_code_edit, 2)

            self.entry_btn = QPushButton('🚪 登记进入')
            self.entry_btn.clicked.connect(self._record_entry)
            self.entry_btn.setStyleSheet('''
                QPushButton {
                    background: #67c23a; color: white; padding: 10px 20px;
                    border: none; border-radius: 4px; font-weight: bold;
                }
                QPushButton:hover { background: #5daf34; }
            ''')
            entry_layout.addWidget(self.entry_btn)

            self.exit_btn = QPushButton('🚪 登记离开')
            self.exit_btn.clicked.connect(self._record_exit)
            self.exit_btn.setStyleSheet('''
                QPushButton {
                    background: #e6a23c; color: white; padding: 10px 20px;
                    border: none; border-radius: 4px; font-weight: bold;
                }
                QPushButton:hover { background: #d48806; }
            ''')
            entry_layout.addWidget(self.exit_btn)

            layout.addWidget(entry_group)

        self.tab_widget = QTabWidget()

        self.pending_tab = QWidget()
        self._init_pending_tab()
        self.tab_widget.addTab(self.pending_tab, '✅ 待准入（已通过审批）')

        self.active_tab = QWidget()
        self._init_active_tab()
        self.tab_widget.addTab(self.active_tab, '⏰ 进行中')

        self.history_tab = QWidget()
        self._init_history_tab()
        self.tab_widget.addTab(self.history_tab, '📜 历史记录')

        layout.addWidget(self.tab_widget)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._load_data)
        self.timer.start(30000)

    def _init_pending_tab(self):
        layout = QVBoxLayout(self.pending_tab)
        layout.setContentsMargins(0, 0, 0, 0)

        btn_layout = QHBoxLayout()
        self.refresh_btn1 = QPushButton('🔄 刷新')
        self.refresh_btn1.clicked.connect(self._load_pending_bookings)
        btn_layout.addWidget(self.refresh_btn1)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.pending_table = QTableWidget()
        self.pending_table.setColumnCount(8)
        self.pending_table.setHorizontalHeaderLabels([
            '预约ID', '项目名称', '申请人', '笼位', '时段', '审批状态', '操作', '准入码'
        ])
        self.pending_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.pending_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.pending_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.pending_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.pending_table.verticalHeader().setVisible(False)
        self.pending_table.setStyleSheet('''
            QTableWidget { gridline-color: #e4e7ed; }
            QTableWidget::item { padding: 8px; }
            QHeaderView::section {
                background: #f5f7fa; padding: 8px; border: none;
                border-bottom: 1px solid #e4e7ed; font-weight: bold;
            }
        ''')
        layout.addWidget(self.pending_table)

        self.pending_table.itemClicked.connect(self._on_pending_clicked)

    def _init_active_tab(self):
        layout = QVBoxLayout(self.active_tab)
        layout.setContentsMargins(0, 0, 0, 0)

        btn_layout = QHBoxLayout()
        self.refresh_btn2 = QPushButton('🔄 刷新')
        self.refresh_btn2.clicked.connect(self._load_active_access)
        btn_layout.addWidget(self.refresh_btn2)
        btn_layout.addStretch()

        stats_label = QLabel()
        stats_label.setObjectName('stats_label')
        btn_layout.addWidget(stats_label)
        layout.addLayout(btn_layout)

        self.active_table = QTableWidget()
        self.active_table.setColumnCount(7)
        self.active_table.setHorizontalHeaderLabels([
            '准入码', '预约ID', '申请人', '笼位', '进入时间', '登记人', '操作'
        ])
        self.active_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.active_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.active_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.active_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.active_table.verticalHeader().setVisible(False)
        self.active_table.setStyleSheet('''
            QTableWidget { gridline-color: #e4e7ed; }
            QTableWidget::item { padding: 8px; }
            QHeaderView::section {
                background: #f5f7fa; padding: 8px; border: none;
                border-bottom: 1px solid #e4e7ed; font-weight: bold;
            }
        ''')
        layout.addWidget(self.active_table)

    def _init_history_tab(self):
        layout = QVBoxLayout(self.history_tab)
        layout.setContentsMargins(0, 0, 0, 0)

        btn_layout = QHBoxLayout()
        self.refresh_btn3 = QPushButton('🔄 刷新')
        self.refresh_btn3.clicked.connect(self._load_history_access)
        btn_layout.addWidget(self.refresh_btn3)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels([
            '准入码', '预约ID', '申请人', '笼位', '进入时间', '离开时间', '时长', '登记人'
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setStyleSheet('''
            QTableWidget { gridline-color: #e4e7ed; }
            QTableWidget::item { padding: 8px; }
            QHeaderView::section {
                background: #f5f7fa; padding: 8px; border: none;
                border-bottom: 1px solid #e4e7ed; font-weight: bold;
            }
        ''')
        layout.addWidget(self.history_table)

    def _load_data(self):
        self._load_pending_bookings()
        self._load_active_access()
        self._load_history_access()

    def _load_pending_bookings(self):
        self.pending_table.setRowCount(0)
        bookings = BookingService.get_bookings_by_status(BookingStatus.APPROVED)

        is_manager = self.current_user.role == UserRole.FACILITY_MANAGER

        for booking in bookings:
            access = AccessService.get_access_by_booking(booking.id)
            if access and access.is_active:
                continue

            row = self.pending_table.rowCount()
            self.pending_table.insertRow(row)

            self.pending_table.setItem(row, 0, QTableWidgetItem(str(booking.id)))
            self.pending_table.setItem(row, 1, QTableWidgetItem(booking.project_name))
            self.pending_table.setItem(row, 2, QTableWidgetItem(booking.researcher.name))
            self.pending_table.setItem(row, 3, QTableWidgetItem(f'{booking.cage.cage_code} ({booking.cage.room})'))
            
            time_text = (f'{booking.start_time.strftime("%Y-%m-%d %H:%M")}\n'
                        f'{booking.end_time.strftime("%Y-%m-%d %H:%M")}')
            self.pending_table.setItem(row, 4, QTableWidgetItem(time_text))
            
            status_item = QTableWidgetItem(BookingService.get_booking_status_text(booking.status))
            status_item.setForeground(Qt.GlobalColor.darkGreen)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.pending_table.setItem(row, 5, status_item)

            if is_manager:
                register_btn = QPushButton('生成准入码')
                register_btn.setStyleSheet('''
                    QPushButton {
                        background: #409eff; color: white; padding: 4px 12px;
                        border: none; border-radius: 3px;
                    }
                    QPushButton:hover { background: #66b1ff; }
                ''')
                register_btn.clicked.connect(lambda _, b=booking: self._generate_access_code(b))
                self.pending_table.setCellWidget(row, 6, register_btn)
            else:
                self.pending_table.setItem(row, 6, QTableWidgetItem('-'))

            access_code_text = access.access_code if access else '未生成'
            if access and access.is_active:
                access_code_text = f'🔑 {access.access_code}'
            self.pending_table.setItem(row, 7, QTableWidgetItem(access_code_text))

            self.pending_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, booking)

    def _load_active_access(self):
        self.active_table.setRowCount(0)
        access_list = AccessService.get_active_access_registrations()

        is_manager = self.current_user.role == UserRole.FACILITY_MANAGER

        stats = self.findChild(QLabel, 'stats_label')
        if stats:
            stats.setText(f'当前场内人员：<b>{len(access_list)}</b> 人')
            stats.setStyleSheet('font-size: 14px; color: #e6a23c; font-weight: bold;')

        for access in access_list:
            booking = access.booking
            row = self.active_table.rowCount()
            self.active_table.insertRow(row)

            code_item = QTableWidgetItem(f'🔑 {access.access_code}')
            code_item.setForeground(Qt.GlobalColor.darkGreen)
            self.active_table.setItem(row, 0, code_item)
            
            self.active_table.setItem(row, 1, QTableWidgetItem(str(booking.id)))
            self.active_table.setItem(row, 2, QTableWidgetItem(booking.researcher.name))
            self.active_table.setItem(row, 3, QTableWidgetItem(booking.cage.cage_code))
            self.active_table.setItem(row, 4, QTableWidgetItem(
                access.entry_time.strftime('%Y-%m-%d %H:%M') if access.entry_time else '-'
            ))
            self.active_table.setItem(row, 5, QTableWidgetItem(access.registered_by))

            if is_manager and access.entry_time and not access.exit_time:
                exit_btn = QPushButton('登记离开')
                exit_btn.setStyleSheet('''
                    QPushButton {
                        background: #e6a23c; color: white; padding: 4px 12px;
                        border: none; border-radius: 3px;
                    }
                    QPushButton:hover { background: #d48806; }
                ''')
                exit_btn.clicked.connect(lambda _, a=access: self._quick_exit(a))
                self.active_table.setCellWidget(row, 6, exit_btn)
            else:
                self.active_table.setItem(row, 6, QTableWidgetItem('等待进入'))

            self.active_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, access)

    def _load_history_access(self):
        self.history_table.setRowCount(0)
        access_list = AccessService.get_all_access_registrations()

        for access in access_list:
            if access.is_active and not access.exit_time:
                continue

            booking = access.booking
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)

            self.history_table.setItem(row, 0, QTableWidgetItem(access.access_code))
            self.history_table.setItem(row, 1, QTableWidgetItem(str(booking.id)))
            self.history_table.setItem(row, 2, QTableWidgetItem(booking.researcher.name))
            self.history_table.setItem(row, 3, QTableWidgetItem(booking.cage.cage_code))
            self.history_table.setItem(row, 4, QTableWidgetItem(
                access.entry_time.strftime('%Y-%m-%d %H:%M') if access.entry_time else '-'
            ))
            self.history_table.setItem(row, 5, QTableWidgetItem(
                access.exit_time.strftime('%Y-%m-%d %H:%M') if access.exit_time else '-'
            ))

            duration_text = '-'
            if access.entry_time and access.exit_time:
                duration = access.exit_time - access.entry_time
                hours = duration.total_seconds() / 3600
                duration_text = f'{hours:.1f} 小时'
            self.history_table.setItem(row, 6, QTableWidgetItem(duration_text))
            self.history_table.setItem(row, 7, QTableWidgetItem(access.registered_by))

    def _on_access_code_submit(self):
        code = self.access_code_edit.text().strip()
        if not code:
            return

        if not self.access_code_edit.property('mode') or self.access_code_edit.property('mode') == 'entry':
            self._record_entry()
        else:
            self._record_exit()

    def _record_entry(self):
        code = self.access_code_edit.text().strip()
        if not code:
            QMessageBox.warning(self, '提示', '请输入准入码')
            return

        success, message = AccessService.record_entry(code)
        if success:
            QMessageBox.information(self, '成功', message)
            self.access_code_edit.clear()
            self._load_data()
        else:
            QMessageBox.warning(self, '失败', message)

    def _record_exit(self):
        code = self.access_code_edit.text().strip()
        if not code:
            QMessageBox.warning(self, '提示', '请输入准入码')
            return

        success, message = AccessService.record_exit(code)
        if success:
            QMessageBox.information(self, '成功', message)
            self.access_code_edit.clear()
            self._load_data()
        else:
            QMessageBox.warning(self, '失败', message)

    def _quick_exit(self, access):
        success, message = AccessService.record_exit(access.access_code)
        if success:
            QMessageBox.information(self, '成功', message)
            self._load_data()
        else:
            QMessageBox.warning(self, '失败', message)

    def _generate_access_code(self, booking):
        success, message, access = AccessService.create_access_registration(
            booking.id, self.current_user.name
        )
        if success:
            dialog = AccessCodeDialog(self, access.access_code, booking)
            dialog.exec()
            self._load_pending_bookings()
        else:
            QMessageBox.critical(self, '失败', message)

    def _on_pending_clicked(self, item):
        pass


class AccessCodeDialog(QDialog):
    def __init__(self, parent=None, access_code='', booking=None):
        super().__init__(parent)
        self.setWindowTitle('准入码已生成')
        self.setFixedWidth(400)
        self._init_ui(access_code, booking)

    def _init_ui(self, access_code, booking):
        layout = QFormLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel('✅ 准入码生成成功！')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet('font-size: 16px; font-weight: bold; color: #67c23a;')
        layout.addRow(title)

        code_label = QLabel(f'<h2 style="text-align: center; color: #409eff; font-family: monospace;">{access_code}</h2>')
        code_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addRow(code_label)

        if booking:
            info = QLabel(
                f'<p style="text-align: center; color: #666;">'
                f'预约 #{booking.id}<br>'
                f'{booking.project_name}<br>'
                f'笼位：{booking.cage.cage_code}<br>'
                f'时段：{booking.start_time.strftime("%Y-%m-%d %H:%M")} ~ {booking.end_time.strftime("%Y-%m-%d %H:%M")}'
                f'</p>'
            )
            layout.addRow(info)

        hint = QLabel('请将此准入码告知申请人，进入动物房时需核验。')
        hint.setStyleSheet('color: #999; text-align: center;')
        hint.setWordWrap(True)
        layout.addRow(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addRow(buttons)
