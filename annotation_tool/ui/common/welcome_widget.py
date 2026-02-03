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
        title.setObjectName("welcome_title_lbl")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        # Create Project Button
        self.create_btn = QPushButton("Create New Project")
        self.create_btn.setFixedSize(200, 50)
        self.create_btn.setProperty("class", "welcome_action_btn")
        self.create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Import Project Button
        self.import_btn = QPushButton("Import Project JSON")
        self.import_btn.setFixedSize(200, 50)
        self.import_btn.setProperty("class", "welcome_action_btn")
        self.import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout.addWidget(self.create_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.import_btn, alignment=Qt.AlignmentFlag.AlignHCenter)