# main.py

import sys
import os
import time
import random
import json
import datetime 
import shutil
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QStyle, QTreeWidgetItem
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen

# 确保 ui_components 导入正确
from ui_components import MainWindowUI, RightPanel

# --- 模拟AI模型和排序辅助函数 (保持不变) ---
def run_model_on_action(action_clips):
    # 确保在不同平台下路径显示正常
    path_to_display = os.path.dirname(action_clips[0]) if os.path.isdir(os.path.dirname(action_clips[0])) else os.path.basename(action_clips[0])
    print(f"Analyzing Action: {path_to_display}...")
    
    # 使用 RightPanel 的默认列表作为模拟模型的输出范围，以保持一致性
    foul_types = RightPanel.DEFAULT_FOUL_TYPES
    foul_probs = [random.random() for _ in foul_types]
    foul_sum = sum(foul_probs)
    normalized_foul_probs = [p / foul_sum for p in foul_probs]
    foul_distribution = dict(zip(foul_types, normalized_foul_probs))
    
    severities = RightPanel.DEFAULT_SEVERITY_TYPES
    
    raw_sev_probs = [random.random() for _ in severities]
    sev_sum = sum(raw_sev_probs)
    normalized_sev_probs = [p / sev_sum for p in raw_sev_probs]
    
    severity_distribution = dict(zip(severities, normalized_sev_probs))
    return {"foul_distribution": foul_distribution, "severity_distribution": severity_distribution}

