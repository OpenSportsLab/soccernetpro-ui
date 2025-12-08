import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QRadioButton, QTreeView, QDialogButtonBox,
    QAbstractItemView, QGroupBox, QFormLayout, QLineEdit, QHBoxLayout,
    QCheckBox, QFrame, QListWidget, QComboBox, QPushButton, QLabel,
    QMessageBox, QWidget, QListWidgetItem, QStyle
)
from PyQt6.QtCore import QDir, Qt
from PyQt6.QtGui import QFileSystemModel
from utils import get_square_remove_btn_style

class FolderPickerDialog(QDialog):
    """Custom Folder Picker (Multi-Select without Ctrl)."""
    def __init__(self, initial_dir="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Scene Folders (Click to Toggle Multiple)")
        self.resize(900, 600)
        
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(QRadioButton("Tip: Click multiple folders to select them. No need to hold Ctrl."))
        
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        self.model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot)
        
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        
        self.tree.setColumnWidth(0, 400)
        for i in range(1, 4):
            self.tree.hideColumn(i)
        
        start_path = initial_dir if initial_dir and os.path.exists(initial_dir) else QDir.currentPath()
        root_idx = self.model.index(start_path)
        self.tree.scrollTo(root_idx)
        self.tree.expand(root_idx)
        
        self.layout.addWidget(self.tree)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def get_selected_paths(self):
        paths = []
        indexes = self.tree.selectionModel().selectedRows()
        for idx in indexes:
            file_path = self.model.filePath(idx)
            if file_path:
                paths.append(file_path)
        return paths

