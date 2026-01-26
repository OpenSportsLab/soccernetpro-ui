import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QComboBox, QPushButton, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal

# Import the shared controls
from ui.common.project_controls import UnifiedProjectControls

class CommonProjectTreePanel(QWidget):
    """
    A unified Left Panel for both Classification and Localization.
    Contains:
    1. UnifiedProjectControls (New, Load, Save...)
    2. A Title Label
    3. A QTreeWidget (The list)
    4. A Filter and Clear button row at the bottom
    """
    
    # Signal emitted when "Remove Item" is clicked in context menu
    request_remove_item = pyqtSignal(QTreeWidgetItem)

    def __init__(self, 
                 tree_title="Project Items", 
                 filter_items=None, 
                 clear_text="Clear All", 
                 enable_context_menu=True,
                 parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)
        
        # Main Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 1. Project Controls
        self.project_controls = UnifiedProjectControls()
        
        # Expose control buttons for external controller connections
        self.import_btn = self.project_controls.btn_load
        self.create_btn = self.project_controls.btn_create
        self.add_data_btn = self.project_controls.btn_add
        
        layout.addWidget(self.project_controls)
        
        # 2. Tree Title
        self.lbl_title = QLabel(tree_title)
        self.lbl_title.setStyleSheet("font-weight: bold; color: #888; margin-top: 10px;")
        layout.addWidget(self.lbl_title)
        
        # 3. The Tree Widget
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        layout.addWidget(self.tree)
        
        # Context Menu Logic
        if enable_context_menu:
            self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.tree.customContextMenuRequested.connect(self._show_context_menu)

        # 4. Filter & Clear Row
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 5, 0, 0)
        
        self.lbl_filter = QLabel("Filter:")
        self.filter_combo = QComboBox()
        if filter_items:
            self.filter_combo.addItems(filter_items)
            
        self.clear_btn = QPushButton(clear_text)
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setStyleSheet("padding: 4px 8px;")
        
        bottom_layout.addWidget(self.lbl_filter)
        bottom_layout.addWidget(self.filter_combo, 1) # Stretch
        bottom_layout.addWidget(self.clear_btn)
        
        layout.addLayout(bottom_layout)
        

    def add_tree_item(self, name, path, source_files=None, icon=None):
        """
        Helper to add a standard item to the tree.
        """
        item = QTreeWidgetItem(self.tree, [name])
        item.setData(0, Qt.ItemDataRole.UserRole, path)
        
        if icon:
            item.setIcon(0, icon)
        
        # Handle child items (e.g. multi-view inputs)
        if source_files and len(source_files) > 1:
            for src in source_files:
                child = QTreeWidgetItem(item, [os.path.basename(src)])
                child.setData(0, Qt.ItemDataRole.UserRole, src)
                
        return item

    def _show_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if item:
            menu = QMenu()
            remove_action = menu.addAction("Remove Item")
            action = menu.exec(self.tree.mapToGlobal(pos))
            if action == remove_action:
                self.request_remove_item.emit(item)