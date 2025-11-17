import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QHeaderView, QStyle,
    QProgressBar, QLabel, QTreeWidget, QTreeWidgetItem, QScrollArea, QSizePolicy,
    QGroupBox, QRadioButton, QButtonGroup, QComboBox, QLineEdit, QCheckBox,
    QSlider, QGridLayout 
)
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QTime, QSize, pyqtSignal
from PyQt6.QtCharts import QChartView, QChart, QPieSeries
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QPixmap

# Define all supported media extensions for file filtering (Moved outside LeftPanel for easier import in main.py)
SUPPORTED_EXTENSIONS = (
    '.mp4', '.avi', '.mov',  # Video
    '.jpg', '.jpeg', '.png', '.bmp', # Image
    '.wav', '.mp3', '.aac'  # Audio
)

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

# --- LeftPanel (File Management) ---
class LeftPanel(QWidget):
    """Defines the UI for the left panel (file management)."""
    
    # Expose the global constant locally for easy access by its methods
    SUPPORTED_EXTENSIONS = SUPPORTED_EXTENSIONS
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)

        layout = QVBoxLayout(self)

        # English UI
        title = QLabel("Scenes / Clips")
        title.setObjectName("titleLabel")

        self.action_tree = QTreeWidget()
        self.action_tree.setHeaderLabels(["Actions"])
        
        top_button_layout = QHBoxLayout()
        self.import_annotations_button = QPushButton("Import Annotations") 
        # Renamed button text to English 'Add Data'
        self.add_data_button = QPushButton("Add Data")
        
        top_button_layout.addWidget(self.import_annotations_button)
        top_button_layout.addWidget(self.add_data_button)
        top_button_layout.addStretch()
        
        bottom_button_layout = QHBoxLayout()
        
        # English UI
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
        
        layout.addWidget(title)
        layout.addLayout(top_button_layout)
        layout.addWidget(self.action_tree)
        layout.addLayout(bottom_button_layout)

        self.import_button = self.import_annotations_button 
        # Alias for main.py compatibility
        # Keep add_video_button alias for backward compatibility with main.py's connect_signals
        self.add_video_button = self.add_data_button 


    def add_action_item(self, name, path):
        """Adds a parent item for an action and its child clip items."""
        action_item = QTreeWidgetItem(self.action_tree, [name])
        action_item.setData(0, Qt.ItemDataRole.UserRole, path)
        
        # If the path is a directory (Virtual Folder), scan its children
        if os.path.isdir(path):
            # Scan for all supported media types
            try:
                for sub_entry in sorted(os.scandir(path), key=lambda e: e.name):
                    # Use the class constant (which points to the global one)
                    if sub_entry.is_file() and sub_entry.name.lower().endswith(self.SUPPORTED_EXTENSIONS):
                        clip_item = QTreeWidgetItem(action_item, [os.path.basename(sub_entry.path)])
                        clip_item.setData(0, Qt.ItemDataRole.UserRole, sub_entry.path)
            except FileNotFoundError:
                 print(f"Warning: Directory not found during tree population: {path}")
            except Exception as e:
                print(f"Error scanning directory {path}: {e}")
        # If the path is a file (Single file import), do nothing, as it is the leaf node itself
        
        return action_item

    def get_all_action_items(self):
        """Returns a list of all top-level action items."""
        root = self.action_tree.invisibleRootItem()
        return [root.child(i) for i in range(root.childCount())]

