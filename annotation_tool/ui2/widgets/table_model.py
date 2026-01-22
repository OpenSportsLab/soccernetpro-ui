from PyQt6.QtCore import QAbstractTableModel, Qt

class AnnotationTableModel(QAbstractTableModel):
    def __init__(self, annotations=None):
        super().__init__()
        self._data = annotations or []
        # [修改] 移除了 "Del" 列，只保留数据列
        self._headers = ["Time", "Head", "Label"]

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        
        if role == Qt.ItemDataRole.DisplayRole:
            row = index.row()
            col = index.column()
            item = self._data[row]
            
            if col == 0:
                return self._fmt_ms(item.get('position_ms', 0))
            elif col == 1:
                # 显示时去下划线
                return item.get('head', '').replace('_', ' ')
            elif col == 2:
                # 显示时去下划线
                return item.get('label', '').replace('_', ' ')
                
        # [新增] 存储原始数据 UserRole，方便逻辑处理
        elif role == Qt.ItemDataRole.UserRole:
            return self._data[index.row()]
            
        return None

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
        # 格式化时间为 mm:ss.mmm
        s = ms // 1000
        m = s // 60
        return f"{m:02}:{s%60:02}.{ms%1000:03}"
