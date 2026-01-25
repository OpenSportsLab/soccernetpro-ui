import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel, QButtonGroup, 
    QRadioButton, QCheckBox, QGroupBox, QLineEdit, QPushButton, QStyle,
    QScrollArea, QStyleOptionSlider
)
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QTime, pyqtSignal, QSize, QPoint
from PyQt6.QtGui import QPixmap
from utils import get_square_remove_btn_style

class ClickableSlider(QSlider):
    """
    A custom QSlider that jumps to the click position immediately.
    Standard QSlider only moves by pageStep on click.
    """
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            val = self._pixel_pos_to_value(event.pos())
            self.setValue(val)
            # Emit sliderMoved so connected slots handle the seek
            self.sliderMoved.emit(val)

    def _pixel_pos_to_value(self, pos):
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        gr = self.style().subControlRect(QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderGroove, self)
        sr = self.style().subControlRect(QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderHandle, self)

        if self.orientation() == Qt.Orientation.Horizontal:
            slider_length = sr.width()
            slider_min = gr.x()
            slider_max = gr.right() - slider_length + 1
            pos_x = pos.x()
        else:
            slider_length = sr.height()
            slider_min = gr.y()
            slider_max = gr.bottom() - slider_length + 1
            pos_x = pos.y()
            
        return QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), pos_x - slider_min,
                                              slider_max - slider_min, opt.upsideDown)

class VideoViewAndControl(QWidget):
    """
    Wraps a QVideoWidget and its controls (Slider/Label).
    Used in Classification CenterPanel.
    """
    def __init__(self, clip_path, parent=None):
        super().__init__(parent)
        self.clip_path = clip_path
        
        # 1. Player Setup
        self.player = QMediaPlayer()
        self.player.setLoops(QMediaPlayer.Loops.Infinite) 
        self.video_widget = QVideoWidget()
        self.player.setVideoOutput(self.video_widget)
        
        # 2. Controls
        # Use custom ClickableSlider instead of standard QSlider
        self.slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.setEnabled(False) # Disabled until media loads
        self.slider.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.clip_name = os.path.basename(clip_path) if clip_path else "No Clip"
        self.time_label = QLabel(f"00:00 / 00:00")
        self.time_label.setFixedWidth(120)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.time_label.setStyleSheet("font-family: monospace; font-weight: bold;")
        
        # 3. Layout
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.setSpacing(5)
        
        self.v_layout.addWidget(self.video_widget, 1) # Video takes expandable space
        
        # Control Row
        h_controls = QHBoxLayout()
        h_controls.setContentsMargins(5, 0, 5, 5)
        h_controls.addWidget(self.slider)
        h_controls.addWidget(self.time_label)
        self.v_layout.addLayout(h_controls)

        # 4. Connections
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        
        # Slider interactions
        self.slider.sliderMoved.connect(self._on_slider_moved)
        self.slider.sliderPressed.connect(self.player.pause) # Pause while dragging
        self.slider.sliderReleased.connect(self.player.play) # Resume after dragging

        self._duration_ms = 0

    def _on_duration_changed(self, duration):
        """Called when video loads or duration changes."""
        self._duration_ms = duration
        if duration > 0:
            self.slider.setRange(0, duration)
            self.slider.setEnabled(True)
            self.slider.setValue(0)
            self._update_time_label(0, duration)
        else:
            self.slider.setEnabled(False)

    def _on_position_changed(self, position):
        """Update slider position as video plays (if not dragging)."""
        if not self.slider.isSliderDown():
            self.slider.setValue(position)
        self._update_time_label(position, self._duration_ms)

    def _on_slider_moved(self, position):
        """User dragged or clicked the slider."""
        self.player.setPosition(position)
        self._update_time_label(position, self._duration_ms)

    def _update_time_label(self, current_ms, total_ms):
        def fmt(ms):
            s = (ms // 1000) % 60
            m = (ms // 60000) % 60
            return f"{m:02}:{s:02}"
        self.time_label.setText(f"{fmt(current_ms)} / {fmt(total_ms)}")


# =========================================================
# Dynamic Schema Widgets
# =========================================================

class DynamicSingleLabelGroup(QWidget):
    value_changed = pyqtSignal(str, str) # head, selected_label
    remove_category_signal = pyqtSignal(str) # head
    # [Fix] Signal must be defined at class level!
    remove_label_signal = pyqtSignal(str, str) # label, head

    def __init__(self, head_name, definition, parent=None):
        super().__init__(parent)
        self.head_name = head_name
        self.definition = definition # {'type': 'single_label', 'labels': [...]}
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 5, 0, 15)
        
        # Header
        header_layout = QHBoxLayout()
        self.lbl_head = QLabel(head_name)
        self.lbl_head.setStyleSheet("font-weight: bold; font-size: 13px; color: #00BFFF;")
        
        self.btn_del_cat = QPushButton("×")
        self.btn_del_cat.setFixedSize(20, 20)
        self.btn_del_cat.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_del_cat.setStyleSheet(get_square_remove_btn_style())
        self.btn_del_cat.clicked.connect(lambda: self.remove_category_signal.emit(self.head_name))
        
        header_layout.addWidget(self.lbl_head)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_del_cat)
        self.layout.addLayout(header_layout)
        
        # Radio Group
        self.radio_group = QButtonGroup(self)
        self.radio_group.setExclusive(True)
        self.radio_container = QWidget()
        self.radio_layout = QVBoxLayout(self.radio_container)
        self.radio_layout.setContentsMargins(10, 0, 0, 0)
        self.layout.addWidget(self.radio_container)
        
        # Input for new label
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(f"Add option to {head_name}...")
        self.add_btn = QPushButton("+")
        self.add_btn.setFixedSize(30, 30)
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.add_btn)
        self.layout.addLayout(input_layout)

        # Initial Population
        self.update_radios(definition.get('labels', []))
        
        self.radio_group.buttonClicked.connect(self._on_radio_clicked)

    def update_radios(self, labels):
        # Clear existing
        for btn in self.radio_group.buttons():
            self.radio_group.removeButton(btn)
            btn.deleteLater()
            
        # Clear layout items including delete buttons
        while self.radio_layout.count():
            item = self.radio_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        for i, lbl_text in enumerate(labels):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 2, 0, 2)
            
            rb = QRadioButton(lbl_text)
            self.radio_group.addButton(rb, i)
            
            del_label_btn = QPushButton("×")
            del_label_btn.setFixedSize(20, 20)
            del_label_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_label_btn.setStyleSheet(get_square_remove_btn_style())
            
            # Use lambda to pass specific label text
            del_label_btn.clicked.connect(lambda _, l=lbl_text: self.remove_label_signal.emit(l, self.head_name))
            
            row_layout.addWidget(rb)
            row_layout.addStretch()
            row_layout.addWidget(del_label_btn)
            
            self.radio_layout.addWidget(row_widget)

    def _on_radio_clicked(self, btn):
        self.value_changed.emit(self.head_name, btn.text())

    def get_checked_label(self):
        btn = self.radio_group.checkedButton()
        return btn.text() if btn else None

    def set_checked_label(self, label_text):
        if not label_text:
            # Deselect
            btn = self.radio_group.checkedButton()
            if btn: 
                self.radio_group.setExclusive(False)
                btn.setChecked(False)
                self.radio_group.setExclusive(True)
            return

        for btn in self.radio_group.buttons():
            if btn.text() == label_text:
                btn.setChecked(True)
                break

