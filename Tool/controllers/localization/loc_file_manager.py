import os
import json
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog
from utils import SINGLE_VIDEO_PREFIX, SUPPORTED_EXTENSIONS, natural_sort_key

class LocFileManager:
    def __init__(self, main_window):
        self.main = main_window
        self.model = main_window.model
        self.ui = main_window.ui

    def load_project(self, data, file_path):
        """专门加载 Localization 项目"""
        self._clear_workspace(full_reset=True)
        
        self.model.current_working_directory = os.path.dirname(file_path)
        self.model.current_task_name = data.get('dataset_name', "Localization Task")
        self.model.modalities = data.get('modalities', [])
        
        # Load Labels
        if 'labels' in data:
            self.model.label_definitions = data['labels']
            # Pass to UI
            self.main.loc_manager.right_panel.annot_mgmt.update_schema(self.model.label_definitions)
            # Ensure "action" head exists in editor default
            if "action" in self.model.label_definitions:
                self.main.loc_manager.current_head = "action"
                self.main.loc_manager.right_panel.label_editor.set_current_head("action")
        
        # Load Data
        for item in data.get('data', []):
            aid = item.get('id')
            if not aid: continue
            
            src_files = []
            for inp in item.get('inputs', []):
                 p = inp.get('path', '')
                 fp = p if os.path.isabs(p) else os.path.normpath(os.path.join(self.model.current_working_directory, p))
                 src_files.append(fp)
            
            key = src_files[0] if src_files else aid
            self.model.action_item_data.append({'name': aid, 'path': key, 'source_files': src_files})
            self.model.action_path_to_name[key] = aid
            
            if 'events' in item:
                self.model.localization_events[key] = item['events']

        self.model.current_json_path = file_path
        self.model.json_loaded = True
        
        # 刷新 UI
        self.main.loc_manager.populate_tree()
        self.main.show_temp_msg("Imported", f"Loaded {len(self.model.action_item_data)} clips.")

    def overwrite_json(self):
        """[新增] 直接保存到当前文件，不弹窗"""
        if self.model.current_json_path:
            return self._write_json(self.model.current_json_path)
        else:
            # 如果是新项目没有路径，则回退到 Export (Save As)
            return self.export_json()

    def export_json(self):
        """[新增] 另存为/导出"""
        path, _ = QFileDialog.getSaveFileName(self.main, "Export Localization JSON", "", "JSON (*.json)")
        if path:
            result = self._write_json(path)
            if result:
                # 只有 Save As 会更新当前工作路径，Export 通常不更新，
                # 但根据您的需求，如果想让后续 Save 指向这个新文件，可以更新。
                # 这里假设 Export 只是导出副本，不改变当前工作环境。
                # 如果是 Save As 语义，应该 self.model.current_json_path = path
                # 按照常规逻辑：Save = 覆盖，Export = 副本。
                pass 
            return result
        return False

    def _write_json(self, path):
        output = {
            "version": "1.0",
            "modalities": self.model.modalities,
            "dataset_name": self.model.current_task_name,
            "labels": self.model.label_definitions,
            "data": []
        }
        
        base_dir = os.path.dirname(path)
        
        # Sort output to keep it consistent
        sorted_items = sorted(self.model.action_item_data, key=lambda d: natural_sort_key(d.get('name', '')))
        
        for data in sorted_items:
            abs_path = data['path']
            try:
                rel_path = os.path.relpath(abs_path, base_dir).replace(os.sep, '/')
            except:
                rel_path = abs_path
                
            events = self.model.localization_events.get(abs_path, [])
            
            # Construct entry matching user requirement
            entry = {
                "id": data['name'], 
                "inputs": [
                    {
                        "type": "video",
                        "path": rel_path,
                        "fps": 25 # Default fps
                    }
                ],
                "events": events
            }
            output["data"].append(entry)
            
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            
            # 如果是 overwrite 操作，或者是第一次保存
            if self.model.current_json_path is None or os.path.abspath(path) == os.path.abspath(self.model.current_json_path):
                self.model.current_json_path = path
                self.model.is_data_dirty = False
            
            self.main.show_temp_msg("Saved", f"Saved to {os.path.basename(path)}")
            return True
        except Exception as e:
            QMessageBox.critical(self.main, "Error", f"Save failed: {e}")
            return False

    def _clear_workspace(self, full_reset=False):
        # 清理 Localization UI
        if hasattr(self.main, 'loc_manager'):
            self.main.loc_manager.left_panel.clip_tree.clear()
            
        self.model.reset(full_reset)
        if full_reset:
            self.main.ui.show_welcome_view()