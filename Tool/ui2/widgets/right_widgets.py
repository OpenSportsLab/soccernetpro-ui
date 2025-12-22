from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget,
    QGridLayout, QLabel, QScrollArea, QMenu, QInputDialog, QMessageBox,
    QSizePolicy, QFrame, QTableView, QHeaderView, QDialog, QComboBox, 
    QDialogButtonBox, QFormLayout, QTimeEdit, QLineEdit
)
from PyQt6.QtCore import pyqtSignal, Qt, QPoint, QTime, QAbstractTableModel

# ==================== Table Model (嵌入以确保完整性) ====================
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
        
        row = index.row()
        item = self._data[row]

        if role == Qt.ItemDataRole.DisplayRole:
            col = index.column()
            if col == 0:
                return self._fmt_ms(item.get('position_ms', 0))
            elif col == 1:
                # 显示时去下划线
                return item.get('head', '').replace('_', ' ')
            elif col == 2:
                # 显示时去下划线
                return item.get('label', '').replace('_', ' ')
        
        # [新增] 存储原始数据 UserRole，方便逻辑获取
        elif role == Qt.ItemDataRole.UserRole:
            return item
            
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
        s = ms // 1000
        m = s // 60
        return f"{m:02}:{s%60:02}.{ms%1000:03}"

# ==================== Widgets ====================

class LabelButton(QPushButton):
    """自定义标签按钮"""
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

# ==================== [New] Edit Dialog & Table Widget ====================

class EditEventDialog(QDialog):
    """
    通用编辑对话框：
    - 支持下拉选择现有的 (Head/Label)
    - 包含 <Create New> 选项，选择后显示输入框添加新值
    """
    def __init__(self, current_value, existing_options, item_type="Head", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit {item_type}")
        self.resize(300, 150)
        self.is_new = False
        
        layout = QVBoxLayout(self)
        
        # 1. ComboBox
        layout.addWidget(QLabel(f"Select {item_type}:"))
        self.combo = QComboBox()
        
        # 映射 Display (无下划线) -> Real Key (有下划线)
        self.options_map = {} 
        
        sorted_options = sorted(existing_options)
        current_display = current_value.replace('_', ' ')
        
        for key in sorted_options:
            display = key.replace('_', ' ')
            self.options_map[display] = key
            self.combo.addItem(display)
            
        self.combo.addItem("-- Create New --")
        
        # 选中当前值
        idx = self.combo.findText(current_display)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)
        else:
            # 如果当前值不在列表中（比如是 "???" 占位符），不选中任何现有项，或者保持默认
            pass
            
        layout.addWidget(self.combo)
        
        # 2. Input Field (默认隐藏)
        self.new_input_container = QWidget()
        h_layout = QHBoxLayout(self.new_input_container)
        h_layout.setContentsMargins(0, 5, 0, 5)
        h_layout.addWidget(QLabel(f"New {item_type}:"))
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(f"Enter new {item_type} name")
        h_layout.addWidget(self.line_edit)
        
        self.new_input_container.setVisible(False)
        layout.addWidget(self.new_input_container)
        
        # 逻辑连接
        self.combo.currentIndexChanged.connect(self._on_combo_change)
        
        # 按钮
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
    def _on_combo_change(self):
        txt = self.combo.currentText()
        if txt == "-- Create New --":
            self.new_input_container.setVisible(True)
            self.line_edit.setFocus()
            self.is_new = True
        else:
            self.new_input_container.setVisible(False)
            self.is_new = False
            
    def get_value(self):
        """返回 (value, is_created_new)"""
        if self.is_new:
            val = self.line_edit.text().strip()
            return val
        else:
            display = self.combo.currentText()
            return self.options_map.get(display, display)


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
        self.table.setModel(self.model)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        
        # [修改] 启用右键菜单
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
        # [核心修改] 根据点击的列展示不同的菜单
        index = self.table.indexAt(pos)
        if not index.isValid(): return
        
        col = index.column() # 0:Time, 1:Head, 2:Label
        row = index.row()
        item = self.model.get_annotation_at(row)
        if not item: return
        
        menu = QMenu(self)
        
        action_map = {}
        
        if col == 0:
            act = menu.addAction("Edit Time")
            action_map[act] = "edit_time"
        elif col == 1:
            act = menu.addAction("Edit Head")
            action_map[act] = "edit_head"
        elif col == 2:
            act = menu.addAction("Edit Label")
            action_map[act] = "edit_label"
            
        menu.addSeparator()
        act_delete = menu.addAction("Delete Event")
        action_map[act_delete] = "delete"
        
        selected_action = menu.exec(self.table.mapToGlobal(pos))
        
        if selected_action:
            mode = action_map.get(selected_action)
            if mode == "delete":
                self.annotationDeleted.emit(item)
            elif mode == "edit_time":
                self._edit_time(item)
            elif mode == "edit_head":
                self._edit_head(item)
            elif mode == "edit_label":
                self._edit_label(item)

    def _edit_time(self, item):
        ms = item.get('position_ms', 0)
        total_seconds = ms // 1000
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        ms_part = ms % 1000
        cur_time = QTime(h, m, s, ms_part)
        
        dlg = QDialog(self)
        dlg.setWindowTitle("Edit Time")
        l = QVBoxLayout(dlg)
        
        te = QTimeEdit()
        te.setDisplayFormat("HH:mm:ss.zzz")
        te.setTime(cur_time)
        l.addWidget(QLabel("New Time:"))
        l.addWidget(te)
        
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        l.addWidget(bb)
        
        if dlg.exec():
            t = te.time()
            new_ms = (t.hour()*3600 + t.minute()*60 + t.second())*1000 + t.msec()
            
            new_item = item.copy()
            new_item['position_ms'] = new_ms
            self.annotationModified.emit(item, new_item)

    def _edit_head(self, item):
        heads = list(self.current_schema.keys())
        dlg = EditEventDialog(item.get('head', ''), heads, "Head", self)
        
        if dlg.exec():
            new_head = dlg.get_value()
            if not new_head: return
            
            new_item = item.copy()
            new_item['head'] = new_head
            # 这里不处理 Label 置空，交给 Manager 处理
            self.annotationModified.emit(item, new_item)

    def _edit_label(self, item):
        head = item.get('head', '')
        labels = []
        if head in self.current_schema:
            labels = self.current_schema[head].get('labels', [])
            
        dlg = EditEventDialog(item.get('label', ''), labels, "Label", self)
        
        if dlg.exec():
            new_label = dlg.get_value()
            # 允许输入空字符串，如果用户想置空
            new_item = item.copy()
            new_item['label'] = new_label
            self.annotationModified.emit(item, new_item)
