import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem,
    QLabel, QComboBox, QScrollArea, QGroupBox, QLineEdit, QMenu, QStyle, QGridLayout,
    QFrame, QStackedLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QUrl, QTime
from PyQt6.QtGui import QAction, QColor, QPixmap
from PyQt6.QtMultimedia import QMediaPlayer

# 引入基础组件
# 注意：请根据您的实际目录结构调整引用。如果 ui2 文件夹下有 widgets 文件夹：
from .widgets.clip_explorer import ProjectControlsWidget
from .widgets.media_player import MediaPreviewWidget, TimelineWidget, PlaybackControlBar
from .widgets.event_editor import AnnotationManagementWidget, AnnotationTableWidget

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

        # 3. Filter & Clear All
        self.filter_label = QLabel("Filter:")
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Show All", "Show Labelled", "No Labelled"])

        # Clear All 按钮 - [修改] 移除红色样式，使其与 Export JSON 保持一致
        self.btn_clear_all = QPushButton("Clear All")
        self.btn_clear_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_all.setFixedWidth(80) 
        # 这里不再设置特殊的 setStyleSheet，让它使用全局样式

        filter_row = QHBoxLayout()
        filter_row.addWidget(self.filter_label)
        filter_row.addWidget(self.filter_combo, 1) # Stretch combo
        filter_row.addWidget(self.btn_clear_all)   # Add button at the end

        layout.addWidget(self.project_controls)
        layout.addWidget(self.clip_tree_label)
        layout.addWidget(self.clip_tree, 1)
        layout.addLayout(filter_row)


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
        
        # --- Undo/Redo 按钮区域 ---
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 5)
        
        lbl = QLabel("Annotation Controls")
        lbl.setStyleSheet("font-weight: bold; color: #BBB; font-size: 13px;")
        
        self.undo_btn = QPushButton("Undo")
        self.redo_btn = QPushButton("Redo")
        
        # 按钮样式
        btn_style = """
            QPushButton {
                background-color: #444; color: #DDD; 
                border: 1px solid #555; border-radius: 4px; padding: 4px 10px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #555; border-color: #777; }
            QPushButton:pressed { background-color: #333; }
            QPushButton:disabled { color: #777; background-color: #333; border-color: #444; }
        """
        for btn in [self.undo_btn, self.redo_btn]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(btn_style)
            btn.setFixedWidth(60)
            btn.setEnabled(False) # 初始禁用
            
        header_layout.addWidget(lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.undo_btn)
        header_layout.addWidget(self.redo_btn)
        
        layout.addLayout(header_layout)
        # -----------------------------------
        
        # 1. 顶部：多 Head 管理 + 标签打点区域
        self.annot_mgmt = AnnotationManagementWidget()
        
        # 2. 底部：已标注事件列表
        self.table = AnnotationTableWidget()
        
        layout.addWidget(self.annot_mgmt, 3) 
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