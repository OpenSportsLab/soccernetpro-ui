from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QStackedLayout
)
from PyQt6.QtMultimedia import QMediaPlayer

from .preview import MediaPreview
from .controls import NavigationToolbar

class ClassificationMediaPlayer(QWidget):
    """
    Center Panel for Classification Mode.
    Combines MediaPreview and NavigationToolbar.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Main View Area
        self.view_container = QWidget()
        self.view_layout = QStackedLayout(self.view_container)
        self.layout.addWidget(self.view_container, 1) 
        
        # [Compatibility] Kept name 'single_view_widget' to avoid breaking NavigationManager
        self.single_view_widget = MediaPreview()
        self.view_layout.addWidget(self.single_view_widget)
        
        # Placeholder for Grid View
        self.multi_view_widget = QWidget()
        self.view_layout.addWidget(self.multi_view_widget)
        
        # 2. Navigation Toolbar
        self.controls = NavigationToolbar()
        self.layout.addWidget(self.controls)
        
        # Expose buttons for easy access by Controllers (Forwarding)
        self.prev_action = self.controls.prev_action
        self.prev_clip = self.controls.prev_clip
        self.play_btn = self.controls.play_btn
        self.next_clip = self.controls.next_clip
        self.next_action = self.controls.next_action
        self.multi_view_btn = self.controls.multi_view_btn

    def show_single_view(self, path):
        """Helper to load video and switch stack."""
        self.single_view_widget.load_video(path)
        self.view_layout.setCurrentWidget(self.single_view_widget)

    def toggle_play_pause(self):
        """Helper to toggle playback."""
        player = self.single_view_widget.player
        if player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            player.pause()
        else:
            player.play()
    
    def show_all_views(self, paths):
        pass