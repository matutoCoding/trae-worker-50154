from PyQt6.QtWidgets import (QMainWindow, QWidget, QTabWidget, QVBoxLayout, 
                             QLabel, QStatusBar, QHBoxLayout, QPushButton, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from models.user import User, UserRole
from services.user_service import UserService
from ui.login_dialog import LoginDialog
from ui.tabs.cage_tab import CageTab
from ui.tabs.booking_tab import BookingTab
from ui.tabs.approval_tab import ApprovalTab
from ui.tabs.access_tab import AccessTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_user: User = None
        self._show_login()

    def _show_login(self):
        login_dialog = LoginDialog(self)
        if login_dialog.exec():
            self.current_user = login_dialog.user
            self._init_ui()
        else:
            self.close()

    def _init_ui(self):
        self.setWindowTitle('实验动物房预约管理系统')
        self.resize(1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        header = self._create_header()
        main_layout.addWidget(header)

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet('''
            QTabWidget::pane {
                border: 1px solid #dcdfe6;
                background: white;
            }
            QTabBar::tab {
                background: #f5f7fa;
                padding: 12px 24px;
                margin-right: 2px;
                border: 1px solid #dcdfe6;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 14px;
            }
            QTabBar::tab:selected {
                background: white;
                color: #409eff;
                border-bottom: 2px solid #409eff;
            }
        ''')

        self.cage_tab = CageTab(self.current_user)
        self.booking_tab = BookingTab(self.current_user)
        self.approval_tab = ApprovalTab(self.current_user)
        self.access_tab = AccessTab(self.current_user)

        self.tab_widget.addTab(self.cage_tab, '🏠 笼位排期')
        self.tab_widget.addTab(self.booking_tab, '📋 我的预约')
        self.tab_widget.addTab(self.approval_tab, '✅ 审批管理')
        self.tab_widget.addTab(self.access_tab, '🔐 准入登记')

        main_layout.addWidget(self.tab_widget)

        status_bar = QStatusBar()
        status_bar.showMessage(f'欢迎 {self.current_user.name} | 角色：{UserService.get_role_name(self.current_user.role)}')
        self.setStatusBar(status_bar)

        self._create_menu()

    def _create_header(self):
        header = QWidget()
        header.setFixedHeight(60)
        header.setStyleSheet('background: linear-gradient(90deg, #2c3e50, #34495e);')
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel('🐭 实验动物房预约管理系统')
        title.setStyleSheet('font-size: 18px; font-weight: bold; color: white;')
        header_layout.addWidget(title)

        header_layout.addStretch()

        user_info = QLabel(f'👤 {self.current_user.name} ({UserService.get_role_name(self.current_user.role)})')
        user_info.setStyleSheet('color: #ecf0f1; font-size: 14px;')
        header_layout.addWidget(user_info)

        logout_btn = QPushButton('退出登录')
        logout_btn.setStyleSheet('''
            QPushButton {
                background: transparent;
                color: #ecf0f1;
                border: 1px solid #ecf0f1;
                padding: 6px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.1);
            }
        ''')
        logout_btn.clicked.connect(self._logout)
        header_layout.addWidget(logout_btn)

        return header

    def _create_menu(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu('文件')
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu('帮助')
        about_action = QAction('关于', self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _logout(self):
        reply = QMessageBox.question(self, '确认', '确定要退出登录吗？',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.current_user = None
            self._show_login()

    def _show_about(self):
        QMessageBox.about(self, '关于', 
            '<h3>实验动物房预约管理系统</h3>'
            '<p>版本 1.0.0</p>'
            '<p>功能模块：笼位排期、冲突校验、多级审批、准入登记</p>'
            '<p>© 2026 科研机构动物实验中心</p>')
