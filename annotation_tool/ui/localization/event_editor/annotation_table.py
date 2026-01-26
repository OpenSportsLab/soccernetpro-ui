from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableView, QHeaderView, QMenu,
    QAbstractItemView
)
from PyQt6.QtCore import pyqtSignal, Qt, QAbstractTableModel

# ==================== Table Model ====================
class AnnotationTableModel(QAbstractTableModel):
    """
    Data model for the events table.
    """
    # Signal emitted when a cell is edited: old_data, new_data
    itemChanged = pyqtSignal(dict, dict)

    def __init__(self, annotations=None):
        super().__init__()
        self._data = annotations or []
        self._headers = ["Time", "Head", "Label"]

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        # Enable selection and editing
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        
        row = index.row()
        item = self._data[row]

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            col = index.column()
            if col == 0:
                return self._fmt_ms(item.get('position_ms', 0))
            elif col == 1:
                return item.get('head', '').replace('_', ' ')
            elif col == 2:
                return item.get('label', '').replace('_', ' ')
        
        elif role == Qt.ItemDataRole.UserRole:
            return item
            
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        """
        Handle user edits directly from the table cells.
        """
        if not index.isValid() or role != Qt.ItemDataRole.EditRole:
            return False

        row = index.row()
        col = index.column()
        
        # Get the original object
        old_item = self._data[row]
        # Create a shallow copy to modify
        new_item = old_item.copy()

        text_val = str(value).strip()

        if col == 0:  # Time Column
            try:
                ms = self._parse_time_str(text_val)
                new_item['position_ms'] = ms
            except ValueError:
                # Invalid time format, reject the edit
                return False
        elif col == 1:  # Head Column
            new_item['head'] = text_val
        elif col == 2:  # Label Column
            new_item['label'] = text_val

        # If data changed, emit signal for the Manager to handle (Undo Stack)
        if new_item != old_item:
            self.itemChanged.emit(old_item, new_item)
            return True
            
        return False

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._headers[section]
        return None

    def set_annotations(self, annotations):
        self.beginResetModel()
        self._data = annotations
        self.endResetModel()

    def get_annotation_at(self, row):
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

    def _fmt_ms(self, ms):
        s = ms // 1000
        m = s // 60
        return f"{m:02}:{s%60:02}.{ms%1000:03}"

    def _parse_time_str(self, time_str):
        if not time_str:
            return 0
        parts = time_str.split(':')
        total_seconds = 0.0
        if len(parts) == 3: # HH:MM:SS.mmm
            total_seconds += float(parts[0]) * 3600
            total_seconds += float(parts[1]) * 60
            total_seconds += float(parts[2])
        elif len(parts) == 2: # MM:SS.mmm
            total_seconds += float(parts[0]) * 60
            total_seconds += float(parts[1])
        elif len(parts) == 1: # SS.mmm
            total_seconds += float(parts[0])
        return int(total_seconds * 1000)


# ==================== Table Widget ====================
class AnnotationTableWidget(QWidget):
    """
    Widget containing the list of events (QTableView).
    """
    annotationSelected = pyqtSignal(int) 
    annotationModified = pyqtSignal(dict, dict) # old_event, new_event
    annotationDeleted = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        lbl = QLabel("Events List")
        lbl.setStyleSheet("font-weight: bold; color: #888; margin-top: 10px;")
        layout.addWidget(lbl)
        
        self.table = QTableView()
        self.table.setStyleSheet("""
            QTableView {
                background-color: #2E2E2E;
                gridline-color: #555;
                color: #DDD;
                selection-background-color: #0078D7;
                selection-color: white;
                alternate-background-color: #3A3A3A;
            }
            QHeaderView::section {
                background-color: #444; color: white; border: 1px solid #555; padding: 4px;
            }
        """)
        
        self.model = AnnotationTableModel()
        self.model.itemChanged.connect(self.annotationModified.emit)
        
        self.table.setModel(self.model)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        layout.addWidget(self.table)
        
        self.current_schema = {} 

    def set_data(self, annotations):
        self.model.set_annotations(annotations)

    def set_schema(self, schema):
        self.current_schema = schema

    def _on_selection_changed(self, selected, deselected):
        indexes = selected.indexes()
        if indexes:
            row = indexes[0].row()
            item = self.model.get_annotation_at(row)
            if item:
                self.annotationSelected.emit(item.get('position_ms', 0))

    def _show_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid(): return
        
        row = index.row()
        item = self.model.get_annotation_at(row)
        if not item: return
        
        menu = QMenu(self)
        act_delete = menu.addAction("Delete Event")
        selected_action = menu.exec(self.table.mapToGlobal(pos))
        
        if selected_action == act_delete:
            self.annotationDeleted.emit(item)