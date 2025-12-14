from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox, 
    QLineEdit, QTableView, QHeaderView, QGridLayout, QLabel, QScrollArea,
    QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
from .table_model import AnnotationTableModel
from utils import get_square_remove_btn_style

class SpottingGroup(QGroupBox):
    """
    专门用于 Spotting 的标签组。
    每个单元格包含：[ 标签按钮 (点击打点) ] [ X (删除标签) ]
    """
    labelClicked = pyqtSignal(str, str) # head, label
    labelRemoved = pyqtSignal(str, str) # head, label

    def __init__(self, head, labels, parent=None):
        super().__init__(head.title(), parent)
        self.head = head
        layout = QGridLayout(self)
        layout.setSpacing(5)
        
        cols = 3
        for i, label in enumerate(labels):
            container = QWidget()
            c_layout = QHBoxLayout(container)
            c_layout.setContentsMargins(0, 0, 0, 0)
            c_layout.setSpacing(2)
            
            btn_lbl = QPushButton(label)
            btn_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            btn_lbl.setStyleSheet("""
                QPushButton {
                    background-color: #444; 
                    color: white; 
                    border: 1px solid #555;
                    border-radius: 4px;
                    padding: 6px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #555; border-color: #00BFFF; }
                QPushButton:pressed { background-color: #00BFFF; }
            """)
            btn_lbl.clicked.connect(lambda _, l=label: self.labelClicked.emit(self.head, l))
            
            btn_del = QPushButton("×")
            btn_del.setFixedSize(20, 20)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet(get_square_remove_btn_style())
            btn_del.setToolTip(f"Remove '{label}' from schema")
            btn_del.clicked.connect(lambda _, l=label: self.labelRemoved.emit(self.head, l))
            
            c_layout.addWidget(btn_lbl)
            c_layout.addWidget(btn_del)
            layout.addWidget(container, i // cols, i % cols)

class AnnotationManagementWidget(QWidget):
    labelActionTriggered = pyqtSignal(str, str) 
    labelRemoveTriggered = pyqtSignal(str, str)
    undoRequested = pyqtSignal()
    redoRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # [修改] 设置最小高度，防止被表格挤压得太小
        self.setMinimumHeight(150)
        
        # Undo/Redo Header
        h_ur = QHBoxLayout()
        self.btn_undo = QPushButton("Undo")
        self.btn_redo = QPushButton("Redo")
        self.btn_undo.clicked.connect(self.undoRequested.emit)
        self.btn_redo.clicked.connect(self.redoRequested.emit)
        h_ur.addWidget(self.btn_undo)
        h_ur.addWidget(self.btn_redo)
        layout.addLayout(h_ur)
        
        # Scroll Area for Labels
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        self.groups_container = QWidget()
        self.groups_layout = QVBoxLayout(self.groups_container)
        self.groups_layout.setContentsMargins(0, 0, 0, 0)
        self.groups_layout.addStretch() 
        
        scroll.setWidget(self.groups_container)
        layout.addWidget(scroll)

    def update_schema(self, labels_def):
        while self.groups_layout.count() > 1: 
            item = self.groups_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        heads = sorted(labels_def.keys())
        for head in heads:
            defn = labels_def[head]
            labels = sorted(defn.get('labels', []))
            
            group = SpottingGroup(head, labels)
            group.labelClicked.connect(self.labelActionTriggered.emit)
            group.labelRemoved.connect(self.labelRemoveTriggered.emit)
            self.groups_layout.insertWidget(self.groups_layout.count()-1, group)

class LabelEditorWidget(QWidget):
    newLabelAdded = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        group = QGroupBox("Add New Label at Current Time")
        v = QVBoxLayout(group)
        
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type label name...")
        self.input.returnPressed.connect(self._on_add)
        
        self.btn_add = QPushButton("Label and Mark")
        self.btn_add.clicked.connect(self._on_add)
        
        v.addWidget(self.input)
        v.addWidget(self.btn_add)
        layout.addWidget(group)
        
        self.current_head = "action" 

    def set_current_head(self, head):
        self.current_head = head
        self.input.setPlaceholderText(f"Add label to '{head}'")

    def _on_add(self):
        txt = self.input.text().strip()
        if txt and self.current_head:
            self.newLabelAdded.emit(self.current_head, txt)
            self.input.clear()

class AnnotationTableWidget(QWidget):
    annotationSelected = pyqtSignal(int) 
    annotationDeleted = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        lbl = QLabel("Events List")
        lbl.setStyleSheet("font-weight: bold; color: #888;")
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
                background-color: #444;
                color: white;
                border: 1px solid #555;
                padding: 4px;
            }
        """)
        
        self.model = AnnotationTableModel()
        self.table.setModel(self.model)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed) 
        self.table.setColumnWidth(3, 40)
        
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        
        layout.addWidget(self.table)

    def set_data(self, annotations):
        self.model.set_annotations(annotations)
        # 为每一行添加删除按钮
        for row in range(len(annotations)):
            btn = QPushButton("×")
            btn.setFixedSize(24, 24)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent; 
                    color: #FF5555; 
                    border: none; 
                    font-weight: bold; font-size: 16px;
                }
                QPushButton:hover { background-color: rgba(255,85,85,0.2); border-radius: 4px; }
            """)
            
            item = annotations[row]
            btn.clicked.connect(lambda _, i=item: self.annotationDeleted.emit(i))
            
            self.table.setIndexWidget(self.model.index(row, 3), btn)

    def _on_selection_changed(self, selected, deselected):
        indexes = selected.indexes()
        if indexes:
            row = indexes[0].row()
            item = self.model.get_annotation_at(row)
            if item:
                self.annotationSelected.emit(item.get('position_ms', 0))