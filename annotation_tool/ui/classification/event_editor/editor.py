import math
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QGroupBox, QLineEdit, QScrollArea, QFrame, QProgressBar, QToolTip, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QCursor

from .dynamic_widgets import DynamicSingleLabelGroup, DynamicMultiLabelGroup

class NativeDonutChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 220)
        self.setMouseTracking(True) 
        
        self.data_dict = {}
        self.top_label = ""
        self.slices_info = [] 
        self.setVisible(False)

    def update_chart(self, top_label, conf_dict):
        self.top_label = top_label
        
        sorted_data = {top_label: conf_dict.get(top_label, 0.0)}
        for k, v in conf_dict.items():
            if k != top_label:
                sorted_data[k] = v
                
        self.data_dict = sorted_data
        self.repaint()
        self.setVisible(True)

    def paintEvent(self, event):
        if not self.data_dict:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        margin = 30
        rect = QRectF(margin, margin, self.width() - margin * 2, self.height() - margin * 2)
        pen_width = 35

        start_angle_qt = 90 * 16 
        self.slices_info.clear()

        color_top = QColor("#4CAF50") 
        colors_other = [QColor("#607D8B"), QColor("#78909C"), QColor("#546E7A"), QColor("#455A64")]
        color_idx = 0

        current_angle_deg = 0.0 

        for label, prob in self.data_dict.items():
            span_deg = prob * 360
            span_angle_qt = int(round(-span_deg * 16))

            if span_angle_qt == 0:
                continue

            color = color_top if label == self.top_label else colors_other[color_idx % len(colors_other)]
            if label != self.top_label:
                color_idx += 1

            pen = QPen(color)
            pen.setWidth(pen_width)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            painter.setPen(pen)

            painter.drawArc(rect, start_angle_qt, span_angle_qt)

            self.slices_info.append({
                "label": label,
                "prob": prob,
                "start_deg": current_angle_deg,
                "end_deg": current_angle_deg + span_deg
            })

            start_angle_qt += span_angle_qt
            current_angle_deg += span_deg

        painter.setPen(QColor("white"))
        font = QFont("Arial", 12, QFont.Weight.Bold)
        painter.setFont(font)
        top_prob = self.data_dict.get(self.top_label, 0.0)
        
        text_rect = QRectF(0, 0, self.width(), self.height())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, f"{self.top_label}\n{top_prob*100:.1f}%")

    def mouseMoveEvent(self, event):
        if not self.data_dict:
            return

        pos = event.position()
        center_x = self.width() / 2
        center_y = self.height() / 2
        dx = pos.x() - center_x
        dy = pos.y() - center_y

        distance = math.sqrt(dx**2 + dy**2)
        radius = (self.width() - 60) / 2 
        pen_width = 35
        
        if distance < (radius - pen_width/2) or distance > (radius + pen_width/2):
            QToolTip.hideText()
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad) + 90
        if angle_deg < 0:
            angle_deg += 360

        hovered_text = None
        for slice_info in self.slices_info:
            if slice_info["start_deg"] <= angle_deg <= slice_info["end_deg"]:
                hovered_text = f"{slice_info['label']}: {slice_info['prob']*100:.1f}%"
                break

        if hovered_text:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            QToolTip.showText(event.globalPosition().toPoint(), hovered_text, self)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            QToolTip.hideText()