def get_action_number(entry):
    try:
        # 尝试解析 action_xxx 或 virtual_action_xxx 后面的数字
        parts = entry.name.split('_')
        if len(parts) > 1 and parts[-1].isdigit():
            return int(parts[-1])
        if len(parts) > 2 and parts[-2].isdigit():
             return int(parts[-2])
        return float('inf')
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
    
    # --- 虚拟 Action Name 前缀 ---
    SINGLE_VIDEO_PREFIX = "virtual_action_" 
    
    # --- 相对路径定义 ---
    RELATIVE_PROJECT_FOLDER = "test" 
    
    # 默认的内置任务列表 (不允许删除)
    BUILT_IN_TASKS = [
        "Select Task...", 
        "action_classification", 
        "action_spotting", 
        "video_captioning", 
        "dense_video_captioning"
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SoccerNet Pro Analysis Tool (Action Classification​)")
        self.setGeometry(100, 100, 1400, 900)
        
        self.ui = MainWindowUI()
        self.setCentralWidget(self.ui)

        # --- 路径查找核心修改 ---
        # 1. 确定应用程序的基路径
        if getattr(sys, 'frozen', False):
            # 运行在 PyInstaller 环境中：基路径是可执行文件所在的目录
            base_dir = os.path.dirname(sys.executable)
        else:
            # 运行在标准 Python 环境中：基路径是 main.py 所在的目录
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        # 2. 设置 DEFAULT_LOAD_PATH 为相对路径 (EXE 旁边的 'test' 文件夹)
        self.DEFAULT_LOAD_PATH = os.path.join(base_dir, self.RELATIVE_PROJECT_FOLDER)
        
        # 3. 确保目录存在
        if not os.path.exists(self.DEFAULT_LOAD_PATH):
            try:
                os.makedirs(self.DEFAULT_LOAD_PATH, exist_ok=True)
                print(f"Created default video directory: {self.DEFAULT_LOAD_PATH}")
            except OSError as e:
                # 如果创建失败，弹出致命错误警告
                QMessageBox.critical(self, "Fatal Error", f"Failed to create default data directory:\n{self.DEFAULT_LOAD_PATH}\nCheck write permissions. Error: {e}")

        # ---------------------------

        self.analysis_results = {} 
        self.manual_annotations = {} 
        
        self.action_path_to_name = {}
        self.action_item_data = [] # 存储预加载的 Action 目录信息 (name, path)
        self.custom_tasks = set() # 新增：存储用户添加的自定义任务
        
        # --- 新增：存储自定义 Foul/Severity Type ---
        self.foul_types = set(RightPanel.DEFAULT_FOUL_TYPES)
        self.severity_types = set(RightPanel.DEFAULT_SEVERITY_TYPES)
        
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
            QMessageBox.warning(self, "Warning", f"Default action folder not found or inaccessible:\n{self.DEFAULT_LOAD_PATH}")
        
        # 确保默认 Annotation 内容是隐藏的 
        self.ui.right_panel.annotation_content_widget.setVisible(False) 

        # --- 设置默认筛选器为 "Show Done" ---
        self.ui.left_panel.filter_combo.blockSignals(True)
        self.ui.left_panel.filter_combo.setCurrentIndex(self.FILTER_DONE) 
        self.ui.left_panel.filter_combo.blockSignals(False)
    
    # --- 状态指示器辅助方法 (保持不变) ---
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
        msg_box.setStandardButtons(QMessageBox.StandardButton.NoButton) # 避免用户点击OK，只等计时器
        timer.start(duration_ms)
        msg_box.exec()

    def connect_signals(self):
        """Connects all UI element signals to the application's logic methods."""
        self.ui.left_panel.clear_button.clicked.connect(self.clear_action_list)
        self.ui.left_panel.import_button.clicked.connect(self.import_annotations) 
        self.ui.left_panel.add_video_button.clicked.connect(self.add_single_video) 
        
        self.ui.left_panel.action_tree.currentItemChanged.connect(self.on_item_selected)
        
        self.ui.left_panel.filter_combo.currentIndexChanged.connect(self.apply_action_filter)
        
        self.ui.center_panel.play_button.clicked.connect(self.play_video)
        self.ui.center_panel.multi_view_button.clicked.connect(self.show_all_views)
        
        # --- 连接顶部任务管理按钮信号 ---
        self.ui.right_panel.add_label_button.clicked.connect(self.add_custom_task)
        self.ui.right_panel.remove_label_button.clicked.connect(self.remove_custom_task)
        
        # --- 连接 Label Annotation 下拉框信号 ---
        self.ui.right_panel.label_combo.currentIndexChanged.connect(self.toggle_annotation_view)

        self.ui.right_panel.start_button.clicked.connect(self.start_analysis)
        
        self.ui.right_panel.save_button.clicked.connect(self.save_results_to_json)
        self.ui.right_panel.export_button.clicked.connect(self.export_results_to_json)
        
        self.ui.right_panel.confirm_manual_button.clicked.connect(self.save_manual_annotation)
        self.ui.right_panel.clear_manual_button.clicked.connect(self.clear_current_manual_annotation)
        
        # --- 新增：连接 Foul Type 管理按钮信号 ---
        self.ui.right_panel.foul_add_btn.clicked.connect(lambda: self.add_custom_type("foul"))
        self.ui.right_panel.foul_remove_btn.clicked.connect(lambda: self.remove_custom_type("foul"))
        
        # --- 新增：连接 Severity Type 管理按钮信号 ---
        self.ui.right_panel.sev_add_btn.clicked.connect(lambda: self.add_custom_type("severity"))
        self.ui.right_panel.sev_remove_btn.clicked.connect(lambda: self.remove_custom_type("severity"))


    def apply_stylesheet(self):
        """修改：处理 PyInstaller 打包后的资源路径问题"""
        
        # 1. 确定资源路径
        if getattr(sys, 'frozen', False):
            # PyInstaller 打包后的环境
            base_path = sys._MEIPASS
        else:
            # 正常运行时环境
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        style_path = os.path.join(base_path, "style.qss")

        try:
            with open(style_path, "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            # 兼容性处理，如果找不到，使用默认样式并打印警告
            QMessageBox.warning(self, "Warning", f"Stylesheet not found at {style_path}. Using default system styles.")
            print(f"Warning: style.qss not found at {style_path}. Using default system styles.")
        except Exception as e:
            print(f"Warning: Failed to load stylesheet: {e}")


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
        """扫描并预加载 Action 文件夹路径，包括新增的 virtual_action_ 文件夹。"""
        if not os.path.isdir(dir_path):
            return

        self.action_path_to_name.clear()
        self.action_item_data.clear()

        all_entries = sorted(os.scandir(dir_path), key=get_action_number)
        
        for entry in all_entries:
            if entry.is_dir() and (entry.name.startswith("action_") or entry.name.startswith(self.SINGLE_VIDEO_PREFIX)):
                self.action_item_data.append({'name': entry.name, 'path': entry.path})
                self.action_path_to_name[entry.path] = entry.name
                
    def add_single_video(self):
        """打开文件对话框，让用户选择单个视频文件，将其复制到虚拟 Action 文件夹。"""
        if not self.json_loaded:
             self._show_temp_message_box("Action Blocked", 
                                        "Please import a GAC JSON file before adding videos.", 
                                        QMessageBox.Icon.Warning, 2000)
             return
             
        # 必须有一个默认路径来创建 virtual_action_ 文件夹
        if not self.DEFAULT_LOAD_PATH or not os.path.isdir(self.DEFAULT_LOAD_PATH):
             QMessageBox.critical(self, "Action Blocked", 
                                  f"Video storage path not found: {self.DEFAULT_LOAD_PATH}\nCannot create virtual action folder.")
             return
             
        video_formats = "Video Files (*.mp4 *.avi *.mov)" 
        original_file_path, _ = QFileDialog.getOpenFileName(self, "Select Video File for Annotation", "", video_formats)
        
        if not original_file_path:
            return

        video_name = os.path.basename(original_file_path)
        
        action_name = ""
        virtual_action_path = ""
        counter = 1
        
        max_counter = 0
        for name in self.action_path_to_name.values():
            if name.startswith(self.SINGLE_VIDEO_PREFIX):
                try:
                    max_counter = max(max_counter, int(name.split('_')[-1]))
                except ValueError:
                    continue
        
        counter = max_counter + 1
        
        while True:
            action_name = f"{self.SINGLE_VIDEO_PREFIX}{counter:03d}"
            virtual_action_path = os.path.join(self.DEFAULT_LOAD_PATH, action_name)
            if not os.path.exists(virtual_action_path):
                break
            counter += 1
        
        try:
            os.makedirs(virtual_action_path)
            target_file_path = os.path.join(virtual_action_path, video_name)
            shutil.copy2(original_file_path, target_file_path) 
            
            action_path = virtual_action_path
            
            self.action_item_data.insert(0, {'name': action_name, 'path': action_path})
            self.action_path_to_name[action_path] = action_name
            
            self._populate_action_tree()
                
            new_item = self.action_item_map.get(action_path)
            if new_item:
                self.ui.left_panel.action_tree.setCurrentItem(new_item)
                    
            self.update_save_export_button_state()
            self._show_temp_message_box("Video Added", 
                                        f"'{video_name}' added to {action_name}.", 
                                        QMessageBox.Icon.Information, 2000)

        except Exception as e:
            QMessageBox.critical(self, "File Error", f"Failed to copy video or create folder: {e}")
            return
            
    def _populate_action_tree(self):
        """将预加载的数据实际填充到 QTreeWidget 中。"""
        if not self.action_item_data:
            return

        self.ui.left_panel.action_tree.clear()
        self.action_item_map.clear()
        
        action_folders = [data for data in self.action_item_data if data['name'].startswith("action_")]
        virtual_actions = [data for data in self.action_item_data if data['name'].startswith(self.SINGLE_VIDEO_PREFIX)]

        sorted_virtual = sorted(virtual_actions, key=lambda d: get_action_number(type('MockEntry', (object,), {'name': d['name']})()))
        sorted_actions = sorted(action_folders, key=lambda d: get_action_number(type('MockEntry', (object,), {'name': d['name']})()))
        
        final_list = sorted_virtual + sorted_actions

        for data in final_list:
            action_item = self.ui.left_panel.add_action_item(data['name'], data['path'])
            self.action_item_map[data['path']] = action_item
            
        for path in self.action_item_map.keys():
            self.update_action_item_status(path)
            
        self.apply_action_filter()

    # --- 新增方法: 添加自定义任务 (顶部下拉框) ---
    def add_custom_task(self):
        new_task_name = self.ui.right_panel.new_label_input.text().strip()
        
        if not new_task_name:
            self._show_temp_message_box("Warning", "Task name cannot be empty.", QMessageBox.Icon.Warning, 1500)
            return

        combo = self.ui.right_panel.label_combo
        
        if combo.findText(new_task_name) != -1:
            self._show_temp_message_box("Warning", f"Task '{new_task_name}' already exists.", QMessageBox.Icon.Warning, 1500)
            self.ui.right_panel.new_label_input.clear()
            return
            
        combo.addItem(new_task_name)
        self.custom_tasks.add(new_task_name)
        
        self._show_temp_message_box("Success", f"Task '{new_task_name}' added.", QMessageBox.Icon.Information, 1000)
        self.ui.right_panel.new_label_input.clear()
        
        if not combo.isEnabled():
            combo.setEnabled(True)


    # --- 新增方法: 移除自定义任务 (顶部下拉框) ---
    def remove_custom_task(self):
        combo = self.ui.right_panel.label_combo
        current_text = combo.currentText()
        current_index = combo.currentIndex()

        if current_index == 0:
            self._show_temp_message_box("Warning", "Cannot remove 'Select Task...'.", QMessageBox.Icon.Warning, 1500)
            return

        if current_text in self.BUILT_IN_TASKS:
            self._show_temp_message_box("Warning", f"Cannot remove built-in task: '{current_text}'.", QMessageBox.Icon.Warning, 1500)
            return

        combo.removeItem(current_index)
        
        if current_text in self.custom_tasks:
            self.custom_tasks.remove(current_text)
            
        self._show_temp_message_box("Success", f"Task '{current_text}' removed.", QMessageBox.Icon.Information, 1000)
        
        self.toggle_annotation_view()
        
    # --- 新增：添加自定义 Foul/Severity Type (中间分组) ---
    def add_custom_type(self, type_group):
        if type_group == "foul":
            input_field = self.ui.right_panel.foul_input
            type_set = self.foul_types
            update_func = self.ui.right_panel.update_foul_radios
            default_types = RightPanel.DEFAULT_FOUL_TYPES
        elif type_group == "severity":
            input_field = self.ui.right_panel.sev_input
            type_set = self.severity_types
            update_func = self.ui.right_panel.update_sev_radios
            default_types = RightPanel.DEFAULT_SEVERITY_TYPES
        else:
            return

        new_type = input_field.text().strip()
        
        if not new_type:
            self._show_temp_message_box("Warning", "Type name cannot be empty.", QMessageBox.Icon.Warning, 1500)
            return
            
        if new_type in type_set:
            self._show_temp_message_box("Warning", f"'{new_type}' already exists.", QMessageBox.Icon.Warning, 1500)
            input_field.clear()
            return
        
        type_set.add(new_type)
        updated_list = sorted(list(type_set))
        
        # 确保默认类型在列表中始终排在前面
        if type_group == "severity":
            sorted_defaults = [t for t in default_types if t in updated_list]
            sorted_customs = [t for t in updated_list if t not in default_types]
            updated_list = sorted_defaults + sorted(sorted_customs)
            
        update_func(updated_list)
        
        self._show_temp_message_box("Success", f"'{new_type}' added to {type_group.capitalize()} types.", QMessageBox.Icon.Information, 1000)
        input_field.clear()


    # --- 新增：移除自定义 Foul/Severity Type (中间分组) ---
    def remove_custom_type(self, type_group):
        if type_group == "foul":
            radio_map = self.ui.right_panel.foul_radio_buttons
            type_set = self.foul_types
            update_func = self.ui.right_panel.update_foul_radios
            default_types = RightPanel.DEFAULT_FOUL_TYPES
        elif type_group == "severity":
            radio_map = self.ui.right_panel.sev_radio_buttons
            type_set = self.severity_types
            update_func = self.ui.right_panel.update_sev_radios
            default_types = RightPanel.DEFAULT_SEVERITY_TYPES
        else:
            return

        checked_button = next((rb for rb in radio_map.values() if rb.isChecked()), None)
        
        if not checked_button:
            self._show_temp_message_box("Warning", "Please select a type to remove first.", QMessageBox.Icon.Warning, 1500)
            return
            
        type_to_remove = checked_button.text()

        if type_to_remove in default_types:
            self._show_temp_message_box("Warning", f"Cannot remove built-in type: '{type_to_remove}'.", QMessageBox.Icon.Warning, 1500)
            return

        if type_to_remove in type_set:
            type_set.remove(type_to_remove)
            
        updated_list = sorted(list(type_set))
        
        # 保持默认类型在列表中的排序位置
        if type_group == "severity":
            sorted_defaults = [t for t in default_types if t in updated_list]
            sorted_customs = [t for t in updated_list if t not in default_types]
            updated_list = sorted_defaults + sorted(sorted_customs)
            
        update_func(updated_list)
            
        keys_to_delete = []
        for path, anno in self.manual_annotations.items():
            if type_group == "foul" and anno.get('foul') == type_to_remove:
                anno['foul'] = None 
            elif type_group == "severity" and anno.get('severity') == type_to_remove:
                anno['severity'] = None 
            
            if not anno.get('foul') and not anno.get('severity'):
                 keys_to_delete.append(path)

        for path in keys_to_delete:
            del self.manual_annotations[path]
            self.update_action_item_status(path) 
            
        current_path = self._get_current_action_path()
        if current_path:
             self.display_manual_annotation(current_path)

        self._show_temp_message_box("Success", f"'{type_to_remove}' removed.", QMessageBox.Icon.Information, 1000)
        self.update_save_export_button_state()
            
    def import_annotations(self):
        # 检查是否有Action文件夹数据，没有则提示先加载
        if not self.action_path_to_name:
            QMessageBox.warning(self, "Import Blocked", "Please ensure the action folder is accessible before importing annotations.")
            
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

        is_first_json_load = not self.json_loaded
        
        # --- 导入自定义标签和类型 ---
        self.foul_types.update(data.get('labels', {}).get('foul_type', {}).get('labels', []))
        self.severity_types.update(data.get('labels', {}).get('severity', {}).get('labels', []))
        
        # 更新 UI 中的单选按钮列表
        self.ui.right_panel.update_foul_radios(sorted(list(self.foul_types)))
        self.ui.right_panel.update_sev_radios(sorted(list(self.severity_types)))
        
        for item in data['data']:
            action_name = item.get('id')
            if not action_name:
                continue
                
            action_path = action_name_to_path.get(action_name)
            
            if not action_path and action_name.startswith(self.SINGLE_VIDEO_PREFIX):
                potential_path = os.path.join(self.DEFAULT_LOAD_PATH, action_name)
                if os.path.isdir(potential_path):
                    self.action_item_data.append({'name': action_name, 'path': potential_path})
                    self.action_path_to_name[potential_path] = action_name
                    action_path = potential_path
                    print(f"Loaded existing virtual action: {action_name}")
                
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
        
        if is_first_json_load or imported_count > 0:
            self._populate_action_tree()
        
        self.json_loaded = True 
        
        self.ui.right_panel.label_combo.setEnabled(True)
        combo = self.ui.right_panel.label_combo
        
        combo.blockSignals(True)
        combo.setCurrentIndex(0) 
        combo.blockSignals(False)
        
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
        self.ui.left_panel.action_tree.clear()
        
        self.analysis_results.clear()
        self.manual_annotations.clear()
        self.action_item_map.clear()
        
        self.current_json_path = None
        self.json_loaded = False 
        self.update_save_export_button_state()

        self.ui.right_panel.start_button.setEnabled(False)
        self.ui.right_panel.results_widget.setVisible(False)
        self.ui.center_panel.multi_view_button.setEnabled(False)
        self.ui.right_panel.clear_manual_selection()
        
        self.ui.right_panel.manual_group_box.setEnabled(False) 
        self.ui.right_panel.manual_group_box.setChecked(False) 
        self.ui.right_panel.auto_group_box.setChecked(False)
        
        # --- 重置 Label Annotation 下拉框 ---
        self.ui.right_panel.label_combo.setEnabled(False)
        combo = self.ui.right_panel.label_combo
        combo.blockSignals(True)
        
        # 1. 移除所有自定义任务
        for task in self.custom_tasks:
             index = combo.findText(task)
             if index != -1:
                 combo.removeItem(index)
        self.custom_tasks.clear()

        # 2. 重置回 'Select Task...'
        combo.setCurrentIndex(0) # 选中 "Select Task..."
        combo.blockSignals(False)
        self.ui.right_panel.annotation_content_widget.setVisible(False) # 隐藏内容
        
        # --- 重置 Foul/Severity Types ---
        self.foul_types = set(RightPanel.DEFAULT_FOUL_TYPES)
        self.severity_types = set(RightPanel.DEFAULT_SEVERITY_TYPES)
        self.ui.right_panel.update_foul_radios(RightPanel.DEFAULT_FOUL_TYPES)
        self.ui.right_panel.update_sev_radios(RightPanel.DEFAULT_SEVERITY_TYPES)
        
        # 重置筛选器下拉菜单
        self.ui.left_panel.filter_combo.blockSignals(True)
        self.ui.left_panel.filter_combo.setCurrentIndex(self.FILTER_ALL)
        self.ui.left_panel.filter_combo.blockSignals(False)


    def toggle_annotation_view(self):
        selected_task = self.ui.right_panel.label_combo.currentText()
        is_action_classification = selected_task == "action_classification"
        
        self.ui.right_panel.annotation_content_widget.setVisible(is_action_classification)
        
        can_annotate_and_analyze = False 

        if is_action_classification:
            current_item = self.ui.left_panel.action_tree.currentItem()
            
            if current_item and current_item.childCount() > 0 and self.json_loaded:
                can_annotate_and_analyze = True
        
        self.ui.right_panel.manual_group_box.setEnabled(bool(can_annotate_and_analyze))
        self.ui.right_panel.start_button.setEnabled(bool(can_annotate_and_analyze))
            
        if not is_action_classification:
             self.ui.right_panel.results_widget.setVisible(False)
             self.ui.right_panel.auto_group_box.setChecked(False)
             self.ui.right_panel.manual_group_box.setChecked(False)


    def on_item_selected(self, current_item, _):
        if not current_item:
            self.toggle_annotation_view() 
            return
        
        is_action_item = current_item.childCount() > 0 
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
            
        self.toggle_annotation_view()
        
        if self.ui.right_panel.label_combo.currentText() == "action_classification":
            self.display_analysis_results(action_path)
            self.display_manual_annotation(action_path)
        else:
            self.ui.right_panel.results_widget.setVisible(False)
            self.ui.right_panel.auto_group_box.setChecked(False)
            self.ui.right_panel.manual_group_box.setChecked(False)
            
        self.update_save_export_button_state() 
            
    def play_video(self):
        self.ui.center_panel.toggle_play_pause()

    def show_all_views(self):
        current_item = self.ui.left_panel.action_tree.currentItem()
        if current_item:
            action_path = current_item.data(0, Qt.ItemDataRole.UserRole)
            
            if current_item.childCount() > 0:
                clip_paths = [current_item.child(j).data(0, Qt.ItemDataRole.UserRole) for j in range(current_item.childCount())]
            else:
                return 

            self.ui.center_panel.show_all_views(clip_paths)


    def start_analysis(self):
        # 额外的JSON检查
        if not self.json_loaded:
             self._show_temp_message_box("Action Blocked", 
                                        "Please import a GAC JSON file before starting analysis.", 
                                        QMessageBox.Icon.Warning, 2000)
             return
             
        # 额外的任务类型检查
        if self.ui.right_panel.label_combo.currentText() != "action_classification":
             self._show_temp_message_box("Action Blocked", 
                                        "Analysis is only enabled for 'action_classification' task.", 
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
        # 如果是 Action Item (父节点)
        if current_item.childCount() > 0 or current_item.parent() is None:
            return current_item.data(0, Qt.ItemDataRole.UserRole)
        # 如果是 Clip Item (子节点)
        else:
            return current_item.parent().data(0, Qt.ItemDataRole.UserRole)

    def save_manual_annotation(self):
        # 额外的任务类型检查
        if self.ui.right_panel.label_combo.currentText() != "action_classification":
             self._show_temp_message_box("Action Blocked", 
                                        "Saving is only enabled for 'action_classification' task.", 
                                        QMessageBox.Icon.Warning, 2000)
             return
             
        if not self.json_loaded:
             self._show_temp_message_box("Action Blocked", 
                                        "Please import a GAC JSON file before saving annotations.", 
                                        QMessageBox.Icon.Warning, 2000)
             return
             
        action_path = self._get_current_action_path()
        if not action_path:
            return
        
        data = self.ui.right_panel.get_manual_annotation()
        
        action_name = self.action_path_to_name.get(action_path)
        
        if data["foul"] or data["severity"]:
            self.manual_annotations[action_path] = data
            self._show_temp_message_box("Success", 
                                        f"Annotation saved for {action_name}.", 
                                        QMessageBox.Icon.Information, 1500)
            self.ui.right_panel.manual_group_box.setChecked(True) 
        elif action_path in self.manual_annotations:
            del self.manual_annotations[action_path]
            self._show_temp_message_box("Success", 
                                        f"Annotation cleared for {action_name}.", 
                                        QMessageBox.Icon.Information, 1500)
            self.ui.right_panel.manual_group_box.setChecked(False) 
        else:
            self._show_temp_message_box("No Selection", 
                                        "Please select a foul type or severity to save.",
                                        QMessageBox.Icon.Warning, 1500)

        self.update_save_export_button_state()
        self.update_action_item_status(action_path)

    def clear_current_manual_annotation(self):
        # 额外的任务类型检查
        if self.ui.right_panel.label_combo.currentText() != "action_classification":
             self._show_temp_message_box("Action Blocked", 
                                        "Clearing is only enabled for 'action_classification' task.", 
                                        QMessageBox.Icon.Warning, 2000)
             return
             
        action_path = self._get_current_action_path()
        if not action_path:
            return
            
        self.ui.right_panel.clear_manual_selection()
        
        action_name = self.action_path_to_name.get(action_path)
        
        if action_path in self.manual_annotations:
            del self.manual_annotations[action_path]
            self._show_temp_message_box("Cleared", 
                                        f"Annotation for {action_name} has been cleared.",
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
        # 包含所有 Action Folder 路径 (包括 virtual_action_)
        all_action_paths = set(self.action_path_to_name.keys()) 
        # 同时包含那些有结果但未在列表中显示的路径（以防万一）
        all_action_paths.update(self.analysis_results.keys()) 
        all_action_paths.update(self.manual_annotations.keys()) 
        
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

        # --- 核心修改：使用动态的类型集合 ---
        foul_types_list = sorted(list(self.foul_types))
        sev_types_list = sorted(list(self.severity_types))
        
        output_data["labels"] = {
            "foul_type": {
                "type": "single_label",
                "labels": foul_types_list
            },
            "severity": {
                "type": "single_label",
                "labels": sev_types_list
            }
        }

        output_data["data"] = []
        
        path_to_item_map = {}
        root = self.ui.left_panel.action_tree.invisibleRootItem()
        # 确保只有在 action_tree 已填充时才尝试获取 item
        if self.json_loaded:
            for i in range(root.childCount()):
                item = root.child(i)
                path_to_item_map[item.data(0, Qt.ItemDataRole.UserRole)] = item

        for action_path in all_action_paths:
            
            action_name = self.action_path_to_name.get(action_path)
            if not action_name:
                # 如果没有 Action Name，则跳过
                continue
                
            auto_result = self.analysis_results.get(action_path)
            manual_result = self.manual_annotations.get(action_path)
            
            if not auto_result and not manual_result:
                continue

            final_foul_class = None
            final_severity_class = None
            annotation_source = "None"

            # 仅在类型存在于当前集合中时才使用，否则视为 None
            if manual_result and manual_result.get("foul") and manual_result.get("foul") in self.foul_types:
                final_foul_class = manual_result.get("foul")
                annotation_source = "Manual"
            elif auto_result:
                foul_dist = auto_result['foul_distribution']
                # 确保预测的最高分类型在当前类型集合中
                predicted_foul = max(foul_dist, key=foul_dist.get)
                if predicted_foul in self.foul_types:
                    final_foul_class = predicted_foul
                    if annotation_source == "None": annotation_source = "Automated"
            
            if manual_result and manual_result.get("severity") and manual_result.get("severity") in self.severity_types:
                final_severity_class = manual_result.get("severity")
                if annotation_source != "Manual": annotation_source = "Manual" 
            elif auto_result:
                sev_dist = auto_result['severity_distribution']
                 # 确保预测的最高分类型在当前类型集合中
                predicted_sev = max(sev_dist, key=sev_dist.get)
                if predicted_sev in self.severity_types:
                    final_severity_class = predicted_sev
                    if annotation_source == "None": annotation_source = "Automated"
            
            data_item = {
                "id": action_name,
                "metadata": {
                    "AnnotationSource": annotation_source 
                },
                "inputs": [],
                "labels": {}
            }
            
            action_item = path_to_item_map.get(action_path)

            if action_item:
                for j in range(action_item.childCount()):
                    clip_item = action_item.child(j)
                    clip_path = clip_item.data(0, Qt.ItemDataRole.UserRole)
                    clip_name_no_ext = os.path.splitext(os.path.basename(clip_path))[0]
                    
                    # 使用 Action Name 作为 URL 路径的一部分
                    url_path = f"Dataset/Test/{action_name}/{clip_name_no_ext}" 
                    data_item["inputs"].append({
                        "type": "video",
                        "path": url_path
                    })
            else:
                print(f"Warning: Action {action_name} not found in tree. Inputs skipped in JSON export.")
            
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
    # 修复 AA_EnableHighDpiScaling 错误，移除该设置
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    window = ActionClassifierApp()
    window.show()
    sys.exit(app.exec())
