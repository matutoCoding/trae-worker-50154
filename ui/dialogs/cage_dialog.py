from PyQt6.QtWidgets import (QDialog, QFormLayout, QLineEdit, QSpinBox, QComboBox, 
                             QTextEdit, QPushButton, QHBoxLayout, QMessageBox, QDialogButtonBox)
from PyQt6.QtCore import Qt
from services.cage_service import CageService
from models.cage import CageStatus

class CageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('新增笼位')
        self.setFixedWidth(400)
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        self.cage_code_edit = QLineEdit()
        self.cage_code_edit.setPlaceholderText('如：A-001')
        layout.addRow('笼位编号：', self.cage_code_edit)

        self.room_edit = QLineEdit()
        self.room_edit.setPlaceholderText('如：A区1室')
        layout.addRow('所在房间：', self.room_edit)

        self.capacity_spin = QSpinBox()
        self.capacity_spin.setRange(1, 100)
        self.capacity_spin.setValue(5)
        layout.addRow('容纳数量：', self.capacity_spin)

        self.animal_type_edit = QLineEdit()
        self.animal_type_edit.setPlaceholderText('如：小鼠、大鼠、豚鼠')
        layout.addRow('动物类型：', self.animal_type_edit)

        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText('备注信息（可选）')
        self.description_edit.setFixedHeight(80)
        layout.addRow('备注：', self.description_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _on_ok(self):
        cage_code = self.cage_code_edit.text().strip()
        room = self.room_edit.text().strip()
        capacity = self.capacity_spin.value()
        animal_type = self.animal_type_edit.text().strip()
        description = self.description_edit.toPlainText().strip()

        if not all([cage_code, room, animal_type]):
            QMessageBox.warning(self, '提示', '请填写完整信息')
            return

        success, message, _ = CageService.create_cage(
            cage_code, room, capacity, animal_type, description
        )
        if success:
            QMessageBox.information(self, '成功', message)
            self.accept()
        else:
            QMessageBox.critical(self, '失败', message)
