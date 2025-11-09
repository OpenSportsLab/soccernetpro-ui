import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QHeaderView, QStyle,
    QProgressBar, QLabel, QTreeWidget, QTreeWidgetItem, QScrollArea, QSizePolicy,
    QGroupBox, QRadioButton, QButtonGroup, QComboBox, QLineEdit, QCheckBox,
    QSlider, QGridLayout 
)
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QTime 
from PyQt6.QtCharts import QChartView, QChart, QPieSeries
from PyQt6.QtGui import QPainter, QColor, QFont, QPen

# --- Helper Class: Wraps a single video and its controls ---
class VideoViewAndControl(QWidget):
    """Wraps a QVideoWidget and its QSlider/QLabel controls."""
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

# --- LeftPanel ---
class LeftPanel(QWidget):
    """Defines the UI for the left panel (file management)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)

        layout = QVBoxLayout(self)

        title = QLabel("Scenes / Clips")
        title.setObjectName("titleLabel")

        self.action_tree = QTreeWidget()
        self.action_tree.setHeaderLabels(["Actions"])
        
        top_button_layout = QHBoxLayout()
        self.import_annotations_button = QPushButton("Import Annotations") 
        self.add_video_button = QPushButton("Add Video")
        
        top_button_layout.addWidget(self.import_annotations_button)
        top_button_layout.addWidget(self.add_video_button)
        top_button_layout.addStretch()
        
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
        
        layout.addWidget(title)
        layout.addLayout(top_button_layout)
        layout.addWidget(self.action_tree)
        layout.addLayout(bottom_button_layout)

        self.import_button = self.import_annotations_button


    def add_action_item(self, name, path):
        """Adds a parent item for an action and its child clip items."""
        action_item = QTreeWidgetItem(self.action_tree, [name])
        action_item.setData(0, Qt.ItemDataRole.UserRole, path)
        for sub_entry in sorted(os.scandir(path), key=lambda e: e.name):
            if sub_entry.is_file() and sub_entry.name.lower().endswith(('.mp4', '.avi', '.mov')):
                clip_item = QTreeWidgetItem(action_item, [os.path.basename(sub_entry.path)])
                clip_item.setData(0, Qt.ItemDataRole.UserRole, sub_entry.path)
        
        return action_item

    def get_all_action_items(self):
        """Returns a list of all top-level action items."""
        root = self.action_tree.invisibleRootItem()
        return [root.child(i) for i in range(root.childCount())]

# --- CenterPanel ---
class CenterPanel(QWidget):
    """Defines the UI for the center panel (video preview)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.view_controls = [] 
        
        layout = QVBoxLayout(self)

        title = QLabel("Video Preview")
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
        """Converts milliseconds to an mm:ss format string."""
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
        """Finds the corresponding VideoViewAndControl instance by player_id."""
        return next((vc for vc in self.view_controls if id(vc.player) == player_id), None)

    def update_duration(self, player_id, duration):
        """Updates the total video duration and enables the slider."""
        vc = self._get_control_by_id(player_id)
        if vc:
            vc.total_duration = duration
            vc.slider.setEnabled(duration > 0)
            current_pos = vc.player.position()
            current_time = self.format_time(current_pos)
            total_time = self.format_time(duration)
            vc.time_label.setText(f"{current_time} / {total_time}")
            
    def update_slider(self, player_id, position):
        """Updates the slider position and time label when playback position changes."""
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
        """Sets the video playback position when the user drags the slider."""
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
        
        if clip_path:
            view_control = VideoViewAndControl(clip_path)
            view_control.player.setSource(QUrl.fromLocalFile(clip_path))
            view_control.player.playbackStateChanged.connect(self._media_state_changed)
            self._setup_controls(view_control)

            self.video_layout.addWidget(view_control)

            self.play_button.setEnabled(True)
            view_control.player.play()
        else:
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