# --- CenterPanel (Media Preview) ---
class CenterPanel(QWidget):
    """Defines the UI for the center panel (media preview)."""
    
    # Helper class to handle image scaling within a scroll area on resize
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
            # Scale pixmap to fit the viewport while maintaining aspect ratio
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

        # English UI
        title = QLabel("Media Preview")
        title.setObjectName("titleLabel")

        self.video_container = QWidget()
        self.video_layout = QVBoxLayout(self.video_container) 
        self.video_layout.setContentsMargins(0,0,0,0)
        
        control_layout = QHBoxLayout()
        self.play_button = QPushButton()
        self.play_button.setEnabled(False)
        self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

        # English UI
        self.multi_view_button = QPushButton("Sync-Play All Views")
        self.multi_view_button.setEnabled(False)

        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.multi_view_button)

        layout.addWidget(title)
        layout.addWidget(self.video_container, 1) 
        layout.addLayout(control_layout)

        self.show_single_view(None)

    def format_time(self, milliseconds):
        """Converts milliseconds to mm:ss format."""
        t = QTime(0, 0)
        t = t.addMSecs(milliseconds)
        return t.toString('mm:ss')

    def _setup_controls(self, view_control: VideoViewAndControl):
        """Sets up signal connections for a single VideoViewAndControl instance."""
        player = view_control.player
        slider = view_control.slider
        player_id = id(player)

        player.positionChanged.connect(lambda pos: self.update_slider(player_id, pos))
        player.durationChanged.connect(lambda dur: self.update_duration(player_id, dur))
        slider.sliderMoved.connect(lambda value: self.seek_slider(player_id, value))
        
        self.view_controls.append(view_control)

    def _clear_video_layout(self):
        # Cleans up all existing media and controls
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
        """Finds the VideoViewAndControl instance by player_id."""
        return next((vc for vc in self.view_controls if id(vc.player) == player_id), None)

    def update_duration(self, player_id, duration):
        """Updates total video duration and enables the Slider."""
        vc = self._get_control_by_id(player_id)
        if vc:
            vc.total_duration = duration
            vc.slider.setEnabled(duration > 0)
            current_pos = vc.player.position()
            current_time = self.format_time(current_pos)
            total_time = self.format_time(duration)
            vc.time_label.setText(f"{current_time} / {total_time}")
            
    def update_slider(self, player_id, position):
        """Updates the Slider position and time label when playback position changes."""
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
        """Sets the video playback position when the user drags the Slider."""
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
        """Displays a single media file (video, image, or audio)."""
        self._clear_video_layout()
        
        if not clip_path or not os.path.exists(clip_path):
            self.play_button.setEnabled(False)
            # English UI
            placeholder = QLabel("No media selected or file not found.")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.video_layout.addWidget(placeholder)
            return

        ext = os.path.splitext(clip_path)[1].lower()

        # -----------------------------------------------
        # Mode A: Video or Audio (using QMediaPlayer)
        # -----------------------------------------------
        if ext in ('.mp4', '.avi', '.mov', '.wav', '.mp3', '.aac'):
            view_control = VideoViewAndControl(clip_path)
            view_control.player.setSource(QUrl.fromLocalFile(clip_path))
            view_control.player.playbackStateChanged.connect(self._media_state_changed)
            self._setup_controls(view_control)

            self.video_layout.addWidget(view_control)

            self.play_button.setEnabled(True)
            # Hide video widget if it's only audio
            if ext in ('.wav', '.mp3', '.aac'):
                 view_control.video_widget.setStyleSheet("background-color: black;")
            
            view_control.player.play()
        
        # -----------------------------------------------
        # Mode B: Image (using QLabel and QPixmap)
        # -----------------------------------------------
        elif ext in ('.jpg', '.jpeg', '.png', '.bmp'):
            
            pixmap = QPixmap(clip_path)
            
            if pixmap.isNull():
                # English UI
                image_label = QLabel(f"Failed to load image:\n{os.path.basename(clip_path)}")
                image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.video_layout.addWidget(image_label)
            else:
                # Use ImageScrollArea for dynamic scaling and scrolling
                scroll_area = self.ImageScrollArea(pixmap)
                self.video_layout.addWidget(scroll_area)
            
            self.play_button.setEnabled(False) # Disable play button for static image
            self._media_state_changed(QMediaPlayer.PlaybackState.StoppedState) # Reset icon

        # -----------------------------------------------
        # Mode C: Unsupported file
        # -----------------------------------------------
        else:
            # English UI
            placeholder = QLabel(f"Unsupported file type:\n{os.path.basename(clip_path)}")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.video_layout.addWidget(placeholder)
            self.play_button.setEnabled(False)


    def show_all_views(self, clip_paths):
        """Displays multiple video views in a grid (only for video clips)."""
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


