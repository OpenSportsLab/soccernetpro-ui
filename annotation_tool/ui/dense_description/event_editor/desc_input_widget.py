from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal

class DenseDescriptionInputWidget(QWidget):
    """
    Panel for entering free-text descriptions at specific timestamps.
    """
    descriptionSubmitted = pyqtSignal(str) # Emits the text to be added

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. Title & Time Display
        self.title_lbl = QLabel("Create/Edit Description")
        self.title_lbl.setProperty("class", "panel_header_lbl")
        layout.addWidget(self.title_lbl)

        self.time_display = QLabel("Current Time: 00:00.000")
        self.time_display.setStyleSheet("font-size: 14px; font-weight: bold; color: #55AAFF;")
        self.time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_display)

        # 2. Text Input (Long Text)
        layout.addWidget(QLabel("Description Text:"))
        self.text_editor = QTextEdit()
        self.text_editor.setPlaceholderText("Enter the description of the event here...")
        self.text_editor.setMinimumHeight(150)
        self.text_editor.setStyleSheet("background-color: #222; color: #EEE; border: 1px solid #444;")
        layout.addWidget(self.text_editor)

        # 3. Add/Update Button
        self.add_btn = QPushButton("Confirm Description")
        self.add_btn.setFixedHeight(40)
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setStyleSheet("""
            QPushButton { background-color: #2E7D32; color: white; font-weight: bold; border-radius: 4px; }
            QPushButton:hover { background-color: #388E3C; }
        """)
        self.add_btn.clicked.connect(self._on_submit)
        layout.addWidget(self.add_btn)

    def update_time(self, time_str):
        self.time_display.setText(f"Current Time: {time_str}")

    def set_text(self, text):
        """[NEW] Programmatically set the text in the editor (for editing existing events)."""
        self.text_editor.setPlainText(text)

    def _on_submit(self):
        text = self.text_editor.toPlainText().strip()
        if text:
            self.descriptionSubmitted.emit(text)
            # We don't clear immediately here, giving user feedback that it's saved/updated.
            # But typically clearing is good for 'Add' mode. 
            # For 'Edit' mode, keeping it might be better.
            # Let's clear it to indicate submission success.
            #self.text_editor.clear()