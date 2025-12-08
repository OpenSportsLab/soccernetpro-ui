import sys
from PyQt6.QtWidgets import QApplication
from viewer import ActionClassifierApp

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ActionClassifierApp()
    window.show()
    sys.exit(app.exec())