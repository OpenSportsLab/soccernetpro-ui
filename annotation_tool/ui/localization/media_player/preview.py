from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, pyqtSignal, QUrl

class MediaPreviewWidget(QWidget):
    positionChanged = pyqtSignal(int)
    durationChanged = pyqtSignal(int)
    stateChanged = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: black;")
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video_widget)
        
        layout.addWidget(self.video_widget)
        
        self.player.positionChanged.connect(self.positionChanged.emit)
        self.player.durationChanged.connect(self.durationChanged.emit)
        self.player.playbackStateChanged.connect(self.stateChanged.emit)
        self.player.errorOccurred.connect(self._on_error)

    def load_video(self, path):
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.pause()
        self.player.setPosition(0)

    def play(self): self.player.play()
    def pause(self): self.player.pause()
    def stop(self): self.player.stop()
        
    def toggle_play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            if self.player.position() >= self.player.duration() and self.player.duration() > 0:
                self.player.setPosition(0)
            self.player.play()

    def set_position(self, ms): self.player.setPosition(ms)
    def set_playback_rate(self, rate): self.player.setPlaybackRate(rate)
    
    def _on_error(self):
        print(f"Media Error: {self.player.errorString()}")