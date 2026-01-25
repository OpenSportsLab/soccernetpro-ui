from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QPushButton, 
    QTreeWidget, QTreeWidgetItem, QComboBox, QHBoxLayout, 
    QLabel, QGridLayout, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt

# Import the unified widget
from ui.common.project_controls import UnifiedProjectControls

# We reuse the UnifiedProjectControls but keep the name ProjectControlsWidget 
# to avoid breaking imports in ui2/panels.py, 
# OR we simply subclass it to allow for specific extensions if needed later.
class ProjectControlsWidget(UnifiedProjectControls):
    """
    Inherits from the standard UnifiedProjectControls.
    This ensures Localization uses the exact same 3x2 grid as Classification.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        # The signals (loadRequested, addVideoRequested, etc.) are inherited.
        # The 3x2 Layout is inherited.
        
# --- Legacy ActionListWidget (kept for file integrity, though mostly unused in UI2) ---
class ActionListWidget(QWidget):
    labelSelected = pyqtSignal(str, str) 
    listCleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        group = QGroupBox("Action List")
        v_layout = QVBoxLayout(group)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemClicked.connect(self._on_item_clicked)
        v_layout.addWidget(self.tree)
        
        h_layout = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All")
        self.filter_combo.currentTextChanged.connect(self._apply_filter)
        
        self.btn_clear = QPushButton("Clear Selection")
        self.btn_clear.clicked.connect(self._on_clear_clicked)
        
        h_layout.addWidget(self.filter_combo)
        h_layout.addWidget(self.btn_clear)
        v_layout.addLayout(h_layout)
        
        layout.addWidget(group)

    def set_labels(self, labels: dict):
        self.tree.clear()
        self.filter_combo.blockSignals(True)
        self.filter_combo.clear()
        self.filter_combo.addItem("All")
        
        for head, defn in labels.items():
            self.filter_combo.addItem(head)
            head_item = QTreeWidgetItem(self.tree, [head])
            head_item.setFlags(head_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            head_item.setExpanded(True)
            font = head_item.font(0)
            font.setBold(True)
            head_item.setFont(0, font)
            
            items_list = defn.get('labels', [])
            for lbl in items_list:
                item = QTreeWidgetItem(head_item, [lbl])
                item.setData(0, Qt.ItemDataRole.UserRole, head)
                
        self.filter_combo.blockSignals(False)

    def _on_item_clicked(self, item, col):
        head = item.data(0, Qt.ItemDataRole.UserRole)
        if head:
            label = item.text(0)
            self.labelSelected.emit(head, label)

    def _apply_filter(self, text):
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            head_item = root.child(i)
            head_name = head_item.text(0)
            hidden = (text != "All" and text != head_name)
            head_item.setHidden(hidden)

    def _on_clear_clicked(self):
        self.tree.clearSelection()
        self.listCleared.emit()