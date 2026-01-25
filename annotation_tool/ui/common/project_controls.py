from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QPushButton, QGridLayout
from PyQt6.QtCore import pyqtSignal, Qt

class UnifiedProjectControls(QWidget):
    """
    A standardized 3x2 grid control panel for project management.
    Used by both Classification and Localization tasks to ensure UI consistency.
    
    Layout:
    [ Create ] [  Load  ]
    [  Add   ] [  Close ]
    [  Save  ] [ Export ]
    """
    # Define signals for all 6 actions
    createRequested = pyqtSignal()
    loadRequested = pyqtSignal()
    addVideoRequested = pyqtSignal()
    closeRequested = pyqtSignal()
    saveRequested = pyqtSignal()
    exportRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        group = QGroupBox("Project Controls")
        
        # Use GridLayout for 3x2 arrangement
        grid_layout = QGridLayout(group)
        grid_layout.setSpacing(10)
        grid_layout.setContentsMargins(10, 20, 10, 10)
        
        # --- Row 1: Lifecycle ---
        self.btn_create = QPushButton("New Project")
        self.btn_load = QPushButton("Load Project")
        
        # --- Row 2: Content / Nav ---
        self.btn_add = QPushButton("Add Data")
        self.btn_close = QPushButton("Close Project")
        
        # --- Row 3: Persistence ---
        self.btn_save = QPushButton("Save JSON")
        self.btn_export = QPushButton("Export JSON")
        
        # Initial state: Save/Export disabled until project loaded
        self.btn_save.setEnabled(False)
        self.btn_export.setEnabled(False)
        
        # Apply Styling
        btns = [
            self.btn_create, self.btn_load,
            self.btn_add, self.btn_close,
            self.btn_save, self.btn_export
        ]
        
        for btn in btns:
            btn.setMinimumHeight(35)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    border-radius: 6px;
                    padding: 5px;
                    background-color: #444;
                    color: #EEE;
                    border: 1px solid #555;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #555; border-color: #777; }
                QPushButton:pressed { background-color: #0078D7; border-color: #0078D7; }
                QPushButton:disabled { background-color: #333; color: #777; border-color: #333; }
            """)
        
        # Add to Grid (Widget, Row, Column)
        grid_layout.addWidget(self.btn_create, 0, 0)
        grid_layout.addWidget(self.btn_load, 0, 1)
        
        grid_layout.addWidget(self.btn_add, 1, 0)
        grid_layout.addWidget(self.btn_close, 1, 1)
        
        grid_layout.addWidget(self.btn_save, 2, 0)
        grid_layout.addWidget(self.btn_export, 2, 1)
        
        layout.addWidget(group)
        
        # Connect internal clicks to external signals
        self.btn_create.clicked.connect(self.createRequested.emit)
        self.btn_load.clicked.connect(self.loadRequested.emit)
        self.btn_add.clicked.connect(self.addVideoRequested.emit)
        self.btn_close.clicked.connect(self.closeRequested.emit)
        self.btn_save.clicked.connect(self.saveRequested.emit)
        self.btn_export.clicked.connect(self.exportRequested.emit)

    def set_project_loaded_state(self, loaded: bool):
        """
        Updates button states based on whether a project is currently active.
        """
        self.btn_save.setEnabled(loaded)
        self.btn_export.setEnabled(loaded)
        # Create/Load/Close are always enabled to allow switching or exiting