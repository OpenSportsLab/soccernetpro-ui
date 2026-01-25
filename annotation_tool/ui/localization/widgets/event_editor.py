from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget,
    QGridLayout, QLabel, QScrollArea, QMenu, QInputDialog, QMessageBox,
    QSizePolicy, QFrame, QTableView, QHeaderView, QDialog, QComboBox, 
    QDialogButtonBox, QFormLayout, QTimeEdit, QLineEdit
)
from PyQt6.QtCore import pyqtSignal, Qt, QPoint, QTime, QAbstractTableModel

# ==================== Table Model ====================
class AnnotationTableModel(QAbstractTableModel):
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
        """
        Parses a string like "MM:SS.mmm" or "SS.mmm" into milliseconds.
        """
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

# ==================== Widgets ====================

class LabelButton(QPushButton):
    """Custom Label Button"""
    rightClicked = pyqtSignal()
    doubleClicked = pyqtSignal()

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(40)
        self.setStyleSheet("""
            QPushButton {
                background-color: #444; 
                color: white; 
                border: 1px solid #555;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                text-align: center;
                padding: 4px;
            }
            QPushButton:hover { background-color: #555; border-color: #777; }
            QPushButton:pressed { background-color: #0078D7; border-color: #0078D7; }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.rightClicked.emit()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit()
        else:
            super().mouseDoubleClickEvent(event)

class HeadSpottingPage(QWidget):
    labelClicked = pyqtSignal(str)       
    addLabelRequested = pyqtSignal()     
    renameLabelRequested = pyqtSignal(str) 
    deleteLabelRequested = pyqtSignal(str) 

    def __init__(self, head_name, labels, parent=None):
        super().__init__(parent)
        self.head_name = head_name
        self.labels = labels
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        self.time_label = QLabel("Current Time: 00:00.000")
        self.time_label.setStyleSheet("color: #00BFFF; font-weight: bold; font-family: monospace; font-size: 14px;")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(8)
        self.grid_layout.setContentsMargins(0,0,0,0)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll.setWidget(self.grid_container)
        layout.addWidget(scroll)
        
        self._populate_grid()

    def update_time_display(self, text):
        self.time_label.setText(f"Current Time: {text}")

    def refresh_labels(self, new_labels):
        self.labels = new_labels
        self._populate_grid()

    def _populate_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cols = 2 
        row, col = 0, 0
        
        for lbl in self.labels:
            display_text = lbl.replace('_', ' ')
            btn = LabelButton(display_text)
            btn.clicked.connect(lambda _, l=lbl: self.labelClicked.emit(l))
            btn.rightClicked.connect(lambda l=lbl: self._show_context_menu(l))
            btn.doubleClicked.connect(lambda l=lbl: self.renameLabelRequested.emit(l))
            self.grid_layout.addWidget(btn, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1

        add_btn = QPushButton("Add new label at current time")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setMinimumHeight(45) 
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: 1px solid #005A9E;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #1084E3; border-color: #2094F3; }
            QPushButton:pressed { background-color: #005A9E; }
        """)
        add_btn.clicked.connect(self.addLabelRequested.emit)
        
        if col != 0: 
            row += 1
        self.grid_layout.addWidget(add_btn, row, 0, 1, 2) 

    def _show_context_menu(self, label):
        display_label = label.replace('_', ' ')
        menu = QMenu(self)
        rename_action = menu.addAction(f"Rename '{display_label}'")
        delete_action = menu.addAction(f"Delete '{display_label}'")
        
        action = menu.exec(self.cursor().pos())
        if action == rename_action:
            self.renameLabelRequested.emit(label)
        elif action == delete_action:
            self.deleteLabelRequested.emit(label)


