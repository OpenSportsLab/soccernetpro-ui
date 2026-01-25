import json
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from controllers.classification.class_file_manager import ClassFileManager
from controllers.localization.loc_file_manager import LocFileManager
from ui.common.dialogs import ProjectTypeDialog

class AppRouter:
    """
    Handles application entry points and routing:
    1. Open JSON / Create New Project
    2. Determine Mode (Classification vs Localization)
    3. Delegate to specific Managers
    4. Handle Project Closure
    """
    def __init__(self, main_window):
        self.main = main_window
        self.class_fm = ClassFileManager(main_window)
        self.loc_fm = LocFileManager(main_window)

    def create_new_project_flow(self):
        """
        Unified entry point for creating a new project.
        """
        # 1. Ask user for project type
        dlg = ProjectTypeDialog(self.main)
        if dlg.exec():
            mode = dlg.selected_mode
            
            # 2. Delegate to specific manager logic
            # Note: Managers should handle 'check_and_close_current_project' internally
            if mode == "classification":
                self.class_fm.create_new_project()
                
            elif mode == "localization":
                self.loc_fm.create_new_project()

    def import_annotations(self):
        """
        Global entry point for loading a JSON file.
        """
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
            if self.loc_fm.load_project(data, file_path):
                self.main.ui.show_localization_view()
            
        else:
            QMessageBox.critical(self.main, "Error", "Unknown JSON format.")

    def close_project(self):
        """
        [New] Handles closing the current project and returning to the Welcome Screen.
        """
        # 1. Check for unsaved changes
        if not self.main.check_and_close_current_project():
            return

        # 2. Clear workspaces (both just in case, or check current mode)
        # Using full_reset=True ensures models are wiped
        self.class_fm._clear_workspace(full_reset=True)
        self.loc_fm._clear_workspace(full_reset=True)

        # 3. Return to Welcome Screen
        self.main.ui.show_welcome_view()
        self.main.show_temp_msg("Project Closed", "Returned to Home Screen", duration=1000)

    def _detect_json_type(self, data):
        items = data.get("data", [])
        first = items[0] if items else {}

        # 1) Classification check
        if isinstance(first, dict) and "labels" in first:
            return "classification"

        # 2) Localization check
        if isinstance(first, dict) and "events" in first:
            return "localization"
            
        return "unknown"