from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton
)
from PyQt6.QtCore import Qt

class WelcomeWidget(QWidget):
    """
    The Welcome Screen Widget.
    Provides entry points to Create or Import a project.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        
        # Title Label
        title = QLabel("SoccerNet Annotation Tool")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #00BFFF;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        # Create Project Button
        self.create_btn = QPushButton("Create New Project")
        self.create_btn.setFixedSize(200, 50)
        self.create_btn.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Import Project Button
        self.import_btn = QPushButton("Import Project JSON")
        self.import_btn.setFixedSize(200, 50)
        self.import_btn.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout.addWidget(self.create_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.import_btn, alignment=Qt.AlignmentFlag.AlignHCenter)