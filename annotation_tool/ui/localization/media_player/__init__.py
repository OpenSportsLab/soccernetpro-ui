from PyQt6.QtWidgets import QWidget, QVBoxLayout

# Import components from sibling files
from .preview import MediaPreviewWidget
from .timeline import TimelineWidget
from .controls import PlaybackControlBar

class LocCenterPanel(QWidget):
    """
    Center Panel for Localization Mode.
    Contains: MediaPreview, Timeline, Playback Controls.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        self.media_preview = MediaPreviewWidget()
        self.timeline = TimelineWidget()
        self.playback = PlaybackControlBar()
        
        layout.addWidget(self.media_preview, 1) # Expandable
        layout.addWidget(self.timeline)
        layout.addWidget(self.playback)