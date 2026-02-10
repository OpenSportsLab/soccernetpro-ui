from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QAbstractItemView
from PyQt6.QtCore import Qt
from .desc_input_widget import DenseDescriptionInputWidget
from .dense_table import DenseTableModel, AnnotationTableWidget

class DenseRightPanel(QWidget):
    """
    Right Panel for Dense Description Mode.
    Contains Undo/Redo, Input Field, and Description Table.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(400)
        layout = QVBoxLayout(self)

        # 1. Header with Undo/Redo (Reusing Localization Style)
        header_layout = QHBoxLayout()
        self.undo_btn = QPushButton("Undo")
        self.redo_btn = QPushButton("Redo")
        
        # Style header...
        header_layout.addWidget(QLabel("<b>Dense Annotation</b>"))
        header_layout.addStretch()
        header_layout.addWidget(self.undo_btn)
        header_layout.addWidget(self.redo_btn)
        layout.addLayout(header_layout)

        # 2. Top: Input Widget
        self.input_widget = DenseDescriptionInputWidget()
        layout.addWidget(self.input_widget, 1)

        # 3. Bottom: Table Widget
        self.table = AnnotationTableWidget()
        
        # [CRITICAL FIX] Swap Model and Reconnect Signals
        # ---------------------------------------------------------
        # 1. Create and Set the specific Dense Model
        self.dense_model = DenseTableModel()
        self.table.model = self.dense_model          # Update python reference
        self.table.table.setModel(self.dense_model)  # Update QTableView
        
        # 2. Reconnect Editing Signal (Fix: "Cannot modify")
        self.dense_model.itemChanged.connect(self.table.annotationModified.emit)
        
        # 3. Reconnect Selection Signal (Fix: "Timeline does not jump")
        # extending the widget's behavior externally.
        selection_model = self.table.table.selectionModel()
        selection_model.selectionChanged.connect(self.table._on_selection_changed)
        
        # 4. Enforce Edit Triggers
        # Ensure double-click or typing explicitly triggers the editor.
        self.table.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked | 
            QAbstractItemView.EditTrigger.EditKeyPressed |
            QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        # ---------------------------------------------------------
        
        layout.addWidget(self.table, 2)