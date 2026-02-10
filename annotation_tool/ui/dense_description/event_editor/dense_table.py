from ui.localization.event_editor.annotation_table import AnnotationTableModel, AnnotationTableWidget
from PyQt6.QtCore import Qt

class DenseTableModel(AnnotationTableModel):
    """
    Modified Model for Dense Description.
    Columns: [Time, Lang, Text]
    """
    def __init__(self, annotations=None):
        super().__init__(annotations)
        self._headers = ["Time", "Lang", "Description"]

    def flags(self, index):
        """
        [FIX] Explicitly ensure items are editable.
        """
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        
        # Allow selection and editing for all valid cells
        return (Qt.ItemFlag.ItemIsEnabled | 
                Qt.ItemFlag.ItemIsSelectable | 
                Qt.ItemFlag.ItemIsEditable)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid(): return None
        row = index.row()
        item = self._data[row]
        col = index.column()

        if role in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            if col == 0:
                return self._fmt_ms(item.get('position_ms', 0))
            elif col == 1:
                return item.get('lang', 'en')
            elif col == 2:
                return item.get('text', '')
        return super().data(index, role)

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid() or role != Qt.ItemDataRole.EditRole: return False
        
        row, col = index.row(), index.column()
        old_item = self._data[row]
        new_item = old_item.copy()
        val_str = str(value).strip()

        # Handle columns
        if col == 0:
            try: new_item['position_ms'] = self._parse_time_str(val_str)
            except ValueError: return False
        elif col == 1: new_item['lang'] = val_str
        elif col == 2: new_item['text'] = val_str

        # Only emit change if actual data differs
        if new_item != old_item:
            self._data[row] = new_item # Update internal data immediately for consistency
            self.itemChanged.emit(old_item, new_item)
            return True
        return False