class DynamicMultiLabelGroup(QWidget):
    value_changed = pyqtSignal(str, list)
    remove_category_signal = pyqtSignal(str)
    remove_label_signal = pyqtSignal(str, str) # label, head

    def __init__(self, head_name, definition, parent=None):
        super().__init__(parent)
        self.head_name = head_name
        self.definition = definition
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 5, 0, 15)
        
        # Header
        header_layout = QHBoxLayout()
        self.lbl_head = QLabel(head_name + " (Multi)")
        self.lbl_head.setStyleSheet("font-weight: bold; font-size: 13px; color: #32CD32;")
        
        self.btn_del_cat = QPushButton("×")
        self.btn_del_cat.setFixedSize(20, 20)
        self.btn_del_cat.setStyleSheet(get_square_remove_btn_style())
        self.btn_del_cat.clicked.connect(lambda: self.remove_category_signal.emit(self.head_name))
        
        header_layout.addWidget(self.lbl_head)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_del_cat)
        self.layout.addLayout(header_layout)
        
        self.checkbox_container = QWidget()
        self.checkbox_layout = QVBoxLayout(self.checkbox_container)
        self.checkbox_layout.setContentsMargins(10, 0, 0, 0)
        self.layout.addWidget(self.checkbox_container)
        
        # Input
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(f"Add option...")
        self.add_btn = QPushButton("+")
        self.add_btn.setFixedSize(30, 30)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.add_btn)
        self.layout.addLayout(input_layout)
        
        self.checkboxes = {} # text -> QCheckBox
        self.update_checkboxes(definition.get('labels', []))

    def update_checkboxes(self, new_types):
        while self.checkbox_layout.count():
            item = self.checkbox_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        self.checkboxes.clear()
        
        for type_name in sorted(list(set(new_types))): 
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 2, 0, 2)

            cb = QCheckBox(type_name)
            cb.clicked.connect(self._on_box_clicked)
            self.checkboxes[type_name] = cb
            
            del_label_btn = QPushButton("×")
            del_label_btn.setFixedSize(20, 20)
            del_label_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_label_btn.setStyleSheet(get_square_remove_btn_style())
            del_label_btn.clicked.connect(lambda _, n=type_name: self.remove_label_signal.emit(n, self.head_name))

            row_layout.addWidget(cb)
            row_layout.addStretch()
            row_layout.addWidget(del_label_btn)
            self.checkbox_layout.addWidget(row_widget)
            
    def _on_box_clicked(self):
        self.value_changed.emit(self.head_name, self.get_checked_labels())

    def get_checked_labels(self):
        return [cb.text() for cb in self.checkboxes.values() if cb.isChecked()]

    def set_checked_labels(self, label_list):
        self.blockSignals(True)
        if not label_list: label_list = []
        for text, cb in self.checkboxes.items():
            cb.setChecked(text in label_list)
        self.blockSignals(False)