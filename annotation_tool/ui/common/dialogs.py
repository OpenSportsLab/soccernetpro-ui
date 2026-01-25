import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QRadioButton, QTreeView, QDialogButtonBox,
    QAbstractItemView, QGroupBox, QFormLayout, QLineEdit, QHBoxLayout,
    QCheckBox, QFrame, QListWidget, QComboBox, QPushButton, QLabel,
    QMessageBox, QWidget, QListWidgetItem, QStyle, QButtonGroup, QScrollArea
)
from PyQt6.QtCore import QDir, Qt, QSize
from PyQt6.QtGui import QFileSystemModel, QIcon
from utils import get_square_remove_btn_style

class ProjectTypeDialog(QDialog):
    """Project type chooser (Classification vs. Localization)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Select Project Type")
        self.resize(400, 250)
        self.selected_mode: str | None = None

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        lbl = QLabel("Please select the type of project you want to create:")
        lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #ccc;")
        layout.addWidget(lbl)

        # Two large buttons side-by-side
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)

        self.btn_cls = QPushButton("Classification")
        self.btn_cls.setMinimumSize(QSize(0, 80))
        self.btn_cls.setStyleSheet(
            """
            QPushButton {
                font-size: 16px; background-color: #2A2A2A; border: 2px solid #444; border-radius: 8px;
            }
            QPushButton:hover { background-color: #3A3A3A; border-color: #00BFFF; }
            """
        )
        self.btn_cls.clicked.connect(lambda: self._finish("classification"))

        self.btn_loc = QPushButton("Localization\n(Action Spotting)")
        self.btn_loc.setMinimumSize(QSize(0, 80))
        self.btn_loc.setStyleSheet(
            """
            QPushButton {
                font-size: 16px; background-color: #2A2A2A; border: 2px solid #444; border-radius: 8px;
            }
            QPushButton:hover { background-color: #3A3A3A; border-color: #00BFFF; }
            """
        )
        self.btn_loc.clicked.connect(lambda: self._finish("localization"))

        btn_layout.addWidget(self.btn_cls)
        btn_layout.addWidget(self.btn_loc)

        layout.addLayout(btn_layout)
        layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _finish(self, mode: str) -> None:
        self.selected_mode = mode
        self.accept()


class CreateProjectDialog(QDialog):
    """
    Dialog to create a new project.

    Flow (top-down):
      1) Project info
      2) Head (category) builder (staging)
      3) Final list of heads in the project schema
    """

    def __init__(self, parent=None, project_type: str = "classification") -> None:
        super().__init__(parent)

        self.project_type = project_type
        self.setWindowTitle(f"Create New {project_type.capitalize()} Project")
        self.resize(600, 750)

        # Final result: { "HeadName": { "type": "...", "labels": [...] } }
        self.final_categories: dict[str, dict] = {}
        # Labels being staged for the head currently edited
        self.current_head_labels: list[str] = []

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        # ==========================================================
        # 1. Project Info
        # ==========================================================
        info_group = QGroupBox("1. Project Information")
        form = QFormLayout(info_group)

        self.task_name_edit = QLineEdit("My Task")
        form.addRow("Task Name:", self.task_name_edit)

        self.desc_edit = QLineEdit()
        form.addRow("Description:", self.desc_edit)

        # Modalities
        mod_layout = QHBoxLayout()
        self.mod_video = QCheckBox("Video")
        self.mod_video.setChecked(True)
        self.mod_image = QCheckBox("Image")
        self.mod_audio = QCheckBox("Audio")

        mod_layout.addWidget(self.mod_video)
        mod_layout.addWidget(self.mod_image)
        mod_layout.addWidget(self.mod_audio)

        # Localization is video-only: keep the UI simple and avoid invalid configs
        if self.project_type == "localization":
            self.mod_image.setVisible(False)
            self.mod_audio.setVisible(False)
            self.mod_video.setEnabled(False)

        form.addRow("Modalities:", mod_layout)
        main_layout.addWidget(info_group)

        # ==========================================================
        # 2. Head Creator (Staging Area)
        # ==========================================================
        creator_group = QGroupBox("2. Define a New Head (Category)")
        creator_layout = QVBoxLayout(creator_group)

        # 2.1 Head name
        h_name_layout = QHBoxLayout()
        h_name_layout.addWidget(QLabel("Head Name:"))
        self.head_name_edit = QLineEdit()
        self.head_name_edit.setPlaceholderText("e.g. Action, Team, Player...")
        h_name_layout.addWidget(self.head_name_edit)
        creator_layout.addLayout(h_name_layout)

        # 2.2 Label type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Label Type:"))

        self.type_group = QButtonGroup(self)
        self.rb_single = QRadioButton("Single Label (Mutually Exclusive)")
        self.rb_single.setChecked(True)
        self.rb_multi = QRadioButton("Multi Label")

        type_layout.addWidget(self.rb_single)
        type_layout.addWidget(self.rb_multi)
        type_layout.addStretch()

        self.type_group.addButton(self.rb_single)
        self.type_group.addButton(self.rb_multi)

        # Action spotting typically uses one label per event; enforce it here.
        if self.project_type == "localization":
            self.rb_multi.setVisible(False)
            self.rb_single.setText("Single Label (Fixed for Action Spotting)")
            self.rb_single.setEnabled(False)

        creator_layout.addLayout(type_layout)

        # 2.3 Labels for this head
        lbl_def_group = QGroupBox("Labels for this Head")
        lbl_def_group.setStyleSheet(
            "QGroupBox { border: 1px solid #555; margin-top: 5px; } "
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }"
        )
        lbl_def_layout = QVBoxLayout(lbl_def_group)

        inp_row = QHBoxLayout()
        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("Type label name and press Enter (e.g. Pass, Shot)")
        self.label_input.returnPressed.connect(self.add_label_to_staging)

        btn_add_lbl = QPushButton("Add Label")
        btn_add_lbl.clicked.connect(self.add_label_to_staging)

        inp_row.addWidget(self.label_input)
        inp_row.addWidget(btn_add_lbl)
        lbl_def_layout.addLayout(inp_row)

        self.staged_labels_list = QListWidget()
        self.staged_labels_list.setFixedHeight(100)
        lbl_def_layout.addWidget(self.staged_labels_list)

        creator_layout.addWidget(lbl_def_group)

        # 2.4 Commit head into project schema
        self.btn_add_head_to_project = QPushButton("Add Head Categories to Project ↓")
        self.btn_add_head_to_project.setStyleSheet("font-weight: bold; padding: 8px; font-size: 14px;")
        self.btn_add_head_to_project.clicked.connect(self.commit_head_to_project)
        creator_layout.addWidget(self.btn_add_head_to_project)

        main_layout.addWidget(creator_group)

        # ==========================================================
        # 3. Final Schema (Heads)
        # ==========================================================
        result_group = QGroupBox("3. Project Structure (Heads)")
        result_layout = QVBoxLayout(result_group)

        self.project_heads_list = QListWidget()
        result_layout.addWidget(self.project_heads_list)

        main_layout.addWidget(result_group)

        # Bottom buttons
        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bbox.accepted.connect(self.validate_and_accept)
        bbox.rejected.connect(self.reject)
        main_layout.addWidget(bbox)

    # ------------------------------------------------------------------
    # Staging / commit logic
    # ------------------------------------------------------------------
    def add_label_to_staging(self) -> None:
        """Add a label into the staging list for the current head."""
        txt = self.label_input.text().strip()
        if not txt:
            return

        # Case-insensitive duplicate guard
        if any(l.lower() == txt.lower() for l in self.current_head_labels):
            QMessageBox.warning(self, "Duplicate Label", f"Label '{txt}' already exists (case-insensitive)!")
            self.label_input.selectAll()
            return

        self.current_head_labels.append(txt)

        item = QListWidgetItem(self.staged_labels_list)
        widget = QWidget()
        h = QHBoxLayout(widget)
        h.setContentsMargins(5, 2, 5, 2)
        h.addWidget(QLabel(txt))
        h.addStretch()

        rem_btn = QPushButton("×")
        rem_btn.setFixedSize(20, 20)
        rem_btn.setStyleSheet(get_square_remove_btn_style())
        rem_btn.clicked.connect(lambda: self.remove_label_from_staging(txt, item))
        h.addWidget(rem_btn)

        item.setSizeHint(widget.sizeHint())
        self.staged_labels_list.setItemWidget(item, widget)

        self.label_input.clear()
        self.label_input.setFocus()

    def remove_label_from_staging(self, txt: str, item: QListWidgetItem) -> None:
        """Remove a staged label (both UI and the backing list)."""
        if txt in self.current_head_labels:
            self.current_head_labels.remove(txt)

        row = self.staged_labels_list.row(item)
        self.staged_labels_list.takeItem(row)

    def commit_head_to_project(self) -> None:
        """Move the staged head definition into the final project schema."""
        head_name = self.head_name_edit.text().strip()
        if not head_name:
            QMessageBox.warning(self, "Warning", "Head name cannot be empty.")
            return

        # Case-insensitive check
        if any(k.lower() == head_name.lower() for k in self.final_categories):
            QMessageBox.warning(self, "Error", f"Head '{head_name}' already exists in the project.")
            return

        ltype = "single_label"
        if self.project_type == "classification" and self.rb_multi.isChecked():
            ltype = "multi_label"

        self.final_categories[head_name] = {"type": ltype, "labels": list(self.current_head_labels)}
        self.add_head_to_project_list_ui(head_name, ltype, self.current_head_labels)

        # Reset staging area
        self.head_name_edit.clear()
        self.label_input.clear()
        self.staged_labels_list.clear()
        self.current_head_labels = []
        self.head_name_edit.setFocus()

    def add_head_to_project_list_ui(self, name: str, ltype: str, labels: list[str]) -> None:
        """Render a committed head in the final list with a remove button."""
        item = QListWidgetItem(self.project_heads_list)
        widget = QWidget()
        h = QHBoxLayout(widget)
        h.setContentsMargins(5, 5, 5, 5)

        type_str = "[S]" if ltype == "single_label" else "[M]"
        label_summary = ", ".join(labels)
        if len(label_summary) > 30:
            label_summary = label_summary[:30] + "..."

        info_label = QLabel(f"<b>{name}</b> {type_str} : {label_summary}")
        h.addWidget(info_label)
        h.addStretch()

        rem_btn = QPushButton()
        rem_btn.setFixedSize(24, 24)
        rem_btn.setFlat(True)
        rem_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        rem_btn.setToolTip("Remove head")
        rem_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        rem_btn.clicked.connect(lambda: self.remove_head_from_project(name, item))
        h.addWidget(rem_btn)

        item.setSizeHint(widget.sizeHint())
        self.project_heads_list.setItemWidget(item, widget)

    def remove_head_from_project(self, name: str, item: QListWidgetItem) -> None:
        """Remove a head from the final schema list."""
        self.final_categories.pop(name, None)
        row = self.project_heads_list.row(item)
        self.project_heads_list.takeItem(row)

    def validate_and_accept(self) -> None:
        """Final validation before closing with OK."""
        if not self.task_name_edit.text().strip():
            self.task_name_edit.setPlaceholderText("NAME REQUIRED!")
            self.task_name_edit.setFocus()
            return

        if not self.final_categories:
            QMessageBox.warning(self, "Warning", "Please define at least one head and add it to the project.")
            return

        self.accept()

    def get_data(self) -> dict:
        """Collect dialog data into a config-like dict."""
        modalities: list[str] = []
        if self.mod_video.isChecked():
            modalities.append("video")
        if self.mod_image.isChecked():
            modalities.append("image")
        if self.mod_audio.isChecked():
            modalities.append("audio")

        return {
            "task": self.task_name_edit.text().strip(),
            "description": self.desc_edit.text().strip(),
            "modalities": modalities,
            "labels": self.final_categories,
        }


class FolderPickerDialog(QDialog):
    """Custom folder picker (multi-select without requiring Ctrl)."""

    def __init__(self, initial_dir: str = "", parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Select Scene Folders (Click to Toggle Multiple)")
        self.resize(900, 600)

        layout = QVBoxLayout(self)
        layout.addWidget(QRadioButton("Tip: Click multiple folders to select them. No need to hold Ctrl."))

        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        self.model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot)

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.tree.setColumnWidth(0, 400)
        for i in range(1, 4):
            self.tree.hideColumn(i)

        start_path = initial_dir if initial_dir and os.path.exists(initial_dir) else QDir.rootPath()
        self.tree.setRootIndex(self.model.index(start_path))

        layout.addWidget(self.tree)

        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

    def get_selected_folders(self) -> list[str]:
        """Return absolute paths for all selected folders."""
        indexes = self.tree.selectionModel().selectedRows()
        return [self.model.filePath(idx) for idx in indexes]
