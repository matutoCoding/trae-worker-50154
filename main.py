import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from db.database import init_db, create_sample_data

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    init_db()
    create_sample_data()
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
