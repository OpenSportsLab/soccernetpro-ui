import json
from PyQt6.QtWidgets import QFileDialog, QMessageBox
# 导入两个专属的文件管理器
from controllers.classification.class_file_manager import ClassFileManager
from controllers.localization.loc_file_manager import LocFileManager

class AppRouter:
    """
    负责应用的入口路由：
    1. 打开 JSON 文件
    2. 判断是 Classification 还是 Localization
    3. 将控制权移交给对应的专用管理器
    """
    def __init__(self, main_window):
        self.main = main_window
        # 初始化两个专用的文件管理器
        self.class_fm = ClassFileManager(main_window)
        self.loc_fm = LocFileManager(main_window)

    def import_annotations(self):
        # 全局入口
        if not self.main.check_and_close_current_project(): return
        
        file_path, _ = QFileDialog.getOpenFileName(self.main, "Select Project JSON", "", "JSON Files (*.json)")
        if not file_path: return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f: 
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self.main, "Error", f"Invalid JSON: {e}"); return

        json_type = self._detect_json_type(data)

        if json_type == "classification":
            # 移交给分类管理器处理加载
            self.class_fm.load_project(data, file_path)
            self.main.ui.show_classification_view()
            
        elif json_type == "localization":
            # 移交给定位管理器处理加载
            self.loc_fm.load_project(data, file_path)
            self.main.ui.show_localization_view()
            
        else:
            QMessageBox.critical(self.main, "Error", "Unknown JSON format.")

    def _detect_json_type(self, data):
        if "dataset_name" in data: return "localization"
        items = data.get("data", [])
        if items and len(items) > 0 and "events" in items[0]: return "localization"
        if "labels" in data and "data" in data: return "classification"
        return "unknown"