# --- Helper Class: Dynamic Single Label Group (QRadioButton) ---
class DynamicSingleLabelGroup(QWidget):
    """Encapsulates the UI and management for a single_label classification head."""
    def __init__(self, label_head_name, label_type_definition, parent=None):
        super().__init__(parent)
        self.head_name = label_head_name
        self.definition = label_type_definition
        self.radio_buttons = {}
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True) 
        
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 5, 0, 5)

        # 1. Label Title (e.g., "Foul_type:")
        self.label_title = QLabel(f"{self.head_name.capitalize()}:")
        self.label_title.setObjectName("subtitleLabel")
        self.v_layout.addWidget(self.label_title)
        
        # 2. Radio Button Container
        self.radio_container = QWidget()
        self.radio_layout = QVBoxLayout(self.radio_container)
        self.radio_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.addWidget(self.radio_container)
        
        # 3. Type Management (LineEdit + Buttons)
        self.manager_group = QGroupBox() 
        self.manager_group.setFlat(True)
        h_layout = QHBoxLayout(self.manager_group)
        h_layout.setContentsMargins(0, 10, 0, 5)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(f"New {self.head_name} type...")
        self.add_btn = QPushButton("Add")
        self.remove_btn = QPushButton("Remove Selected") 
        
        h_layout.addWidget(self.input_field, 1)
        h_layout.addWidget(self.add_btn)
        h_layout.addWidget(self.remove_btn)
        self.v_layout.addWidget(self.manager_group)

        # Initialize buttons
        self.update_radios(self.definition.get("labels", []))

    def update_radios(self, new_types):
        """Rebuilds the radio buttons based on the new list of types."""
        self.button_group.setExclusive(False)
        
        for name, rb in self.radio_buttons.items():
            self.button_group.removeButton(rb)
            self.radio_layout.removeWidget(rb)
            rb.deleteLater()
            
        self.radio_buttons.clear()
        
        for type_name in sorted(list(set(new_types))): 
            rb = QRadioButton(type_name)
            self.radio_buttons[type_name] = rb
            self.button_group.addButton(rb)
            self.radio_layout.addWidget(rb)
            
        self.button_group.setExclusive(True)
        
    def get_checked_label(self):
        """Gets the text of the currently checked radio button."""
        checked_btn = self.button_group.checkedButton()
        return checked_btn.text() if checked_btn else None

    def set_checked_label(self, label_name):
        """Sets the checked state for the given label name."""
        self.button_group.setExclusive(False)
        for rb in self.radio_buttons.values():
            rb.setChecked(False)
        self.button_group.setExclusive(True)
        
        if label_name in self.radio_buttons:
            self.radio_buttons[label_name].setChecked(True)

# --- Helper Class: Dynamic Multi Label Group (QCheckBox) ---
class DynamicMultiLabelGroup(QWidget):
    """Encapsulates the UI and management for a multi_label classification head."""
    def __init__(self, label_head_name, label_type_definition, parent=None):
        super().__init__(parent)
        self.head_name = label_head_name
        self.definition = label_type_definition
        # Stores QCheckBox instances
        self.checkboxes = {}
        
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 5, 0, 5)

        # 1. Label Title
        self.label_title = QLabel(f"{self.head_name.capitalize()}:")
        self.label_title.setObjectName("subtitleLabel")
        self.v_layout.addWidget(self.label_title)
        
        # 2. Checkbox Container
        self.checkbox_container = QWidget()
        self.checkbox_layout = QVBoxLayout(self.checkbox_container)
        self.checkbox_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.addWidget(self.checkbox_container)
        
        # 3. Type Management (LineEdit + Buttons)
        self.manager_group = QGroupBox() 
        self.manager_group.setFlat(True)
        h_layout = QHBoxLayout(self.manager_group)
        h_layout.setContentsMargins(0, 10, 0, 5)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(f"New {self.head_name} type...")
        self.add_btn = QPushButton("Add")
        self.remove_btn = QPushButton("Remove Checked") 
        
        h_layout.addWidget(self.input_field, 1)
        h_layout.addWidget(self.add_btn)
        h_layout.addWidget(self.remove_btn)
        self.v_layout.addWidget(self.manager_group)

        # Initialize checkboxes
        self.update_checkboxes(self.definition.get("labels", []))

    def update_checkboxes(self, new_types):
        """Rebuilds the checkboxes based on the new list of types."""
        
        # Clear old checkboxes
        for name, cb in self.checkboxes.items():
            self.checkbox_layout.removeWidget(cb)
            cb.deleteLater()
            
        self.checkboxes.clear()
        
        # Create new checkboxes
        for type_name in sorted(list(set(new_types))): 
            cb = QCheckBox(type_name)
            self.checkboxes[type_name] = cb
            self.checkbox_layout.addWidget(cb)
            
    def get_checked_labels(self):
        """Gets the list of labels for all checked boxes."""
        return [cb.text() for cb in self.checkboxes.values() if cb.isChecked()]
    
    def get_all_checkbox_labels(self):
        """Gets all available checkbox labels and their states."""
        return self.checkboxes.items()

    def set_checked_labels(self, label_list):
        """Sets the checked state for checkboxes based on the input list."""
        checked_set = set(label_list)
        for cb_name, cb in self.checkboxes.items():
            cb.setChecked(cb_name in checked_set)


