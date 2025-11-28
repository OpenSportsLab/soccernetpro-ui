import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QHeaderView, QStyle,
    QProgressBar, QLabel, QTreeWidget, QTreeWidgetItem, QScrollArea, QSizePolicy,
    QGroupBox, QRadioButton, QButtonGroup, QComboBox, QLineEdit, QCheckBox,
    QSlider, QGridLayout, QDialog, QFormLayout, QDialogButtonBox, QTableWidget, 
    QTableWidgetItem, QAbstractItemView, QListWidget, QListWidgetItem, QFrame,
    QMessageBox, QMenu
)
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QTime, QSize, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QPixmap, QAction
 
# Define all supported media extensions for file filtering
SUPPORTED_EXTENSIONS = (
    '.mp4', '.avi', '.mov',  # Video
    '.jpg', '.jpeg', '.png', '.bmp', # Image
    '.wav', '.mp3', '.aac'  # Audio
)

# --- Helper Style for the "Small Square with Cross" Button ---
# Optimized for perfect centering and size (16px Arial)
def get_square_remove_btn_style():
    return """
        QPushButton {
            background-color: transparent;
            border: 1px solid #999999;
            border-radius: 3px;
            color: #999999;
            font-family: Arial;
            font-weight: bold;
            font-size: 16px;
            padding: 0px;
            margin: 0px;
        }
        QPushButton:hover {
            border-color: #FF4444;
            color: #FF4444;
            background-color: rgba(255, 68, 68, 0.1);
        }
    """

# --- Helper Class: Wrapper for a single video view and its controls ---
class VideoViewAndControl(QWidget):
    """Wraps a QVideoWidget and its controls (Slider/Label)."""
    def __init__(self, clip_path, parent=None):
        super().__init__(parent)
        self.clip_path = clip_path
        self.player = QMediaPlayer()
        self.player.setLoops(QMediaPlayer.Loops.Infinite)
        self.video_widget = QVideoWidget()
        self.player.setVideoOutput(self.video_widget)
        
        # Controls
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.setEnabled(False)
        self.clip_name = os.path.basename(clip_path) if clip_path else "No Clip"
        self.time_label = QLabel(f"00:00 / 00:00")
        
        # Layout
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        
        self.v_layout.addWidget(self.video_widget, 1) 
        
        h_control_layout = QHBoxLayout()
        self.time_label.setFixedWidth(100) 
        h_control_layout.addWidget(self.time_label)
        h_control_layout.addWidget(self.slider)
        self.v_layout.addLayout(h_control_layout)
        
        self.total_duration = 0

