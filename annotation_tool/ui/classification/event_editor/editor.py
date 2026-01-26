from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QGroupBox, QLineEdit, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal

from .dynamic_widgets import DynamicSingleLabelGroup, DynamicMultiLabelGroup

class ClassificationEventEditor(QWidget):
    """
    Right Panel for Classification Mode.
    Renamed from ClassRightPanel to ClassificationEventEditor for consistency with folder name.
    """
    
    add_head_clicked = pyqtSignal(str)
    remove_head_clicked = pyqtSignal(str)
    style_mode_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(350)
        layout = QVBoxLayout(self)
        
        # 1. Undo/Redo Controls
        h_undo = QHBoxLayout()
        self.undo_btn = QPushButton("Undo")
        self.redo_btn = QPushButton("Redo")
        for btn in [self.undo_btn, self.redo_btn]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setEnabled(False) 
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #444; color: #DDD; border: 1px solid #555;
                    border-radius: 4px; padding: 4px; font-weight: bold;
                }
                QPushButton:hover { background-color: #555; border-color: #777; }
                QPushButton:disabled { color: #666; background-color: #333; }
            """)
        h_undo.addWidget(self.undo_btn)
        h_undo.addWidget(self.redo_btn)
        layout.addLayout(h_undo)
        
        # 2. Task Information
        self.task_label = QLabel("Task: N/A")
        self.task_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 5px;")
        layout.addWidget(self.task_label)

        # 3. Schema Editor
        schema_box = QGroupBox("Schema Editor")
        schema_layout = QHBoxLayout(schema_box)
        self.new_head_edit = QLineEdit()
        self.new_head_edit.setPlaceholderText("New Category Name...")
        self.add_head_btn = QPushButton("Add Head")
        self.add_head_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_head_btn.clicked.connect(lambda: self.add_head_clicked.emit(self.new_head_edit.text()))
        schema_layout.addWidget(self.new_head_edit)
        schema_layout.addWidget(self.add_head_btn)
        layout.addWidget(schema_box)

        # 4. Dynamic Annotation Area
        self.manual_box = QGroupBox("Annotations")
        self.manual_box.setEnabled(False) 
        manual_layout = QVBoxLayout(self.manual_box)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self.label_container = QWidget()
        self.label_container_layout = QVBoxLayout(self.label_container)
        self.label_container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll.setWidget(self.label_container)
        manual_layout.addWidget(scroll)
        
        btn_row = QHBoxLayout()
        self.confirm_btn = QPushButton("Save Annotation")
        self.clear_sel_btn = QPushButton("Clear Selection")
        self.confirm_btn.setStyleSheet("background-color: #0078D7; color: white; font-weight: bold;")
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_sel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        btn_row.addWidget(self.confirm_btn)
        btn_row.addWidget(self.clear_sel_btn)
        manual_layout.addLayout(btn_row)
        
        layout.addWidget(self.manual_box, 1) 
        
        self.label_groups = {} 

    def setup_dynamic_labels(self, label_definitions):
        while self.label_container_layout.count():
            item = self.label_container_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.label_groups = {}

        for head, defn in label_definitions.items():
            l_type = defn.get('type', 'single_label')
            if l_type == 'single_label':
                group = DynamicSingleLabelGroup(head, defn)
            else:
                group = DynamicMultiLabelGroup(head, defn)
            
            group.remove_category_signal.connect(self.remove_head_clicked.emit)
            self.label_container_layout.addWidget(group)
            self.label_groups[head] = group
        
        self.label_container_layout.addStretch()

    def set_annotation(self, data):
        if not data: data = {}
        for head, group in self.label_groups.items():
            val = data.get(head)
            if hasattr(group, 'set_checked_label'):
                group.set_checked_label(val)
            elif hasattr(group, 'set_checked_labels'):
                group.set_checked_labels(val)

    def get_annotation(self):
        result = {}
        for head, group in self.label_groups.items():
            if hasattr(group, 'get_checked_label'):
                val = group.get_checked_label()
                if val: result[head] = val
            elif hasattr(group, 'get_checked_labels'):
                vals = group.get_checked_labels()
                if vals: result[head] = vals
        return result

    def clear_selection(self):
        for group in self.label_groups.values():
            if hasattr(group, 'set_checked_label'):
                group.set_checked_label(None)
            elif hasattr(group, 'set_checked_labels'):
                group.set_checked_labels([])