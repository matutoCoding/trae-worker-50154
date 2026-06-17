from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QMessageBox, QLabel, QComboBox,
                             QGroupBox, QTextEdit, QDialog, QFormLayout, QDialogButtonBox,
                             QTabWidget)
from PyQt6.QtCore import Qt
from models.user import User, UserRole
from models.booking import Booking, BookingStatus
from models.approval import Approval, ApprovalNode, ApprovalStatus
from services.approval_service import ApprovalService
from services.booking_service import BookingService
from services.user_service import UserService

class ApprovalTab(QWidget):
    def __init__(self, current_user: User):
        super().__init__()
        self.current_user = current_user
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        role_text = UserService.get_role_name(self.current_user.role)
        title = QLabel(f'🔐 审批工作台 - {role_text}')
        title.setStyleSheet('font-size: 16px; font-weight: bold; color: #2c3e50;')
        layout.addWidget(title)

        self.tab_widget = QTabWidget()

        self.pending_tab = QWidget()
        self._init_pending_tab()
        self.tab_widget.addTab(self.pending_tab, '⏳ 待我审批')

        self.history_tab = QWidget()
        self._init_history_tab()
        self.tab_widget.addTab(self.history_tab, '📜 审批历史')

        layout.addWidget(self.tab_widget)

        self.tab_widget.currentChanged.connect(self._on_tab_changed)

    def _init_pending_tab(self):
        layout = QVBoxLayout(self.pending_tab)
        layout.setContentsMargins(0, 0, 0, 0)

        btn_layout = QHBoxLayout()
        self.refresh_pending_btn = QPushButton('🔄 刷新')
        self.refresh_pending_btn.clicked.connect(self._load_pending_approvals)
        btn_layout.addWidget(self.refresh_pending_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.pending_table = QTableWidget()
        self.pending_table.setColumnCount(7)
        self.pending_table.setHorizontalHeaderLabels([
            'ID', '项目名称', '申请人', '笼位', '时段', '提交时间', '审批节点'
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

        action_layout = QHBoxLayout()
        
        self.booking_detail = QTextEdit()
        self.booking_detail.setReadOnly(True)
        self.booking_detail.setFixedHeight(100)
        action_layout.addWidget(self.booking_detail, 2)

        right_panel = QVBoxLayout()
        
        self.approve_btn = QPushButton('✓ 通过')
        self.approve_btn.setStyleSheet('''
            QPushButton {
                background: #67c23a; color: white; padding: 12px;
                border: none; border-radius: 4px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background: #5daf34; }
            QPushButton:disabled { background: #c0c4cc; }
        ''')
        self.approve_btn.clicked.connect(self._on_approve)
        self.approve_btn.setEnabled(False)
        right_panel.addWidget(self.approve_btn)

        self.reject_btn = QPushButton('✗ 驳回')
        self.reject_btn.setStyleSheet('''
            QPushButton {
                background: #f56c6c; color: white; padding: 12px;
                border: none; border-radius: 4px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background: #e74c3c; }
            QPushButton:disabled { background: #c0c4cc; }
        ''')
        self.reject_btn.clicked.connect(self._on_reject)
        self.reject_btn.setEnabled(False)
        right_panel.addWidget(self.reject_btn)

        action_layout.addLayout(right_panel, 1)
        layout.addLayout(action_layout)

        self.pending_table.itemSelectionChanged.connect(self._on_pending_selected)

    def _init_history_tab(self):
        layout = QVBoxLayout(self.history_tab)
        layout.setContentsMargins(0, 0, 0, 0)

        btn_layout = QHBoxLayout()
        self.refresh_history_btn = QPushButton('🔄 刷新')
        self.refresh_history_btn.clicked.connect(self._load_history_approvals)
        btn_layout.addWidget(self.refresh_history_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels([
            'ID', '项目名称', '审批节点', '结果', '审批人', '时间', '意见', '当前状态'
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
        self._load_pending_approvals()
        self._load_history_approvals()

    def _on_tab_changed(self, index):
        if index == 0:
            self._load_pending_approvals()
        else:
            self._load_history_approvals()

    def _load_pending_approvals(self):
        self.pending_table.setRowCount(0)
        approvals = ApprovalService.get_approvals_for_user(self.current_user.id)

        node_names = {
            ApprovalNode.ADVISOR: '导师审批',
            ApprovalNode.FACILITY_MANAGER: '管理员审批',
            ApprovalNode.ETHICS_COMMITTEE: '伦理审批',
        }

        for approval in approvals:
            booking = approval.booking
            row = self.pending_table.rowCount()
            self.pending_table.insertRow(row)

            self.pending_table.setItem(row, 0, QTableWidgetItem(str(booking.id)))
            self.pending_table.setItem(row, 1, QTableWidgetItem(booking.project_name))
            self.pending_table.setItem(row, 2, QTableWidgetItem(booking.researcher.name))
            self.pending_table.setItem(row, 3, QTableWidgetItem(booking.cage.cage_code))
            
            time_text = (f'{booking.start_time.strftime("%Y-%m-%d %H:%M")}\n'
                        f'{booking.end_time.strftime("%Y-%m-%d %H:%M")}')
            self.pending_table.setItem(row, 4, QTableWidgetItem(time_text))
            
            self.pending_table.setItem(row, 5, QTableWidgetItem(booking.created_at.strftime('%Y-%m-%d %H:%M')))
            
            node_item = QTableWidgetItem(node_names.get(approval.node, approval.node.value))
            node_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.pending_table.setItem(row, 6, node_item)

            self.pending_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, (approval, booking))

    def _load_history_approvals(self):
        self.history_table.setRowCount(0)
        
        from db.database import SessionLocal
        db = SessionLocal()
        try:
            approvals = db.query(Approval).filter(
                Approval.approver_id == self.current_user.id,
                Approval.status != ApprovalStatus.PENDING
            ).order_by(Approval.updated_at.desc()).all()
        finally:
            db.close()

        node_names = {
            ApprovalNode.ADVISOR: '导师审批',
            ApprovalNode.FACILITY_MANAGER: '管理员审批',
            ApprovalNode.ETHICS_COMMITTEE: '伦理审批',
        }
        status_names = {
            ApprovalStatus.APPROVED: '✓ 通过',
            ApprovalStatus.REJECTED: '✗ 驳回',
        }

        for approval in approvals:
            booking = approval.booking
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)

            self.history_table.setItem(row, 0, QTableWidgetItem(str(booking.id)))
            self.history_table.setItem(row, 1, QTableWidgetItem(booking.project_name))
            self.history_table.setItem(row, 2, QTableWidgetItem(node_names.get(approval.node, approval.node.value)))
            
            status_item = QTableWidgetItem(status_names.get(approval.status, approval.status.value))
            if approval.status == ApprovalStatus.APPROVED:
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            else:
                status_item.setForeground(Qt.GlobalColor.red)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_table.setItem(row, 3, status_item)

            self.history_table.setItem(row, 4, QTableWidgetItem(approval.approver.name))
            self.history_table.setItem(row, 5, QTableWidgetItem(approval.updated_at.strftime('%Y-%m-%d %H:%M')))
            self.history_table.setItem(row, 6, QTableWidgetItem(approval.comments or '无'))
            self.history_table.setItem(row, 7, QTableWidgetItem(BookingService.get_booking_status_text(booking.status)))

    def _on_pending_selected(self):
        selected = self.pending_table.selectedItems()
        if not selected:
            self.booking_detail.clear()
            self.approve_btn.setEnabled(False)
            self.reject_btn.setEnabled(False)
            return

        row = selected[0].row()
        approval, booking = self.pending_table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        detail_text = (
            f'📋 预约 #{booking.id}\n'
            f'项目：{booking.project_name}\n'
            f'申请人：{booking.researcher.name}\n'
            f'笼位：{booking.cage.cage_code} ({booking.cage.room})\n'
            f'动物：{booking.cage.animal_type} × {booking.animal_count}\n'
            f'时段：{booking.start_time.strftime("%Y-%m-%d %H:%M")} 至 {booking.end_time.strftime("%Y-%m-%d %H:%M")}\n'
            f'实验目的：{booking.purpose}'
        )
        if booking.reject_reason:
            detail_text += f'\n\n⚠️ 上一步驳回原因：{booking.reject_reason}'
        
        self.booking_detail.setText(detail_text)
        self.approve_btn.setEnabled(True)
        self.reject_btn.setEnabled(True)

    def _on_approve(self):
        selected = self.pending_table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        approval, booking = self.pending_table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        dialog = ApprovalDialog(self, is_approve=True)
        if dialog.exec():
            success, message = ApprovalService.approve(
                booking.id, self.current_user.id, dialog.comments
            )
            if success:
                QMessageBox.information(self, '成功', message)
                self._load_pending_approvals()
                self._load_history_approvals()
            else:
                QMessageBox.critical(self, '失败', message)

    def _on_reject(self):
        selected = self.pending_table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        approval, booking = self.pending_table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        dialog = ApprovalDialog(self, is_approve=False)
        if dialog.exec():
            if not dialog.comments.strip():
                QMessageBox.warning(self, '提示', '驳回时必须填写原因')
                return
            
            success, message = ApprovalService.reject(
                booking.id, self.current_user.id, dialog.comments
            )
            if success:
                QMessageBox.information(self, '成功', message)
                self._load_pending_approvals()
                self._load_history_approvals()
            else:
                QMessageBox.critical(self, '失败', message)


class ApprovalDialog(QDialog):
    def __init__(self, parent=None, is_approve=True):
        super().__init__(parent)
        self.is_approve = is_approve
        self.comments = ''
        self.setWindowTitle('通过审批' if is_approve else '驳回申请')
        self.setFixedWidth(400)
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        hint_text = '请输入审批意见（可选）：' if self.is_approve else '请输入驳回原因（必填）：'
        hint = QLabel(hint_text)
        hint.setStyleSheet('font-weight: bold;')
        layout.addRow(hint)

        self.comments_edit = QTextEdit()
        self.comments_edit.setPlaceholderText('请输入意见...' if self.is_approve else '请详细说明驳回原因...')
        self.comments_edit.setFixedHeight(120)
        layout.addRow(self.comments_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText('确认通过' if self.is_approve else '确认驳回')
        if not self.is_approve:
            ok_btn.setStyleSheet('background: #f56c6c; color: white; padding: 8px 16px; border: none; border-radius: 4px;')
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_ok(self):
        self.comments = self.comments_edit.toPlainText().strip()
        self.accept()
