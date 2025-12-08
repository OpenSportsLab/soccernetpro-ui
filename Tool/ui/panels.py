import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem,
    QLabel, QComboBox, QScrollArea, QGroupBox, QLineEdit, QMenu, QStyle, QGridLayout,
    QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QUrl, QTime
from PyQt6.QtGui import QAction, QColor, QPixmap
from PyQt6.QtMultimedia import QMediaPlayer

from .widgets import VideoViewAndControl, DynamicSingleLabelGroup, DynamicMultiLabelGroup
from utils import SUPPORTED_EXTENSIONS

class LeftPanel(QWidget):
    request_remove_item = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Scenes / Clips")
        title.setObjectName("titleLabel")
        self.undo_btn = QPushButton(); self.undo_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        self.undo_btn.setToolTip("Undo"); self.undo_btn.setFixedSize(28, 28); self.undo_btn.setEnabled(False)
        self.redo_btn = QPushButton(); self.redo_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        self.redo_btn.setToolTip("Redo"); self.redo_btn.setFixedSize(28, 28); self.redo_btn.setEnabled(False)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.undo_btn)
        header_layout.addWidget(self.redo_btn)
        layout.addWidget(header_widget)
        
        # Buttons
        top_button_layout = QVBoxLayout() 
        row1 = QHBoxLayout()
        self.import_btn = QPushButton("Import JSON")
        self.create_btn = QPushButton("Create JSON")
        row1.addWidget(self.import_btn); row1.addWidget(self.create_btn)
        self.add_data_btn = QPushButton("Add Data")
        top_button_layout.addLayout(row1)
        top_button_layout.addWidget(self.add_data_btn)
        layout.addLayout(top_button_layout)
        
        # Tree
        self.action_tree = QTreeWidget()
        self.action_tree.setHeaderLabels(["Actions"])
        self.action_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.action_tree.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.action_tree)
        
        # Filter & Clear
        bot = QHBoxLayout()
        self.filter_label = QLabel("Filter:")
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Show All", "Show Done", "Show Not Done"])
        self.filter_combo.setFixedWidth(120)
        self.clear_btn = QPushButton("Clear List")
        bot.addWidget(self.filter_label); bot.addWidget(self.filter_combo)
        bot.addWidget(self.clear_btn)
        bot.addStretch()
        layout.addLayout(bot)

    def _show_context_menu(self, pos):
        item = self.action_tree.itemAt(pos)
        if item:
            menu = QMenu()
            act = QAction("Remove", self)
            act.triggered.connect(lambda: self.request_remove_item.emit(item))
            menu.addAction(act)
            menu.exec(self.action_tree.viewport().mapToGlobal(pos))

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
                    if sub_entry.is_file() and sub_entry.name.lower().endswith(SUPPORTED_EXTENSIONS):
                        clip_item = QTreeWidgetItem(action_item, [os.path.basename(sub_entry.path)])
                        clip_item.setData(0, Qt.ItemDataRole.UserRole, sub_entry.path)
            except Exception as e:
                print(f"Error scanning directory {path}: {e}")
        return action_item


