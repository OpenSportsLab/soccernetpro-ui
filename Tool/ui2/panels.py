from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QLabel, QComboBox
from .widgets.left_widgets import ProjectControlsWidget
from .widgets.center_widgets import MediaPreviewWidget, TimelineWidget, PlaybackControlBar
from .widgets.right_widgets import AnnotationManagementWidget, LabelEditorWidget, AnnotationTableWidget

class LocLeftPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)
        layout = QVBoxLayout(self)
        
        # 1. Project Controls
        self.project_controls = ProjectControlsWidget()
        
        # 2. Clip List Tree
        self.clip_tree_label = QLabel("Clips / Sequences")
        self.clip_tree_label.setStyleSheet("font-weight: bold; color: #888; margin-top: 10px;")
        self.clip_tree = QTreeWidget()
        self.clip_tree.setHeaderHidden(True)
        
        # 3. Filter
        self.filter_label = QLabel("Filter:")
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Show All", "Show Annotated", "Show Unannotated"])
        
        layout.addWidget(self.project_controls)
        layout.addWidget(self.clip_tree_label)
        layout.addWidget(self.clip_tree)
        layout.addWidget(self.filter_label)
        layout.addWidget(self.filter_combo)

class LocCenterPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        self.media_preview = MediaPreviewWidget()
        self.timeline = TimelineWidget()
        self.playback = PlaybackControlBar()
        
        layout.addWidget(self.media_preview, 1) 
        layout.addWidget(self.timeline)
        layout.addWidget(self.playback)

class LocRightPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(400)
        layout = QVBoxLayout(self)
        
        # 1. 顶部：标签按钮区域
        self.annot_mgmt = AnnotationManagementWidget()
        
        # 2. 中部：新增标签输入框 (高度固定)
        self.label_editor = LabelEditorWidget()
        
        # 3. 底部：已标注事件列表
        self.table = AnnotationTableWidget()
        
        # [修改] 布局权重分配
        # annot_mgmt (权重 1): 允许它占据约 1/3 的垂直空间，随内容扩展
        # label_editor (权重 0): 固定高度
        # table (权重 2): 占据约 2/3 的垂直空间
        layout.addWidget(self.annot_mgmt, 1) 
        layout.addWidget(self.label_editor)
        layout.addWidget(self.table, 2)

class LocalizationUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        self.left_panel = LocLeftPanel()
        self.center_panel = LocCenterPanel()
        self.right_panel = LocRightPanel()
        
        layout.addWidget(self.left_panel)
        layout.addWidget(self.center_panel, 1)
        layout.addWidget(self.right_panel)