# --- Helper Class: Dynamic Single Label Group (QRadioButton) ---
class DynamicSingleLabelGroup(QWidget):
    """Wraps the UI and management for a single_label group."""
    def __init__(self, label_head_name, label_type_definition, parent=None):
        super().__init__(parent)
        self.head_name = label_head_name
        self.definition = label_type_definition
        self.radio_buttons = {}
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True) 
        
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 5, 0, 5)

        # English UI
        self.label_title = QLabel(f"{self.head_name.capitalize()}:")
        self.label_title.setObjectName("subtitleLabel")
        self.v_layout.addWidget(self.label_title)
        
        # Radio button container
        self.radio_container = QWidget()
        self.radio_layout = QVBoxLayout(self.radio_container)
        self.radio_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.addWidget(self.radio_container)
        
        # Type management (LineEdit + Buttons)
        self.manager_group = QGroupBox() 
        self.manager_group.setFlat(True)
        v_manager_layout = QVBoxLayout(self.manager_group)
        v_manager_layout.setContentsMargins(0, 10, 0, 5)
        
        # --- 1. Add New Label Widget ---
        h_add_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(f"New {self.head_name} type...")
        self.add_btn = QPushButton("Add")
        h_add_layout.addWidget(self.input_field, 1)
        h_add_layout.addWidget(self.add_btn)
        
        # --- 2. Remove Label Widget (QComboBox + Button) ---
        h_remove_layout = QHBoxLayout()
        self.remove_combo = QComboBox() 
        self.remove_combo.setPlaceholderText("Select label to remove")
        self.remove_btn = QPushButton("Remove Label") # English UI
        h_remove_layout.addWidget(self.remove_combo, 1)
        h_remove_layout.addWidget(self.remove_btn)
        
        # Add layouts to manager group
        v_manager_layout.addLayout(h_add_layout)
        v_manager_layout.addLayout(h_remove_layout)

        self.v_layout.addWidget(self.manager_group)

        # Initialize buttons
        self.update_radios(self.definition.get("labels", []))

    def update_radios(self, new_types):
        """Rebuilds radio buttons and updates the remove combo box based on the new list of types."""
        self.button_group.setExclusive(False)
        
        # 1. Update Radio Buttons
        for name, rb in self.radio_buttons.items():
            self.button_group.removeButton(rb)
            self.radio_layout.removeWidget(rb)
            rb.deleteLater()
            
        self.radio_buttons.clear()
        
        sorted_types = sorted(list(set(new_types)))
        for type_name in sorted_types: 
            rb = QRadioButton(type_name)
            self.radio_buttons[type_name] = rb
            self.button_group.addButton(rb)
            self.radio_layout.addWidget(rb)
            
        self.button_group.setExclusive(True)
        
        # 2. Update Remove ComboBox
        self.remove_combo.clear()
        # Add a placeholder/instruction item
        self.remove_combo.addItem("Select label to remove")
        self.remove_combo.setItemData(0, QSize(0,0), Qt.ItemDataRole.SizeHintRole) # Hide item to ensure user selects a real one
        for type_name in sorted_types:
            self.remove_combo.addItem(type_name)
        self.remove_combo.setCurrentIndex(0)

    def get_checked_label(self):
        """Returns the text of the currently checked item."""
        checked_btn = self.button_group.checkedButton()
        return checked_btn.text() if checked_btn else None

    def get_selected_label_to_remove(self):
        """Returns the text of the item selected in the removal combo box."""
        # Index 0 is the placeholder
        if self.remove_combo.currentIndex() > 0:
            return self.remove_combo.currentText()
        return None

    def set_checked_label(self, label_name):
        """Sets the currently checked item."""
        self.button_group.setExclusive(False)
        for rb in self.radio_buttons.values():
            rb.setChecked(False)
        self.button_group.setExclusive(True)
        
        if label_name in self.radio_buttons:
            self.radio_buttons[label_name].setChecked(True)

