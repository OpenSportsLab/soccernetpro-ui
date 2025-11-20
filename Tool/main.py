# main.py
import sys
import os
import time
import random
import json
import datetime 
import shutil
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox, QStyle, 
    QTreeWidgetItem, QRadioButton, QProgressDialog
)
from PyQt6.QtCore import Qt, QTimer, QPointF, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen

# Explicit import of ui_components
from ui_components import MainWindowUI, RightPanel, DynamicSingleLabelGroup, DynamicMultiLabelGroup, LeftPanel, SUPPORTED_EXTENSIONS, CreateProjectDialog

# --- PyInstaller Path Resolver ---
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- Helper Function: Get Directory Size ---
def get_dir_size(start_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            if f.lower().endswith(SUPPORTED_EXTENSIONS): 
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp) and os.path.exists(fp):
                    total_size += os.path.getsize(fp)
    return total_size

def format_size(size_bytes):
    if size_bytes >= 1024**3:
        return f"{size_bytes / 1024**3:.2f} GB"
    elif size_bytes >= 1024**2:
        return f"{size_bytes / 1024**2:.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes} Bytes"

# --- Simulate AI Model and Sorting Helper Functions ---
def run_model_on_action(action_clips, label_heads):
    print(f"Analyzing Action: {os.path.dirname(action_clips[0]) if os.path.isdir(os.path.dirname(action_clips[0])) else os.path.basename(action_clips[0])}...")
    results = {}
    for head_name, definition in label_heads.items():
        if definition['type'] == 'single_label':
            labels = definition['labels']
            if len(labels) < 2:
                labels = labels + ['Label B', 'Label C']
            label_probs = [random.random() for _ in labels]
            label_sum = sum(label_probs)
            normalized_probs = [p / label_sum for p in label_probs]
            results[head_name] = {
                "distribution": dict(zip(labels, normalized_probs))
            }
    return results

def get_action_number(entry):
    try:
        parts = entry.name.split('_')
        if len(parts) > 1 and parts[-1].isdigit():
            return int(parts[-1])
        if len(parts) > 2 and parts[-2].isdigit():
             return int(parts[-2])
        return float('inf')
    except (IndexError, ValueError):
        return float('inf')

