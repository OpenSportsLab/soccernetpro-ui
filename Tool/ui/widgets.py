import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel, QButtonGroup, 
    QRadioButton, QCheckBox, QGroupBox, QLineEdit, QPushButton, QStyle,
    QScrollArea
)
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QTime, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap
from utils import get_square_remove_btn_style

class VideoViewAndControl(QWidget):
    """Wraps a QVideoWidget and its controls (Slider/Label)."""
    def __init__(self, clip_path, parent=None):
        super().__init__(parent)
        self.clip_path = clip_path
        self.player = QMediaPlayer()
        self.player.setLoops(QMediaPlayer.Loops.Infinite)
        self.video_widget = QVideoWidget()
        self.player.setVideoOutput(self.video_widget)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.setEnabled(False)
        self.clip_name = os.path.basename(clip_path) if clip_path else "No Clip"
        self.time_label = QLabel(f"00:00 / 00:00")
        self.time_label.setFixedWidth(100) 
        
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.addWidget(self.video_widget, 1) 
        
        h_control_layout = QHBoxLayout()
        h_control_layout.addWidget(self.time_label)
        h_control_layout.addWidget(self.slider)
        self.v_layout.addLayout(h_control_layout)
        
        self.total_duration = 0

class DynamicSingleLabelGroup(QWidget):
    
    remove_category_signal = pyqtSignal(str) 
    remove_label_signal = pyqtSignal(str) 
    value_changed = pyqtSignal(str, object) 

    def __init__(self, label_head_name, label_type_definition, parent=None):
        super().__init__(parent)
        self.head_name = label_head_name
        self.definition = label_type_definition
        self.radio_buttons = {}
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True) 
        
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 5, 0, 5)

        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.label_title = QLabel(f"{self.head_name.replace('_', ' ').title()}:")
        self.label_title.setObjectName("subtitleLabel")
        
        self.trash_btn = QPushButton()
        self.trash_btn.setFixedSize(24, 24)
        self.trash_btn.setFlat(True)
        self.trash_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.trash_btn.setToolTip("Remove this category")
        self.trash_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.trash_btn.clicked.connect(self._on_remove_category_clicked)
        
        header_layout.addWidget(self.label_title)
        header_layout.addStretch()
        header_layout.addWidget(self.trash_btn)
        
        self.v_layout.addWidget(header_widget)
        
        self.radio_container = QWidget()
        self.radio_layout = QVBoxLayout(self.radio_container)
        self.radio_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.addWidget(self.radio_container)
        
        self.manager_group = QGroupBox() 
        self.manager_group.setFlat(True)
        v_manager_layout = QVBoxLayout(self.manager_group)
        v_manager_layout.setContentsMargins(0, 10, 0, 5)
        
        h_add_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(f"New {self.head_name} type...")
        self.add_btn = QPushButton("Add")
        h_add_layout.addWidget(self.input_field, 1)
        h_add_layout.addWidget(self.add_btn)
        
        v_manager_layout.addLayout(h_add_layout)
        self.v_layout.addWidget(self.manager_group)

        self.update_radios(self.definition.get("labels", []))

    def _on_remove_category_clicked(self):
        self.remove_category_signal.emit(self.head_name)

    def update_radios(self, new_types):
        self.button_group.setExclusive(False)
        while self.radio_layout.count():
            item = self.radio_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        self.radio_buttons.clear()
        sorted_types = sorted(list(set(new_types)))
        
        for type_name in sorted_types: 
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 2, 0, 2)
            
            rb = QRadioButton(type_name)
            rb.clicked.connect(self._on_radio_clicked)
            self.radio_buttons[type_name] = rb
            self.button_group.addButton(rb)
            
            del_label_btn = QPushButton("×")
            del_label_btn.setFixedSize(20, 20)
            del_label_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_label_btn.setStyleSheet(get_square_remove_btn_style())
            del_label_btn.clicked.connect(lambda _, n=type_name: self.remove_label_signal.emit(n))
            
            row_layout.addWidget(rb)
            row_layout.addStretch()
            row_layout.addWidget(del_label_btn)
            self.radio_layout.addWidget(row_widget)
            
        self.button_group.setExclusive(True)
    
    def _on_radio_clicked(self):
        self.value_changed.emit(self.head_name, self.get_checked_label())

    def get_checked_label(self):
        checked_btn = self.button_group.checkedButton()
        return checked_btn.text() if checked_btn else None

    def set_checked_label(self, label_name):
        self.blockSignals(True)
        self.button_group.setExclusive(False)
        for rb in self.radio_buttons.values(): rb.setChecked(False)
        self.button_group.setExclusive(True)
        if label_name in self.radio_buttons:
            self.radio_buttons[label_name].setChecked(True)
        self.blockSignals(False)

class DynamicMultiLabelGroup(QWidget):
    
    remove_category_signal = pyqtSignal(str) 
    remove_label_signal = pyqtSignal(str) 
    value_changed = pyqtSignal(str, object) 

    def __init__(self, label_head_name, label_type_definition, parent=None):
        super().__init__(parent)
        self.head_name = label_head_name
        self.definition = label_type_definition
        self.checkboxes = {}
        
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(0, 5, 0, 5)

        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.label_title = QLabel(f"{self.head_name.replace('_', ' ').title()}:")
        self.label_title.setObjectName("subtitleLabel")
        
        self.trash_btn = QPushButton()
        self.trash_btn.setFixedSize(24, 24)
        self.trash_btn.setFlat(True)
        self.trash_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.trash_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.trash_btn.clicked.connect(self._on_remove_category_clicked)
        
        header_layout.addWidget(self.label_title)
        header_layout.addStretch()
        header_layout.addWidget(self.trash_btn)
        
        self.v_layout.addWidget(header_widget)
        
        self.checkbox_container = QWidget()
        self.checkbox_layout = QVBoxLayout(self.checkbox_container)
        self.checkbox_layout.setContentsMargins(0, 0, 0, 0)
        self.v_layout.addWidget(self.checkbox_container)
        
        self.manager_group = QGroupBox() 
        self.manager_group.setFlat(True)
        h_layout = QHBoxLayout(self.manager_group)
        h_layout.setContentsMargins(0, 10, 0, 5)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(f"New {self.head_name} type...")
        self.add_btn = QPushButton("Add")
        
        h_layout.addWidget(self.input_field, 1)
        h_layout.addWidget(self.add_btn)
        self.v_layout.addWidget(self.manager_group) 
        self.update_checkboxes(self.definition.get("labels", []))

    def _on_remove_category_clicked(self):
        self.remove_category_signal.emit(self.head_name)

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
            del_label_btn.clicked.connect(lambda _, n=type_name: self.remove_label_signal.emit(n))

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
        if label_list is None: label_list = []
        checked_set = set(label_list)
        for cb_name, cb in self.checkboxes.items():
            cb.setChecked(cb_name in checked_set)
        self.blockSignals(False)