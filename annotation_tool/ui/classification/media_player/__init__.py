from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtMultimedia import QMediaPlayer

from .player_panel import PlayerPanel
from .controls import PlaybackControlBar 

class ClassificationMediaPlayer(QWidget):
    """
    Main container for Classification Mode Media Player.
    Combines PlayerPanel (Video Surface + Timeline/Slider) and PlaybackControlBar.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Instantiate the Panel (Video + Slider)
        self.single_view_widget = PlayerPanel()
        layout.addWidget(self.single_view_widget, 1) # Stretch factor 1
        
        # 2. Instantiate Controls
        self.controls = PlaybackControlBar()
        layout.addWidget(self.controls)

        # 3. Expose components for external Controllers
        # Player reference
        self.player = self.single_view_widget.player
        
        # Button references
        self.play_btn = self.controls.play_btn
        self.prev_action = self.controls.prev_action
        self.prev_clip = self.controls.prev_clip
        self.next_clip = self.controls.next_clip
        self.next_action = self.controls.next_action
        self.multi_view_btn = self.controls.multi_view_btn

    # =========================================================
    # [新增] 补充缺失的接口方法，修复 AttributeError
    # =========================================================

    def show_single_view(self, path):
        """
        Loads a single video into the player.
        Called by ClassFileManager and NavigationManager.
        """
        self.single_view_widget.load_video(path)

    def toggle_play_pause(self):
        """
        Toggles playback state.
        Called by NavigationManager.
        """
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def show_all_views(self, paths):
        """
        Stub for Multi-View (Grid) support.
        If you haven't implemented grid view yet, just load the first video to avoid crash.
        """
        if paths:
            # Fallback: Just show the first video in single view for now
            self.show_single_view(paths[0])