# --- Helper Class: Dynamic Multi Label Group (QCheckBox) ---
class DynamicMultiLabelGroup(QWidget):
    """Wraps the UI and management for a multi_label group."""
    def __init__(self, label_head_name, label_type_definition, parent=None):
        super().__init__(parent)
        self.head_name = label_head_name
        self.definition = label_type_definition
        self.checkboxes = {}
        
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 5, 0, 5)

        # English UI
        self.label_title = QLabel(f"{self.head_name.capitalize()}:")
        self.label_title.setObjectName("subtitleLabel")
        self.v_layout.addWidget(self.label_title)
        
        # Checkbox container
        self.checkbox_container = QWidget()
        self.checkbox_layout = QVBoxLayout(self.checkbox_container)
        self.checkbox_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.addWidget(self.checkbox_container)
        
        # Type management (LineEdit + Buttons)
        self.manager_group = QGroupBox() 
        self.manager_group.setFlat(True)
        h_layout = QHBoxLayout(self.manager_group)
        h_layout.setContentsMargins(0, 10, 0, 5)
        
        # --- Add New Label Widget ---
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(f"New {self.head_name} type...")
        self.add_btn = QPushButton("Add")
        
        # --- Remove Label Widget (QComboBox + Button) ---
        # For multi-label, removal is via checked boxes.
        self.remove_btn = QPushButton("Remove Checked") # English UI - Renamed for clarity
        
        # Group Add elements
        h_layout.addWidget(self.input_field, 1)
        h_layout.addWidget(self.add_btn)
        h_layout.addWidget(self.remove_btn) # Keep the remove button here
        
        self.v_layout.addWidget(self.manager_group) # Add the combined management group

        # Initialize checkboxes
        self.update_checkboxes(self.definition.get("labels", []))

    def update_checkboxes(self, new_types):
        """Rebuilds checkboxes based on the new list of types."""
        
        for name, cb in self.checkboxes.items():
            self.checkbox_layout.removeWidget(cb)
            cb.deleteLater()
            
        self.checkboxes.clear()
        
        for type_name in sorted(list(set(new_types))): 
            cb = QCheckBox(type_name)
            self.checkboxes[type_name] = cb
            self.checkbox_layout.addWidget(cb)
            
    def get_checked_labels(self):
        """Returns a list of labels for all checked checkboxes."""
        return [cb.text() for cb in self.checkboxes.values() if cb.isChecked()]
    
    def get_all_checkbox_labels(self):
        """Returns all available labels and their states."""
        return self.checkboxes.items()

    def set_checked_labels(self, label_list):
        """Sets the checked state based on the input list."""
        checked_set = set(label_list)
        for cb_name, cb in self.checkboxes.items():
            cb.setChecked(cb_name in checked_set)


