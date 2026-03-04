from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
)
from PyQt6.QtCore import Qt

# Import the separated components from the same package
from .spotting_controls import AnnotationManagementWidget
from .annotation_table import AnnotationTableWidget

# --- [Assembled] Localization Right Panel ---
class LocRightPanel(QWidget):
    """
    Right Panel for Localization Mode.
    Contains: Undo/Redo Buttons, Annotation Tabs (Top), and Events Table (Bottom).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(400)
        layout = QVBoxLayout(self)
        
        # --- Undo/Redo Button Header ---
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 5)
        
        lbl = QLabel("Annotation Controls")
        lbl.setStyleSheet("font-weight: bold; color: #BBB; font-size: 13px;")
        
        self.undo_btn = QPushButton("Undo")
        self.redo_btn = QPushButton("Redo")
        
        # Button Styling
        btn_style = """
            QPushButton {
                background-color: #444; color: #DDD; 
                border: 1px solid #555; border-radius: 4px; padding: 4px 10px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #555; border-color: #777; }
            QPushButton:pressed { background-color: #333; }
            QPushButton:disabled { color: #777; background-color: #333; border-color: #444; }
        """
        for btn in [self.undo_btn, self.redo_btn]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(btn_style)
            btn.setFixedWidth(60)
            btn.setEnabled(False) 
            
        header_layout.addWidget(lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.undo_btn)
        header_layout.addWidget(self.redo_btn)
        
        layout.addLayout(header_layout)
        # -----------------------------------
        
        # 1. Top: Multi Head Management (Tabs)
        self.annot_mgmt = AnnotationManagementWidget()
        
        # 2. Bottom: Labelled Event List (Table)
        self.table = AnnotationTableWidget()
        
        layout.addWidget(self.annot_mgmt, 3) 
        layout.addWidget(self.table, 2)