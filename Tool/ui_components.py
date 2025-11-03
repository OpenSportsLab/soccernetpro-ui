import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QHeaderView, QStyle,
    QProgressBar, QLabel, QTreeWidget, QTreeWidgetItem, QScrollArea, QSizePolicy,
    QGroupBox, QRadioButton, QButtonGroup, QComboBox,
    QSlider, QGridLayout # 导入 QGridLayout
)
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QTime # 导入 QTime
from PyQt6.QtCharts import QChartView, QChart, QPieSeries
from PyQt6.QtGui import QPainter, QColor, QFont, QPen

# --- 辅助类: 封装单个视频和其控制条 ---
class VideoViewAndControl(QWidget):
    """将一个 QVideoWidget 和其 QSlider/QLabel 封装在一起的 Widget。"""
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
        # 修改点：只显示初始时间，不显示文件名
        self.time_label = QLabel(f"00:00 / 00:00")
        
        # Layout
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        
        self.v_layout.addWidget(self.video_widget, 1) # Video takes up space
        
        h_control_layout = QHBoxLayout()
        # 调整 QLabel 宽度以适应时间，防止挤压 Slider
        self.time_label.setFixedWidth(100) 
        h_control_layout.addWidget(self.time_label)
        h_control_layout.addWidget(self.slider)
        self.v_layout.addLayout(h_control_layout)
        
        # Data and Connections (to be set by CenterPanel)
        self.total_duration = 0

# --- LeftPanel (不变) ---
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
        
        # 1. 顶部按钮布局 (只保留 Import Annotations)
        top_button_layout = QHBoxLayout()
        self.import_annotations_button = QPushButton("Import Annotations") 
        
        top_button_layout.addWidget(self.import_annotations_button)
        top_button_layout.addStretch()
        
        # 2. 底部按钮布局 (Filter & Clear List)
        bottom_button_layout = QHBoxLayout()
        
        # --- 新增筛选器 ---
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
        
        # 3. 组装布局
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