class ClassificationEventEditor(QWidget):
    add_head_clicked = pyqtSignal(str)
    remove_head_clicked = pyqtSignal(str)
    style_mode_changed = pyqtSignal(str)
    
    smart_infer_requested = pyqtSignal() 
    confirm_infer_requested = pyqtSignal(dict) 
    
    batch_run_requested = pyqtSignal(int, int)
    batch_confirm_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(350)
        layout = QVBoxLayout(self)
        
        self.is_batch_mode_active = False
        self.pending_batch_results = {}
        
        # 1. Undo/Redo Controls
        h_undo = QHBoxLayout()
        self.undo_btn = QPushButton("Undo")
        self.redo_btn = QPushButton("Redo")
        for btn in [self.undo_btn, self.redo_btn]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setEnabled(False) 
            btn.setProperty("class", "editor_control_btn")
        h_undo.addWidget(self.undo_btn)
        h_undo.addWidget(self.redo_btn)
        layout.addLayout(h_undo)
        
        # 2. Task Information
        self.task_label = QLabel("Task: N/A")
        self.task_label.setProperty("class", "editor_task_lbl")
        layout.addWidget(self.task_label)

        # 3. Schema Editor
        schema_box = QGroupBox("Category Editor")
        schema_layout = QHBoxLayout(schema_box)
        self.new_head_edit = QLineEdit()
        self.new_head_edit.setPlaceholderText("New Category Name...")
        self.add_head_btn = QPushButton("Add Head")
        self.add_head_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_head_btn.clicked.connect(lambda: self.add_head_clicked.emit(self.new_head_edit.text()))
        schema_layout.addWidget(self.new_head_edit)
        schema_layout.addWidget(self.add_head_btn)
        layout.addWidget(schema_box)

        # --- 4. Hand Annotation  ---
        self.manual_box = QGroupBox("Hand Annotations")
        self.manual_box.setEnabled(False) 
        manual_layout = QVBoxLayout(self.manual_box)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self.label_container = QWidget()
        self.label_container_layout = QVBoxLayout(self.label_container)
        self.label_container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll.setWidget(self.label_container)
        manual_layout.addWidget(scroll)
        layout.addWidget(self.manual_box, 1) 

        # --- 5. Smart Annotation ---
        self.smart_box = QGroupBox("Smart Annotation")
        smart_layout = QVBoxLayout(self.smart_box)
        
        # Two Buttons
        btn_h_layout = QHBoxLayout()
        self.btn_smart_infer = QPushButton("🚀Single Inference")
        self.btn_smart_infer.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_smart_infer.clicked.connect(self.smart_infer_requested.emit)
        
        self.btn_batch_infer = QPushButton("🚀Batch Inference")
        self.btn_batch_infer.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_batch_infer.clicked.connect(lambda: self.batch_input_widget.setVisible(not self.batch_input_widget.isVisible()))

        btn_h_layout.addWidget(self.btn_smart_infer)
        btn_h_layout.addWidget(self.btn_batch_infer)
        smart_layout.addLayout(btn_h_layout)

        # Input Box
        self.batch_input_widget = QWidget()
        h_batch = QHBoxLayout(self.batch_input_widget)
        h_batch.setContentsMargins(0, 5, 0, 5)
        self.spin_start = QLineEdit()
        self.spin_start.setPlaceholderText("Start Idx")
        self.spin_end = QLineEdit()
        self.spin_end.setPlaceholderText("End Idx")
        self.btn_run_batch = QPushButton("Run Batch")
        self.btn_run_batch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run_batch.clicked.connect(self._on_run_batch_clicked)
        h_batch.addWidget(self.spin_start)
        h_batch.addWidget(self.spin_end)
        h_batch.addWidget(self.btn_run_batch)
        self.batch_input_widget.setVisible(False)
        
        self.infer_progress = QProgressBar()
        self.infer_progress.setRange(0, 0) 
        self.infer_progress.setVisible(False)
        
        self.chart_widget = NativeDonutChart()
        
        self.batch_result_text = QTextEdit()
        self.batch_result_text.setReadOnly(True)
        self.batch_result_text.setVisible(False)
        self.batch_result_text.setMinimumHeight(200)
        
        smart_layout.addWidget(self.batch_input_widget)
        smart_layout.addWidget(self.infer_progress)
        smart_layout.addWidget(self.chart_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        smart_layout.addWidget(self.batch_result_text)
        layout.addWidget(self.smart_box)

        btn_row = QHBoxLayout()
        self.confirm_btn = QPushButton("✅ Confirm Annotation")
        self.clear_sel_btn = QPushButton("🗑️ Clear Selection")
        self.confirm_btn.setProperty("class", "editor_save_btn")
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_sel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.confirm_btn.clicked.connect(self.on_confirm_clicked)

        btn_row.addWidget(self.confirm_btn)
        btn_row.addWidget(self.clear_sel_btn)
        layout.addLayout(btn_row)
        
        self.label_groups = {} 

    def _on_run_batch_clicked(self):
        try:
            start_idx = int(self.spin_start.text().strip())
            end_idx = int(self.spin_end.text().strip())
            self.batch_run_requested.emit(start_idx, end_idx)
        except ValueError:
            pass 

    def on_confirm_clicked(self):
        if self.is_batch_mode_active:
            self.batch_confirm_requested.emit(self.pending_batch_results)
        self.reset_smart_inference()

    def reset_smart_inference(self):
        self.is_batch_mode_active = False
        self.chart_widget.setVisible(False)
        self.batch_result_text.setVisible(False)
        self.btn_smart_infer.setEnabled(True)
        self.btn_batch_infer.setEnabled(True)
        self.infer_progress.setVisible(False)

    def show_inference_loading(self, is_loading: bool):
        self.btn_smart_infer.setEnabled(not is_loading)
        self.btn_batch_infer.setEnabled(not is_loading)
        self.infer_progress.setVisible(is_loading)
        if is_loading:
            self.chart_widget.setVisible(False)
            self.batch_result_text.setVisible(False)

    def display_inference_result(self, target_head: str, predicted_label: str, conf_dict: dict):
        self.show_inference_loading(False)
        self.is_batch_mode_active = False
        self.chart_widget.update_chart(predicted_label, conf_dict)
        
        group = self.label_groups.get(target_head)
        if group:
            if hasattr(group, 'set_checked_label'):
                group.set_checked_label(predicted_label)
            elif hasattr(group, 'set_checked_labels'):
                group.set_checked_labels([predicted_label])
                
    def display_batch_inference_result(self, result_text: str, batch_predictions: dict):
        self.show_inference_loading(False)
        self.is_batch_mode_active = True
        self.pending_batch_results = batch_predictions
        self.chart_widget.setVisible(False)
        self.batch_result_text.setText(result_text)
        self.batch_result_text.setVisible(True)

    def setup_dynamic_labels(self, label_definitions):
        while self.label_container_layout.count():
            item = self.label_container_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.label_groups = {}

        for head, defn in label_definitions.items():
            l_type = defn.get('type', 'single_label')
            if l_type == 'single_label':
                group = DynamicSingleLabelGroup(head, defn)
            else:
                group = DynamicMultiLabelGroup(head, defn)
            
            group.remove_category_signal.connect(self.remove_head_clicked.emit)
            self.label_container_layout.addWidget(group)
            self.label_groups[head] = group
        
        self.label_container_layout.addStretch()

    def set_annotation(self, data):
        self.reset_smart_inference()
        
        if not data: data = {}
        for head, group in self.label_groups.items():
            val = data.get(head)
            if hasattr(group, 'set_checked_label'):
                group.set_checked_label(val)
            elif hasattr(group, 'set_checked_labels'):
                group.set_checked_labels(val)

    def get_annotation(self):
        result = {}
        for head, group in self.label_groups.items():
            if hasattr(group, 'get_checked_label'):
                val = group.get_checked_label()
                if val: result[head] = val
            elif hasattr(group, 'get_checked_labels'):
                vals = group.get_checked_labels()
                if vals: result[head] = vals
        return result

    def clear_selection(self):
        self.reset_smart_inference()
        for group in self.label_groups.values():
            if hasattr(group, 'set_checked_label'):
                group.set_checked_label(None)
            elif hasattr(group, 'set_checked_labels'):
                group.set_checked_labels([])
