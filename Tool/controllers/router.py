import json
from PyQt6.QtWidgets import QFileDialog, QMessageBox
# 导入两个专属的文件管理器
from controllers.classification.class_file_manager import ClassFileManager
from controllers.localization.loc_file_manager import LocFileManager
from dialogs import ProjectTypeDialog  # [导入]

class AppRouter:
    """
    负责应用的入口路由：
    1. 打开 JSON 文件 / 创建新项目
    2. 判断是 Classification 还是 Localization
    3. 将控制权移交给对应的专用管理器
    """
    def __init__(self, main_window):
        self.main = main_window
        # 初始化两个专用的文件管理器
        self.class_fm = ClassFileManager(main_window)
        self.loc_fm = LocFileManager(main_window)

    def create_new_project_flow(self):
        """
        [新增] 创建新项目的统一入口流程
        """
        # 1. 弹出类型选择框
        dlg = ProjectTypeDialog(self.main)
        if dlg.exec():
            mode = dlg.selected_mode
            
            # 2. 根据选择分发到对应的 Manager
            if mode == "classification":
                # 调用 Classification 的创建流程 (它内部会处理 check_and_close)
                self.class_fm.create_new_project()
                
            elif mode == "localization":
                # 调用 Localization 的创建流程
                self.loc_fm.create_new_project()

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
            self.class_fm.load_project(data, file_path)
            self.main.ui.show_classification_view()
            
        elif json_type == "localization":
            # 检查返回值
            if self.loc_fm.load_project(data, file_path):
                self.main.ui.show_localization_view()
            
        else:
            QMessageBox.critical(self.main, "Error", "Unknown JSON format.")

    def _detect_json_type(self, data):
        items = data.get("data", [])
        first = items[0] if items else {}

        # 1) 先判定“样本级 labels” => classification
        if isinstance(first, dict) and "labels" in first:
            return "classification"

        # 2) 再判定“事件 events” => localization
        if isinstance(first, dict) and "events" in first:
            return "localization"
            
        # 3) 兜底：根据顶层 labels 结构判断（可选）
        if "labels" in data:
            pass

        return "unknown"
