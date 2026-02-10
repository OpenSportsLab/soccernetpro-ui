import os
import json
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtCore import QUrl
from utils import natural_sort_key

class DenseFileManager:
    """
    Handles JSON I/O for Dense Video Captioning projects.
    """
    def __init__(self, main_window):
        self.main = main_window
        self.model = main_window.model

    def create_new_project(self):
        """
        [NEW] Create a new Dense Description project (Blank).
        This method initializes the workspace for a fresh project.
        """
        # 1. Safety Check: Ensure current project is closed/saved first
        if not self.main.check_and_close_current_project():
            return

        # 2. Clear Workspace
        self._clear_workspace(full_reset=True)

        # 3. Initialize Model State
        self.model.current_task_name = "Untitled Dense Task"
        self.model.project_description = ""
        self.model.modalities = ["video"]
        self.model.dense_description_events = {}
        
        # Reset paths
        self.model.current_working_directory = None
        self.model.current_json_path = None
        
        # [CRITICAL] Mark as loaded to enable UI interactions (Add Video, Save, etc.)
        self.model.json_loaded = True
        self.model.is_data_dirty = True

        # 4. Refresh UI
        # Clear tree (it's a new project, so it starts empty)
        self.main.dense_manager.populate_tree()
        
        # Switch View to Index 4 (Dense Description)
        self.main.ui.show_dense_description_view()
        self.main.update_save_export_button_state()
        
        # Unlock the specific Dense UI panels (Right panel, etc.)
        if hasattr(self.main, "prepare_new_dense_ui"):
            self.main.prepare_new_dense_ui()
            
        self.main.statusBar().showMessage("Project Created — Dense Description Workspace Ready", 5000)

    def load_project(self, data, file_path):
        """Loads dense description project from JSON data."""
        # 1. Clear workspace
        self._clear_workspace(full_reset=True)
        
        project_root = os.path.dirname(os.path.abspath(file_path))
        self.model.current_working_directory = project_root
        self.model.current_task_name = data.get("task", "Dense Captioning")

        missing_files = []
        loaded_count = 0

        # 2. Iterate through items
        for item in data.get("data", []):
            inputs = item.get("inputs", [])
            if not inputs: continue
            
            raw_path = inputs[0].get("path", "")
            aid = item.get("id") or os.path.splitext(os.path.basename(raw_path))[0]
            
            # Resolve relative/absolute path
            final_path = os.path.normpath(os.path.join(project_root, raw_path))
            if not os.path.exists(final_path):
                missing_files.append(aid)

            # Register in Model
            self.model.action_item_data.append({"name": aid, "path": final_path, "source_files": [final_path]})
            self.model.action_path_to_name[final_path] = aid

            # [FIXED] Process Dense Events using the correct key 'dense_captions'
            # Looking for 'dense_captions' first, fallback to 'events'
            events = item.get("dense_captions", item.get("events", []))
            
            if events:
                self.model.dense_description_events[final_path] = []
                for e in events:
                    self.model.dense_description_events[final_path].append({
                        "position_ms": int(e.get("position_ms", 0)),
                        "lang": e.get("lang", "en"),
                        "text": e.get("text", "")
                    })
            loaded_count += 1

        self.model.current_json_path = file_path
        self.model.json_loaded = True
        
        # 3. Refresh UI
        self.main.dense_manager.populate_tree()
        self.main.statusBar().showMessage(f"Dense Mode: Loaded {loaded_count} clips.", 2000)
        return True

    def overwrite_json(self):
        if self.model.current_json_path:
            return self._write_json(self.model.current_json_path)
        return self.export_json()

    def export_json(self):
        path, _ = QFileDialog.getSaveFileName(self.main, "Export Dense JSON", "", "JSON (*.json)")
        if path: return self._write_json(path)
        return False

    def _write_json(self, path):
        """Serializes current dense description state to JSON."""
        output = {
            "version": "1.0",
            "task": "dense_video_captioning",
            "dataset_name": self.model.current_task_name,
            "data": []
        }
        
        base_dir = os.path.dirname(path)
        
        # Sort items naturally so the output JSON is ordered
        sorted_items = sorted(
            self.model.action_item_data, key=lambda d: natural_sort_key(d.get("name", ""))
        )

        for data in sorted_items:
            abs_path = data["path"]
            events = self.model.dense_description_events.get(abs_path, [])
            
            try:
                rel_path = os.path.relpath(abs_path, base_dir).replace(os.sep, "/")
            except:
                rel_path = abs_path

            # Export events with 'text' field
            export_events = []
            # Sort events by time before export
            sorted_events = sorted(events, key=lambda x: x.get("position_ms", 0))
            
            for e in sorted_events:
                export_events.append({
                    "position_ms": e["position_ms"],
                    "lang": e["lang"],
                    "text": e["text"]
                })

            output["data"].append({
                "id": data["name"],
                "inputs": [{"type": "video", "path": rel_path}],
                # [FIXED] Use 'dense_captions' to maintain consistency with input format
                "dense_captions": export_events
            })

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=4, ensure_ascii=False)
            
            self.model.current_json_path = path
            self.model.is_data_dirty = False
            self.main.statusBar().showMessage(f"Saved — {os.path.basename(path)}", 1500)
            return True
        except Exception as e:
            QMessageBox.critical(self.main, "Error", f"Save failed: {e}")
            return False

    def _clear_workspace(self, full_reset=False):
        """Resets the workspace for Dense Description mode."""
        self.model.reset(full_reset)
        if hasattr(self.main, "dense_manager"):
            # Stop playback
            self.main.dense_manager.media_controller.stop()
            # Clear table
            self.main.dense_manager.right_panel.table.set_data([])
            # Clear text input
            self.main.dense_manager.right_panel.input_widget.set_text("")