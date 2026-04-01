# smart_spotting.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QGroupBox, QLineEdit
)
from PyQt6.QtCore import pyqtSignal, Qt

# Reuse the existing table widget for displaying smart predictions
from .annotation_table import AnnotationTableWidget

class TimeLineEdit(QLineEdit):
    """
    Custom QLineEdit tailored for time input in the format MM:SS.mmm.
    Supports free typing and using Up/Down arrow keys to increment/decrement time.
    """
    timeChanged = pyqtSignal(int) # Emits the new time in milliseconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ms = 0
        self.setText("00:00.000")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("font-family: monospace; font-weight: bold; font-size: 13px; padding: 2px;")
        self.setFixedWidth(100)
        
        # When user finishes typing and loses focus or hits Enter
        self.editingFinished.connect(self._on_edit_finished)

    def set_time_ms(self, ms: int):
        """Programmatically set the time in milliseconds."""
        self._ms = max(0, ms)
        self.setText(self._fmt_ms(self._ms))
        self.timeChanged.emit(self._ms)

    def get_time_ms(self) -> int:
        """Get the current time in milliseconds."""
        return self._ms

    def _fmt_ms(self, ms: int) -> str:
        """Format milliseconds to MM:SS.mmm"""
        s = ms // 1000
        m = s // 60
        return f"{m:02}:{s%60:02}.{ms%1000:03}"

    def _parse_time(self, text: str) -> int:
        """Parse MM:SS.mmm string back to milliseconds."""
        try:
            parts = text.split(':')
            if len(parts) >= 2:
                m = int(parts[0])
                s_parts = parts[1].split('.')
                s = int(s_parts[0])
                ms = int(s_parts[1]) if len(s_parts) > 1 else 0
                return (m * 60 + s) * 1000 + ms
        except Exception:
            pass
        return self._ms # Return the last valid time if parsing fails

    def _on_edit_finished(self):
        """Validate and apply manually typed time."""
        parsed_ms = self._parse_time(self.text())
        self.set_time_ms(parsed_ms)

    def keyPressEvent(self, event):
        """Intercept Up/Down arrows to adjust time dynamically."""
        if event.key() == Qt.Key.Key_Up:
            self._adjust_time(1)
            event.accept()
        elif event.key() == Qt.Key.Key_Down:
            self._adjust_time(-1)
            event.accept()
        else:
            super().keyPressEvent(event)

    def _adjust_time(self, direction: int):
        """Adjust time based on cursor position."""
        cursor = self.cursorPosition()
        ms = self._ms
        
        # Cursor positions for MM:SS.mmm:
        # <= 2: Minutes
        # 3 to 5: Seconds
        # >= 6: Milliseconds
        if cursor <= 2:
            ms += direction * 60000  # +/- 1 minute
        elif cursor <= 5:
            ms += direction * 1000   # +/- 1 second
        else:
            ms += direction * 100    # +/- 100 milliseconds for smoother scrolling
            
        self.set_time_ms(max(0, ms))
        self.setCursorPosition(cursor) # Restore cursor position so user can keep pressing