# --- RightPanel (Annotation & Analysis) ---
class RightPanel(QWidget):
    """Defines the UI for the right panel (Annotation & Analysis)."""
    
    DEFAULT_TASK_NAME = "N/A (Please Import JSON)" 
    
    # Signal to notify main.py to change the stylesheet
    style_mode_changed = pyqtSignal(str) 
    # New signals for managing label heads
    add_head_clicked = pyqtSignal(str) 
    remove_head_clicked = pyqtSignal(str) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(400)
        
        self.label_groups = {} 

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Top Header and Mode Toggle Container ---
        header_widget = QWidget()
        header_h_layout = QHBoxLayout(header_widget)
        header_h_layout.setContentsMargins(0, 0, 0, 0)

        # English UI
        title = QLabel("Annotation & Analysis")
        title.setObjectName("titleLabel")
        
        # Mode toggle button (English UI)
        self.mode_toggle_button = QPushButton("Day Mode") 
        self.mode_toggle_button.setObjectName("modeToggleButton")
        self.mode_toggle_button.setFixedSize(QSize(100, 30))
        self.mode_toggle_button.clicked.connect(self._toggle_style_mode)

        header_h_layout.addWidget(title)
        header_h_layout.addStretch()
        header_h_layout.addWidget(self.mode_toggle_button)

        main_layout.addWidget(header_widget)
        # --- End Top Header ---


        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        content_widget = QWidget()
        scroll_area.setWidget(content_widget)

        layout = QVBoxLayout(content_widget)
        
        # Task Label (updated dynamically in main.py)
        self.task_label = QLabel(f"Task: {self.DEFAULT_TASK_NAME}")
        self.task_label.setObjectName("subtitleLabel")
        layout.addWidget(self.task_label)

        # --- NEW: Label Head Management ---
        # English UI
        self.head_manager_group = QGroupBox("Add/Remove Category") # Renamed title
        self.head_manager_group.setCheckable(False)
        self.head_manager_group.setChecked(True)
        head_manager_layout = QVBoxLayout(self.head_manager_group)
        
        # --- Row 1: Add Category ---
        h_add_head_layout = QHBoxLayout()
        self.new_head_input = QLineEdit()
        self.new_head_input.setPlaceholderText("Enter category name")
        
        self.add_head_btn = QPushButton("Add Category")
        self.add_head_btn.clicked.connect(self._emit_add_head_signal)
        
        h_add_head_layout.addWidget(self.new_head_input, 1)
        h_add_head_layout.addWidget(self.add_head_btn)

        # --- Row 2: Remove Category (using QComboBox) ---
        h_remove_head_layout = QHBoxLayout()
        # Dropdown for selecting category to remove
        self.remove_head_combo = QComboBox() 
        self.remove_head_combo.setPlaceholderText("Select category to remove")
        
        self.remove_head_btn = QPushButton("Remove Category")
        self.remove_head_btn.clicked.connect(self._emit_remove_head_signal)
        
        h_remove_head_layout.addWidget(self.remove_head_combo, 1)
        h_remove_head_layout.addWidget(self.remove_head_btn)
        
        head_manager_layout.addLayout(h_add_head_layout)
        head_manager_layout.addLayout(h_remove_head_layout) 
        
        layout.addWidget(self.head_manager_group)
        # --- END NEW: Label Head Management ---

        # --- 3. Annotation/Analysis Main Container ---
        self.annotation_content_widget = QWidget()
        self.annotation_content_layout = QVBoxLayout(self.annotation_content_widget)
        self.annotation_content_layout.setContentsMargins(0, 0, 0, 0)


        # --- 1. Manual Annotation Module ---
        # English UI
        self.manual_group_box = QGroupBox("Manual Annotation")
        self.manual_group_box.setEnabled(False)
        manual_layout = QVBoxLayout(self.manual_group_box)
        
        # Dynamic label area container
        self.dynamic_label_container = QWidget()
        self.dynamic_label_layout = QVBoxLayout(self.dynamic_label_container)
        self.dynamic_label_layout.setContentsMargins(0, 0, 0, 0)
        manual_layout.addWidget(self.dynamic_label_container)
        
        # Confirm/Clear buttons (English UI)
        manual_layout.addStretch()
        manual_button_layout = QHBoxLayout()
        self.confirm_manual_button = QPushButton("Confirm Annotation")
        self.clear_manual_button = QPushButton("Clear Selection") 
        manual_button_layout.addWidget(self.confirm_manual_button)
        manual_button_layout.addWidget(self.clear_manual_button)
        manual_layout.addLayout(manual_button_layout) 
        
        self.annotation_content_layout.addWidget(self.manual_group_box) 

        # --- 2. Automated Analysis Module ---
        # English UI
        self.auto_group_box = QGroupBox("Automated Annotation")
        self.auto_group_box.setCheckable(True) 
        self.auto_group_box.setChecked(False)
        auto_layout = QVBoxLayout(self.auto_group_box)

        self.start_button = QPushButton("Analyze Selected Scene")
        self.start_button.setObjectName("startButton")
        self.start_button.setEnabled(False)
        auto_layout.addWidget(self.start_button)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        auto_layout.addWidget(self.progress_bar)

        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget) 
        self.results_layout.setContentsMargins(0, 10, 0, 0)
        self.results_widget.setVisible(False)
        
        auto_layout.addWidget(self.results_widget)
        self.annotation_content_layout.addWidget(self.auto_group_box) 
        
        layout.addWidget(self.annotation_content_widget) 


        # --- 4. Bottom Controls ---
        layout.addStretch() 
        
        bottom_button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save (JSON)")
        self.export_button = QPushButton("Save As... (JSON)") 
        
        self.save_button.setEnabled(False)
        self.export_button.setEnabled(False)
        
        bottom_button_layout.addWidget(self.save_button)
        bottom_button_layout.addWidget(self.export_button)
        
        layout.addLayout(bottom_button_layout)
        
        self.annotation_content_widget.setVisible(True)
        
        main_layout.addWidget(scroll_area, 1)

    def _toggle_style_mode(self):
        """Toggles Day/Night mode and emits a signal."""
        if self.mode_toggle_button.text() == "Day Mode":
            self.mode_toggle_button.setText("Night Mode")
            self.style_mode_changed.emit("Day") 
        else:
            self.mode_toggle_button.setText("Day Mode")
            self.style_mode_changed.emit("Night")
            
    def _emit_add_head_signal(self):
        """Emits the signal with the text from the input field."""
        head_name = self.new_head_input.text().strip()
        if head_name:
            self.add_head_clicked.emit(head_name)

    def _emit_remove_head_signal(self):
        """Emits the signal with the text from the removal combo box."""
        head_name = self.remove_head_combo.currentText()
        if head_name and self.remove_head_combo.currentIndex() > 0: # Ensure not placeholder
            self.remove_head_clicked.emit(head_name)


    def setup_dynamic_labels(self, labels_definition):
        """Creates dynamic UI elements based on 'labels' definition in JSON and updates comboboxes."""
        
        # 1. Clear existing dynamic groups
        for group in self.label_groups.values():
            self.dynamic_label_layout.removeWidget(group)
            group.deleteLater()
        self.label_groups.clear()
        
        category_names = []
        
        # 2. Re-add groups based on the updated dictionary order
        for head_name, definition in labels_definition.items(): 
            category_names.append(head_name)
            if definition.get("type") == "single_label":
                group = DynamicSingleLabelGroup(head_name, definition, self.dynamic_label_container)
                self.label_groups[head_name] = group
                self.dynamic_label_layout.addWidget(group)
            elif definition.get("type") == "multi_label":
                group = DynamicMultiLabelGroup(head_name, definition, self.dynamic_label_container)
                self.label_groups[head_name] = group
                self.dynamic_label_layout.addWidget(group)

        self.dynamic_label_layout.addStretch()
        
        # 3. Update Category Removal ComboBox
        self.remove_head_combo.clear()
        self.remove_head_combo.addItem("Select category to remove") # Placeholder
        # Use an empty size hint to make the placeholder effectively hidden/unselectable as data
        self.remove_head_combo.setItemData(0, QSize(0,0), Qt.ItemDataRole.SizeHintRole)
        for name in sorted(category_names):
            self.remove_head_combo.addItem(name)
        self.remove_head_combo.setCurrentIndex(0) # Select placeholder

    # --- Manual Annotation API ---
    def get_manual_annotation(self):
        """Retrieves the current manual annotation values."""
        annotations = {}
        for head_name, group in self.label_groups.items():
            if isinstance(group, DynamicSingleLabelGroup):
                annotations[head_name] = group.get_checked_label()
            elif isinstance(group, DynamicMultiLabelGroup):
                annotations[head_name] = group.get_checked_labels()
        return annotations

    def clear_manual_selection(self):
        """Clears all manual annotation selections."""
        for group in self.label_groups.values():
            if isinstance(group, DynamicSingleLabelGroup):
                group.set_checked_label(None)
            elif isinstance(group, DynamicMultiLabelGroup):
                group.set_checked_labels([])

    def set_manual_annotation(self, data):
        """Sets the manual annotation based on the provided data."""
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

    # --- Automated Analysis Results UI API ---
    def clear_results_ui(self):
        """Cleans up the automated analysis results area."""
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                item.layout().deleteLater()

    def update_results(self, result):
        """Dynamically populates automated analysis results (single_label distribution only)."""
        self.clear_results_ui()
        
        for head_name, data in result.items():
            if 'distribution' not in data or head_name not in self.label_groups or not isinstance(self.label_groups[head_name], DynamicSingleLabelGroup):
                continue

            dist = data['distribution']
            
            # English UI
            title = QLabel(f"{head_name.capitalize()} Prediction:")
            title.setObjectName("subtitleLabel")
            self.results_layout.addWidget(title)
            
            # Top 2 text results
            sorted_dist = sorted(dist.items(), key=lambda item: item[1], reverse=True)
            
            if len(sorted_dist) > 0:
                label_1 = QLabel(f"1. {sorted_dist[0][0]} - {sorted_dist[0][1]:.1%}")
                self.results_layout.addWidget(label_1)
            
            if len(sorted_dist) > 1:
                label_2 = QLabel(f"2. {sorted_dist[1][0]} - {sorted_dist[1][1]:.1%}")
                self.results_layout.addWidget(label_2)

            # Pie Chart
            chart_view = QChartView()
            chart = self._create_pie_chart(dist, f"{head_name.capitalize()} Distribution")
            chart_view.setChart(chart)
            chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            chart_view.setMinimumHeight(250)
            self.results_layout.addWidget(chart_view)

    def _create_pie_chart(self, distribution, title):
        """Creates a QChart Pie Chart from a distribution dictionary."""
        series = QPieSeries()
        series.setHoleSize(0.35)

        sorted_dist = sorted(distribution.items(), key=lambda item: item[1], reverse=True)
        
        for i, (label, value) in enumerate(sorted_dist):
            slice = series.append(label, value)
            slice.setLabelVisible(False)
            if i == 0:
                slice.setExploded(True)
                pen = QPen(QColor("#d0d0d0"), 2)
                slice.setPen(pen)

        def on_hover(slice, state):
            if state:
                label_font = QFont("Arial", 8)
                slice.setLabelFont(label_font)
                slice.setLabelBrush(QColor("#ffffff"))
                slice.setLabel(f"{slice.label()} ({slice.percentage():.1%})")
                slice.setLabelVisible(True)
            else:
                slice.setLabelVisible(False)
        series.hovered.connect(on_hover)

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle(title)
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.setTheme(QChart.ChartTheme.ChartThemeDark)
        
        legend = chart.legend()
        legend.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        chart.setBackgroundBrush(QColor("#2E2E2E"))
        title_font = QFont("Arial", 12, QFont.Weight.Bold)
        chart.setTitleFont(title_font)
        chart.setTitleBrush(QColor("#f0f0f0"))
        
        legend_font = legend.font()
        legend_font.setPointSize(9)
        legend.setFont(legend_font)
        legend.setLabelColor(QColor("#f0f0f0"))

        for marker in legend.markers():
            marker.setLabel(marker.slice().label())

        return chart


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
