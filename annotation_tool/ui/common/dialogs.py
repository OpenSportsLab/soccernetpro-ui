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
    """
    Project type chooser (Classification vs. Localization).
    This is the only dialog shown after clicking 'New Project'.
    """

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