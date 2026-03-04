from PyQt6.QtCore import QUrl, QTimer, QObject
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtWidgets import QWidget

class MediaController(QObject):
    """
    A unified controller for managing video playback logic across all modes.
    Now handles:
    1. Robust Playback State (Stop -> Clear -> Load -> Delay -> Play)
    2. Timer Cancellation (Prevents race conditions on rapid switching)
    3. Visual Clearing (Forces VideoWidget to refresh)
    """
    def __init__(self, player: QMediaPlayer, video_widget: QWidget = None):
        super().__init__()
        self.player = player
        self.video_widget = video_widget
        
        # [CRITICAL FIX] Use an instance timer so we can cancel it!
        # This prevents the "Ghost Timer" bug where a video starts playing 
        # *after* the user has closed the project or switched modes.
        self.play_timer = QTimer()
        self.play_timer.setSingleShot(True)
        self.play_timer.setInterval(150) # 150ms delay
        self.play_timer.timeout.connect(self._execute_play)

    def load_and_play(self, file_path: str, auto_play: bool = True):
        """
        Standardized sequence to load and play a video.
        """
        # 1. Force Stop & Cancel any pending play requests
        self.stop() 

        if not file_path:
            return

        # 2. Load Source
        self.player.setSource(QUrl.fromLocalFile(file_path))

        # 3. Auto-play with safety delay
        if auto_play:
            self.play_timer.start()

    def _execute_play(self):
        """Actual slot called by timer to start playback."""
        self.player.play()

    def toggle_play_pause(self):
        """Toggle between Play and Pause."""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def stop(self):
        """
        Stops playback, clears source, cancels timers, and forces UI refresh.
        """
        # A. Cancel pending auto-play if user clicked away quickly
        if self.play_timer.isActive():
            self.play_timer.stop()
            
        # B. Stop Player logic
        self.player.stop()
        self.player.setSource(QUrl())
        
        # C. [Visual Fix] Force the video widget to repaint/update
        # This helps clear the "stuck frame" from the GPU buffer
        if self.video_widget:
            self.video_widget.update()
            self.video_widget.repaint()

        
    def set_looping(self, enable: bool):
        """Helper to set looping."""
        if enable:
            self.player.setLoops(QMediaPlayer.Loops.Infinite)
        else:
            self.player.setLoops(QMediaPlayer.Loops.Once)

    def set_position(self, position):
        self.player.setPosition(position)