# --- Main Application Logic Class ---
class ActionClassifierApp(QMainWindow):
    
    FILTER_ALL = 0
    FILTER_DONE = 1
    FILTER_NOT_DONE = 2
    
    SINGLE_VIDEO_PREFIX = "Annotation_" 
    
    DEFAULT_LABEL_DEFINITIONS = {
        "Label_type": {"type": "single_label", "labels": []}, 
    }
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"SoccerNet Pro Analysis Tool ({RightPanel.DEFAULT_TASK_NAME} Tool)")
        self.setGeometry(100, 100, 1400, 900)
        
        self.ui = MainWindowUI()
        self.setCentralWidget(self.ui)

        self.analysis_results = {} 
        self.manual_annotations = {} 
        
        self.action_path_to_name = {}
        self.action_item_data = [] 
        self.current_working_directory = None
        
        self.label_definitions = self.DEFAULT_LABEL_DEFINITIONS.copy()
        self.current_task_name = RightPanel.DEFAULT_TASK_NAME 
        
        self.action_item_map = {} 
        
        self.current_json_path = None
        self.json_loaded = False 
        
        self.modalities = [] 
        self.is_data_dirty = False 
        self.current_style_mode = "Night"
        
        self.imported_action_metadata = {} 
        self.imported_input_metadata = {}  
        
        bright_blue = QColor("#00BFFF") 
        self.done_icon = self._create_checkmark_icon(bright_blue)
        self.empty_icon = QIcon() 
        
        self.connect_signals()
        self.apply_stylesheet(self.current_style_mode) 
        
        self.ui.right_panel.annotation_content_widget.setVisible(True) 
        self.ui.left_panel.filter_combo.setCurrentIndex(self.FILTER_ALL) 
        self.ui.right_panel.manual_group_box.setEnabled(False)
        self.ui.right_panel.start_button.setEnabled(False)
        
        self._setup_dynamic_ui()

    def closeEvent(self, event):
        can_export = self.json_loaded and (bool(self.manual_annotations) or bool(self.analysis_results))
        if not self.is_data_dirty or not can_export:
            event.accept()
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Unsaved Annotations")
        msg.setText("Do you want to save your annotations before quitting?")
        msg.setIcon(QMessageBox.Icon.Question)
        
        save_btn = msg.addButton("Save & Exit", QMessageBox.ButtonRole.AcceptRole)
        discard_btn = msg.addButton("Discard & Exit", QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg.setDefaultButton(save_btn)
        msg.exec()
        
        clicked_button = msg.clickedButton()

        if clicked_button == save_btn:
            if self._write_gac_json_wrapper():
                event.accept() 
            else:
                event.ignore() 
        elif clicked_button == discard_btn:
            event.accept()
        elif clicked_button == cancel_btn:
            event.ignore()
        else:
            event.ignore()

    def _write_gac_json_wrapper(self):
        if not self.json_loaded:
            path, _ = QFileDialog.getSaveFileName(self, "Save GAC JSON Annotation As...", "", "JSON Files (*.json)")
            if not path:
                return False 
            try:
                self._write_gac_json(path)
                return True
            except Exception:
                return False
        else:
            try:
                self._write_gac_json(self.current_json_path)
                return True
            except Exception:
                return False

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
        is_done = (action_path in self.manual_annotations and bool(self.manual_annotations[action_path])) or \
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
        msg_box.setStandardButtons(QMessageBox.StandardButton.NoButton) 
        timer.start(duration_ms)
        msg_box.exec()

    def connect_signals(self):
        self.ui.left_panel.clear_button.clicked.connect(self.clear_action_list)
        self.ui.left_panel.import_button.clicked.connect(self.import_annotations) 
        self.ui.left_panel.create_json_button.clicked.connect(self.create_new_project) # <--- NEW SIGNAL
        self.ui.left_panel.add_data_button.clicked.connect(self._dynamic_data_import) 
        
        self.ui.left_panel.action_tree.currentItemChanged.connect(self.on_item_selected)
        self.ui.left_panel.filter_combo.currentIndexChanged.connect(self.apply_action_filter)
        
        self.ui.center_panel.play_button.clicked.connect(self.play_video)
        self.ui.center_panel.multi_view_button.clicked.connect(self.show_all_views)
        
        self.ui.right_panel.start_button.clicked.connect(self.start_analysis)
        self.ui.right_panel.save_button.clicked.connect(self.save_results_to_json)
        self.ui.right_panel.export_button.clicked.connect(self.export_results_to_json)
        self.ui.right_panel.confirm_manual_button.clicked.connect(self.save_manual_annotation)
        self.ui.right_panel.clear_manual_button.clicked.connect(self.clear_current_manual_annotation)
        
        self.ui.right_panel.add_head_clicked.connect(self._handle_add_label_head)
        self.ui.right_panel.remove_head_clicked.connect(self._handle_remove_label_head) 
        self.ui.right_panel.style_mode_changed.connect(self.change_style_mode)

    def _handle_add_label_head(self, head_name):
        clean_name = head_name.strip().replace(' ', '_').lower()
        if not clean_name:
            self._show_temp_message_box("Warning", "Category name cannot be empty.", QMessageBox.Icon.Warning, 1500)
            return
        if clean_name in self.label_definitions:
            self._show_temp_message_box("Warning", f"Category '{head_name}' already exists.", QMessageBox.Icon.Warning, 1500)
            return
        new_head_definition = {
            "type": "single_label", 
            "labels": [] 
        }
        self.label_definitions[clean_name] = new_head_definition
        self.ui.right_panel.new_head_input.clear()
        self._setup_dynamic_ui()
        self._show_temp_message_box("Success", f"New category '{head_name}' added.", QMessageBox.Icon.Information, 2500)
        self.is_data_dirty = True
        self.update_save_export_button_state()

    def _handle_remove_label_head(self, head_name):
        clean_name = head_name.strip().replace(' ', '_').lower()
        if clean_name not in self.label_definitions:
            self._show_temp_message_box("Warning", f"Category '{head_name}' not found.", QMessageBox.Icon.Warning, 1500)
            self.ui.right_panel.remove_head_combo.setCurrentIndex(0)
            return
        if clean_name in self.DEFAULT_LABEL_DEFINITIONS:
            self._show_temp_message_box("Warning", f"Cannot remove default imported category '{head_name}'.", QMessageBox.Icon.Warning, 2500)
            self.ui.right_panel.remove_head_combo.setCurrentIndex(0)
            return

        reply = QMessageBox.question(self, 'Confirm Removal',
            f"Are you sure you want to remove the category '{head_name}'? All annotations will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.No:
            self.ui.right_panel.remove_head_combo.setCurrentIndex(0)
            return

        try:
            del self.label_definitions[clean_name]
            paths_to_update = set()
            keys_to_delete = []
            for path, anno in list(self.manual_annotations.items()):
                if clean_name in anno:
                    del anno[clean_name]
                    paths_to_update.add(path)
                if not any(v for k, v in anno.items() if k in self.label_definitions and v):
                    keys_to_delete.append(path)

            for path in keys_to_delete:
                del self.manual_annotations[path]
                paths_to_update.add(path)

            for path, result in list(self.analysis_results.items()):
                if clean_name in result:
                    del result[clean_name]
                    paths_to_update.add(path)

            for path in paths_to_update:
                self.update_action_item_status(path)

            self.ui.right_panel.new_head_input.clear()
            self._setup_dynamic_ui() 
            
            current_path = self._get_current_action_path()
            if current_path:
                 self.display_manual_annotation(current_path)

            self._show_temp_message_box("Success", f"Category '{head_name}' removed.", QMessageBox.Icon.Information, 2500)
            self.is_data_dirty = True
            self.update_save_export_button_state()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")

    def _connect_dynamic_type_buttons(self):
        for head_name, group in self.ui.right_panel.label_groups.items():
            try:
                group.add_btn.clicked.disconnect()
                group.remove_btn.clicked.disconnect()
            except TypeError:
                pass 
            
            group.add_btn.clicked.connect(lambda _, h=head_name: self.add_custom_type(h))
            if isinstance(group, DynamicSingleLabelGroup):
                group.remove_btn.clicked.connect(lambda _, h=head_name: self.remove_custom_type(h))
            elif isinstance(group, DynamicMultiLabelGroup):
                group.remove_btn.clicked.connect(lambda _, h=head_name: self._remove_multi_labels_via_checkboxes(h))
                
    def _remove_multi_labels_via_checkboxes(self, head_name):
        group = self.ui.right_panel.label_groups.get(head_name)
        if not group or not isinstance(group, DynamicMultiLabelGroup): return

        labels_to_remove = group.get_checked_labels()
        if not labels_to_remove:
            self._show_temp_message_box("Warning", "Please check one or more labels to remove.", QMessageBox.Icon.Warning, 1500)
            return
            
        labels_removed = 0
        for type_to_remove in labels_to_remove:
            definition = self.label_definitions[head_name]
            if len(definition['labels']) <= 1:
                 self._show_temp_message_box("Warning", f"Cannot remove the last label in {head_name}.", QMessageBox.Icon.Warning, 1500)
                 continue

            self.label_definitions[head_name]['labels'].remove(type_to_remove)
            paths_to_update = set()
            keys_to_delete = []
            for path, anno in self.manual_annotations.items():
                if head_name in anno:
                    anno[head_name] = [label for label in anno[head_name] if label != type_to_remove]
                    if not anno[head_name]:
                        anno[head_name] = None
                    paths_to_update.add(path)
                if not any(v for k, v in anno.items() if k in self.label_definitions and v):
                     keys_to_delete.append(path)

            for path in keys_to_delete:
                del self.manual_annotations[path]
                paths_to_update.add(path)

            for path in paths_to_update:
                self.update_action_item_status(path)
            labels_removed += 1
            
        group.update_checkboxes(self.label_definitions[head_name]['labels'])
        current_path = self._get_current_action_path()
        if current_path:
             self.display_manual_annotation(current_path)

        if labels_removed > 0:
            self.is_data_dirty = True
        self._show_temp_message_box("Success", f"Successfully removed {labels_removed} label(s).", QMessageBox.Icon.Information, 1000)
        self.update_save_export_button_state()
            
    def _setup_dynamic_ui(self):
        self.ui.right_panel.setup_dynamic_labels(self.label_definitions)
        self._connect_dynamic_type_buttons()
        self.ui.right_panel.task_label.setText(f"Task: {self.current_task_name}")
        self.setWindowTitle(f"SoccerNet Pro Analysis Tool ({self.current_task_name} Tool)")
        
    def apply_stylesheet(self, mode="Night"):
        qss_path_name = "style.qss" if mode == "Night" else "style_day.qss"
        qss_path = resource_path(qss_path_name) 
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
            self.current_style_mode = mode
            print(f"Applied style: {mode}")
        except FileNotFoundError:
             print(f"Warning: {qss_path_name} not found.")
        except Exception as e:
             print(f"Error loading stylesheet: {e}")

    def change_style_mode(self, mode):
        self.apply_stylesheet(mode)

    def apply_action_filter(self):
        current_filter = self.ui.left_panel.filter_combo.currentIndex()
        if current_filter == self.FILTER_ALL:
            for item in self.action_item_map.values():
                item.setHidden(False)
            return
        for action_path, item in self.action_item_map.items():
            is_done = (action_path in self.manual_annotations and bool(self.manual_annotations[action_path])) or \
                      (action_path in self.analysis_results)
            if current_filter == self.FILTER_DONE:
                item.setHidden(not is_done)
            elif current_filter == self.FILTER_NOT_DONE:
                item.setHidden(is_done)

    # --- Data Import Logic ---
    def _dynamic_data_import(self):
        if not self.json_loaded:
             self._show_temp_message_box("Action Blocked", "Please import or create a GAC JSON project first.", QMessageBox.Icon.Warning, 2000)
             return
             
        if not self.current_working_directory or not os.path.isdir(self.current_working_directory):
             self.current_working_directory = QFileDialog.getExistingDirectory(self, "Select Working Directory to Store New Data")
             if not self.current_working_directory:
                 self._show_temp_message_box("Action Blocked", "A working directory is required.", QMessageBox.Icon.Warning, 2000)
                 return
                 
        has_video = 'video' in self.modalities
        has_image_or_audio = any(m in ['image', 'audio'] for m in self.modalities)

        if has_video and not has_image_or_audio:
            self._show_temp_message_box("Import Mode", "Detected: Video-Only. Batch Import Single Video Files.", QMessageBox.Icon.Information, 1500)
            self._prompt_media_import_options()
        elif has_video and has_image_or_audio:
            self._show_temp_message_box("Import Mode", "Detected: Multi-Modal. Scene Folder Import.", QMessageBox.Icon.Information, 1500)
            self._prompt_multi_modal_directory_import()
        else:
             self._show_temp_message_box("Import Blocked", "Unsupported modalities.", QMessageBox.Icon.Warning, 2500)
             
    def handle_data_import(self):
         self._dynamic_data_import() 

    def _prompt_media_import_options(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Single Video File Import (Mode 1)")
        msg.setText(f"How do you want to import video files?\n(Copied to '{self.SINGLE_VIDEO_PREFIX}XXX' folder)")
        
        btn_multi_files = msg.addButton("Import Multiple Files (Batch)", QMessageBox.ButtonRole.ActionRole)
        btn_single_file = msg.addButton("Import Single File", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg.setIcon(QMessageBox.Icon.Question)
        msg.exec()
        
        if msg.clickedButton() == btn_multi_files:
            self._import_files_as_virtual_actions(batch_mode=True)
        elif msg.clickedButton() == btn_single_file:
            self._import_files_as_virtual_actions(batch_mode=False)
            
    def _import_files_as_virtual_actions(self, batch_mode=True):
        video_ext_str = ' '.join(ext for ext in SUPPORTED_EXTENSIONS if ext in ('.mp4', '.avi', '.mov')).replace('.', '*')
        video_formats = f"Video Files ({video_ext_str})" 
        
        if batch_mode:
            original_file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Multiple Video Files", self.current_working_directory, video_formats)
        else:
            original_file_path, _ = QFileDialog.getOpenFileName(self, "Select Single Video File", self.current_working_directory, video_formats)
            original_file_paths = [original_file_path] if original_file_path else []

        if not original_file_paths:
            return

        total_files = len(original_file_paths)
        confirm_msg = QMessageBox(self)
        confirm_msg.setWindowTitle(f"Confirm Batch Video Import")
        confirm_msg.setText(f"Importing {total_files} video file(s).\nDo you want to proceed?")
        confirm_msg.setIcon(QMessageBox.Icon.Information)
        confirm_msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        if confirm_msg.exec() == QMessageBox.StandardButton.Cancel:
            return

        progress = QProgressDialog(f"Importing {total_files} video files...", "Cancel", 0, total_files, self)
        progress.setWindowTitle("Importing Media")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(0)
        progress.show()

        max_counter = 0
        for name in self.action_path_to_name.values():
            if name.startswith(self.SINGLE_VIDEO_PREFIX):
                try:
                    parts = name.split('_')
                    if len(parts) > 1 and parts[-1].isdigit():
                        max_counter = max(max_counter, int(parts[-1]))
                except ValueError:
                    continue
        counter = max_counter + 1
        
        added_actions = []

        for i, original_file_path in enumerate(original_file_paths):
            if progress.wasCanceled():
                break
            media_name = os.path.basename(original_file_path)
            progress.setLabelText(f"Importing {i+1}/{total_files}: {media_name}...")
            QApplication.processEvents()

            action_name = f"{self.SINGLE_VIDEO_PREFIX}{counter:03d}"
            virtual_action_path = os.path.join(self.current_working_directory, action_name)
            while os.path.exists(virtual_action_path):
                counter += 1
                action_name = f"{self.SINGLE_VIDEO_PREFIX}{counter:03d}"
                virtual_action_path = os.path.join(self.current_working_directory, action_name)
            
            try:
                os.makedirs(virtual_action_path)
                target_file_path = os.path.join(virtual_action_path, media_name)
                shutil.copy2(original_file_path, target_file_path) 
                self.action_item_data.insert(0, {'name': action_name, 'path': virtual_action_path})
                self.action_path_to_name[virtual_action_path] = action_name
                added_actions.append({'name': action_name, 'path': virtual_action_path})
                counter += 1
            except Exception as e:
                 shutil.rmtree(virtual_action_path, ignore_errors=True)
            progress.setValue(i + 1)
            QApplication.processEvents()

        progress.close()
        if added_actions:
            self._populate_action_tree()
            last_item = self.action_item_map.get(added_actions[-1]['path'])
            if last_item:
                self.ui.left_panel.action_tree.setCurrentItem(last_item)
            self.is_data_dirty = True
            self.update_save_export_button_state()
            self._show_temp_message_box("Import Complete", f"Imported {len(added_actions)} files.", QMessageBox.Icon.Information, 2000)

    # --- UPDATED: Multi-modal Directory Import Options ---
    def _prompt_multi_modal_directory_import(self):
        """
        Updates: Provides options to import a Root Directory (Batch) OR specific Scene Folder(s).
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("Multi-modal Scene Import (Mode 2)")
        msg.setText("How do you want to import the scene folders?\n(Folders containing video+image data)")
        
        # Option 1: Batch (Existing logic)
        btn_batch = msg.addButton("Batch Import (Select Root Folder)", QMessageBox.ButtonRole.ActionRole)
        # Option 2: Specific (New logic)
        btn_single = msg.addButton("Import Single Scene Folder", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg.setIcon(QMessageBox.Icon.Question)
        msg.exec()
        
        clicked = msg.clickedButton()
        
        if clicked == btn_batch:
            # --- Option 1: Root Directory Import (Batch) ---
            root_dir_path = QFileDialog.getExistingDirectory(
                self, 
                "Select Root Directory Containing All Multi-view Scenes",
                self.current_working_directory
            )
            if not root_dir_path: return

            dir_paths = [
                os.path.join(root_dir_path, name) 
                for name in os.listdir(root_dir_path)
                if os.path.isdir(os.path.join(root_dir_path, name))
            ]

            if not dir_paths:
                self._show_temp_message_box("Import Warning", f"No subdirectories found in: {root_dir_path}", QMessageBox.Icon.Warning, 2500)
                return

            self._process_multi_modal_directories(dir_paths)
            
        elif clicked == btn_single:
            # --- Option 2: Specific Single Directory Import ---
            # Note: QFileDialog doesn't natively support multi-directory selection easily. 
            # To import multiple specific folders, the user repeats this step.
            specific_dir_path = QFileDialog.getExistingDirectory(
                self,
                "Select Specific Scene Directory",
                self.current_working_directory
            )
            if not specific_dir_path: return
            
            self._process_multi_modal_directories([specific_dir_path])

    def _process_multi_modal_directories(self, dir_paths):
        """Helper function to process a list of directories (used by both Batch and Single modes)."""
        all_added_actions = []
        total_dirs = len(dir_paths)
        
        progress = QProgressDialog(f"Processing {total_dirs} directories...", "Cancel", 0, total_dirs, self)
        progress.setWindowTitle("Importing Multi-modal Scenes")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(0)
        progress.show()

        for i, dir_path in enumerate(dir_paths):
            if progress.wasCanceled():
                break
            
            progress.setLabelText(f"Processing: {os.path.basename(dir_path)}...")
            QApplication.processEvents()

            if any(os.path.splitext(f)[1].lower().endswith(SUPPORTED_EXTENSIONS) for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))):
                action_data = self._import_single_directory_as_action(dir_path)
                if action_data:
                    all_added_actions.append(action_data)
            else:
                 print(f"Skipping directory {dir_path}: No supported media files found.")

            progress.setValue(i + 1)
            QApplication.processEvents()

        progress.close()
        
        if all_added_actions:
            self.action_item_data.extend(all_added_actions) 
            self._populate_action_tree()

            last_item = self.action_item_map.get(all_added_actions[-1]['path'])
            if last_item:
                self.ui.left_panel.action_tree.setCurrentItem(last_item)

            self.is_data_dirty = True
            self.update_save_export_button_state()
            self._show_temp_message_box("Import Complete", f"Successfully imported {len(all_added_actions)} scene(s).", QMessageBox.Icon.Information, 2000)

    def _import_single_directory_as_action(self, dir_path):
        file_paths = [os.path.join(dir_path, entry.name) for entry in os.scandir(dir_path) 
                      if entry.is_file() and entry.name.lower().endswith(SUPPORTED_EXTENSIONS)]
        
        if not file_paths:
            return None
        
        max_counter = 0
        for name in self.action_path_to_name.values():
            if name.startswith(self.SINGLE_VIDEO_PREFIX):
                try:
                    parts = name.split('_')
                    if len(parts) > 1 and parts[-1].isdigit():
                        max_counter = max(max_counter, int(parts[-1]))
                except ValueError:
                    continue
        counter = max_counter + 1

        action_name = f"{self.SINGLE_VIDEO_PREFIX}{counter:03d}"
        virtual_action_path = os.path.join(self.current_working_directory, action_name)
        
        while os.path.exists(virtual_action_path):
             counter += 1
             action_name = f"{self.SINGLE_VIDEO_PREFIX}{counter:03d}"
             virtual_action_path = os.path.join(self.current_working_directory, action_name)

        try:
            os.makedirs(virtual_action_path)
            added_count = 0
            for original_file_path in file_paths:
                media_name = os.path.basename(original_file_path)
                target_file_path = os.path.join(virtual_action_path, media_name)
                shutil.copy2(original_file_path, target_file_path)
                added_count += 1
            
            if added_count > 0:
                self.action_path_to_name[virtual_action_path] = action_name
                return {'name': action_name, 'path': virtual_action_path}
            else:
                shutil.rmtree(virtual_action_path, ignore_errors=True)
                return None

        except Exception as e:
            shutil.rmtree(virtual_action_path, ignore_errors=True)
            return None
            
    def _import_directory_as_single_action(self):
        self._prompt_multi_modal_directory_import()

    def _populate_action_tree(self):
        if not self.action_item_data:
            self.ui.left_panel.action_tree.clear() 
            self.action_item_map.clear()
            return

        self.ui.left_panel.action_tree.clear()
        self.action_item_map.clear()
        
        action_folders = []
        virtual_actions = [] 

        for data in self.action_item_data:
            name = data['name']
            if name.startswith("action_"):
                action_folders.append(data)
            elif name.startswith(self.SINGLE_VIDEO_PREFIX):
                virtual_actions.append(data)
            else:
                action_folders.append(data) 

        sorted_virtual = sorted(virtual_actions, key=lambda d: get_action_number(type('MockEntry', (object,), {'name': d['name']})()))
        sorted_actions = sorted(action_folders, key=lambda d: get_action_number(type('MockEntry', (object,), {'name': d['name']})()))
        final_list = sorted_virtual + sorted_actions

        for data in final_list:
            action_item = self.ui.left_panel.add_action_item(data['name'], data['path'])
            self.action_item_map[data['path']] = action_item
            
        for path in self.action_item_map.keys():
            self.update_action_item_status(path)
        self.apply_action_filter()

    def add_custom_type(self, head_name):
        group = self.ui.right_panel.label_groups.get(head_name)
        if not group: return

        new_type = group.input_field.text().strip()
        if not new_type:
            self._show_temp_message_box("Warning", "Type name cannot be empty.", QMessageBox.Icon.Warning, 1500)
            return
        type_set = set(self.label_definitions[head_name]['labels'])
        if new_type in type_set:
            self._show_temp_message_box("Warning", f"'{new_type}' already exists in {head_name}.", QMessageBox.Icon.Warning, 1500)
            group.input_field.clear()
            return
        
        self.label_definitions[head_name]['labels'].append(new_type)
        self.label_definitions[head_name]['labels'].sort()
        
        if isinstance(group, DynamicSingleLabelGroup):
             group.update_radios(self.label_definitions[head_name]['labels'])
        elif isinstance(group, DynamicMultiLabelGroup):
             group.update_checkboxes(self.label_definitions[head_name]['labels'])
        
        self.is_data_dirty = True
        self._show_temp_message_box("Success", f"'{new_type}' added.", QMessageBox.Icon.Information, 1000)
        group.input_field.clear()
        self.update_save_export_button_state()

    def remove_custom_type(self, head_name):
        group = self.ui.right_panel.label_groups.get(head_name)
        if not group or not isinstance(group, DynamicSingleLabelGroup): 
             return
        definition = self.label_definitions[head_name]
        type_set = set(definition['labels'])
        type_to_remove = group.get_selected_label_to_remove()

        if not type_to_remove:
            self._show_temp_message_box("Warning", "Please select a label to remove.", QMessageBox.Icon.Warning, 1500)
            return
        if len(definition['labels']) <= 1:
             self._show_temp_message_box("Warning", f"Cannot remove the last label in {head_name}.", QMessageBox.Icon.Warning, 1500)
             group.remove_combo.setCurrentIndex(0)
             return

        if type_to_remove in type_set:
            self.label_definitions[head_name]['labels'].remove(type_to_remove)
            
        if isinstance(group, DynamicSingleLabelGroup):
            group.update_radios(self.label_definitions[head_name]['labels'])
            
        paths_to_update = set()
        keys_to_delete = []
        for path, anno in self.manual_annotations.items():
            if definition['type'] == 'single_label' and anno.get(head_name) == type_to_remove:
                anno[head_name] = None
                paths_to_update.add(path)
            if not any(v for k, v in anno.items() if k in self.label_definitions and v):
                 keys_to_delete.append(path)

        for path in keys_to_delete:
            del self.manual_annotations[path]
            paths_to_update.add(path)

        for path in paths_to_update:
            self.update_action_item_status(path)
        current_path = self._get_current_action_path()
        if current_path:
             self.display_manual_annotation(current_path)

        self.is_data_dirty = True
        self._show_temp_message_box("Success", f"'{type_to_remove}' removed.", QMessageBox.Icon.Information, 1000)
        self.update_save_export_button_state()
            
    def _validate_gac_json(self, data):
        if 'modalities' not in data:
            return False, "Missing 'modalities' field."
        if not isinstance(data['modalities'], list):
            return False, "'modalities' must be a list."
        if 'labels' not in data:
            return False, "Missing 'labels' field."
        if not isinstance(data['labels'], dict):
            return False, "'labels' must be a dictionary."
        for head_name, definition in data['labels'].items():
            if not isinstance(definition, dict):
                 return False, f"Label head '{head_name}' must be a dictionary."
            if definition.get('type') not in ['single_label', 'multi_label']:
                return False, f"Label head '{head_name}' missing valid 'type'."
            if not isinstance(definition.get('labels'), list):
                return False, f"Label head '{head_name}' missing 'labels' list."
        return True, None

    def import_annotations(self):
        self.clear_action_list(clear_working_dir=False) 
        file_path, _ = QFileDialog.getOpenFileName(self, "Select GAC JSON Annotation File", "", "JSON Files (*.json)")
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to parse JSON: {e}")
            return
        is_valid, error_msg = self._validate_gac_json(data)
        if not is_valid:
            QMessageBox.critical(self, "JSON Format Error", error_msg)
            self.clear_action_list()
            return
        
        imported_count = 0
        self.modalities = data.get('modalities', [])
        self.current_working_directory = os.path.dirname(file_path)
        self.current_task_name = data.get('task', RightPanel.DEFAULT_TASK_NAME)
        self.label_definitions.clear()
        if 'labels' in data and isinstance(data['labels'], dict):
            for head_name, definition in data['labels'].items():
                label_type = definition.get('type')
                if label_type in ['single_label', 'multi_label']:
                    labels = sorted(list(set(definition.get('labels', []))))
                    self.label_definitions[head_name] = {'type': label_type, 'labels': labels}
        self._setup_dynamic_ui()
        
        for item in data.get('data', []):
            action_id = item.get('id') 
            if not action_id: continue
            action_path = None
            potential_dir_path = os.path.join(self.current_working_directory, action_id)
            if os.path.isdir(potential_dir_path):
                 action_path = potential_dir_path
            else:
                for input_item in item.get('inputs', []):
                     if 'path' in input_item:
                          media_file_name = os.path.basename(input_item['path'])
                          potential_clip_path = os.path.join(self.current_working_directory, media_file_name)
                          if os.path.isfile(potential_clip_path):
                               action_path = os.path.dirname(potential_clip_path) 
                               break
            if not action_path: continue 
            action_name = action_id 

            if action_path not in self.action_path_to_name:
                self.action_item_data.append({'name': action_name, 'path': action_path})
                self.action_path_to_name[action_path] = action_name

            self.imported_action_metadata[action_path] = item.get('metadata', {})
            for input_item in item.get('inputs', []):
                 if 'path' in input_item:
                     fname = os.path.basename(input_item['path'])
                     self.imported_input_metadata[(action_path, fname)] = input_item.get('metadata', {})

            item_labels = item.get('labels', {})
            manual_labels = {}
            has_label = False
            for head_name, definition in self.label_definitions.items():
                if head_name in item_labels:
                    label_content = item_labels[head_name]
                    if isinstance(label_content, dict):
                        if definition['type'] == 'single_label' and 'label' in label_content:
                            val = label_content['label']
                            if val in definition['labels']:
                                manual_labels[head_name] = val
                                has_label = True
                        elif definition['type'] == 'multi_label' and 'labels' in label_content:
                             vals = [l for l in label_content['labels'] if l in definition['labels']]
                             if vals:
                                 manual_labels[head_name] = vals
                                 has_label = True
                    elif isinstance(label_content, str) and definition['type'] == 'single_label':
                         if label_content in definition['labels']:
                             manual_labels[head_name] = label_content
                             has_label = True
                    elif isinstance(label_content, list) and definition['type'] == 'multi_label':
                         valid_vals = [l for l in label_content if l in definition['labels']]
                         if valid_vals:
                             manual_labels[head_name] = valid_vals
                             has_label = True
            if has_label:
                self.manual_annotations[action_path] = manual_labels
                imported_count += 1
        
        self.current_json_path = file_path
        self._populate_action_tree()
        self.json_loaded = True
        self.is_data_dirty = False 
        self.ui.right_panel.manual_group_box.setEnabled(True)
        self.toggle_annotation_view() 
        for path in self.action_path_to_name.keys():
            self.update_action_item_status(path) 
        self.update_save_export_button_state()
        self._show_temp_message_box("Import Complete", f"Imported {imported_count} annotations.", QMessageBox.Icon.Information, 2000)
        current_item = self.ui.left_panel.action_tree.currentItem()
        if current_item:
            self.on_item_selected(current_item, None) 

    # --- NEW FUNCTION: Create New Project Logic ---
    def create_new_project(self):
        """Opens dialog to create a new JSON structure in memory."""
        # 1. Check for unsaved work before clearing
        if self.is_data_dirty:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes in the current project. Creating a new project will clear them.\nDo you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # 2. Show Dialog
        dialog = CreateProjectDialog(self)
        if dialog.exec():
            # 3. Get Data
            new_project_data = dialog.get_data()
            
            # 4. Clear current workspace (similar to import, but keeps us in memory)
            self.clear_action_list(clear_working_dir=False)
            
            # 5. Initialize State
            self.current_task_name = new_project_data['task']
            self.modalities = new_project_data['modalities']
            self.label_definitions = new_project_data['labels']
            
            # Set a description if needed
            self.project_description = new_project_data['description']
            
            # 6. Set Flags
            self.json_loaded = True
            self.current_json_path = None # No file path yet, user must "Save As"
            self.is_data_dirty = True # It's a new unsaved project
            
            # 7. Update UI
            self._setup_dynamic_ui()
            self.update_save_export_button_state()
            self.toggle_annotation_view()
            
            # 8. Feedback
            self._show_temp_message_box(
                "Project Created", 
                f"Project '{self.current_task_name}' created.\nYou can now Add Data.", 
                QMessageBox.Icon.Information, 
                2500
            )

    def clear_action_list(self, clear_working_dir=True):
        self.ui.left_panel.action_tree.clear()
        self.analysis_results.clear()
        self.manual_annotations.clear()
        self.action_item_map.clear()
        self.action_item_data.clear()
        self.action_path_to_name.clear()
        self.modalities.clear() 
        self.imported_action_metadata.clear() 
        self.imported_input_metadata.clear()  
        self.current_json_path = None
        self.json_loaded = False 
        self.is_data_dirty = False 
        self.project_description = "" # Reset description
        if clear_working_dir:
            self.current_working_directory = None
        self.update_save_export_button_state()
        self.ui.right_panel.start_button.setEnabled(False)
        self.ui.right_panel.progress_bar.setVisible(False)
        self.ui.right_panel.results_widget.setVisible(False)
        self.ui.right_panel.auto_group_box.setChecked(False)
        self.ui.right_panel.manual_group_box.setEnabled(False) 
        self.current_task_name = RightPanel.DEFAULT_TASK_NAME
        self.label_definitions = self.DEFAULT_LABEL_DEFINITIONS.copy()
        self._setup_dynamic_ui()

    def toggle_annotation_view(self):
        can_annotate_and_analyze = False 
        current_item = self.ui.left_panel.action_tree.currentItem()
        if current_item and current_item.childCount() > 0 and self.json_loaded:
            can_annotate_and_analyze = True
        self.ui.right_panel.manual_group_box.setEnabled(bool(can_annotate_and_analyze))
        self.ui.right_panel.start_button.setEnabled(bool(can_annotate_and_analyze))

    def on_item_selected(self, current_item, _):
        if not current_item:
            self.toggle_annotation_view() 
            self.ui.right_panel.results_widget.setVisible(False)
            self.ui.right_panel.auto_group_box.setChecked(False)
            return
        is_action_item = (current_item.childCount() > 0) or (current_item.parent() is None) 
        action_path = None
        if is_action_item:
            action_path = current_item.data(0, Qt.ItemDataRole.UserRole)
            first_media_path = None
            if current_item.childCount() > 0:
                first_media_path = current_item.child(0).data(0, Qt.ItemDataRole.UserRole)
            self.ui.center_panel.show_single_view(first_media_path)
            self.ui.center_panel.multi_view_button.setEnabled(True) 
        else:
            clip_path = current_item.data(0, Qt.ItemDataRole.UserRole)
            self.ui.center_panel.show_single_view(clip_path)
            if current_item.parent():
                action_path = current_item.parent().data(0, Qt.ItemDataRole.UserRole)
            self.ui.center_panel.multi_view_button.setEnabled(False) 
        self.toggle_annotation_view()
        if action_path:
            self.display_analysis_results(action_path)
            self.display_manual_annotation(action_path)
        self.update_save_export_button_state() 
            
    def play_video(self):
        self.ui.center_panel.toggle_play_pause()

    def show_all_views(self):
        current_item = self.ui.left_panel.action_tree.currentItem()
        if not current_item:
            return
        if current_item.parent() is not None:
             current_item = current_item.parent()
        action_path = current_item.data(0, Qt.ItemDataRole.UserRole)
        if current_item.childCount() > 0:
            clip_paths = []
            for j in range(current_item.childCount()):
                clip_path = current_item.child(j).data(0, Qt.ItemDataRole.UserRole)
                if clip_path.lower().endswith(('.mp4', '.avi', '.mov')):
                     clip_paths.append(clip_path)
        else:
            return 
        self.ui.center_panel.show_all_views(clip_paths)

    def start_analysis(self):
        if not self.json_loaded:
             self._show_temp_message_box("Action Blocked", "Please import a GAC JSON file before starting analysis.", QMessageBox.Icon.Warning, 2000)
             return
        current_item = self.ui.left_panel.action_tree.currentItem()
        if not current_item:
            return
        if current_item.parent() is not None:
             current_item = current_item.parent()
        if current_item.childCount() == 0:
            return
        self.ui.right_panel.start_button.setEnabled(False)
        self.ui.left_panel.action_tree.setEnabled(False)
        action_path = current_item.data(0, Qt.ItemDataRole.UserRole)
        clip_paths = []
        for j in range(current_item.childCount()):
            clip_path = current_item.child(j).data(0, Qt.ItemDataRole.UserRole)
            if clip_path.lower().endswith(('.mp4', '.avi', '.mov')):
                 clip_paths.append(clip_path)
        
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
            result = run_model_on_action(clip_paths, self.label_definitions)
            self.analysis_results[action_path] = result
            self.is_data_dirty = True
            self.ui.right_panel.export_button.setEnabled(True)
            self.display_analysis_results(action_path)
            self.update_action_item_status(action_path)
        else:
             self._show_temp_message_box("Analysis Skipped", "No video files to analyze.", QMessageBox.Icon.Warning, 2000)
        self.ui.right_panel.start_button.setEnabled(True)
        self.ui.left_panel.action_tree.setEnabled(True)
        self.update_save_export_button_state()

    def _get_current_action_path(self):
        current_item = self.ui.left_panel.action_tree.currentItem()
        if not current_item: return None
        if current_item.parent() is None:
            return current_item.data(0, Qt.ItemDataRole.UserRole)
        else:
            return current_item.parent().data(0, Qt.ItemDataRole.UserRole)

    def save_manual_annotation(self):
        if not self.json_loaded:
             self._show_temp_message_box("Action Blocked", "Please import a GAC JSON file first.", QMessageBox.Icon.Warning, 2000)
             return
        action_path = self._get_current_action_path()
        if not action_path: return
        data = self.ui.right_panel.get_manual_annotation()
        action_name = self.action_path_to_name.get(action_path)
        is_annotated = False
        cleaned_data = {}
        for k, v in data.items():
            if isinstance(v, list) and v: 
                cleaned_data[k] = v
                is_annotated = True
            elif isinstance(v, str) and v: 
                cleaned_data[k] = v
                is_annotated = True
            elif v is not None: 
                pass
        if is_annotated:
            self.manual_annotations[action_path] = cleaned_data
            self.is_data_dirty = True
            self._show_temp_message_box("Success", f"Annotation saved for {action_name}.", QMessageBox.Icon.Information, 1500)
        elif action_path in self.manual_annotations:
            del self.manual_annotations[action_path]
            self.is_data_dirty = True
            self._show_temp_message_box("Success", f"Annotation cleared for {action_name}.", QMessageBox.Icon.Information, 1500)
        else:
            self._show_temp_message_box("No Selection", "Please select at least one label.", QMessageBox.Icon.Warning, 1500)
        self.update_save_export_button_state()
        self.update_action_item_status(action_path)

    def clear_current_manual_annotation(self):
        action_path = self._get_current_action_path()
        if not action_path: return
        self.ui.right_panel.clear_manual_selection()
        action_name = self.action_path_to_name.get(action_path)
        if action_path in self.manual_annotations:
            del self.manual_annotations[action_path]
            self.is_data_dirty = True
            self._show_temp_message_box("Cleared", f"Annotation for {action_name} cleared.", QMessageBox.Icon.Information, 1500)
        self.update_save_export_button_state()
        self.update_action_item_status(action_path)

    def display_manual_annotation(self, action_path):
        if action_path in self.manual_annotations:
            self.ui.right_panel.set_manual_annotation(self.manual_annotations[action_path])
        else:
            self.ui.right_panel.clear_manual_selection()

    def display_analysis_results(self, action_path):
        if action_path in self.analysis_results:
            self.ui.right_panel.update_results(self.analysis_results[action_path])
            self.ui.right_panel.results_widget.setVisible(True)
            self.ui.right_panel.auto_group_box.setChecked(True)
        else:
            self.ui.right_panel.results_widget.setVisible(False)
            self.ui.right_panel.auto_group_box.setChecked(False)

    def update_save_export_button_state(self):
        can_export = self.json_loaded and (bool(self.analysis_results) or bool(self.manual_annotations))
        can_save = can_export and (self.current_json_path is not None) and self.is_data_dirty
        self.ui.right_panel.export_button.setEnabled(can_export)
        self.ui.right_panel.save_button.setEnabled(can_save)

    def save_results_to_json(self):
        if not self.json_loaded:
             self._show_temp_message_box("Action Blocked", "Please import a GAC JSON file first.", QMessageBox.Icon.Warning, 2000)
             return
        if self.current_json_path:
            self._write_gac_json(self.current_json_path)
        else:
            self.export_results_to_json()

    def export_results_to_json(self):
        if not self.json_loaded:
             self._show_temp_message_box("Action Blocked", "Please import a GAC JSON file first.", QMessageBox.Icon.Warning, 2000)
             return
        path, _ = QFileDialog.getSaveFileName(self, "Save GAC JSON Annotation As...", "", "JSON Files (*.json)")
        if not path: return
        self._write_gac_json(path)
        self.current_json_path = path
        self.update_save_export_button_state()

    def _write_gac_json(self, file_path):
        all_action_paths = set(self.action_path_to_name.keys()) 
        all_action_paths.update(self.analysis_results.keys()) 
        all_action_paths.update(self.manual_annotations.keys()) 
        
        # If it's a newly created project with no data yet, allow saving empty structure
        if not all_action_paths and not self.json_loaded:
             self._show_temp_message_box("No Data", "There is no project data to save.", QMessageBox.Icon.Warning)
             return False

        output_data = {
            "version": "1.0",
            "date": datetime.datetime.now().isoformat().split('T')[0],
            "task": self.current_task_name, 
            "description": getattr(self, 'project_description', ""),
            "dataset_name": "Dynamic Action Classification Export",
            "metadata": {
                "created_by": "SoccerNet Pro Analysis Tool",
                "source": "Professional Soccer Dataset",
                "license": "CC-BY-NC-4.0"
            },
            "modalities": self.modalities, 
            "labels": self.label_definitions.copy()
        }

        output_data["data"] = []
        path_to_item_map = {}
        root = self.ui.left_panel.action_tree.invisibleRootItem()

        if self.json_loaded:
            for i in range(root.childCount()):
                item = root.child(i)
                path_to_item_map[item.data(0, Qt.ItemDataRole.UserRole)] = item

        sorted_paths = sorted(list(all_action_paths), key=lambda p: self.action_path_to_name.get(p, ""))

        for action_path in sorted_paths:
            action_name = self.action_path_to_name.get(action_path)
            if not action_name: continue
                
            auto_result = self.analysis_results.get(action_path, {})
            manual_result = self.manual_annotations.get(action_path, {})
            stored_metadata = self.imported_action_metadata.get(action_path, {})
            
            data_item = {
                "id": action_name,
                "inputs": [],
                "labels": {},
                "metadata": stored_metadata 
            }
            
            for head_name, definition in self.label_definitions.items():
                if definition['type'] == 'single_label':
                    final_label = None
                    if manual_result and manual_result.get(head_name) and isinstance(manual_result.get(head_name), str):
                        final_label = manual_result.get(head_name)
                    elif auto_result and head_name in auto_result and 'distribution' in auto_result[head_name]:
                        dist = auto_result[head_name]['distribution']
                        predicted_label = max(dist, key=dist.get)
                        if predicted_label in definition['labels']:
                            final_label = predicted_label
                    if final_label:
                        data_item["labels"][head_name] = {"label": final_label}
                elif definition['type'] == 'multi_label':
                    final_label_list = []
                    if manual_result and manual_result.get(head_name) and isinstance(manual_result.get(head_name), list):
                        final_label_list = manual_result[head_name]
                    data_item["labels"][head_name] = {"labels": final_label_list}

            action_item = path_to_item_map.get(action_path)
            if action_item:
                for j in range(action_item.childCount()):
                    clip_item = action_item.child(j)
                    clip_path = clip_item.data(0, Qt.ItemDataRole.UserRole)
                    clip_name_with_ext = os.path.basename(clip_path)
                    
                    file_ext = os.path.splitext(clip_name_with_ext)[1].lower()
                    modality_type = "unknown"
                    if file_ext in ('.mp4', '.avi', '.mov'):
                        modality_type = "video"
                    elif file_ext in ('.jpg', '.jpeg', '.png', '.bmp'):
                        modality_type = "image"
                    elif file_ext in ('.wav', '.mp3', '.aac'):
                         modality_type = "audio"
                    
                    input_meta = self.imported_input_metadata.get((action_path, clip_name_with_ext), {})
                    simulated_path = f"Dataset/Train/{action_name}/{clip_name_with_ext}" 
                    
                    data_item["inputs"].append({
                        "type": modality_type,
                        "path": simulated_path,
                        "metadata": input_meta 
                    })

            if data_item["labels"] or data_item["inputs"]: 
                output_data["data"].append(data_item)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            self.is_data_dirty = False
            self._show_temp_message_box("Save Complete", f"Saved to {os.path.basename(file_path)}", QMessageBox.Icon.Information, 2000)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to write JSON: {e}")
            return False

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ActionClassifierApp()
    window.show()
    sys.exit(app.exec())