class CreateProjectDialog(QDialog):
    """Dialog to initialize a new JSON project structure."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Annotation Project")
        self.resize(700, 600)
        self.final_categories = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 1. Basic Info
        form_group = QGroupBox("Project Metadata")
        form_layout = QFormLayout(form_group)
        self.task_name_edit = QLineEdit()
        self.task_name_edit.setPlaceholderText("e.g., Soccer Foul Detection")
        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Optional description...")
        
        form_layout.addRow("Task Name:", self.task_name_edit)
        form_layout.addRow("Description:", self.desc_edit)
        layout.addWidget(form_group)
        
        # 2. Modalities
        mod_group = QGroupBox("Modalities")
        mod_layout = QHBoxLayout(mod_group)
        self.mod_video = QCheckBox("Video")
        self.mod_video.setChecked(True)
        self.mod_image = QCheckBox("Image")
        self.mod_audio = QCheckBox("Audio")
        
        mod_layout.addWidget(self.mod_video)
        mod_layout.addWidget(self.mod_image)
        mod_layout.addWidget(self.mod_audio)
        layout.addWidget(mod_group)
        
        # 3. Categories / Labels Definition
        cat_group = QGroupBox("Create a Heads")
        cat_layout = QVBoxLayout(cat_group)
        
        input_frame = QFrame()
        input_frame.setFrameShape(QFrame.Shape.StyledPanel)
        input_layout = QVBoxLayout(input_frame)
        
        # Row A: Name and Type
        row_a = QHBoxLayout()
        self.cat_name_edit = QLineEdit()
        self.cat_name_edit.setPlaceholderText("Category Name")
        
        self.cat_type_combo = QComboBox()
        self.cat_type_combo.addItems(["Single Label", "Multi Label"])
        
        row_a.addWidget(QLabel("Name:"))
        row_a.addWidget(self.cat_name_edit, 2)
        row_a.addWidget(QLabel("Type:"))
        row_a.addWidget(self.cat_type_combo, 1)
        input_layout.addLayout(row_a)
        
        # Row B: Label Adding
        row_b = QHBoxLayout()
        self.current_labels_list = QListWidget() 
        self.current_labels_list.setMaximumHeight(120) 
        self.current_labels_list.setAlternatingRowColors(True)
        
        label_input_layout = QVBoxLayout()
        h_label_in = QHBoxLayout()
        self.single_label_input = QLineEdit()
        self.single_label_input.setPlaceholderText("Type a label")
        self.single_label_input.returnPressed.connect(self.add_label_to_temp_list)
        
        self.add_label_btn = QPushButton("Add Label")
        self.add_label_btn.clicked.connect(self.add_label_to_temp_list)
        
        h_label_in.addWidget(self.single_label_input)
        h_label_in.addWidget(self.add_label_btn)
        
        label_input_layout.addLayout(h_label_in)
        label_input_layout.addWidget(QLabel("Current Labels:"))
        label_input_layout.addWidget(self.current_labels_list)
        
        input_layout.addLayout(label_input_layout)
        
        self.add_category_btn = QPushButton("Add Category to Project")
        self.add_category_btn.setStyleSheet("font-weight: bold; padding: 5px;")
        self.add_category_btn.clicked.connect(self.add_category_to_main_list)
        input_layout.addWidget(self.add_category_btn)
        
        cat_layout.addWidget(input_frame)
        cat_layout.addWidget(QLabel("Pre-defined Categories:"))
        self.categories_list_widget = QListWidget() 
        cat_layout.addWidget(self.categories_list_widget)
        
        layout.addWidget(cat_group)
        
        # 4. Dialog Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def add_label_to_temp_list(self):
        txt = self.single_label_input.text().strip()
        if not txt: return
        txt_lower = txt.lower() 
        for i in range(self.current_labels_list.count()):
            item = self.current_labels_list.item(i)
            existing_text = item.data(Qt.ItemDataRole.UserRole)
            if existing_text and existing_text.lower() == txt_lower:
                QMessageBox.warning(self, "Duplicate Label", f"The label '{txt}' already exists.")
                return
        
        item = QListWidgetItem(self.current_labels_list)
        item.setData(Qt.ItemDataRole.UserRole, txt)
        
        item_widget = QWidget()
        h_layout = QHBoxLayout(item_widget)
        h_layout.setContentsMargins(5, 2, 5, 2)
        
        lbl = QLabel(txt)
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(20, 20)
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setStyleSheet(get_square_remove_btn_style())
        remove_btn.clicked.connect(lambda _, it=item: self.remove_temp_label(it))
        
        h_layout.addWidget(lbl, 1)
        h_layout.addWidget(remove_btn)
        
        item.setSizeHint(item_widget.sizeHint())
        self.current_labels_list.setItemWidget(item, item_widget)
        self.single_label_input.clear()
        self.single_label_input.setFocus()

    def remove_temp_label(self, item):
        row = self.current_labels_list.row(item)
        self.current_labels_list.takeItem(row)

    def add_category_to_main_list(self):
        raw_name = self.cat_name_edit.text().strip()
        if not raw_name:
            self.cat_name_edit.setPlaceholderText("NAME REQUIRED!")
            return
        cat_key = raw_name.replace(" ", "_").lower()
        
        if cat_key in self.final_categories:
            QMessageBox.warning(self, "Duplicate Category", f"Category '{cat_key}' already exists.")
            return

        cat_type_disp = self.cat_type_combo.currentText()
        cat_type_internal = "single_label" if "Single" in cat_type_disp else "multi_label"
        
        labels = []
        for i in range(self.current_labels_list.count()):
            item = self.current_labels_list.item(i)
            label_text = item.data(Qt.ItemDataRole.UserRole)
            if label_text: labels.append(label_text)
        
        self.final_categories[cat_key] = {"type": cat_type_internal, "labels": sorted(list(set(labels)))}
        
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(5, 2, 5, 2)
        
        clean_title = cat_key.replace('_', ' ').title()
        info_text = f"<b>{clean_title}</b> ({cat_type_disp}) - {len(labels)} labels"
        label_info = QLabel(info_text)
        
        delete_btn = QPushButton()
        delete_btn.setFixedSize(24, 24)
        delete_btn.setFlat(True)
        delete_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        delete_btn.clicked.connect(lambda _, n=cat_key: self.remove_category(n))
        
        item_layout.addWidget(label_info, 1)
        item_layout.addWidget(delete_btn)
        
        list_item = QListWidgetItem(self.categories_list_widget)
        list_item.setSizeHint(item_widget.sizeHint())
        list_item.setData(Qt.ItemDataRole.UserRole, cat_key)
        
        self.categories_list_widget.addItem(list_item)
        self.categories_list_widget.setItemWidget(list_item, item_widget)
        
        self.cat_name_edit.clear()
        self.current_labels_list.clear()
        self.single_label_input.clear()

    def remove_category(self, cat_name):
        if cat_name in self.final_categories:
            del self.final_categories[cat_name]
        for i in range(self.categories_list_widget.count()):
            item = self.categories_list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == cat_name:
                self.categories_list_widget.takeItem(i)
                break

    def validate_and_accept(self):
        if not self.task_name_edit.text().strip():
            self.task_name_edit.setPlaceholderText("NAME REQUIRED!")
            self.task_name_edit.setFocus()
            return
        self.accept()

    def get_data(self):
        modalities = []
        if self.mod_video.isChecked(): modalities.append("video")
        if self.mod_image.isChecked(): modalities.append("image")
        if self.mod_audio.isChecked(): modalities.append("audio")
            
        return {
            "task": self.task_name_edit.text().strip(),
            "description": self.desc_edit.text().strip(),
            "modalities": modalities,
            "labels": self.final_categories
        }