class CenterPanel(QWidget):
    
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
                self.viewport().size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
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
        layout.addWidget(title)

        self.video_container = QWidget()
        self.video_layout = QVBoxLayout(self.video_container) 
        self.video_layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.video_container, 1)
        
        # Play Controls
        control_layout = QHBoxLayout()
        self.play_btn = QPushButton()
        self.play_btn.setEnabled(False)
        self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.multi_view_btn = QPushButton("Sync-Play All Views")
        self.multi_view_btn.setEnabled(False)
        control_layout.addWidget(self.play_btn)
        control_layout.addWidget(self.multi_view_btn)
        layout.addLayout(control_layout)
        
        # Navigation
        nav_layout = QHBoxLayout()
        self.prev_action = QPushButton("Prev Action")
        self.prev_clip = QPushButton("Prev Clip")
        self.next_clip = QPushButton("Next Clip")
        self.next_action = QPushButton("Next Action")
        nav_layout.addWidget(self.prev_action)
        nav_layout.addWidget(self.prev_clip)
        nav_layout.addWidget(self.next_clip)
        nav_layout.addWidget(self.next_action)
        layout.addLayout(nav_layout)

    def _clear_video_layout(self):
        for vc in self.view_controls:
            vc.player.stop(); vc.player.setVideoOutput(None); vc.player.deleteLater(); vc.deleteLater()
        self.view_controls.clear()
        while self.video_layout.count():
            item = self.video_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            elif item.layout():
                while item.layout().count(): 
                    c = item.layout().takeAt(0)
                    if c.widget(): c.widget().deleteLater()
                item.layout().deleteLater()

    def _media_state_changed(self, state):
        icon = QStyle.StandardPixmap.SP_MediaPause if state == QMediaPlayer.PlaybackState.PlayingState else QStyle.StandardPixmap.SP_MediaPlay
        self.play_btn.setIcon(self.style().standardIcon(icon))

    def _setup_controls(self, view_control: VideoViewAndControl):
        # Helper to connect slider updates
        player = view_control.player
        slider = view_control.slider
        def update_dur(d):
            view_control.total_duration = d
            slider.setEnabled(d > 0)
            view_control.time_label.setText(f"{self._fmt(player.position())} / {self._fmt(d)}")
        def update_pos(p):
            if view_control.total_duration > 0 and not slider.isSliderDown():
                slider.setValue(int((p/view_control.total_duration)*1000))
            view_control.time_label.setText(f"{self._fmt(p)} / {self._fmt(view_control.total_duration)}")
        def seek(v):
            if view_control.total_duration > 0:
                player.setPosition(int((v/1000)*view_control.total_duration))
        player.durationChanged.connect(update_dur)
        player.positionChanged.connect(update_pos)
        slider.sliderMoved.connect(seek)
        self.view_controls.append(view_control)

    def _fmt(self, ms):
        t = QTime(0, 0); t = t.addMSecs(ms)
        return t.toString('mm:ss')

    def show_single_view(self, clip_path):
        self._clear_video_layout()
        if not clip_path or not os.path.exists(clip_path):
            self.play_btn.setEnabled(False)
            msg = f"No media selected or file not found.\nPath: {clip_path}" if clip_path else "No media selected"
            lbl = QLabel(msg); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.video_layout.addWidget(lbl)
            return

        ext = os.path.splitext(clip_path)[1].lower()
        if ext in ('.mp4', '.avi', '.mov', '.wav', '.mp3', '.aac'):
            vc = VideoViewAndControl(clip_path)
            vc.player.setSource(QUrl.fromLocalFile(clip_path))
            vc.player.playbackStateChanged.connect(self._media_state_changed)
            self._setup_controls(vc)
            self.video_layout.addWidget(vc)
            self.play_btn.setEnabled(True)
            if ext in ('.wav', '.mp3', '.aac'): vc.video_widget.setStyleSheet("background-color: black;")
            vc.player.play()
        elif ext in ('.jpg', '.jpeg', '.png', '.bmp'):
            pix = QPixmap(clip_path)
            if pix.isNull():
                lbl = QLabel(f"Failed to load image:\n{os.path.basename(clip_path)}"); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.video_layout.addWidget(lbl)
            else:
                self.video_layout.addWidget(self.ImageScrollArea(pix))
            self.play_btn.setEnabled(False)
            self._media_state_changed(QMediaPlayer.PlaybackState.StoppedState)
        else:
            lbl = QLabel(f"Unsupported file type:\n{os.path.basename(clip_path)}"); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.video_layout.addWidget(lbl)
            self.play_btn.setEnabled(False)

    def show_all_views(self, clip_paths):
        self._clear_video_layout()
        grid_widget = QWidget(); grid_layout = QGridLayout(grid_widget)
        num = len(clip_paths)
        if num == 0: return
        cols = 2 if num > 1 else 1
        
        for i, path in enumerate(clip_paths):
            vc = VideoViewAndControl(path)
            vc.player.setSource(QUrl.fromLocalFile(path))
            self._setup_controls(vc)
            grid_layout.addWidget(vc, i // cols, i % cols)
            if i == 0: vc.player.playbackStateChanged.connect(self._media_state_changed)
            
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(grid_widget)
        self.video_layout.addWidget(scroll)
        if self.view_controls:
            self.play_btn.setEnabled(True)
            self.toggle_play_pause()

    def toggle_play_pause(self):
        if not self.view_controls: return
        is_playing = self.view_controls[0].player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        for vc in self.view_controls:
            if is_playing: vc.player.pause()
            else: vc.player.play()

class RightPanel(QWidget):
    style_mode_changed = pyqtSignal(str)
    add_head_clicked = pyqtSignal(str)
    remove_head_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(400)
        self.label_groups = {}
        
        main_l = QVBoxLayout(self)
        main_l.setContentsMargins(0, 0, 0, 0)
        
        # Header
        h_widget = QWidget()
        h = QHBoxLayout(h_widget); h.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Annotation"); title.setObjectName("titleLabel")
        self.mode_btn = QPushButton("Day Mode"); self.mode_btn.setObjectName("modeToggleButton")
        self.mode_btn.setFixedSize(QSize(100, 30))
        self.mode_btn.clicked.connect(self._toggle_mode)
        h.addWidget(title); h.addStretch(); h.addWidget(self.mode_btn)
        main_l.addWidget(h_widget)
        
        # Scroll
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content = QWidget(); scroll.setWidget(content)
        self.c_layout = QVBoxLayout(content)
        
        self.task_label = QLabel("Task: N/A"); self.task_label.setObjectName("subtitleLabel")
        self.c_layout.addWidget(self.task_label)
        
        # Annotation Content
        self.content_widget = QWidget()
        self.annot_layout = QVBoxLayout(self.content_widget); self.annot_layout.setContentsMargins(0, 0, 0, 0)
        
        self.manual_box = QGroupBox("Manual Annotation"); self.manual_box.setEnabled(False)
        mbox_l = QVBoxLayout(self.manual_box)
        
        self.dyn_container = QWidget(); self.dyn_layout = QVBoxLayout(self.dyn_container); self.dyn_layout.setContentsMargins(0,0,0,0)
        mbox_l.addWidget(self.dyn_container)
        
        # Add Cat
        cat_w = QWidget(); cat_l = QHBoxLayout(cat_w); cat_l.setContentsMargins(0, 20, 0, 10)
        self.new_head_edit = QLineEdit(); self.new_head_edit.setPlaceholderText("New Category Name")
        self.add_head_btn = QPushButton("Add Category")
        self.add_head_btn.clicked.connect(lambda: self.add_head_clicked.emit(self.new_head_edit.text()))
        cat_l.addWidget(self.new_head_edit, 1); cat_l.addWidget(self.add_head_btn)
        mbox_l.addWidget(cat_w)
        
        mbox_l.addStretch()
        
        btns = QHBoxLayout()
        self.confirm_btn = QPushButton("Confirm Annotation")
        self.clear_sel_btn = QPushButton("Clear Selection")
        btns.addWidget(self.confirm_btn); btns.addWidget(self.clear_sel_btn)
        mbox_l.addLayout(btns)
        
        self.annot_layout.addWidget(self.manual_box)
        self.c_layout.addWidget(self.content_widget)
        self.c_layout.addStretch()
        main_l.addWidget(scroll, 1)
        
        # Bottom Save
        bot = QHBoxLayout()
        self.save_btn = QPushButton("Save"); self.save_btn.setEnabled(False)
        self.export_btn = QPushButton("Export"); self.export_btn.setEnabled(False)
        bot.addWidget(self.save_btn); bot.addWidget(self.export_btn)
        main_l.addLayout(bot)

    def _toggle_mode(self):
        txt = self.mode_btn.text()
        self.mode_btn.setText("Night Mode" if txt == "Day Mode" else "Day Mode")
        self.style_mode_changed.emit("Day" if txt == "Day Mode" else "Night")

    def setup_dynamic_labels(self, definitions):
        while self.dyn_layout.count():
            item = self.dyn_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        self.label_groups.clear()
        for head, dfn in definitions.items():
            if dfn.get("type") == "single_label":
                g = DynamicSingleLabelGroup(head, dfn, self.dyn_container)
                g.remove_category_signal.connect(self.remove_head_clicked.emit)
                self.label_groups[head] = g
                self.dyn_layout.addWidget(g)
            elif dfn.get("type") == "multi_label":
                g = DynamicMultiLabelGroup(head, dfn, self.dyn_container)
                g.remove_category_signal.connect(self.remove_head_clicked.emit)
                self.label_groups[head] = g
                self.dyn_layout.addWidget(g)
        self.dyn_layout.addStretch()

    def get_annotation(self):
        res = {}
        for head, g in self.label_groups.items():
            if isinstance(g, DynamicSingleLabelGroup): res[head] = g.get_checked_label()
            elif isinstance(g, DynamicMultiLabelGroup): res[head] = g.get_checked_labels()
        return res

    def clear_selection(self):
        for g in self.label_groups.values():
            if isinstance(g, DynamicSingleLabelGroup): g.set_checked_label(None)
            elif isinstance(g, DynamicMultiLabelGroup): g.set_checked_labels([])

    def set_annotation(self, data):
        self.clear_selection()
        for head, val in data.items():
            if head in self.label_groups:
                g = self.label_groups[head]
                if isinstance(g, DynamicSingleLabelGroup) and isinstance(val, str): g.set_checked_label(val)
                elif isinstance(g, DynamicMultiLabelGroup) and isinstance(val, list): g.set_checked_labels(val)


class MainWindowUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        self.left_panel = LeftPanel()
        self.center_panel = CenterPanel()
        self.right_panel = RightPanel()
        layout.addWidget(self.left_panel)
        layout.addWidget(self.center_panel, 1)
        layout.addWidget(self.right_panel)