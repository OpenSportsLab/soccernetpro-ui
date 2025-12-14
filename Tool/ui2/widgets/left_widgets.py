from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QPushButton, 
    QTreeWidget, QTreeWidgetItem, QComboBox, QHBoxLayout, 
    QLabel, QGridLayout, QFileDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt

class ProjectControlsWidget(QWidget):
    loadRequested = pyqtSignal()
    addVideoRequested = pyqtSignal()
    saveRequested = pyqtSignal()
    exportRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        group = QGroupBox("Project Controls")
        
        # [修改] 优化 Grid 布局参数
        grid_layout = QGridLayout(group)
        
        # 1. 增加按钮之间的间距 (水平和垂直)
        grid_layout.setSpacing(10) 
        
        # 2. 增加 GroupBox 内部的边距 (左, 上, 右, 下)
        grid_layout.setContentsMargins(10, 20, 10, 10)
        
        self.btn_load = QPushButton("Load JSON")
        self.btn_add = QPushButton("Add Video")
        self.btn_save = QPushButton("Save JSON")
        self.btn_export = QPushButton("Export JSON")
        
        self.btn_save.setEnabled(False)
        self.btn_export.setEnabled(False)
        
        # [修改] 设置按钮的最小高度和样式，使其不那么紧缩
        btns = [self.btn_load, self.btn_add, self.btn_save, self.btn_export]
        for btn in btns:
            btn.setMinimumHeight(35) # 增加高度
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            # 可选：增加一点圆角让界面更柔和
            btn.setStyleSheet("""
                QPushButton {
                    border-radius: 6px;
                    padding: 5px;
                    background-color: #444;
                    color: #EEE;
                    border: 1px solid #555;
                }
                QPushButton:hover { background-color: #555; border-color: #777; }
                QPushButton:pressed { background-color: #0078D7; border-color: #0078D7; }
                QPushButton:disabled { background-color: #333; color: #777; border-color: #333; }
            """)
        
        # 添加到网格位置 (行, 列)
        grid_layout.addWidget(self.btn_load, 0, 0)
        grid_layout.addWidget(self.btn_add, 0, 1)
        grid_layout.addWidget(self.btn_save, 1, 0)
        grid_layout.addWidget(self.btn_export, 1, 1)
        
        layout.addWidget(group)
        
        # Connect signals
        self.btn_load.clicked.connect(self.loadRequested.emit)
        self.btn_add.clicked.connect(self.addVideoRequested.emit)
        self.btn_save.clicked.connect(self.saveRequested.emit)
        self.btn_export.clicked.connect(self.exportRequested.emit)

    def set_project_loaded_state(self, loaded: bool):
        self.btn_save.setEnabled(loaded)
        self.btn_export.setEnabled(loaded)

# --- 保留 ActionListWidget 定义以防引用报错 (虽然 UI 中已移除) ---
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