# --- RightPanel (Dynamic) ---
class RightPanel(QWidget):
    """Defines the UI for the right panel (Annotation & Analysis)."""
    
    DEFAULT_TASK_NAME = "N/A (Import JSON)" 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(400)
        
        # Core Dynamic Storage: Head Name -> DynamicLabelGroup Instance
        self.label_groups = {} 

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        main_layout.addWidget(scroll_area)

        content_widget = QWidget()
        scroll_area.setWidget(content_widget)

        layout = QVBoxLayout(content_widget)
        
        title = QLabel("Annotation & Analysis")
        title.setObjectName("titleLabel")
        layout.addWidget(title)
        
        # Task Label (Will be updated dynamically in main.py)
        self.task_label = QLabel(f"Task: {self.DEFAULT_TASK_NAME}")
        self.task_label.setObjectName("subtitleLabel")
        layout.addWidget(self.task_label)

        # --- 3. Annotation/Analysis Main Container ---
        self.annotation_content_widget = QWidget()
        self.annotation_content_layout = QVBoxLayout(self.annotation_content_widget)
        self.annotation_content_layout.setContentsMargins(0, 0, 0, 0)


        # --- 1. Manual Annotation Module (Always expanded) ---
        self.manual_group_box = QGroupBox("Manual Annotation")
        self.manual_group_box.setEnabled(False)
        manual_layout = QVBoxLayout(self.manual_group_box)
        
        # Dynamic label area container
        self.dynamic_label_container = QWidget()
        self.dynamic_label_layout = QVBoxLayout(self.dynamic_label_container)
        self.dynamic_label_layout.setContentsMargins(0, 0, 0, 0)
        manual_layout.addWidget(self.dynamic_label_container)
        
        # Confirmation/Clear buttons
        manual_layout.addStretch()
        manual_button_layout = QHBoxLayout()
        self.confirm_manual_button = QPushButton("Confirm Annotation")
        self.clear_manual_button = QPushButton("Clear Selection") 
        manual_button_layout.addWidget(self.confirm_manual_button)
        manual_button_layout.addWidget(self.clear_manual_button)
        manual_layout.addLayout(manual_button_layout) 
        
        self.annotation_content_layout.addWidget(self.manual_group_box) 

        # --- 2. Automated Analysis Module (Retains collapsible feature) ---
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
        
    def setup_dynamic_labels(self, labels_definition):
        """
        Creates dynamic UI elements based on 'labels' definition from JSON.
        """
        # Clear existing dynamic UI
        for group in self.label_groups.values():
            self.dynamic_label_layout.removeWidget(group)
            group.deleteLater()
        self.label_groups.clear()
        
        # Store and create new label groups
        for head_name, definition in labels_definition.items():
            if definition.get("type") == "single_label":
                group = DynamicSingleLabelGroup(head_name, definition, self.dynamic_label_container)
                self.label_groups[head_name] = group
                self.dynamic_label_layout.addWidget(group)
            elif definition.get("type") == "multi_label":
                group = DynamicMultiLabelGroup(head_name, definition, self.dynamic_label_container)
                self.label_groups[head_name] = group
                self.dynamic_label_layout.addWidget(group)

        self.dynamic_label_layout.addStretch()

    # --- Manual Annotation API ---
    def get_manual_annotation(self):
        """Gets current manual annotation values ({head_name: label_name/label_list, ...})."""
        annotations = {}
        for head_name, group in self.label_groups.items():
            if isinstance(group, DynamicSingleLabelGroup):
                annotations[head_name] = group.get_checked_label()
            elif isinstance(group, DynamicMultiLabelGroup):
                annotations[head_name] = group.get_checked_labels()
        return annotations

    def clear_manual_selection(self):
        """Clears all manual annotations (radio or checkbox selections)."""
        for group in self.label_groups.values():
            if isinstance(group, DynamicSingleLabelGroup):
                group.set_checked_label(None)
            elif isinstance(group, DynamicMultiLabelGroup):
                group.set_checked_labels([])

    def set_manual_annotation(self, data):
        """Sets the manual annotation based on the input data."""
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
        """Clears all UI elements in the automated analysis results area."""
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                item.layout().deleteLater()

    def update_results(self, result):
        """Dynamically populates the automated analysis results (only for single_label distribution)."""
        self.clear_results_ui()
        
        for head_name, data in result.items():
            # Only process single_label heads with distribution data
            if 'distribution' not in data or head_name not in self.label_groups or not isinstance(self.label_groups[head_name], DynamicSingleLabelGroup):
                continue

            dist = data['distribution']
            
            # 1. Result Title
            title = QLabel(f"{head_name.capitalize()} Prediction:")
            title.setObjectName("subtitleLabel")
            self.results_layout.addWidget(title)
            
            # 2. Top 2 Text Results
            sorted_dist = sorted(dist.items(), key=lambda item: item[1], reverse=True)
            
            if len(sorted_dist) > 0:
                label_1 = QLabel(f"1. {sorted_dist[0][0]} - {sorted_dist[0][1]:.1%}")
                self.results_layout.addWidget(label_1)
            
            if len(sorted_dist) > 1:
                label_2 = QLabel(f"2. {sorted_dist[1][0]} - {sorted_dist[1][1]:.1%}")
                self.results_layout.addWidget(label_2)

            # 3. Pie Chart
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
