import sys
import os
import time
import random
import json
import datetime 
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QStyle
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen

from ui_components import MainWindowUI

# --- 模拟AI模型和排序辅助函数 ---
def run_model_on_action(action_clips):
    print(f"Analyzing Action: {os.path.dirname(action_clips[0])}...")
    foul_types = [
        "Tackling", "Standing Tackling", "Holding", "Pushing", 
        "Challenge", "Elbowing", "High Leg", "Dive"
    ]
    foul_probs = [random.random() for _ in foul_types]
    foul_sum = sum(foul_probs)
    # 修复 TypeError: 使用 foul_probs (float list) 进行归一化
    normalized_foul_probs = [p / foul_sum for p in foul_probs]
    foul_distribution = dict(zip(foul_types, normalized_foul_probs))
    
    severities = ["Offence + Red Card", "Offence + Yellow Card", "Offence + No Card", "No Offence"]
    
    # 修复 TypeError: 生成原始随机值列表
    raw_sev_probs = [random.random() for _ in severities]
    sev_sum = sum(raw_sev_probs)
    # 修复 TypeError: 使用 raw_sev_probs (float list) 进行归一化
    normalized_sev_probs = [p / sev_sum for p in raw_sev_probs]
    
    severity_distribution = dict(zip(severities, normalized_sev_probs))
    return {"foul_distribution": foul_distribution, "severity_distribution": severity_distribution}

def get_action_number(entry):
    try:
        return int(entry.name.split('_')[1])
    except (IndexError, ValueError):
        return float('inf')

