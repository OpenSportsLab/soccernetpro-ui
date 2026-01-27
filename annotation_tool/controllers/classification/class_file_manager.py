import os
import json
import datetime
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from ui.common.dialogs import CreateProjectDialog
from utils import natural_sort_key

class ClassFileManager:
    def __init__(self, main_window):
        self.main = main_window
        self.model = main_window.model
        self.ui = main_window.ui

    def load_project(self, data, file_path):
        """Load Classification Project"""
        valid, err, warn = self.model.validate_gac_json(data)
        if not valid:
            QMessageBox.critical(self.main, "JSON Error", err); return
        if warn:
            QMessageBox.warning(self.main, "Warnings", warn)
            
        self._clear_workspace(full_reset=True)
        
        self.model.current_working_directory = os.path.dirname(file_path)
        
        self.model.current_task_name = data.get('task', "N/A")
        self.model.modalities = data.get('modalities', [])
        
        # Load Labels
        self.model.label_definitions = {}
        if 'labels' in data:
            for k, v in data['labels'].items():
                clean_k = k.strip().replace(' ', '_').lower()
                self.model.label_definitions[clean_k] = {'type': v['type'], 'labels': sorted(list(set(v.get('labels', []))))}
        self.main.setup_dynamic_ui() 
        
        # Load Data
        for item in data.get('data', []):
            aid = item.get('id')
            if not aid: continue
            
            src_files = []
            for inp in item.get('inputs', []):
                p = inp.get('path', '')
                
                if os.path.isabs(p):
                    fp = p
                else:
                    fp = os.path.normpath(os.path.join(self.model.current_working_directory, p))
                
                src_files.append(fp)
                self.model.imported_input_metadata[(aid, os.path.basename(fp))] = inp.get('metadata', {})
            
            path_key = src_files[0] if src_files else aid
            
            self.model.action_item_data.append({'name': aid, 'path': path_key, 'source_files': src_files})
            self.model.action_path_to_name[path_key] = aid
            self.model.imported_action_metadata[path_key] = item.get('metadata', {})
            
            # Load Manual Annotations
            lbls = item.get('labels', {})
            manual = {}
            has_l = False
            for h, content in lbls.items():
                ck = h.strip().replace(' ', '_').lower()
                if ck in self.model.label_definitions:
                    defn = self.model.label_definitions[ck]
                    if isinstance(content, dict):
                        if defn['type'] == 'single_label' and content.get('label') in defn['labels']:
                            manual[ck] = content.get('label'); has_l = True
                        elif defn['type'] == 'multi_label':
                            vals = [x for x in content.get('labels', []) if x in defn['labels']]
                            if vals: manual[ck] = vals; has_l = True
            if has_l:
                self.model.manual_annotations[path_key] = manual

        self.model.current_json_path = file_path
        self.model.json_loaded = True
        
        # [MV Note] populate_action_tree now uses self.main.tree_model internally
        self.main.populate_action_tree()
        self.main.update_save_export_button_state()
        
        # 2s block
        self.main.show_temp_msg(
            "Mode Switched", 
            f"Project loaded with {len(self.model.action_item_data)} items.\n\nCurrent Mode: CLASSIFICATION",
            duration=1500,
            icon=QMessageBox.Icon.Information
        )

    def save_json(self):
        if self.model.current_json_path: 
            return self._write_json(self.model.current_json_path)
        else: 
            return self.export_json()

    def export_json(self):
        path, _ = QFileDialog.getSaveFileName(self.main, "Save Classification JSON", "", "JSON (*.json)")
        if path:
            result = self._write_json(path)
            if result:
                self.model.current_json_path = path
                self.main.update_save_export_button_state()
            return result
        return False

    def _write_json(self, save_path):
        out = {
            "version": "2.0",
            "date": datetime.datetime.now().isoformat().split('T')[0],
            "task": self.model.current_task_name,
            "description": self.model.project_description,
            "modalities": self.model.modalities,
            "labels": self.model.label_definitions,
            "data": []
        }
        
        json_dir = os.path.dirname(os.path.abspath(save_path))
        
        sorted_items = sorted(self.model.action_item_data, key=lambda x: natural_sort_key(x.get('name', '')))
        
        for item in sorted_items:
            path_key = item['path'] 
            aid = item['name']
            
            inputs = []
            for src_abs_path in item.get('source_files', []):
                try:
                    fpath = os.path.relpath(src_abs_path, json_dir)
                    fpath = fpath.replace('\\', '/')
                except ValueError:
                    fpath = src_abs_path.replace('\\', '/')
                
                meta = self.model.imported_input_metadata.get((aid, os.path.basename(src_abs_path)), {})
                
                inputs.append({
                    "type": "video", 
                    "path": fpath,
                    "metadata": meta
                })
            
            data_entry = {
                "id": aid,
                "inputs": inputs,
                "metadata": self.model.imported_action_metadata.get(path_key, {})
            }
            
            if path_key in self.model.manual_annotations:
                annots = self.model.manual_annotations[path_key]
                entry_labels = {}
                for head, val in annots.items():
                    defn = self.model.label_definitions.get(head)
                    if not defn: continue
                    
                    if defn['type'] == 'single_label':
                        entry_labels[head] = {"label": val, "confidence": 1.0, "manual": True}
                    elif defn['type'] == 'multi_label':
                        entry_labels[head] = {"labels": val, "confidence": 1.0, "manual": True}
                
                if entry_labels:
                    data_entry["labels"] = entry_labels
            
            out["data"].append(data_entry)
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f: 
                json.dump(out, f, indent=2, ensure_ascii=False)
            
            self.model.is_data_dirty = False
            self.main.update_save_export_button_state()
            self.main.show_temp_msg("Saved", f"Saved to {os.path.basename(save_path)}")
            return True
        except Exception as e:
            QMessageBox.critical(self.main, "Error", f"Save failed: {e}")
            return False

    def create_new_project(self):
        if not self.main.check_and_close_current_project(): return
        dlg = CreateProjectDialog(self.main)
        if dlg.exec():
            self._clear_workspace(full_reset=True)
            data = dlg.get_data()
            self.model.current_task_name = data['task']
            self.model.modalities = data['modalities']
            self.model.label_definitions = data['labels']
            self.model.project_description = data['description']
            
            self.model.json_loaded = True
            self.model.is_data_dirty = True
            
            self.model.current_json_path = None
            self.model.current_working_directory = None 
            
            self.main.setup_dynamic_ui()
            self.main.update_save_export_button_state()
            self.ui.show_classification_view()

    def _clear_workspace(self, full_reset=False):
        # [MV Fix] Clear the Model, not the View
        # self.ui.classification_ui.left_panel.tree.clear() # Old QTreeWidget code
        self.main.tree_model.clear()
        
        self.model.reset(full_reset)
        self.main.update_save_export_button_state()
        self.ui.classification_ui.right_panel.manual_box.setEnabled(False)
        self.ui.classification_ui.center_panel.show_single_view(None)
        if full_reset: 
            self.main.setup_dynamic_ui()
