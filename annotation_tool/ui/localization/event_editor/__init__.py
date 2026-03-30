# __init__.py (in ui/localization/)

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal

from .spotting_controls import AnnotationManagementWidget
from .annotation_table import AnnotationTableWidget
from .smart_spotting import SmartSpottingWidget

class LocRightPanel(QWidget):
    """
    Right Panel for Localization Mode.
    Contains: Undo/Redo Buttons (Global), and a TabWidget separating 
    Hand Annotation and Smart Annotation interfaces.
    """
    # Signal emitted when the user switches between Hand and Smart tabs
    # The Controller should catch this to swap the Timeline markers
    tabSwitched = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(400)
        layout = QVBoxLayout(self)
        
        # --- 1. Global Undo/Redo Button Header ---
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 5)
        
        lbl = QLabel("Annotation Controls")
        lbl.setStyleSheet("font-weight: bold; color: #BBB; font-size: 13px;")
        
        self.undo_btn = QPushButton("Undo")
        self.redo_btn = QPushButton("Redo")
        
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
        
        # --- 2. Main Tabs ---
        self.tabs = QTabWidget()
        self.tabs.setObjectName("localization_tabs")
        layout.addWidget(self.tabs)

        # ========== TAB 0: Hand Annotation ==========
        self.hand_widget = QWidget()
        hand_layout = QVBoxLayout(self.hand_widget)
        hand_layout.setContentsMargins(0, 5, 0, 0)
        
        # Top: Multi Head Management (Tabs for categories)
        self.annot_mgmt = AnnotationManagementWidget()
        # Bottom: Labelled Event List (Table for hand annotations)
        self.table = AnnotationTableWidget()
        
        hand_layout.addWidget(self.annot_mgmt, 2) 
        hand_layout.addWidget(self.table, 3)
        
        self.tabs.addTab(self.hand_widget, "Hand Annotation")

        # ========== TAB 1: Smart Annotation ==========
        # Loads the newly created SmartSpottingWidget
        self.smart_widget = SmartSpottingWidget()
        self.tabs.addTab(self.smart_widget, "Smart Annotation")

        # Connect tab change signal
        self.tabs.currentChanged.connect(self.tabSwitched.emit)