# --- Create Project Dialog ---
class CreateProjectDialog(QDialog):
    """Dialog to initialize a new JSON project structure with improved UX."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Annotation Project")
        self.resize(700, 600)
        
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
        
        # --- Input Area ---
        input_frame = QFrame()
        input_frame.setFrameShape(QFrame.Shape.StyledPanel)
        input_layout = QVBoxLayout(input_frame)
        
        # Row A: Name and Type
        row_a = QHBoxLayout()
        self.cat_name_edit = QLineEdit()
        self.cat_name_edit.setPlaceholderText("Category Name (e.g., Color)")
        
        self.cat_type_combo = QComboBox()
        # [MODIFIED] Display cleaner names (removed underscores)
        self.cat_type_combo.addItems(["Single Label", "Multi Label"])
        
        row_a.addWidget(QLabel("Name:"))
        row_a.addWidget(self.cat_name_edit, 2)
        row_a.addWidget(QLabel("Type:"))
        row_a.addWidget(self.cat_type_combo, 1)
        input_layout.addLayout(row_a)
        
        # Row B: Label Adding (Tags style)
        row_b = QHBoxLayout()
        self.current_labels_list = QListWidget() 
        self.current_labels_list.setMaximumHeight(120) 
        self.current_labels_list.setToolTip("Labels added for this category will appear here")
        self.current_labels_list.setAlternatingRowColors(True)
        
        label_input_layout = QVBoxLayout()
        h_label_in = QHBoxLayout()
        self.single_label_input = QLineEdit()
        self.single_label_input.setPlaceholderText("Type a label (e.g., Yellow) ")
        self.single_label_input.returnPressed.connect(self.add_label_to_temp_list)
        
        self.add_label_btn = QPushButton("Add Label")
        self.add_label_btn.clicked.connect(self.add_label_to_temp_list)
        
        h_label_in.addWidget(self.single_label_input)
        h_label_in.addWidget(self.add_label_btn)
        
        label_input_layout.addLayout(h_label_in)
        label_input_layout.addWidget(QLabel("Current Labels:"))
        label_input_layout.addWidget(self.current_labels_list)
        
        input_layout.addLayout(label_input_layout)
        
        # Row C: Add Category Button
        self.add_category_btn = QPushButton("Add Category to Project")
        self.add_category_btn.setStyleSheet("font-weight: bold; padding: 5px;")
        self.add_category_btn.clicked.connect(self.add_category_to_main_list)
        input_layout.addWidget(self.add_category_btn)
        
        cat_layout.addWidget(input_frame)
        
        # --- Main List of Added Categories ---
        cat_layout.addWidget(QLabel("Pre-defined Categories:"))
        self.categories_list_widget = QListWidget() 
        cat_layout.addWidget(self.categories_list_widget)
        
        layout.addWidget(cat_group)
        
        # 4. Dialog Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.final_categories = {}

    # Intercept Key Presses to prevent Enter from closing the dialog unless intentional
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.single_label_input.hasFocus():
                self.add_label_to_temp_list()
            return 
        super().keyPressEvent(event)

    def add_label_to_temp_list(self):
        txt = self.single_label_input.text().strip()
        if not txt: return
        
        txt_lower = txt.lower() 
        
        for i in range(self.current_labels_list.count()):
            item = self.current_labels_list.item(i)
            existing_text = item.data(Qt.ItemDataRole.UserRole)
            
            # Duplicated test
            if existing_text and existing_text.lower() == txt_lower:
                QMessageBox.warning(self, "Duplicate Label", f"The label '{txt}' already exists.")
                self.single_label_input.selectAll() 
                self.single_label_input.setFocus()
                return
            
        item = QListWidgetItem(self.current_labels_list)
        item.setData(Qt.ItemDataRole.UserRole, txt)
        
        item_widget = QWidget()
        h_layout = QHBoxLayout(item_widget)
        h_layout.setContentsMargins(5, 2, 5, 2)
        
        lbl = QLabel(txt)
        
        # Small Square X Button for labels in dialog
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(20, 20)
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setToolTip("Remove label")
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
        
        # Case Insensitive: Convert to lowercase for internal key (snake_case)
        cat_key = raw_name.replace(" ", "_").lower()
            
        if cat_key in self.final_categories:
            QMessageBox.warning(self, "Duplicate Category", f"Category '{cat_key}' already exists.")
            self.cat_name_edit.selectAll()
            self.cat_name_edit.setFocus()
            return
            
        for i in range(self.categories_list_widget.count()):
            item = self.categories_list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == cat_key:
                QMessageBox.warning(self, "Duplicate Category", f"Category '{cat_key}' already exists.")
                return

        cat_type_disp = self.cat_type_combo.currentText()
        # Map display text back to internal key for JSON
        cat_type_internal = "single_label" if "Single" in cat_type_disp else "multi_label"
        
        labels = []
        for i in range(self.current_labels_list.count()):
            item = self.current_labels_list.item(i)
            label_text = item.data(Qt.ItemDataRole.UserRole)
            if label_text:
                labels.append(label_text)
        
        # Store using internal keys
        self.final_categories[cat_key] = {
            "type": cat_type_internal,
            "labels": sorted(list(set(labels)))
        }
        
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(5, 2, 5, 2)
        
        # [MODIFIED] Display Clean Title (No underscores)
        clean_title = cat_key.replace('_', ' ').title()
        info_text = f"<b>{clean_title}</b> ({cat_type_disp}) - {len(labels)} labels"
        label_info = QLabel(info_text)
        
        # Trash Icon Button for Categories
        delete_btn = QPushButton()
        delete_btn.setFixedSize(24, 24)
        delete_btn.setFlat(True)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setToolTip(f"Remove '{cat_key}'")
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

# --- LeftPanel (File Management) ---
class LeftPanel(QWidget):
    """Defines the UI for the left panel (file management)."""
    
    SUPPORTED_EXTENSIONS = SUPPORTED_EXTENSIONS
    request_remove_item = pyqtSignal(object) 
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)

        layout = QVBoxLayout(self)
        # [MODIFIED] Reduced spacing to keep Action Tree close to Add Data
        layout.setSpacing(10) 

        # --- HEADER WITH UNDO/REDO BUTTONS ---
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Scenes / Clips")
        title.setObjectName("titleLabel")
        
        # Undo Button
        self.undo_button = QPushButton()
        self.undo_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        self.undo_button.setToolTip("Undo (Ctrl+Z)")
        self.undo_button.setFixedSize(28, 28)
        self.undo_button.setEnabled(False) 

        # Redo Button
        self.redo_button = QPushButton()
        self.redo_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        self.redo_button.setToolTip("Redo (Ctrl+Y)")
        self.redo_button.setFixedSize(28, 28)
        self.redo_button.setEnabled(False)

        header_layout.addWidget(title)
        header_layout.addStretch() 
        header_layout.addWidget(self.undo_button)
        header_layout.addWidget(self.redo_button)
        
        layout.addWidget(header_widget)
        # ---------------------------------------------

        self.action_tree = QTreeWidget()
        self.action_tree.setHeaderLabels(["Actions"])
        
        # Enable Custom Context Menu
        self.action_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.action_tree.customContextMenuRequested.connect(self._show_context_menu)
        
        top_button_layout = QVBoxLayout() 
        # [MODIFIED] Ensure zero bottom margin so Tree sits right against it
        top_button_layout.setContentsMargins(0, 0, 0, 0)
        # [MODIFIED] Added Spacing between "Import/Create" row and "Add Data" button
        top_button_layout.setSpacing(10) 
        
        row1 = QHBoxLayout()
        self.import_annotations_button = QPushButton("Import JSON") 
        self.create_json_button = QPushButton("Create JSON") 
        row1.addWidget(self.import_annotations_button)
        row1.addWidget(self.create_json_button)
        
        self.add_data_button = QPushButton("Add Data")
        
        top_button_layout.addLayout(row1)
        top_button_layout.addWidget(self.add_data_button)
        
        bottom_button_layout = QHBoxLayout()
        
        self.filter_label = QLabel("Filter:")
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Show All")
        self.filter_combo.addItem("Show Done")
        self.filter_combo.addItem("Show Not Done")
        self.filter_combo.setFixedWidth(120)
        
        bottom_button_layout.addWidget(self.filter_label)
        bottom_button_layout.addWidget(self.filter_combo)
        
        self.clear_button = QPushButton("Clear List")
        bottom_button_layout.addWidget(self.clear_button)
        bottom_button_layout.addStretch()
        
        layout.addLayout(top_button_layout)
        layout.addWidget(self.action_tree)
        layout.addLayout(bottom_button_layout)

        self.import_button = self.import_annotations_button 
        self.add_video_button = self.add_data_button 

    def _show_context_menu(self, position):
        item = self.action_tree.itemAt(position)
        if item:
            menu = QMenu()
            remove_action = QAction("Remove", self)
            remove_action.triggered.connect(lambda: self.request_remove_item.emit(item))
            menu.addAction(remove_action)
            menu.exec(self.action_tree.viewport().mapToGlobal(position))

    def add_action_item(self, name, path, explicit_files=None):
        action_item = QTreeWidgetItem(self.action_tree, [name])
        action_item.setData(0, Qt.ItemDataRole.UserRole, path)
        
        if explicit_files:
            for file_path in explicit_files:
                clip_name = os.path.basename(file_path)
                clip_item = QTreeWidgetItem(action_item, [clip_name])
                clip_item.setData(0, Qt.ItemDataRole.UserRole, file_path)
                
                if not os.path.exists(file_path):
                    clip_item.setForeground(0, QColor("red"))
                    clip_item.setToolTip(0, f"File not found: {file_path}")

        elif path and os.path.isdir(path):
            try:
                for sub_entry in sorted(os.scandir(path), key=lambda e: e.name):
                    if sub_entry.is_file() and sub_entry.name.lower().endswith(self.SUPPORTED_EXTENSIONS):
                        clip_item = QTreeWidgetItem(action_item, [os.path.basename(sub_entry.path)])
                        clip_item.setData(0, Qt.ItemDataRole.UserRole, sub_entry.path)
            except Exception as e:
                print(f"Error scanning directory {path}: {e}")
        
        return action_item

    def get_all_action_items(self):
        root = self.action_tree.invisibleRootItem()
        return [root.child(i) for i in range(root.childCount())]

# --- CenterPanel (Media Preview) ---
class CenterPanel(QWidget):
    """Defines the UI for the center panel (media preview)."""
    
    class ImageScrollArea(QScrollArea):
        def __init__(self, pixmap, parent=None):
            super().__init__(parent)
            self.pixmap = pixmap
            self.image_label = QLabel()
            self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setWidget(self.image_label)
            self.setWidgetResizable(True) 
            self.update_pixmap()

        def update_pixmap(self):
            if self.pixmap.isNull():
                self.image_label.setText("Image not loaded")
                return
            self.image_label.setPixmap(self.pixmap.scaled(
                self.viewport().size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

        def resizeEvent(self, event):
            super().resizeEvent(event)
            self.update_pixmap()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.view_controls = [] 
        
        layout = QVBoxLayout(self)

        title = QLabel("Media Preview")
        title.setObjectName("titleLabel")

        self.video_container = QWidget()
        self.video_layout = QVBoxLayout(self.video_container) 
        self.video_layout.setContentsMargins(0,0,0,0)
        
        control_layout = QHBoxLayout()
        self.play_button = QPushButton()
        self.play_button.setEnabled(False)
        self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

        self.multi_view_button = QPushButton("Sync-Play All Views")
        self.multi_view_button.setEnabled(False)

        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.multi_view_button)

        layout.addWidget(title)
        layout.addWidget(self.video_container, 1) 
        layout.addLayout(control_layout)

        self.show_single_view(None)

    def format_time(self, milliseconds):
        t = QTime(0, 0)
        t = t.addMSecs(milliseconds)
        return t.toString('mm:ss')

    def _setup_controls(self, view_control: VideoViewAndControl):
        player = view_control.player
        slider = view_control.slider
        player_id = id(player)

        player.positionChanged.connect(lambda pos: self.update_slider(player_id, pos))
        player.durationChanged.connect(lambda dur: self.update_duration(player_id, dur))
        slider.sliderMoved.connect(lambda value: self.seek_slider(player_id, value))
        
        self.view_controls.append(view_control)

    def _clear_video_layout(self):
        for vc in self.view_controls:
            vc.player.stop()
            vc.player.setVideoOutput(None)
            vc.player.deleteLater()
            vc.deleteLater()
        self.view_controls.clear()

        while self.video_layout.count():
            item = self.video_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                item.layout().deleteLater()
                
    def _get_control_by_id(self, player_id):
        return next((vc for vc in self.view_controls if id(vc.player) == player_id), None)

    def update_duration(self, player_id, duration):
        vc = self._get_control_by_id(player_id)
        if vc:
            vc.total_duration = duration
            vc.slider.setEnabled(duration > 0)
            current_pos = vc.player.position()
            current_time = self.format_time(current_pos)
            total_time = self.format_time(duration)
            vc.time_label.setText(f"{current_time} / {total_time}")
            
    def update_slider(self, player_id, position):
        vc = self._get_control_by_id(player_id)
        if vc and vc.total_duration > 0:
            total_duration = vc.total_duration
            
            if not vc.slider.isSliderDown():
                value = int((position / total_duration) * 1000)
                vc.slider.setValue(value)
            
            current_time = self.format_time(position)
            total_time = self.format_time(total_duration)
            vc.time_label.setText(f"{current_time} / {total_time}")
            
    def seek_slider(self, player_id, value):
        vc = self._get_control_by_id(player_id)
        if vc and vc.total_duration > 0:
            total_duration = vc.total_duration
            new_position = int((value / 1000) * total_duration)
            vc.player.setPosition(new_position)

    def toggle_play_pause(self):
        if not self.view_controls: return
        is_playing = self.view_controls[0].player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        
        for vc in self.view_controls:
            if is_playing: vc.player.pause()
            else: vc.player.play()

    def _media_state_changed(self, state):
        icon = QStyle.StandardPixmap.SP_MediaPause if state == QMediaPlayer.PlaybackState.PlayingState else QStyle.StandardPixmap.SP_MediaPlay
        self.play_button.setIcon(self.style().standardIcon(icon))

    def show_single_view(self, clip_path):
        self._clear_video_layout()
        
        if not clip_path or not os.path.exists(clip_path):
            self.play_button.setEnabled(False)
            msg = "No media selected or file not found."
            if clip_path:
                msg += f"\nPath: {clip_path}"
                
            placeholder = QLabel(msg)
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.video_layout.addWidget(placeholder)
            return

        ext = os.path.splitext(clip_path)[1].lower()

        if ext in ('.mp4', '.avi', '.mov', '.wav', '.mp3', '.aac'):
            view_control = VideoViewAndControl(clip_path)
            view_control.player.setSource(QUrl.fromLocalFile(clip_path))
            view_control.player.playbackStateChanged.connect(self._media_state_changed)
            self._setup_controls(view_control)

            self.video_layout.addWidget(view_control)

            self.play_button.setEnabled(True)
            if ext in ('.wav', '.mp3', '.aac'):
                 view_control.video_widget.setStyleSheet("background-color: black;")
            
            view_control.player.play()
        
        elif ext in ('.jpg', '.jpeg', '.png', '.bmp'):
            
            pixmap = QPixmap(clip_path)
            
            if pixmap.isNull():
                image_label = QLabel(f"Failed to load image:\n{os.path.basename(clip_path)}")
                image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.video_layout.addWidget(image_label)
            else:
                scroll_area = self.ImageScrollArea(pixmap)
                self.video_layout.addWidget(scroll_area)
            
            self.play_button.setEnabled(False)
            self._media_state_changed(QMediaPlayer.PlaybackState.StoppedState)

        else:
            placeholder = QLabel(f"Unsupported file type:\n{os.path.basename(clip_path)}")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.video_layout.addWidget(placeholder)
            self.play_button.setEnabled(False)


    def show_all_views(self, clip_paths):
        self._clear_video_layout()
        
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        
        num_clips = len(clip_paths)
        if num_clips == 0:
            return
            
        cols = 2 if num_clips > 1 else 1 
        rows = (num_clips + cols - 1) // cols

        for i, clip_path in enumerate(clip_paths):
            row = i // cols
            col = i % cols
            
            view_control = VideoViewAndControl(clip_path)
            view_control.player.setSource(QUrl.fromLocalFile(clip_path))
            self._setup_controls(view_control)
            
            grid_layout.addWidget(view_control, row, col)
            
            if i == 0:
                view_control.player.playbackStateChanged.connect(self._media_state_changed)
            
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(grid_widget)
        self.video_layout.addWidget(scroll_area)

        if self.view_controls:
            self.play_button.setEnabled(True)
            self.toggle_play_pause() 

# --- Helper Class: Dynamic Single Label Group ---
class DynamicSingleLabelGroup(QWidget):
    
    remove_category_signal = pyqtSignal(str) # Signal to request removal of this category (Head)
    remove_label_signal = pyqtSignal(str) # Signal to request removal of a specific label option
    value_changed = pyqtSignal(str, object) # [NEW] Signal to report value changes

    def __init__(self, label_head_name, label_type_definition, parent=None):
        super().__init__(parent)
        self.head_name = label_head_name
        self.definition = label_type_definition
        self.radio_buttons = {}
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True) 
        
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 5, 0, 5)

        # --- HEADER (Name + Trash Button) ---
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        # [MODIFIED] Display clean title
        self.label_title = QLabel(f"{self.head_name.replace('_', ' ').title()}:")
        self.label_title.setObjectName("subtitleLabel")
        
        self.trash_btn = QPushButton()
        self.trash_btn.setFixedSize(24, 24)
        self.trash_btn.setFlat(True)
        self.trash_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.trash_btn.setToolTip("Remove this category")
        self.trash_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.trash_btn.clicked.connect(self._on_remove_category_clicked)
        
        header_layout.addWidget(self.label_title)
        header_layout.addStretch()
        header_layout.addWidget(self.trash_btn)
        
        self.v_layout.addWidget(header_widget)
        
        # --- Labels Container ---
        self.radio_container = QWidget()
        self.radio_layout = QVBoxLayout(self.radio_container)
        self.radio_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.addWidget(self.radio_container)
        
        # --- Bottom Controls (Add New Label) ---
        self.manager_group = QGroupBox() 
        self.manager_group.setFlat(True)
        v_manager_layout = QVBoxLayout(self.manager_group)
        v_manager_layout.setContentsMargins(0, 10, 0, 5)
        
        h_add_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(f"New {self.head_name} type...")
        self.add_btn = QPushButton("Add")
        h_add_layout.addWidget(self.input_field, 1)
        h_add_layout.addWidget(self.add_btn)
        
        v_manager_layout.addLayout(h_add_layout)
        
        self.v_layout.addWidget(self.manager_group)

        self.update_radios(self.definition.get("labels", []))

    def _on_remove_category_clicked(self):
        self.remove_category_signal.emit(self.head_name)

    def update_radios(self, new_types):
        self.button_group.setExclusive(False)
        
        while self.radio_layout.count():
            item = self.radio_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.radio_buttons.clear()
        
        sorted_types = sorted(list(set(new_types)))
        for type_name in sorted_types: 
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 2, 0, 2)
            
            rb = QRadioButton(type_name)
            rb.clicked.connect(self._on_radio_clicked)

            self.radio_buttons[type_name] = rb
            self.button_group.addButton(rb)
            
            # [MODIFIED] Small Square X Button
            del_label_btn = QPushButton("×")
            del_label_btn.setFixedSize(20, 20)
            del_label_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_label_btn.setToolTip(f"Remove '{type_name}'")
            del_label_btn.setStyleSheet(get_square_remove_btn_style())
            
            del_label_btn.clicked.connect(lambda _, n=type_name: self.remove_label_signal.emit(n))
            
            row_layout.addWidget(rb)
            row_layout.addStretch()
            row_layout.addWidget(del_label_btn)
            
            self.radio_layout.addWidget(row_widget)
            
        self.button_group.setExclusive(True)
    
    def _on_radio_clicked(self):
        self.value_changed.emit(self.head_name, self.get_checked_label())

    def get_checked_label(self):
        checked_btn = self.button_group.checkedButton()
        return checked_btn.text() if checked_btn else None

    def set_checked_label(self, label_name):
        self.blockSignals(True)
        self.button_group.setExclusive(False)
        for rb in self.radio_buttons.values():
            rb.setChecked(False)
        self.button_group.setExclusive(True)
        
        if label_name in self.radio_buttons:
            self.radio_buttons[label_name].setChecked(True)
        self.blockSignals(False)

# --- Helper Class: Dynamic Multi Label Group ---
class DynamicMultiLabelGroup(QWidget):
    
    remove_category_signal = pyqtSignal(str) 
    remove_label_signal = pyqtSignal(str) 
    value_changed = pyqtSignal(str, object) 

    def __init__(self, label_head_name, label_type_definition, parent=None):
        super().__init__(parent)
        self.head_name = label_head_name
        self.definition = label_type_definition
        self.checkboxes = {}
        
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 5, 0, 5)

        # --- HEADER ---
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        # [MODIFIED] Display clean title
        self.label_title = QLabel(f"{self.head_name.replace('_', ' ').title()}:")
        self.label_title.setObjectName("subtitleLabel")
        
        self.trash_btn = QPushButton()
        self.trash_btn.setFixedSize(24, 24)
        self.trash_btn.setFlat(True)
        self.trash_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.trash_btn.setToolTip("Remove this category")
        self.trash_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.trash_btn.clicked.connect(self._on_remove_category_clicked)
        
        header_layout.addWidget(self.label_title)
        header_layout.addStretch()
        header_layout.addWidget(self.trash_btn)
        
        self.v_layout.addWidget(header_widget)
        
        # --- Checkbox Container ---
        self.checkbox_container = QWidget()
        self.checkbox_layout = QVBoxLayout(self.checkbox_container)
        self.checkbox_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.addWidget(self.checkbox_container)
        
        # --- Bottom Controls ---
        self.manager_group = QGroupBox() 
        self.manager_group.setFlat(True)
        h_layout = QHBoxLayout(self.manager_group)
        h_layout.setContentsMargins(0, 10, 0, 5)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(f"New {self.head_name} type...")
        self.add_btn = QPushButton("Add")
        
        h_layout.addWidget(self.input_field, 1)
        h_layout.addWidget(self.add_btn)
        
        self.v_layout.addWidget(self.manager_group) 

        self.update_checkboxes(self.definition.get("labels", []))

    def _on_remove_category_clicked(self):
        self.remove_category_signal.emit(self.head_name)

    def update_checkboxes(self, new_types):
        while self.checkbox_layout.count():
            item = self.checkbox_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            
        self.checkboxes.clear()
        
        for type_name in sorted(list(set(new_types))): 
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 2, 0, 2)

            cb = QCheckBox(type_name)
            cb.clicked.connect(self._on_box_clicked)

            self.checkboxes[type_name] = cb
            
            # [MODIFIED] Small Square X Button
            del_label_btn = QPushButton("×")
            del_label_btn.setFixedSize(20, 20)
            del_label_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_label_btn.setToolTip(f"Remove '{type_name}'")
            del_label_btn.setStyleSheet(get_square_remove_btn_style())
            
            del_label_btn.clicked.connect(lambda _, n=type_name: self.remove_label_signal.emit(n))

            row_layout.addWidget(cb)
            row_layout.addStretch()
            row_layout.addWidget(del_label_btn)

            self.checkbox_layout.addWidget(row_widget)
            
    def _on_box_clicked(self):
        self.value_changed.emit(self.head_name, self.get_checked_labels())

    def get_checked_labels(self):
        return [cb.text() for cb in self.checkboxes.values() if cb.isChecked()]
    
    def get_all_checkbox_labels(self):
        return self.checkboxes.items()

    def set_checked_labels(self, label_list):
        self.blockSignals(True)
        checked_set = set(label_list)
        for cb_name, cb in self.checkboxes.items():
            cb.setChecked(cb_name in checked_set)
        self.blockSignals(False)


# --- RightPanel (Annotation Only) ---
class RightPanel(QWidget):
    """Defines the UI for the right panel (Annotation Only)."""
    
    DEFAULT_TASK_NAME = "N/A (Please Import JSON)" 
    
    style_mode_changed = pyqtSignal(str) 
    add_head_clicked = pyqtSignal(str) 
    remove_head_clicked = pyqtSignal(str) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(400)
        
        self.label_groups = {} 

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Top Header ---
        header_widget = QWidget()
        header_h_layout = QHBoxLayout(header_widget)
        header_h_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Annotation")
        title.setObjectName("titleLabel")
        
        self.mode_toggle_button = QPushButton("Day Mode") 
        self.mode_toggle_button.setObjectName("modeToggleButton")
        self.mode_toggle_button.setFixedSize(QSize(100, 30))
        self.mode_toggle_button.clicked.connect(self._toggle_style_mode)

        header_h_layout.addWidget(title)
        header_h_layout.addStretch()
        header_h_layout.addWidget(self.mode_toggle_button)

        main_layout.addWidget(header_widget)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        content_widget = QWidget()
        scroll_area.setWidget(content_widget)

        layout = QVBoxLayout(content_widget)
        
        self.task_label = QLabel(f"Task: {self.DEFAULT_TASK_NAME}")
        self.task_label.setObjectName("subtitleLabel")
        layout.addWidget(self.task_label)

        # --- Annotation Content ---
        self.annotation_content_widget = QWidget()
        self.annotation_content_layout = QVBoxLayout(self.annotation_content_widget)
        self.annotation_content_layout.setContentsMargins(0, 0, 0, 0)

        # 1. Manual Annotation
        self.manual_group_box = QGroupBox("Manual Annotation")
        self.manual_group_box.setEnabled(False)
        manual_layout = QVBoxLayout(self.manual_group_box)
        
        self.dynamic_label_container = QWidget()
        self.dynamic_label_layout = QVBoxLayout(self.dynamic_label_container)
        self.dynamic_label_layout.setContentsMargins(0, 0, 0, 0)
        manual_layout.addWidget(self.dynamic_label_container)
        
        # --- Add Category Section at BOTTOM ---
        self.add_cat_container = QWidget()
        add_cat_layout = QHBoxLayout(self.add_cat_container)
        add_cat_layout.setContentsMargins(0, 20, 0, 10)
        
        self.new_head_input = QLineEdit()
        self.new_head_input.setPlaceholderText("New Category Name")
        
        self.add_head_btn = QPushButton("Add Category")
        self.add_head_btn.clicked.connect(self._emit_add_head_signal)
        
        add_cat_layout.addWidget(self.new_head_input, 1)
        add_cat_layout.addWidget(self.add_head_btn)
        
        manual_layout.addWidget(self.add_cat_container)
        # -------------------------------------------
        
        manual_layout.addStretch()
        manual_button_layout = QHBoxLayout()
        self.confirm_manual_button = QPushButton("Confirm Annotation")
        self.clear_manual_button = QPushButton("Clear Selection") 
        manual_button_layout.addWidget(self.confirm_manual_button)
        manual_button_layout.addWidget(self.clear_manual_button)
        manual_layout.addLayout(manual_button_layout) 
        
        self.annotation_content_layout.addWidget(self.manual_group_box) 

        layout.addWidget(self.annotation_content_widget) 


        # --- Bottom Controls ---
        layout.addStretch() 
        
        bottom_button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.export_button = QPushButton("Export") 
        
        self.save_button.setEnabled(False)
        self.export_button.setEnabled(False)
        
        bottom_button_layout.addWidget(self.save_button)
        bottom_button_layout.addWidget(self.export_button)
        
        layout.addLayout(bottom_button_layout)
        
        self.annotation_content_widget.setVisible(True)
        
        main_layout.addWidget(scroll_area, 1)

    def _toggle_style_mode(self):
        if self.mode_toggle_button.text() == "Day Mode":
            self.mode_toggle_button.setText("Night Mode")
            self.style_mode_changed.emit("Day") 
        else:
            self.mode_toggle_button.setText("Day Mode")
            self.style_mode_changed.emit("Night")
            
    def _emit_add_head_signal(self):
        head_name = self.new_head_input.text().strip()
        if head_name:
            self.add_head_clicked.emit(head_name)

    def _emit_remove_head_signal(self, head_name):
        self.remove_head_clicked.emit(head_name)


    def setup_dynamic_labels(self, labels_definition):
        while self.dynamic_label_layout.count():
            item = self.dynamic_label_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                pass
        
        self.label_groups.clear()
        
        for head_name, definition in labels_definition.items(): 
            if definition.get("type") == "single_label":
                group = DynamicSingleLabelGroup(head_name, definition, self.dynamic_label_container)
                group.remove_category_signal.connect(self._emit_remove_head_signal)
                self.label_groups[head_name] = group
                self.dynamic_label_layout.addWidget(group)
            elif definition.get("type") == "multi_label":
                group = DynamicMultiLabelGroup(head_name, definition, self.dynamic_label_container)
                group.remove_category_signal.connect(self._emit_remove_head_signal)
                self.label_groups[head_name] = group
                self.dynamic_label_layout.addWidget(group)

        self.dynamic_label_layout.addStretch()

    def get_manual_annotation(self):
        annotations = {}
        for head_name, group in self.label_groups.items():
            if isinstance(group, DynamicSingleLabelGroup):
                annotations[head_name] = group.get_checked_label()
            elif isinstance(group, DynamicMultiLabelGroup):
                annotations[head_name] = group.get_checked_labels()
        return annotations

    def clear_manual_selection(self):
        for group in self.label_groups.values():
            if isinstance(group, DynamicSingleLabelGroup):
                group.set_checked_label(None)
            elif isinstance(group, DynamicMultiLabelGroup):
                group.set_checked_labels([])

    def set_manual_annotation(self, data):
        self.clear_manual_selection()
        for head_name, label_data in data.items():
            if head_name in self.label_groups:
                group = self.label_groups[head_name]
                if isinstance(group, DynamicSingleLabelGroup):
                    if isinstance(label_data, str):
                        group.set_checked_label(label_data)
                elif isinstance(group, DynamicMultiLabelGroup):
                    if isinstance(label_data, list):
                        group.set_checked_labels(label_data)


class MainWindowUI(QWidget):
    """The main UI container that assembles all panels."""
    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QHBoxLayout(self)

        self.left_panel = LeftPanel()
        self.center_panel = CenterPanel()
        self.right_panel = RightPanel()

        main_layout.addWidget(self.left_panel)
        main_layout.addWidget(self.center_panel, 1)
        main_layout.addWidget(self.right_panel)
