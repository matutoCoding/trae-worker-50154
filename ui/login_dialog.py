from PyQt6.QtWidgets import (QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout, 
                             QHBoxLayout, QMessageBox, QComboBox)
from PyQt6.QtCore import Qt
from services.user_service import UserService
from models.user import UserRole

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('实验动物房预约系统 - 登录')
        self.setFixedSize(400, 300)
        self.user = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel('实验动物房预约管理系统')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet('font-size: 20px; font-weight: bold; color: #2c3e50;')
        layout.addWidget(title)

        subtitle = QLabel('请登录以继续')
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet('font-size: 12px; color: #7f8c8d;')
        layout.addWidget(subtitle)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(10)

        username_label = QLabel('用户名：')
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText('请输入用户名')
        self.username_edit.setText('student1')
        form_layout.addWidget(username_label)
        form_layout.addWidget(self.username_edit)

        password_label = QLabel('密码：')
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText('请输入密码')
        self.password_edit.setText('123456')
        form_layout.addWidget(password_label)
        form_layout.addWidget(self.password_edit)

        test_label = QLabel('测试账号：student1 / advisor1 / manager1 / ethics1，密码均为 123456')
        test_label.setStyleSheet('font-size: 10px; color: #95a5a6;')
        test_label.setWordWrap(True)
        form_layout.addWidget(test_label)

        layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.login_btn = QPushButton('登录')
        self.login_btn.setStyleSheet('''
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        ''')
        self.login_btn.clicked.connect(self._on_login)
        button_layout.addWidget(self.login_btn)

        self.cancel_btn = QPushButton('取消')
        self.cancel_btn.setStyleSheet('''
            QPushButton {
                background-color: #ecf0f1;
                color: #2c3e50;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #bdc3c7;
            }
        ''')
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _on_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()

        if not username or not password:
            QMessageBox.warning(self, '提示', '请输入用户名和密码')
            return

        success, user, message = UserService.authenticate(username, password)
        if success:
            self.user = user
            self.accept()
        else:
            QMessageBox.critical(self, '登录失败', message)
