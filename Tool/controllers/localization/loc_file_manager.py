import os
import json
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtCore import QUrl
from utils import natural_sort_key
from dialogs import CreateProjectDialog  # [导入]

class LocFileManager:
    def __init__(self, main_window):
        self.main = main_window
        self.model = main_window.model
        self.ui = main_window.ui

    def create_new_project(self):
        """
        [新增] 创建新的 Localization 项目
        """
        # 1. 检查当前项目是否需要保存
        if not self.main.check_and_close_current_project():
            return

        # 2. 弹出创建对话框，指定类型为 localization
        dlg = CreateProjectDialog(self.main, project_type="localization")
        
        if dlg.exec():
            # 3. 清空现有工作区
            self._clear_workspace(full_reset=True)
            
            # 4. 获取用户配置
            data = dlg.get_data()
            
            # 5. 初始化 Model
            self.model.current_task_name = data['task']
            self.model.project_description = data['description']
            self.model.modalities = data['modalities']
            self.model.label_definitions = data['labels']
            
            # 设置 Localization 模式下的状态
            self.model.current_working_directory = None 
            self.model.current_json_path = None         
            self.model.json_loaded = True               
            self.model.is_data_dirty = True             
            
            # 6. 刷新 Localization UI
            # 更新右侧 Schema
            self.main.loc_manager.right_panel.annot_mgmt.update_schema(self.model.label_definitions)
            
            # 自动选择第一个 Head
            if self.model.label_definitions:
                first_head = list(self.model.label_definitions.keys())[0]
                self.main.loc_manager.current_head = first_head
                self.main.loc_manager.right_panel.annot_mgmt.tabs.set_current_head(first_head)

            # 刷新左侧树 (空)
            self.main.loc_manager.populate_tree()
            
            # 7. 切换视图
            self.main.ui.show_localization_view()
            self.main.update_save_export_button_state()
            
            self.main.show_temp_msg("Project Created", f"Task: {self.model.current_task_name}")

    def load_project(self, data, file_path):
        """
        加载 Localization 项目。
        返回: Boolean (True 表示加载成功，False 表示失败或取消)
        """
        if hasattr(self.model, 'validate_loc_json'):
            is_valid, error_msg, warning_msg = self.model.validate_loc_json(data)
            
            if not is_valid:
                if len(error_msg) > 800: error_msg = error_msg[:800] + "\n... (truncated)"
                QMessageBox.critical(self.main, "Validation Error", f"Critical errors found in JSON. Load aborted.\n\n{error_msg}")
                return False

            if warning_msg:
                if len(warning_msg) > 800: warning_msg = warning_msg[:800] + "\n... (truncated)"
                res = QMessageBox.warning(
                    self.main,
                    "Validation Warnings",
                    f"The file contains warnings:\n\n{warning_msg}\n\nDo you want to continue loading?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if res != QMessageBox.StandardButton.Yes:
                    return False

        self._clear_workspace(full_reset=True)
        
        project_root = os.path.dirname(os.path.abspath(file_path))
        self.model.current_working_directory = project_root
        
        self.model.current_task_name = data.get('dataset_name', data.get('task', "Localization Task"))
        self.model.modalities = data.get('modalities', ['video']) 
        
        if 'labels' in data:
            self.model.label_definitions = data['labels']
            self.main.loc_manager.right_panel.annot_mgmt.update_schema(self.model.label_definitions)
            
            default_head = None
            if "ball_action" in self.model.label_definitions:
                default_head = "ball_action"
            elif "action" in self.model.label_definitions:
                default_head = "action"
            elif list(self.model.label_definitions.keys()):
                default_head = list(self.model.label_definitions.keys())[0]
            
            if default_head:
                self.main.loc_manager.current_head = default_head
                self.main.loc_manager.right_panel.annot_mgmt.tabs.set_current_head(default_head)
        
        missing_files = []
        loaded_count = 0
        
        for item in data.get('data', []):
            inputs = item.get('inputs', [])
            if not inputs or not isinstance(inputs, list): continue
            
            raw_path = inputs[0].get('path', '')
            aid = item.get('id')
            if not aid:
                aid = os.path.splitext(os.path.basename(raw_path))[0]

            final_path = raw_path 
            
            if os.path.isabs(raw_path) and os.path.exists(raw_path):
                final_path = raw_path
            else:
                norm_raw = raw_path.replace('\\', '/')
                abs_path_strict = os.path.normpath(os.path.join(project_root, norm_raw))
                
                if os.path.exists(abs_path_strict):
                    final_path = abs_path_strict
                else:
                    filename = os.path.basename(norm_raw) 
                    abs_path_flat = os.path.join(project_root, filename)
                    
                    if os.path.exists(abs_path_flat):
                        final_path = abs_path_flat
                    else:
                        final_path = abs_path_strict
                        missing_files.append(f"{aid}: {filename}")

            self.model.action_item_data.append({
                'name': aid, 'path': final_path, 'source_files': [final_path]
            })
            self.model.action_path_to_name[final_path] = aid
            
            raw_events = item.get('events', [])
            processed_events = []
            
            if isinstance(raw_events, list):
                for evt in raw_events:
                    if not isinstance(evt, dict): continue
                    try:
                        pos_ms = int(evt.get('position_ms', 0))
                    except ValueError:
                        pos_ms = 0
                    
                    new_evt = {
                        "head": evt.get('head', 'action'),
                        "label": evt.get('label', '?'),
                        "position_ms": pos_ms
                    }
                    processed_events.append(new_evt)

            if processed_events:
                self.model.localization_events[final_path] = processed_events
            
            loaded_count += 1

        self.model.current_json_path = file_path
        self.model.json_loaded = True
        
        self.main.loc_manager.populate_tree()
        
        if missing_files:
            shown_missing = missing_files[:5]
            msg = f"Loaded {loaded_count} clips.\n\nWARNING: {len(missing_files)} videos not found locally:\n" + "\n".join(shown_missing)
            if len(missing_files) > 5: msg += "\n..."
            QMessageBox.warning(self.main, "Load Warning", msg)
        else:
            # [修改] 使用弹窗进行明显提示
            QMessageBox.information(
                self.main, 
                "Mode Switched", 
                f"Successfully loaded {loaded_count} clips.\n\nCurrent Mode: LOCALIZATION"
            )
            
        return True

    def overwrite_json(self):
        if self.model.current_json_path:
            return self._write_json(self.model.current_json_path)
        return self.export_json()

    def export_json(self):
        path, _ = QFileDialog.getSaveFileName(self.main, "Export Localization JSON", "", "JSON (*.json)")
        if path:
            if self._write_json(path):
                self.model.current_json_path = path 
                self.model.is_data_dirty = False
                return True
        return False

    def _write_json(self, path):
        output = {
            "version": "2.0",
            "date": "2025-12-16",
            "task": "action_spotting",
            "dataset_name": self.model.current_task_name,
            "metadata": {
                "source": "Annotation Tool Export",
                "created_by": "User"
            },
            "labels": self.model.label_definitions,
            "data": []
        }
        
        base_dir = os.path.dirname(path)
        sorted_items = sorted(self.model.action_item_data, key=lambda d: natural_sort_key(d.get('name', '')))
        
        for data in sorted_items:
            abs_path = data['path']
            events = self.model.localization_events.get(abs_path, [])
            
            try:
                rel_path = os.path.relpath(abs_path, base_dir).replace(os.sep, '/')
            except:
                rel_path = abs_path
                
            export_events = []
            for e in events:
                export_events.append({
                    "head": e.get('head'),
                    "label": e.get('label'),
                    "position_ms": str(e.get('position_ms')) 
                })

            entry = {
                "inputs": [{
                    "type": "video",
                    "path": rel_path,
                    "fps": 25.0 
                }],
                "events": export_events
            }
            output["data"].append(entry)
            
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=4, ensure_ascii=False)
            
            self.model.is_data_dirty = False
            self.main.show_temp_msg("Saved", f"Saved to {os.path.basename(path)}")
            return True
        except Exception as e:
            QMessageBox.critical(self.main, "Error", f"Save failed: {e}")
            return False

    def _clear_workspace(self, full_reset=False):
        if hasattr(self.main, 'loc_manager'):
            self.main.loc_manager.left_panel.clip_tree.clear()
            self.main.loc_manager.center_panel.media_preview.stop()
            self.main.loc_manager.center_panel.media_preview.player.setSource(QUrl())
            self.main.loc_manager.right_panel.table.set_data([])
            
        self.model.reset(full_reset)
        if full_reset:
            self.main.ui.show_welcome_view()