# --- 主应用逻辑类 ---
class ActionClassifierApp(QMainWindow):
    REVERSE_SEVERITY_MAP = {
        "5.0": "Offence + Red Card",
        "3.0": "Offence + Yellow Card",
        "1.0": "Offence + No Card",
        "": "No Offence" 
    }

    # --- 筛选器常量 ---
    FILTER_ALL = 0
    FILTER_DONE = 1
    FILTER_NOT_DONE = 2
    
    # 默认加载路径 (Mac路径)
    DEFAULT_LOAD_PATH = "/Users/jintaoma/Downloads/test"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SoccerNet Pro Analysis Tool (Action Classification​)")
        self.setGeometry(100, 100, 1400, 900)
        
        self.ui = MainWindowUI()
        self.setCentralWidget(self.ui)

        self.analysis_results = {} 
        self.manual_annotations = {} 
        
        self.action_path_to_name = {}
        self.action_item_data = [] # 存储预加载的 Action 目录信息 (name, path)
        
        self.action_item_map = {} # QTreeWidget item 映射 (仅在加载JSON后填充)
        
        self.current_json_path = None
        self.json_loaded = False 
        
        # 状态指示器 (蓝色对钩)
        bright_blue = QColor("#00BFFF") 
        self.done_icon = self._create_checkmark_icon(bright_blue)
        self.empty_icon = QIcon() 
        
        self.connect_signals()
        self.apply_stylesheet()
        
        # --- 默认加载 Action 文件夹路径 (预扫描，但不显示) ---
        if os.path.isdir(self.DEFAULT_LOAD_PATH):
            self._preload_action_folders(self.DEFAULT_LOAD_PATH)
        else:
            QMessageBox.warning(self, "Warning", f"Default action folder not found:\n{self.DEFAULT_LOAD_PATH}")
        
        # --- 初始禁用标注功能 ---
        self.ui.right_panel.manual_group_box.setEnabled(False)
        self.ui.right_panel.start_button.setEnabled(False)

        # --- 设置默认筛选器为 "Show Done" ---
        self.ui.left_panel.filter_combo.blockSignals(True)
        self.ui.left_panel.filter_combo.setCurrentIndex(self.FILTER_DONE) 
        self.ui.left_panel.filter_combo.blockSignals(False)
    
    # --- 状态指示器辅助方法 (不变) ---
    def _create_checkmark_icon(self, color):
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent) 
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing) 
        pen = QPen(color)
        pen.setWidth(2) 
        pen.setCapStyle(Qt.PenCapStyle.RoundCap) 
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin) 
        painter.setPen(pen)
        points = [ QPointF(4, 9), QPointF(7, 12), QPointF(12, 5) ]
        painter.drawPolyline(points)
        painter.end()
        return QIcon(pixmap)

    def update_action_item_status(self, action_path):
        action_item = self.action_item_map.get(action_path)
        if not action_item:
            return 
        is_done = (action_path in self.manual_annotations) or \
                  (action_path in self.analysis_results)
        
        if is_done:
            action_item.setIcon(0, self.done_icon)
        else:
            action_item.setIcon(0, self.empty_icon)
            
        self.apply_action_filter()

    def _show_temp_message_box(self, title, message, icon=QMessageBox.Icon.Information, duration_ms=1500):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        timer = QTimer(msg_box)
        timer.timeout.connect(msg_box.accept) 
        timer.setSingleShot(True)
        timer.start(duration_ms)
        msg_box.exec()

    def connect_signals(self):
        """Connects all UI element signals to the application's logic methods."""
        self.ui.left_panel.clear_button.clicked.connect(self.clear_action_list)
        self.ui.left_panel.import_button.clicked.connect(self.import_annotations) 
        self.ui.left_panel.action_tree.currentItemChanged.connect(self.on_item_selected)
        
        self.ui.left_panel.filter_combo.currentIndexChanged.connect(self.apply_action_filter)
        
        self.ui.center_panel.play_button.clicked.connect(self.play_video)
        self.ui.center_panel.multi_view_button.clicked.connect(self.show_all_views)

        self.ui.right_panel.start_button.clicked.connect(self.start_analysis)
        
        self.ui.right_panel.save_button.clicked.connect(self.save_results_to_json)
        self.ui.right_panel.export_button.clicked.connect(self.export_results_to_json)
        
        self.ui.right_panel.confirm_manual_button.clicked.connect(self.save_manual_annotation)
        self.ui.right_panel.clear_manual_button.clicked.connect(self.clear_current_manual_annotation)


    def apply_stylesheet(self):
        try:
            with open("style.qss", "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            try:
                with open("style.qss.py", "r") as f:
                    print("Warning: style.qss not found. Using default styles.") 
            except FileNotFoundError:
                 print("Warning: style.qss and style.qss.py not found. Using default styles.")

    def apply_action_filter(self):
        """根据下拉菜单中的选择，隐藏或显示 action item。"""
        current_filter = self.ui.left_panel.filter_combo.currentIndex()

        if current_filter == self.FILTER_ALL:
            for item in self.action_item_map.values():
                item.setHidden(False)
            return

        for action_path, item in self.action_item_map.items():
            is_done = (action_path in self.manual_annotations) or \
                      (action_path in self.analysis_results)
            
            if current_filter == self.FILTER_DONE:
                item.setHidden(not is_done)
            elif current_filter == self.FILTER_NOT_DONE:
                item.setHidden(is_done)

    def _preload_action_folders(self, dir_path):
        """扫描并预加载 Action 文件夹路径，但不填充 QTreeWidget。"""
        if not os.path.isdir(dir_path):
            return

        self.action_path_to_name.clear()
        self.action_item_data.clear()
        
        for entry in sorted(os.scandir(dir_path), key=get_action_number):
            if entry.is_dir() and entry.name.startswith("action_"):
                self.action_item_data.append({'name': entry.name, 'path': entry.path})
                self.action_path_to_name[entry.path] = entry.name
                
    def _populate_action_tree(self):
        """将预加载的数据实际填充到 QTreeWidget 中。"""
        if not self.action_item_data:
            return

        self.ui.left_panel.action_tree.clear()
        self.action_item_map.clear()
        
        for data in self.action_item_data:
            action_item = self.ui.left_panel.add_action_item(data['name'], data['path'])
            self.action_item_map[data['path']] = action_item
            
        # 初始填充后，应用筛选器 (默认 Show Done)
        self.apply_action_filter()
            
    def import_annotations(self):
        # 检查是否有Action文件夹数据，没有则提示先加载
        if not self.action_path_to_name:
            QMessageBox.warning(self, "Import Blocked", "Please ensure the default action folder is valid before importing annotations.")
            return
            
        file_path, _ = QFileDialog.getOpenFileName(self, "Select GAC JSON Annotation File", "", "JSON Files (*.json)")
        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to read or parse JSON file: {e}")
            return
        
        if 'data' not in data or not isinstance(data['data'], list):
            QMessageBox.warning(self, "Import Warning", "JSON file does not contain a 'data' key, or 'data' is not a list.")
            return

        imported_count = 0
        action_name_to_path = {v: k for k, v in self.action_path_to_name.items()}

        # 检查是否是第一次加载，如果是，记录当前手动标注数量
        is_first_json_load = not self.json_loaded
        
        for item in data['data']:
            action_name = item.get('id')
            if not action_name:
                continue
                
            action_path = action_name_to_path.get(action_name)
            if not action_path:
                print(f"Warning: Action '{action_name}' from JSON not found in loaded folders. Skipping.")
                continue 

            item_labels = item.get('labels', {})
            foul_data = item_labels.get('foul_type', {})
            sev_data = item_labels.get('severity', {})
            foul_label = foul_data.get('label')
            sev_label = sev_data.get('label')

            if foul_label or sev_label:
                self.manual_annotations[action_path] = {
                    "foul": foul_label,
                    "severity": sev_label
                }
                imported_count += 1
        
        self.current_json_path = file_path
        
        # 只有在导入成功后，才填充并显示 Action Tree
        if is_first_json_load:
            self._populate_action_tree()
        
        self.json_loaded = True # 成功导入JSON，设置状态
        
        # 导入后需要更新所有 Action 状态，并重新应用筛选器
        for path in self.action_path_to_name.keys():
            self.update_action_item_status(path) 
        
        self.update_save_export_button_state()
        self._show_temp_message_box("Import Complete", 
                                    f"Successfully imported {imported_count} annotations from GAC JSON.", 
                                    QMessageBox.Icon.Information, 2000)

        current_item = self.ui.left_panel.action_tree.currentItem()
        if current_item:
            self.on_item_selected(current_item, None) 


    def clear_action_list(self):
        # 清空 QTreeWidget 的显示
        self.ui.left_panel.action_tree.clear()
        
        # 清空所有数据
        self.analysis_results.clear()
        self.manual_annotations.clear()
        self.action_item_map.clear()
        
        # 保留 self.action_path_to_name 和 self.action_item_data (预加载数据)
        
        self.current_json_path = None
        self.json_loaded = False # 重置JSON加载状态
        self.update_save_export_button_state()

        self.ui.right_panel.start_button.setEnabled(False)
        self.ui.right_panel.results_widget.setVisible(False)
        self.ui.center_panel.multi_view_button.setEnabled(False)
        self.ui.right_panel.clear_manual_selection()
        
        # 禁用标注功能
        self.ui.right_panel.manual_group_box.setEnabled(False) 
        self.ui.right_panel.manual_group_box.setChecked(False) 
        self.ui.right_panel.auto_group_box.setChecked(False)
        
        # 重置筛选器下拉菜单
        self.ui.left_panel.filter_combo.blockSignals(True)
        self.ui.left_panel.filter_combo.setCurrentIndex(self.FILTER_ALL)
        self.ui.left_panel.filter_combo.blockSignals(False)


    def on_item_selected(self, current_item, _):
        if not current_item:
            self.ui.right_panel.start_button.setEnabled(False)
            self.ui.right_panel.manual_group_box.setEnabled(False)
            self.ui.right_panel.auto_group_box.setChecked(False)
            return
        
        is_action_item = current_item.childCount() > 0
        # 标注和分析的启用取决于：1. 选择了Action文件夹； 2. 已导入JSON
        can_annotate = is_action_item and self.json_loaded
        
        self.ui.right_panel.manual_group_box.setEnabled(can_annotate)
        self.ui.right_panel.start_button.setEnabled(can_annotate)

        self.ui.center_panel.multi_view_button.setEnabled(is_action_item)
        
        if is_action_item:
            if current_item.childCount() > 0:
                first_clip_path = current_item.child(0).data(0, Qt.ItemDataRole.UserRole)
            else:
                first_clip_path = None
            self.ui.center_panel.show_single_view(first_clip_path)
            action_path = current_item.data(0, Qt.ItemDataRole.UserRole)
        else:
            clip_path = current_item.data(0, Qt.ItemDataRole.UserRole)
            self.ui.center_panel.show_single_view(clip_path)
            action_path = current_item.parent().data(0, Qt.ItemDataRole.UserRole)
        
        self.display_analysis_results(action_path)
        self.display_manual_annotation(action_path)
        self.update_save_export_button_state() 
            
    def play_video(self):
        self.ui.center_panel.toggle_play_pause()

    def show_all_views(self):
        current_item = self.ui.left_panel.action_tree.currentItem()
        if current_item and current_item.childCount() > 0:
            clip_paths = [current_item.child(j).data(0, Qt.ItemDataRole.UserRole) for j in range(current_item.childCount())]
            self.ui.center_panel.show_all_views(clip_paths)

    def start_analysis(self):
        # 额外的JSON检查
        if not self.json_loaded:
             self._show_temp_message_box("Action Blocked", 
                                        "Please import a GAC JSON file before starting analysis.", 
                                        QMessageBox.Icon.Warning, 2000)
             return
             
        current_item = self.ui.left_panel.action_tree.currentItem()
        if not current_item or current_item.childCount() == 0:
            return

        self.ui.right_panel.start_button.setEnabled(False)
        self.ui.left_panel.action_tree.setEnabled(False)

        action_path = current_item.data(0, Qt.ItemDataRole.UserRole)
        clip_paths = [current_item.child(j).data(0, Qt.ItemDataRole.UserRole) for j in range(current_item.childCount())]
        
        if clip_paths:
            self.ui.right_panel.progress_bar.setVisible(True)
            total_duration = 3.0
            steps = 100
            self.ui.right_panel.progress_bar.setMaximum(steps)
            for i in range(steps + 1):
                self.ui.right_panel.progress_bar.setValue(i)
                time.sleep(total_duration / steps)
                QApplication.processEvents()
            self.ui.right_panel.progress_bar.setVisible(False)

            result = run_model_on_action(clip_paths)
            self.analysis_results[action_path] = result
            self.ui.right_panel.export_button.setEnabled(True)
            self.display_analysis_results(action_path)
            self.update_action_item_status(action_path)
        
        self.ui.right_panel.start_button.setEnabled(True)
        self.ui.left_panel.action_tree.setEnabled(True)
        self.update_save_export_button_state()

    def _get_current_action_path(self):
        current_item = self.ui.left_panel.action_tree.currentItem()
        if not current_item:
            return None
        if current_item.childCount() > 0:
            return current_item.data(0, Qt.ItemDataRole.UserRole)
        else:
            return current_item.parent().data(0, Qt.ItemDataRole.UserRole)

    def save_manual_annotation(self):
        # 额外的JSON检查
        if not self.json_loaded:
             self._show_temp_message_box("Action Blocked", 
                                        "Please import a GAC JSON file before saving annotations.", 
                                        QMessageBox.Icon.Warning, 2000)
             return
             
        action_path = self._get_current_action_path()
        if not action_path:
            return
        
        data = self.ui.right_panel.get_manual_annotation()
        
        if data["foul"] or data["severity"]:
            self.manual_annotations[action_path] = data
            self._show_temp_message_box("Success", 
                                        f"Annotation saved for {os.path.basename(action_path)}.", 
                                        QMessageBox.Icon.Information, 1500)
            self.ui.right_panel.manual_group_box.setChecked(True) 
        elif action_path in self.manual_annotations:
            del self.manual_annotations[action_path]
            self._show_temp_message_box("Success", 
                                        f"Annotation cleared for {os.path.basename(action_path)}.", 
                                        QMessageBox.Icon.Information, 1500)
            self.ui.right_panel.manual_group_box.setChecked(False) 
        else:
            self._show_temp_message_box("No Selection", 
                                        "Please select a foul type or severity to save.",
                                        QMessageBox.Icon.Warning, 1500)

        self.update_save_export_button_state()
        self.update_action_item_status(action_path)

    def clear_current_manual_annotation(self):
        action_path = self._get_current_action_path()
        if not action_path:
            return
            
        self.ui.right_panel.clear_manual_selection()
        
        if action_path in self.manual_annotations:
            del self.manual_annotations[action_path]
            self._show_temp_message_box("Cleared", 
                                        f"Annotation for {os.path.basename(action_path)} has been cleared.",
                                        QMessageBox.Icon.Information, 1500)
        
        self.ui.right_panel.manual_group_box.setChecked(False) 

        self.update_save_export_button_state()
        self.update_action_item_status(action_path)

    def display_manual_annotation(self, action_path):
        if action_path in self.manual_annotations:
            data = self.manual_annotations[action_path]
            self.ui.right_panel.set_manual_annotation(data)
            self.ui.right_panel.manual_group_box.setChecked(True) 
        else:
            self.ui.right_panel.clear_manual_selection()
            self.ui.right_panel.manual_group_box.setChecked(False)

    def display_analysis_results(self, action_path):
        if action_path in self.analysis_results:
            result = self.analysis_results[action_path]
            self.ui.right_panel.update_results(result)
            self.ui.right_panel.results_widget.setVisible(True)
            self.ui.right_panel.auto_group_box.setChecked(True)
        else:
            self.ui.right_panel.results_widget.setVisible(False)
            self.ui.right_panel.auto_group_box.setChecked(False)

    def update_save_export_button_state(self):
        """检查是否有任何数据可供导出，并更新 Save 和 Export 按钮"""
        # 只有在导入了 JSON 且有数据的情况下才能导出
        can_export = self.json_loaded and (bool(self.analysis_results) or bool(self.manual_annotations))
        self.ui.right_panel.export_button.setEnabled(can_export)
        can_save = can_export and (self.current_json_path is not None)
        self.ui.right_panel.save_button.setEnabled(can_save)

    def save_results_to_json(self):
        """保存到 self.current_json_path (覆盖保存)。"""
        if not self.json_loaded:
             self._show_temp_message_box("Action Blocked", 
                                        "Please import a GAC JSON file before saving.", 
                                        QMessageBox.Icon.Warning, 2000)
             return
             
        if self.current_json_path:
            self._write_gac_json(self.current_json_path)
        else:
            self.export_results_to_json()

    def export_results_to_json(self):
        """打开 "Save As..." (另存为) 对话框，让用户选择一个新路径。"""
        if not self.json_loaded:
             self._show_temp_message_box("Action Blocked", 
                                        "Please import a GAC JSON file before exporting.", 
                                        QMessageBox.Icon.Warning, 2000)
             return
             
        path, _ = QFileDialog.getSaveFileName(self, "Save GAC JSON Annotation As...", "", "JSON Files (*.json)")
        if not path: 
            return

        self._write_gac_json(path)
        self.current_json_path = path
        self.update_save_export_button_state()

    def _write_gac_json(self, file_path):
        """将当前所有标注 (手动和自动) 按照 GAC JSON 格式写入指定的文件路径。"""
        all_action_paths = set(self.analysis_results.keys()) | set(self.manual_annotations.keys())
        if not all_action_paths:
            self._show_temp_message_box("No Data", "There is no annotation data to save.", QMessageBox.Icon.Warning)
            return

        output_data = {
            "version": "1.0",
            "date": datetime.datetime.now().isoformat().split('T')[0],
            "dataset_name": "Action Classification Export",
            "metadata": {
                "created_by": "SoccerNet Pro Analysis Tool"
            },
            "tasks": ["action_classification"]
        }

        foul_types = list(self.ui.right_panel.foul_radio_buttons.keys())
        sev_types = list(self.ui.right_panel.sev_radio_buttons.keys())
        
        output_data["labels"] = {
            "foul_type": {
                "type": "single_label",
                "labels": foul_types
            },
            "severity": {
                "type": "single_label",
                "labels": sev_types
            }
        }

        output_data["data"] = []
        
        path_to_item_map = {}
        root = self.ui.left_panel.action_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            path_to_item_map[item.data(0, Qt.ItemDataRole.UserRole)] = item

        for action_path in all_action_paths:
            action_item = path_to_item_map.get(action_path)
            if not action_item:
                print(f"Warning: Could not find item for path {action_path}. Skipping export.")
                continue

            action_name = os.path.basename(action_path)
            auto_result = self.analysis_results.get(action_path)
            manual_result = self.manual_annotations.get(action_path)

            final_foul_class = None
            final_severity_class = None
            annotation_source = "None"

            if manual_result and manual_result.get("foul"):
                final_foul_class = manual_result.get("foul")
                annotation_source = "Manual"
            elif auto_result:
                foul_dist = auto_result['foul_distribution']
                final_foul_class = max(foul_dist, key=foul_dist.get)
                if annotation_source == "None": annotation_source = "Automated"
            
            if manual_result and manual_result.get("severity"):
                final_severity_class = manual_result.get("severity")
                if annotation_source != "Manual": annotation_source = "Manual" 
            elif auto_result:
                sev_dist = auto_result['severity_distribution']
                final_severity_class = max(sev_dist, key=sev_dist.get)
                if annotation_source == "None": annotation_source = "Automated"
            
            data_item = {
                "id": action_name,
                "metadata": {
                    "AnnotationSource": annotation_source 
                },
                "inputs": [],
                "labels": {}
            }

            for j in range(action_item.childCount()):
                clip_item = action_item.child(j)
                clip_path = clip_item.data(0, Qt.ItemDataRole.UserRole)
                clip_name_no_ext = os.path.splitext(os.path.basename(clip_path))[0]
                url_path = f"Dataset/Test/{action_name}/{clip_name_no_ext}" 
                data_item["inputs"].append({
                    "type": "video",
                    "path": url_path
                })
            
            if final_foul_class:
                data_item["labels"]["foul_type"] = {"label": final_foul_class}
            
            if final_severity_class:
                data_item["labels"]["severity"] = {"label": final_severity_class}

            output_data["data"].append(data_item)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=4, ensure_ascii=False)
            
            self._show_temp_message_box("Save Complete", 
                                        f"Annotations successfully saved to:\n{os.path.basename(file_path)}",
                                        QMessageBox.Icon.Information, 2000)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to write JSON file: {e}")
            print(f"Failed to export GAC JSON: {e}")


# --- 程序入口 ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ActionClassifierApp()
    window.show()
    sys.exit(app.exec())