class SpottingTabWidget(QTabWidget):
    headAdded = pyqtSignal(str)          
    headRenamed = pyqtSignal(str, str)   
    headDeleted = pyqtSignal(str)        
    headSelected = pyqtSignal(str)       
    spottingTriggered = pyqtSignal(str, str) 
    labelAddReq = pyqtSignal(str)            
    labelRenameReq = pyqtSignal(str, str)    
    labelDeleteReq = pyqtSignal(str, str)    

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabBarAutoHide(False)
        self.setMovable(False)
        self.setTabsClosable(False) 
        self.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #444; border-radius: 4px; background: #2E2E2E; }
            QTabBar::tab {
                background: #3A3A3A; color: #BBB; padding: 8px 12px;
                border-top-left-radius: 4px; border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected { background: #2E2E2E; color: white; font-weight: bold; border-bottom: 2px solid #00BFFF; }
            QTabBar::tab:hover { background: #444; color: white; }
        """)
        self.currentChanged.connect(self._on_tab_changed)
        self.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabBar().customContextMenuRequested.connect(self._show_tab_context_menu)
        self._ignore_change = False
        self._plus_tab_index = -1
        self._head_keys_map = []

    def update_schema(self, label_definitions):
        self._ignore_change = True
        self.clear()
        self._head_keys_map = []
        heads = sorted(label_definitions.keys())
        for head in heads:
            labels = label_definitions[head].get('labels', [])
            page = HeadSpottingPage(head, labels)
            page.labelClicked.connect(lambda l, h=head: self.spottingTriggered.emit(h, l))
            page.addLabelRequested.connect(lambda h=head: self.labelAddReq.emit(h))
            page.renameLabelRequested.connect(lambda l, h=head: self.labelRenameReq.emit(h, l))
            page.deleteLabelRequested.connect(lambda l, h=head: self.labelDeleteReq.emit(h, l))
            display_head = head.replace('_', ' ')
            self.addTab(page, display_head)
            self._head_keys_map.append(head) 
        self._plus_tab_index = self.addTab(QWidget(), "+")
        self._ignore_change = False

    def update_current_time(self, time_str):
        current_widget = self.currentWidget()
        if isinstance(current_widget, HeadSpottingPage):
            current_widget.update_time_display(time_str)

    def set_current_head(self, head_name):
        if head_name in self._head_keys_map:
            idx = self._head_keys_map.index(head_name)
            self.setCurrentIndex(idx)

    def _on_tab_changed(self, index):
        if self._ignore_change: return
        if index == self._plus_tab_index and index != -1:
            self.setCurrentIndex(max(0, index - 1))
            self._handle_add_head()
        else:
            if 0 <= index < len(self._head_keys_map):
                real_head = self._head_keys_map[index]
                self.headSelected.emit(real_head)

    def _handle_add_head(self):
        name, ok = QInputDialog.getText(self, "New Task Head", "Enter head name (e.g. 'player_action'):")
        if ok and name.strip():
            self.headAdded.emit(name.strip())

    def _show_tab_context_menu(self, pos):
        index = self.tabBar().tabAt(pos)
        if index == -1 or index == self._plus_tab_index: return
        if 0 <= index < len(self._head_keys_map):
            real_head_name = self._head_keys_map[index]
            display_head_name = self.tabText(index)
            menu = QMenu(self)
            rename_act = menu.addAction(f"Rename '{display_head_name}'")
            delete_act = menu.addAction(f"Delete '{display_head_name}'")
            action = menu.exec(self.mapToGlobal(pos))
            if action == rename_act:
                new_name, ok = QInputDialog.getText(self, "Rename Head", f"Rename '{real_head_name}' to:", text=real_head_name)
                if ok and new_name.strip() and new_name != real_head_name:
                    self.headRenamed.emit(real_head_name, new_name.strip())
            elif action == delete_act:
                self.headDeleted.emit(real_head_name)

class AnnotationManagementWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        title_label = QLabel("Create Annotation")
        title_label.setStyleSheet("font-weight: bold; color: #888; margin-bottom: 2px;")
        layout.addWidget(title_label)
        self.tabs = SpottingTabWidget()
        layout.addWidget(self.tabs)

    def update_schema(self, label_definitions):
        self.tabs.update_schema(label_definitions)

# ==================== Table Widget ====================

class AnnotationTableWidget(QWidget):
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
        # Connect the model's itemChanged signal to this widget's output signal
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
        
        # Redundant editing actions removed. 
        # Editing is now done directly in the table cells.
        
        act_delete = menu.addAction("Delete Event")
        
        selected_action = menu.exec(self.table.mapToGlobal(pos))
        
        if selected_action == act_delete:
            self.annotationDeleted.emit(item)