class SmartSpottingWidget(QWidget):
    """
    UI for Smart Annotation in Localization mode.
    Allows users to select a time range, run inference, and review predicted events
    in a separate table before confirming them.
    """
    # Signals to be connected to the LocalizationManager
    setTimeRequested = pyqtSignal(str)           # 'start' or 'end'
    runInferenceRequested = pyqtSignal(int, int) # start_ms, end_ms
    confirmSmartRequested = pyqtSignal()         # Merge smart events to hand events
    clearSmartRequested = pyqtSignal()           # Clear current smart predictions

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Internal state
        self.start_ms = 0
        self.end_ms = 0

        # --- 1. Time Range Selection Box ---
        self.time_box = QGroupBox("Smart Inference Range")
        self.time_box.setProperty("class", "smart_inference_box")
        time_layout = QVBoxLayout(self.time_box)
        
        # Start Time Row
        start_row = QHBoxLayout()
        self.lbl_start = QLabel("Start Time:")
        self.val_start = TimeLineEdit()
        self.btn_set_start = QPushButton("Set to Current")
        self.btn_set_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_set_start.clicked.connect(lambda: self.setTimeRequested.emit("start"))
        self.val_start.timeChanged.connect(self._on_start_changed)
        
        start_row.addWidget(self.lbl_start)
        start_row.addWidget(self.val_start)
        start_row.addStretch()
        start_row.addWidget(self.btn_set_start)
        
        # End Time Row
        end_row = QHBoxLayout()
        self.lbl_end = QLabel("End Time:")
        self.val_end = TimeLineEdit()
        self.btn_set_end = QPushButton("Set to Current")
        self.btn_set_end.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_set_end.clicked.connect(lambda: self.setTimeRequested.emit("end"))
        self.val_end.timeChanged.connect(self._on_end_changed)
        
        end_row.addWidget(self.lbl_end)
        end_row.addWidget(self.val_end)
        end_row.addStretch()
        end_row.addWidget(self.btn_set_end)
        
        time_layout.addLayout(start_row)
        time_layout.addLayout(end_row)
        
        # Run Button
        self.btn_run_infer = QPushButton("Run Smart Inference")
        self.btn_run_infer.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run_infer.setProperty("class", "run_inference_btn")
        self.btn_run_infer.clicked.connect(self._on_run_clicked)
        
        time_layout.addWidget(self.btn_run_infer)
        layout.addWidget(self.time_box, 0) # 0 stretch means it stays at top

        # --- 2. Smart Events List (Separated from Hand Annotations) ---
        self.smart_table = AnnotationTableWidget()
        self.smart_table.edit_lbl.hide()
        self.smart_table.btn_set_time.hide()
        self.smart_table.list_lbl.setText("Predicted Events List")
        
        layout.addWidget(self.smart_table, 1) # 1 stretch means it fills remaining space

        # --- 3. Bottom Controls ---
        bottom_row = QHBoxLayout()
        self.btn_confirm = QPushButton("Confirm Predictions")
        self.btn_confirm.setProperty("class", "editor_save_btn")
        self.btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_confirm.clicked.connect(self.confirmSmartRequested.emit)
        
        self.btn_clear = QPushButton("Clear Predictions")
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.clicked.connect(self.clearSmartRequested.emit)
        
        bottom_row.addWidget(self.btn_confirm)
        bottom_row.addWidget(self.btn_clear)
        layout.addLayout(bottom_row)

    # ==================== Logic & Validation ====================

    def _on_start_changed(self, ms: int):
        """Ensure Start Time does not exceed End Time"""
        self.start_ms = ms
        # If End Time is set (not 0) and Start > End, push End Time forward
        if self.end_ms > 0 and self.start_ms > self.end_ms:
            self.val_end.blockSignals(True)
            self.val_end.set_time_ms(self.start_ms)
            self.end_ms = self.start_ms
            self.val_end.blockSignals(False)

    def _on_end_changed(self, ms: int):
        """Ensure End Time does not drop below Start Time"""
        self.end_ms = ms
        # If End Time drops below Start Time, push Start Time backward
        if self.end_ms > 0 and self.end_ms < self.start_ms:
            self.val_start.blockSignals(True)
            self.val_start.set_time_ms(self.end_ms)
            self.start_ms = self.end_ms
            self.val_start.blockSignals(False)

    def update_time_display(self, target: str, time_str: str, time_ms: int):
        """Called by controller to update the UI with the player's current time"""
        # We ignore the time_str since TimeLineEdit formats it internally
        if target == "start":
            self.val_start.set_time_ms(time_ms)
        elif target == "end":
            self.val_end.set_time_ms(time_ms)

    def _on_run_clicked(self):
        """Emit the run signal with validated boundaries"""
        self.runInferenceRequested.emit(self.start_ms, self.end_ms)