# --- CenterPanel (已修改) ---
class CenterPanel(QWidget):
    """Defines the UI for the center panel (video preview)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.view_controls = []  # List of VideoViewAndControl instances
        
        layout = QVBoxLayout(self)

        title = QLabel("Video Preview")
        title.setObjectName("titleLabel")

        # 视频/时间条的主容器
        self.video_container = QWidget()
        self.video_layout = QVBoxLayout(self.video_container) # 使用 QVBoxLayout 作为切换容器
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
        layout.addWidget(self.video_container, 1) # Video container takes most space
        layout.addLayout(control_layout)

        self.show_single_view(None)

    # --- 时间工具函数 ---
    def format_time(self, milliseconds):
        """将毫秒转换为 mm:ss 格式的字符串"""
        t = QTime(0, 0)
        t = t.addMSecs(milliseconds)
        return t.toString('mm:ss')

    # --- 进度条连接和逻辑 ---
    def _setup_controls(self, view_control: VideoViewAndControl):
        """为单个 VideoViewAndControl 实例设置信号连接"""
        player = view_control.player
        slider = view_control.slider
        player_id = id(player)

        # 设置连接
        player.positionChanged.connect(lambda pos: self.update_slider(player_id, pos))
        player.durationChanged.connect(lambda dur: self.update_duration(player_id, dur))
        slider.sliderMoved.connect(lambda value: self.seek_slider(player_id, value))
        
        self.view_controls.append(view_control)

    def _clear_video_layout(self):
        # 停止所有播放器并清除控件
        for vc in self.view_controls:
            vc.player.stop()
            vc.player.setVideoOutput(None)
            vc.player.deleteLater()
            vc.deleteLater()
        self.view_controls.clear()

        # 清除主布局中的所有控件/布局
        while self.video_layout.count():
            item = self.video_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # 递归删除布局中的所有控件
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                item.layout().deleteLater()
                
    # --- 进度条更新逻辑 ---
    def _get_control_by_id(self, player_id):
        """通过 player_id 查找对应的 VideoViewAndControl 实例"""
        return next((vc for vc in self.view_controls if id(vc.player) == player_id), None)

    def update_duration(self, player_id, duration):
        """更新视频总时长，并启用 Slider。"""
        vc = self._get_control_by_id(player_id)
        if vc:
            vc.total_duration = duration
            vc.slider.setEnabled(duration > 0)
            
            # 修改点：只显示时间
            current_pos = vc.player.position()
            current_time = self.format_time(current_pos)
            total_time = self.format_time(duration)
            vc.time_label.setText(f"{current_time} / {total_time}")
            
    def update_slider(self, player_id, position):
        """当播放位置变化时，更新 Slider 的位置和时间 Label。"""
        vc = self._get_control_by_id(player_id)
        if vc and vc.total_duration > 0:
            total_duration = vc.total_duration
            
            # 只有当用户没有拖动滑块时才自动更新滑块位置
            if not vc.slider.isSliderDown():
                value = int((position / total_duration) * 1000)
                vc.slider.setValue(value)
            
            # 修改点：只显示时间
            current_time = self.format_time(position)
            total_time = self.format_time(total_duration)
            vc.time_label.setText(f"{current_time} / {total_time}")
            
    def seek_slider(self, player_id, value):
        """当用户拖动 Slider 时，设置视频播放位置 (pos)。"""
        vc = self._get_control_by_id(player_id)
        if vc and vc.total_duration > 0:
            total_duration = vc.total_duration
            # 计算新的播放位置 (毫秒)
            new_position = int((value / 1000) * total_duration)
            vc.player.setPosition(new_position)


    # --- 播放逻辑 (保持同步) ---
    def toggle_play_pause(self):
        if not self.view_controls: return
        # 总是检查第一个播放器状态来同步播放按钮图标
        is_playing = self.view_controls[0].player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        
        # 同步播放/暂停状态
        for vc in self.view_controls:
            if is_playing: vc.player.pause()
            else: vc.player.play()

    def _media_state_changed(self, state):
        icon = QStyle.StandardPixmap.SP_MediaPause if state == QMediaPlayer.PlaybackState.PlayingState else QStyle.StandardPixmap.SP_MediaPlay
        self.play_button.setIcon(self.style().standardIcon(icon))

    # --- 视图切换逻辑 ---
    def show_single_view(self, clip_path):
        self._clear_video_layout()
        
        if clip_path:
            # 1. 创建封装控件
            view_control = VideoViewAndControl(clip_path)
            
            # 2. 设置播放源和连接
            view_control.player.setSource(QUrl.fromLocalFile(clip_path))
            view_control.player.playbackStateChanged.connect(self._media_state_changed)
            self._setup_controls(view_control)

            # 3. 添加到主布局
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
            
        cols = 2 if num_clips > 1 else 1 # 默认使用2列布局，除非只有一个视频
        rows = (num_clips + cols - 1) // cols

        for i, clip_path in enumerate(clip_paths):
            row = i // cols
            col = i % cols
            
            # 1. 创建封装控件
            view_control = VideoViewAndControl(clip_path)
            
            # 2. 设置播放源和连接
            view_control.player.setSource(QUrl.fromLocalFile(clip_path))
            self._setup_controls(view_control)
            
            # 3. 添加到网格布局
            grid_layout.addWidget(view_control, row, col)
            
            # 确保只有第一个视频连接到状态变化，避免图标闪烁
            if i == 0:
                view_control.player.playbackStateChanged.connect(self._media_state_changed)
            
        # 将网格容器添加到主布局
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(grid_widget)
        self.video_layout.addWidget(scroll_area)

        if self.view_controls:
            self.play_button.setEnabled(True)
            self.toggle_play_pause() # 开始播放


class RightPanel(QWidget):
    """Defines the UI for the right panel (Annotation & Analysis)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(400)
        
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

        # --- 1. 手动标注模块 ---
        self.manual_group_box = QGroupBox("Manual Annotation")
        self.manual_group_box.setCheckable(True)
        self.manual_group_box.setChecked(False)
        self.manual_group_box.setEnabled(False)
        manual_layout = QVBoxLayout(self.manual_group_box)

        foul_label = QLabel("Foul Type:")
        foul_label.setObjectName("subtitleLabel")
        manual_layout.addWidget(foul_label)
        
        self.foul_button_group = QButtonGroup(self)
        self.foul_radio_buttons = {}
        foul_types = [
            "Tackling", "Standing Tackling", "Holding", "Pushing", 
            "Challenge", "Elbowing", "High Leg", "Dive"
        ]
        for foul in foul_types:
            rb = QRadioButton(foul)
            self.foul_radio_buttons[foul] = rb
            self.foul_button_group.addButton(rb)
            manual_layout.addWidget(rb)

        severity_label = QLabel("Severity:")
        severity_label.setObjectName("subtitleLabel")
        manual_layout.addWidget(severity_label, 0, Qt.AlignmentFlag.AlignTop)
        
        self.sev_button_group = QButtonGroup(self)
        self.sev_radio_buttons = {}
        sev_types = ["Offence + Red Card", "Offence + Yellow Card", "Offence + No Card", "No Offence"]
        for sev in sev_types:
            rb = QRadioButton(sev)
            self.sev_radio_buttons[sev] = rb
            self.sev_button_group.addButton(rb)
            manual_layout.addWidget(rb)
        
        manual_layout.addStretch()

        manual_button_layout = QHBoxLayout()
        self.confirm_manual_button = QPushButton("Confirm Annotation")
        self.clear_manual_button = QPushButton("Clear Selection") 
        manual_button_layout.addWidget(self.confirm_manual_button)
        manual_button_layout.addWidget(self.clear_manual_button)
        manual_layout.addLayout(manual_button_layout) 
        
        layout.addWidget(self.manual_group_box)

        # --- 2. 自动分析模块 ---
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
        results_layout = QVBoxLayout(self.results_widget)
        results_layout.setContentsMargins(0, 10, 0, 0)
        self.results_widget.setVisible(False)

        foul_type_title = QLabel("Foul Type Prediction:")
        foul_type_title.setObjectName("subtitleLabel")
        self.foul_type_1_label = QLabel("1. -")
        self.foul_type_2_label = QLabel("2. -")
        
        severity_title = QLabel("Severity Prediction:")
        severity_title.setObjectName("subtitleLabel")
        self.severity_1_label = QLabel("1. -")
        self.severity_2_label = QLabel("2. -")

        self.foul_chart_view = QChartView()
        self.severity_chart_view = QChartView()
        self.foul_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.severity_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.foul_chart_view.setMinimumHeight(250)
        self.severity_chart_view.setMinimumHeight(250)
        
        results_layout.addWidget(foul_type_title)
        results_layout.addWidget(self.foul_type_1_label)
        results_layout.addWidget(self.foul_type_2_label)
        results_layout.addWidget(self.foul_chart_view)
        results_layout.addWidget(severity_title)
        results_layout.addWidget(self.severity_1_label)
        results_layout.addWidget(self.severity_2_label)
        results_layout.addWidget(self.severity_chart_view)
        
        auto_layout.addWidget(self.results_widget)
        layout.addWidget(self.auto_group_box)

        # --- 3. 底部控件 (重构) ---
        layout.addStretch() 
        
        bottom_button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save (JSON)")
        self.export_button = QPushButton("Save As... (JSON)") 
        
        self.save_button.setEnabled(False)
        self.export_button.setEnabled(False)
        
        bottom_button_layout.addWidget(self.save_button)
        bottom_button_layout.addWidget(self.export_button)
        
        layout.addLayout(bottom_button_layout)

    def _create_pie_chart(self, distribution, title):
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

    def update_results(self, result):
        """Populates text labels and pie charts with new analysis data."""
        foul_dist = result['foul_distribution']
        sev_dist = result['severity_distribution']

        sorted_fouls = sorted(foul_dist.items(), key=lambda item: item[1], reverse=True)
        self.foul_type_1_label.setText(f"1. {sorted_fouls[0][0]} - {sorted_fouls[0][1]:.1%}")
        self.foul_type_2_label.setText(f"2. {sorted_fouls[1][0]} - {sorted_fouls[1][1]:.1%}")

        sorted_sev = sorted(sev_dist.items(), key=lambda item: item[1], reverse=True)
        self.severity_1_label.setText(f"1. {sorted_sev[0][0]} - {sorted_sev[0][1]:.1%}")
        self.severity_2_label.setText(f"2. {sorted_sev[1][0]} - {sorted_sev[1][1]:.1%}")

        foul_chart = self._create_pie_chart(foul_dist, "Foul Type Distribution")
        self.foul_chart_view.setChart(foul_chart)
        
        sev_chart = self._create_pie_chart(sev_dist, "Severity Distribution")
        self.severity_chart_view.setChart(sev_chart)

    def get_manual_annotation(self):
        """获取当前手动标注的值"""
        foul_btn = self.foul_button_group.checkedButton()
        sev_btn = self.sev_button_group.checkedButton()
        return {
            "foul": foul_btn.text() if foul_btn else None,
            "severity": sev_btn.text() if sev_btn else None
        }

    def clear_manual_selection(self):
        """清除所有手动标注单选按钮"""
        self.foul_button_group.setExclusive(False)
        for rb in self.foul_radio_buttons.values():
            rb.setChecked(False)
        self.foul_button_group.setExclusive(True)

        self.sev_button_group.setExclusive(False)
        for rb in self.sev_radio_buttons.values():
            rb.setChecked(False)
        self.sev_button_group.setExclusive(True)

    def set_manual_annotation(self, data):
        """根据传入的数据设置手动标注"""
        self.clear_manual_selection()
        if data and data.get("foul") in self.foul_radio_buttons:
            self.foul_radio_buttons[data["foul"]].setChecked(True)
        
        if data and data.get("severity") in self.sev_radio_buttons:
            self.sev_radio_buttons[data["severity"]].setChecked(True)


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