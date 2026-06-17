from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QMessageBox, QLabel, QComboBox,
                             QGroupBox, QTextEdit, QDialog, QFormLayout, QDialogButtonBox)
from PyQt6.QtCore import Qt
from models.user import User, UserRole
from models.booking import Booking, BookingStatus
from services.booking_service import BookingService
from services.approval_service import ApprovalService
from services.user_service import UserService

class BookingTab(QWidget):
    def __init__(self, current_user: User):
        super().__init__()
        self.current_user = current_user
        self._init_ui()
        self._load_bookings()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        filter_layout = QHBoxLayout()
        
        filter_label = QLabel('状态筛选：')
        self.status_filter = QComboBox()
        self.status_filter.addItem('全部', None)
        for status in BookingStatus:
            self.status_filter.addItem(BookingService.get_booking_status_text(status), status)
        self.status_filter.currentIndexChanged.connect(self._load_bookings)
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.status_filter)

        filter_layout.addStretch()

        self.refresh_btn = QPushButton('🔄 刷新')
        self.refresh_btn.clicked.connect(self._load_bookings)
        filter_layout.addWidget(self.refresh_btn)

        layout.addLayout(filter_layout)

        table_group = QGroupBox('我的预约')
        table_layout = QVBoxLayout(table_group)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            'ID', '项目名称', '笼位', '时段', '动物数', '状态', '驳回原因', '操作'
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet('''
            QTableWidget { gridline-color: #e4e7ed; }
            QTableWidget::item { padding: 8px; }
            QHeaderView::section {
                background: #f5f7fa; padding: 8px; border: none;
                border-bottom: 1px solid #e4e7ed; font-weight: bold;
            }
        ''')
        table_layout.addWidget(self.table)

        layout.addWidget(table_group)

        self.detail_group = QGroupBox('预约详情')
        detail_layout = QVBoxLayout(self.detail_group)
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setFixedHeight(120)
        detail_layout.addWidget(self.detail_text)

        btn_layout = QHBoxLayout()
        self.submit_btn = QPushButton('📤 提交审批')
        self.submit_btn.clicked.connect(self._submit_booking)
        self.submit_btn.setEnabled(False)
        btn_layout.addWidget(self.submit_btn)

        self.edit_btn = QPushButton('✏️ 修改')
        self.edit_btn.clicked.connect(self._edit_booking)
        self.edit_btn.setEnabled(False)
        btn_layout.addWidget(self.edit_btn)

        self.cancel_btn = QPushButton('❌ 取消预约')
        self.cancel_btn.clicked.connect(self._cancel_booking)
        self.cancel_btn.setEnabled(False)
        btn_layout.addWidget(self.cancel_btn)

        self.view_approval_btn = QPushButton('📜 查看审批记录')
        self.view_approval_btn.clicked.connect(self._view_approval_history)
        self.view_approval_btn.setEnabled(False)
        btn_layout.addWidget(self.view_approval_btn)

        btn_layout.addStretch()
        detail_layout.addLayout(btn_layout)

        layout.addWidget(self.detail_group)

        self.table.itemSelectionChanged.connect(self._on_selection_changed)

    def _load_bookings(self):
        self.table.setRowCount(0)
        
        status_filter = self.status_filter.currentData()
        
        if self.current_user.role == UserRole.RESEARCHER:
            bookings = BookingService.get_bookings_by_researcher(self.current_user.id)
        else:
            bookings = BookingService.get_all_bookings()

        if status_filter:
            bookings = [b for b in bookings if b.status == status_filter]

        status_colors = {
            BookingStatus.DRAFT: '#909399',
            BookingStatus.PENDING_ADVISOR: '#e6a23c',
            BookingStatus.PENDING_FACILITY: '#e6a23c',
            BookingStatus.PENDING_ETHICS: '#e6a23c',
            BookingStatus.APPROVED: '#67c23a',
            BookingStatus.REJECTED: '#f56c6c',
            BookingStatus.CANCELLED: '#909399',
            BookingStatus.COMPLETED: '#409eff',
        }

        for booking in bookings:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(str(booking.id)))
            self.table.setItem(row, 1, QTableWidgetItem(booking.project_name))
            self.table.setItem(row, 2, QTableWidgetItem(f'{booking.cage.cage_code} ({booking.cage.room})'))
            
            time_text = (f'{booking.start_time.strftime("%Y-%m-%d %H:%M")}\n'
                        f'{booking.end_time.strftime("%Y-%m-%d %H:%M")}')
            time_item = QTableWidgetItem(time_text)
            self.table.setItem(row, 3, time_item)
            
            self.table.setItem(row, 4, QTableWidgetItem(str(booking.animal_count)))
            
            status_text = BookingService.get_booking_status_text(booking.status)
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(Qt.GlobalColor.white if booking.status in [BookingStatus.APPROVED] else Qt.GlobalColor.black)
            status_item.setForeground(Qt.GlobalColor.darkGreen if booking.status == BookingStatus.APPROVED else
                                      Qt.GlobalColor.red if booking.status in [BookingStatus.REJECTED, BookingStatus.CANCELLED] else
                                      Qt.GlobalColor.darkYellow if 'PENDING' in booking.status.name else Qt.GlobalColor.gray)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, status_item)

            reject_item = QTableWidgetItem(booking.reject_reason or '-')
            self.table.setItem(row, 6, reject_item)

            self.table.setItem(row, 7, QTableWidgetItem(''))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, booking)

    def _on_selection_changed(self):
        selected = self.table.selectedItems()
        if not selected:
            self._clear_details()
            return

        row = selected[0].row()
        booking = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not booking:
            return

        detail_text = (
            f'预约编号：#{booking.id}\n'
            f'项目名称：{booking.project_name}\n'
            f'笼位：{booking.cage.cage_code} - {booking.cage.room}\n'
            f'动物类型：{booking.cage.animal_type}\n'
            f'数量：{booking.animal_count}\n'
            f'时段：{booking.start_time.strftime("%Y-%m-%d %H:%M")} 至 {booking.end_time.strftime("%Y-%m-%d %H:%M")}\n'
            f'申请人：{booking.researcher.name}\n'
            f'状态：{BookingService.get_booking_status_text(booking.status)}\n'
            f'创建时间：{booking.created_at.strftime("%Y-%m-%d %H:%M")}\n'
            f'实验目的：{booking.purpose}\n'
        )
        if booking.reject_reason:
            detail_text += f'\n驳回原因：{booking.reject_reason}'
        
        self.detail_text.setText(detail_text)

        is_researcher = self.current_user.role == UserRole.RESEARCHER
        is_own = booking.researcher_id == self.current_user.id

        can_submit = is_researcher and is_own and booking.status == BookingStatus.DRAFT
        can_edit = is_researcher and is_own and booking.status == BookingStatus.DRAFT
        can_cancel = is_researcher and is_own and booking.status not in [
            BookingStatus.CANCELLED, BookingStatus.REJECTED, BookingStatus.COMPLETED
        ]
        can_view_history = len(booking.approvals) > 0

        self.submit_btn.setEnabled(can_submit)
        self.edit_btn.setEnabled(can_edit)
        self.cancel_btn.setEnabled(can_cancel)
        self.view_approval_btn.setEnabled(can_view_history)

    def _clear_details(self):
        self.detail_text.clear()
        self.submit_btn.setEnabled(False)
        self.edit_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.view_approval_btn.setEnabled(False)

    def _submit_booking(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        booking = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(self, '确认', 
            f'确定要提交预约 #{booking.id} 进入审批流程吗？\n\n审批流程：导师 → 动物房管理员 → 伦理委员会',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            success, message = BookingService.submit_booking(booking.id)
            if success:
                QMessageBox.information(self, '成功', message)
                self._load_bookings()
            else:
                QMessageBox.critical(self, '失败', message)

    def _edit_booking(self):
        QMessageBox.information(self, '提示', '修改功能可扩展：编辑预约信息后重新提交')

    def _cancel_booking(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        booking = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(self, '确认', 
            f'确定要取消预约 #{booking.id} 吗？\n\n取消后时段将被释放，其他人可以预约。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            success, message = BookingService.cancel_booking(booking.id)
            if success:
                QMessageBox.information(self, '成功', message)
                self._load_bookings()
            else:
                QMessageBox.critical(self, '失败', message)

    def _view_approval_history(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        booking = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        approvals = ApprovalService.get_approval_history(booking.id)
        
        dialog = ApprovalHistoryDialog(self, approvals)
        dialog.exec()


class ApprovalHistoryDialog(QDialog):
    def __init__(self, parent=None, approvals=None):
        super().__init__(parent)
        self.setWindowTitle('审批记录')
        self.resize(500, 400)
        self.approvals = approvals or []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        from models.approval import ApprovalStatus, ApprovalNode
        node_names = {
            ApprovalNode.ADVISOR: '导师审批',
            ApprovalNode.FACILITY_MANAGER: '管理员审批',
            ApprovalNode.ETHICS_COMMITTEE: '伦理审批',
        }
        status_names = {
            ApprovalStatus.PENDING: '待处理',
            ApprovalStatus.APPROVED: '✓ 通过',
            ApprovalStatus.REJECTED: '✗ 驳回',
        }

        for i, approval in enumerate(self.approvals, 1):
            group = QGroupBox(f'第 {i} 步：{node_names.get(approval.node, approval.node.value)}')
            group_layout = QFormLayout(group)
            
            status_text = status_names.get(approval.status, approval.status.value)
            status_label = QLabel(f'<b>{status_text}</b>')
            if approval.status == ApprovalStatus.APPROVED:
                status_label.setStyleSheet('color: #67c23a;')
            elif approval.status == ApprovalStatus.REJECTED:
                status_label.setStyleSheet('color: #f56c6c;')
            group_layout.addRow('结果：', status_label)
            
            group_layout.addRow('审批人：', QLabel(approval.approver.name))
            group_layout.addRow('时间：', QLabel(approval.updated_at.strftime('%Y-%m-%d %H:%M:%S')))
            group_layout.addRow('意见：', QLabel(approval.comments or '无'))
            
            layout.addWidget(group)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
