from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel, QPushButton, QMessageBox,
    QStyle, QStyleOptionSlider, QSizePolicy
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QTime
from PyQt6.QtGui import QPainter, QColor, QPen

class MediaPreviewWidget(QWidget):
    positionChanged = pyqtSignal(int)
    durationChanged = pyqtSignal(int)
    stateChanged = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.video_widget = QVideoWidget()
        # Ensure black background to prevent white flash
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


class TimelineWidget(QWidget):
    seekRequested = pyqtSignal(int)
    markerClicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        self.time_label = QLabel("00:00.000 / 00:00.000")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("font-family: monospace; font-size: 14px; font-weight: bold;")
        
        self.slider = AnnotationSlider(Qt.Orientation.Horizontal)
        self.slider.sliderPressed.connect(self._on_slider_pressed)
        self.slider.sliderMoved.connect(self._on_slider_moved)
        self.slider.sliderReleased.connect(self._on_slider_released)
        
        layout.addWidget(self.time_label)
        layout.addWidget(self.slider)
        
        self.duration = 0
        self.is_dragging = False

    def set_duration(self, ms):
        self.duration = ms
        self.slider.setRange(0, ms)
        self._update_label(self.slider.value())

    def set_position(self, ms):
        if not self.is_dragging:
            self.slider.setValue(ms)
            self._update_label(ms)

    def set_markers(self, markers):
        self.slider.markers = markers
        self.slider.update()

    def _update_label(self, current_ms):
        def fmt(ms):
            s = ms // 1000
            m = s // 60
            # Format: MM:SS.mmm
            return f"{m:02}:{s%60:02}.{ms%1000:03}"
        
        self.time_label.setText(f"{fmt(current_ms)} / {fmt(self.duration)}")

    def _on_slider_pressed(self): self.is_dragging = True
    def _on_slider_moved(self, val): self._update_label(val)
    def _on_slider_released(self):
        self.is_dragging = False
        self.seekRequested.emit(self.slider.value())


class AnnotationSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.markers = []

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.markers or self.maximum() <= 0: return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        groove = self.style().subControlRect(QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderGroove, self)
        
        available_width = groove.width()
        x_offset = groove.x()
        
        for m in self.markers:
            start_ms = m.get('start_ms', 0)
            ratio = start_ms / self.maximum()
            x = x_offset + int(available_width * ratio)
            c = m.get('color', QColor('red'))
            painter.setPen(QPen(c, 2))
            painter.drawLine(x, groove.top(), x, groove.bottom())


class PlaybackControlBar(QWidget):
    seekRelativeRequested = pyqtSignal(int)
    stopRequested = pyqtSignal()
    playPauseRequested = pyqtSignal()
    nextPrevClipRequested = pyqtSignal(int)
    nextPrevAnnotRequested = pyqtSignal(int) # [新增] -1 prev, 1 next
    playbackRateRequested = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # Row 1: Navigation (Clip & Time)
        r1 = QHBoxLayout()
        btns_r1 = [
            ("Prev Clip", lambda: self.nextPrevClipRequested.emit(-1)),
            ("<< 5s", lambda: self.seekRelativeRequested.emit(-5000)),
            ("<< 1s", lambda: self.seekRelativeRequested.emit(-1000)),
            ("Play/Pause", lambda: self.playPauseRequested.emit()),
            ("1s >>", lambda: self.seekRelativeRequested.emit(1000)),
            ("5s >>", lambda: self.seekRelativeRequested.emit(5000)),
            ("Next Clip", lambda: self.nextPrevClipRequested.emit(1))
        ]
        for txt, func in btns_r1:
            b = QPushButton(txt)
            b.clicked.connect(func)
            r1.addWidget(b)
        layout.addLayout(r1)
        
        # Row 2: Speed & Annotation Jump
        r2 = QHBoxLayout()
        
        # [新增] Prev Annotation
        btn_prev_ann = QPushButton("Prev Event")
        btn_prev_ann.clicked.connect(lambda: self.nextPrevAnnotRequested.emit(-1))
        r2.addWidget(btn_prev_ann)
        
        # Speed Buttons
        speeds = [0.25, 0.5, 1.0, 2.0]
        for s in speeds:
            b = QPushButton(f"{s}x")
            b.clicked.connect(lambda _, rate=s: self.playbackRateRequested.emit(rate))
            r2.addWidget(b)
            
        # [新增] Next Annotation
        btn_next_ann = QPushButton("Next Event")
        btn_next_ann.clicked.connect(lambda: self.nextPrevAnnotRequested.emit(1))
        r2.addWidget(btn_next_ann)
        
        layout.addLayout(r2)