import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem,
    QLabel, QComboBox, QScrollArea, QGroupBox, QStackedLayout, QFrame,
    QLineEdit, QMenu, QStyle
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QUrl, QTimer
from PyQt6.QtGui import QAction, QColor, QIcon, QKeySequence
from PyQt6.QtMultimedia import QMediaPlayer

# Import the new unified widget
from ui.common.project_controls import UnifiedProjectControls
from ui.classification.widgets import VideoViewAndControl, DynamicSingleLabelGroup, DynamicMultiLabelGroup
from utils import resource_path, natural_sort_key

# --- Main Window Container ---
class MainWindowUI(QWidget):
    """
    The main container that switches between Welcome, Classification, and Localization views.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stack_layout = QStackedLayout(self)
        
        # 1. Welcome Screen
        self.welcome_widget = WelcomeWidget()
        self.stack_layout.addWidget(self.welcome_widget)
        
        # 2. Classification View
        self.classification_widget = QWidget()
        self.c_layout = QHBoxLayout(self.classification_widget)
        self.c_layout.setContentsMargins(0, 0, 0, 0)
        self.c_layout.setSpacing(5)
        
        self.left_panel = LeftPanel()
        self.center_panel = CenterPanel()
        self.right_panel = RightPanel()
        
        self.c_layout.addWidget(self.left_panel)
        self.c_layout.addWidget(self.center_panel, 1)
        self.c_layout.addWidget(self.right_panel)
        
        self.stack_layout.addWidget(self.classification_widget)
        
        # 3. Localization View
        from ui.localization.panels import LocalizationUI
        self.localization_ui = LocalizationUI()
        self.stack_layout.addWidget(self.localization_ui)

    def show_welcome_view(self):
        self.stack_layout.setCurrentIndex(0)

    def show_classification_view(self):
        self.stack_layout.setCurrentIndex(1)

    def show_localization_view(self):
        self.stack_layout.setCurrentIndex(2)

# --- Welcome Widget ---
class WelcomeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        
        title = QLabel("SoccerNet Annotation Tool")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #00BFFF;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        self.create_btn = QPushButton("Create New Project")
        self.create_btn.setFixedSize(200, 50)
        self.create_btn.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.import_btn = QPushButton("Import Project JSON")
        self.import_btn.setFixedSize(200, 50)
        self.import_btn.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout.addWidget(self.create_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.import_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

# --- Classification Panels ---

class LeftPanel(QWidget):
    # Signal proxies for the controller to connect to
    request_remove_item = pyqtSignal(QTreeWidgetItem)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 1. Unified Project Controls
        self.project_controls = UnifiedProjectControls()
        
        # Expose buttons for viewer.py
        self.import_btn = self.project_controls.btn_load
        self.create_btn = self.project_controls.btn_create
        self.add_data_btn = self.project_controls.btn_add
        
        layout.addWidget(self.project_controls)
        
        # 2. Action List (Tree)
        self.action_tree = QTreeWidget()
        self.action_tree.setHeaderHidden(True)
        self.action_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.action_tree.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(QLabel("Action List:"))
        layout.addWidget(self.action_tree)
        
        # 3. Filters and Clear (Now in one row, matching Localization)
        h_filter = QHBoxLayout()
        h_filter.setContentsMargins(0, 0, 0, 0)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Actions", "Done", "Not Done"])
        
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        h_filter.addWidget(QLabel("Filter:"))
        h_filter.addWidget(self.filter_combo, 1) # stretch factor 1
        h_filter.addWidget(self.clear_btn)
        
        layout.addLayout(h_filter)
        
        # Removed Undo/Redo from here (Moved to RightPanel)

    def add_action_item(self, name, path, children=None):
        item = QTreeWidgetItem(self.action_tree, [name])
        item.setData(0, Qt.ItemDataRole.UserRole, path)
        if children:
            for child_path in children:
                c_item = QTreeWidgetItem(item, [os.path.basename(child_path)])
                c_item.setData(0, Qt.ItemDataRole.UserRole, child_path)
        return item

    def _show_context_menu(self, pos):
        item = self.action_tree.itemAt(pos)
        if item:
            menu = QMenu()
            remove_action = menu.addAction("Remove Item")
            action = menu.exec(self.action_tree.mapToGlobal(pos))
            if action == remove_action:
                self.request_remove_item.emit(item)

class CenterPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Main View Area (Video) - Placed at TOP
        self.view_container = QWidget()
        self.view_layout = QStackedLayout(self.view_container)
        self.layout.addWidget(self.view_container, 1) # Stretch 1 to take available space
        
        self.single_view_widget = VideoViewAndControl(None)
        self.view_layout.addWidget(self.single_view_widget)
        
        # Multi view placeholder
        self.multi_view_widget = QWidget()
        self.view_layout.addWidget(self.multi_view_widget)
        
        # 2. Navigation Toolbar - Placed at BOTTOM
        self.toolbar = QHBoxLayout()
        self.toolbar.setContentsMargins(5, 5, 5, 5)
        
        self.prev_action = QPushButton("<< Prev Action")
        self.prev_clip = QPushButton("< Prev Clip")
        self.play_btn = QPushButton("Play / Pause")
        self.next_clip = QPushButton("Next Clip >")
        self.next_action = QPushButton("Next Action >>")
        
        btns = [self.prev_action, self.prev_clip, self.play_btn, self.next_clip, self.next_action]
        for b in btns:
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.toolbar.addWidget(b)
            
        self.multi_view_btn = QPushButton("Multi-View")
        self.multi_view_btn.setCheckable(True)
        self.multi_view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toolbar.addWidget(self.multi_view_btn)
        
        self.layout.addLayout(self.toolbar)

    def show_single_view(self, media_path):
        self.single_view_widget.player.setSource(QUrl.fromLocalFile(media_path) if media_path else QUrl())
        self.view_layout.setCurrentWidget(self.single_view_widget)
        
    def show_all_views(self, paths):
        pass
    
    def toggle_play_pause(self):
        if self.single_view_widget.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.single_view_widget.player.pause()
        else:
            self.single_view_widget.player.play()

class RightPanel(QWidget):
    # Defined signals
    add_head_clicked = pyqtSignal(str)
    remove_head_clicked = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(350)
        layout = QVBoxLayout(self)
        
        # 1. Undo/Redo Controls (Moved from LeftPanel)
        h_undo = QHBoxLayout()
        self.undo_btn = QPushButton("Undo")
        self.redo_btn = QPushButton("Redo")
        
        # Styling for Undo/Redo
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
        
        # 2. Task Info
        self.task_label = QLabel("Task: N/A")
        self.task_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px 0;")
        layout.addWidget(self.task_label)

        # 3. Dynamic Schema Management
        schema_group = QGroupBox("Schema Management")
        schema_layout = QVBoxLayout(schema_group)
        
        h_new = QHBoxLayout()
        self.new_head_edit = QLineEdit()
        self.new_head_edit.setPlaceholderText("New Category Name...")
        self.add_head_btn = QPushButton("Add Category")
        self.add_head_btn.clicked.connect(lambda: self.add_head_clicked.emit(self.new_head_edit.text()))
        h_new.addWidget(self.new_head_edit)
        h_new.addWidget(self.add_head_btn)
        schema_layout.addLayout(h_new)
        layout.addWidget(schema_group)
        
        # 4. Manual Annotation Area
        self.manual_box = QGroupBox("Manual Annotation")
        self.manual_layout = QVBoxLayout(self.manual_box)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll.setWidget(self.scroll_content)
        self.manual_layout.addWidget(self.scroll)
        
        # Confirmation btns
        h_btns = QHBoxLayout()
        self.confirm_btn = QPushButton("Confirm (Save)")
        self.confirm_btn.setStyleSheet("background-color: #0078D7; color: white; font-weight: bold; padding: 5px;")
        self.clear_sel_btn = QPushButton("Clear Selection")
        h_btns.addWidget(self.confirm_btn)
        h_btns.addWidget(self.clear_sel_btn)
        self.manual_layout.addLayout(h_btns)
        
        layout.addWidget(self.manual_box)
        
        
        self.label_groups = {}

    def setup_dynamic_labels(self, label_definitions):
        # Clear existing
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        self.label_groups.clear()
        
        for head, defn in label_definitions.items():
            l_type = defn.get('type', 'single_label')
            if l_type == 'single_label':
                group = DynamicSingleLabelGroup(head, defn)
            else:
                group = DynamicMultiLabelGroup(head, defn)
            
            group.remove_category_signal.connect(self.remove_head_clicked.emit)
            self.scroll_layout.addWidget(group)
            self.label_groups[head] = group
            
        self.scroll_layout.addStretch()

    def get_annotation(self):
        result = {}
        for head, group in self.label_groups.items():
            if isinstance(group, DynamicSingleLabelGroup):
                val = group.get_checked_label()
                if val: result[head] = val
            else:
                vals = group.get_checked_labels()
                if vals: result[head] = vals
        return result

    def set_annotation(self, data):
        if not data: data = {}
        for head, group in self.label_groups.items():
            val = data.get(head)
            if isinstance(group, DynamicSingleLabelGroup):
                group.set_checked_label(val)
            else:
                group.set_checked_labels(val)
                
    def clear_selection(self):
        for group in self.label_groups.values():
            if isinstance(group, DynamicSingleLabelGroup):
                group.set_checked_label(None)
            else:
                group.set_checked_labels([])