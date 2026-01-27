from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt

class ProjectTreeModel(QStandardItemModel):
    """
    A standalone Model component compliant with Qt's Model/View architecture.
    It manages the hierarchical data for clips and sequences.
    """
    
    # Define custom role for storing file paths
    FilePathRole = Qt.ItemDataRole.UserRole
 
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(1)
    
    def add_entry(self, name: str, path: str, source_files: list = None, icon=None) -> QStandardItem:
        """
        Creates and appends a new row to the model.
        Returns the created QStandardItem for external reference.
        """
        item = QStandardItem(name)
        item.setEditable(False)
        item.setData(path, self.FilePathRole)
        
        if icon:
            item.setIcon(icon)
        
        # Handle child items (e.g., multi-view inputs)
        if source_files and len(source_files) > 1:
            for src in source_files:
                import os
                child_name = os.path.basename(src)
                child = QStandardItem(child_name)
                child.setEditable(False)
                child.setData(src, self.FilePathRole)
                item.appendRow(child)
        
        self.appendRow(item)
        return item
