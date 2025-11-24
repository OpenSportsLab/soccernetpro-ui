# main.py
import sys
import os
import time
import json
import datetime 
import shutil
import copy
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox, QStyle, 
    QTreeWidgetItem, QRadioButton, QProgressDialog
)
from PyQt6.QtCore import Qt, QTimer, QPointF, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QKeySequence, QShortcut

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

def get_action_number(entry):
    try:
        parts = entry.name.split('_')
        if len(parts) > 1 and parts[-1].isdigit():
            return int(parts[-1])
        if len(parts) > 2 and parts[-2].isdigit():
             return int(parts[-2])
        return float('inf')
    except (IndexError, ValueError, AttributeError):
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

        self.manual_annotations = {} 
        
        # --- Undo/Redo Stacks ---
        self.undo_stack = [] 
        self.redo_stack = []
        
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
        self._setup_shortcuts()
        self.apply_stylesheet(self.current_style_mode) 
        
        self.ui.right_panel.annotation_content_widget.setVisible(True) 
        self.ui.left_panel.filter_combo.setCurrentIndex(self.FILTER_ALL) 
        self.ui.right_panel.manual_group_box.setEnabled(False)
        
        self._setup_dynamic_ui()

    def closeEvent(self, event):
        can_export = self.json_loaded and bool(self.manual_annotations)
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
        is_done = (action_path in self.manual_annotations and bool(self.manual_annotations[action_path]))
        
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
        self.ui.left_panel.create_json_button.clicked.connect(self.create_new_project)
        self.ui.left_panel.add_data_button.clicked.connect(self._dynamic_data_import) 
        
        self.ui.left_panel.action_tree.currentItemChanged.connect(self.on_item_selected)
        self.ui.left_panel.filter_combo.currentIndexChanged.connect(self.apply_action_filter)
        
        self.ui.left_panel.undo_button.clicked.connect(self.perform_undo)
        self.ui.left_panel.redo_button.clicked.connect(self.perform_redo)
        
        self.ui.center_panel.play_button.clicked.connect(self.play_video)
        self.ui.center_panel.multi_view_button.clicked.connect(self.show_all_views)
        
        self.ui.right_panel.save_button.clicked.connect(self.save_results_to_json)
        self.ui.right_panel.export_button.clicked.connect(self.export_results_to_json)
        self.ui.right_panel.confirm_manual_button.clicked.connect(self.save_manual_annotation)
        self.ui.right_panel.clear_manual_button.clicked.connect(self.clear_current_manual_annotation)
        
        self.ui.right_panel.add_head_clicked.connect(self._handle_add_label_head)
        self.ui.right_panel.remove_head_clicked.connect(self._handle_remove_label_head) 
        self.ui.right_panel.style_mode_changed.connect(self.change_style_mode)

    def _setup_shortcuts(self):
        self.undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        self.undo_shortcut.activated.connect(self.perform_undo)
        
        self.redo_shortcut = QShortcut(QKeySequence.StandardKey.Redo, self)
        self.redo_shortcut.activated.connect(self.perform_redo)

    # --- UNDO / REDO LOGIC ---
    def _push_undo_command(self, action_path, old_data, new_data):
        """Records an action to the undo stack."""
        if old_data == new_data:
            return

        command = {
            'path': action_path,
            'old': copy.deepcopy(old_data),
            'new': copy.deepcopy(new_data)
        }
        self.undo_stack.append(command)
        self.redo_stack.clear() 
        self._update_undo_redo_buttons()
        self.is_data_dirty = True
        self.update_save_export_button_state()

    def perform_undo(self):
        if not self.undo_stack:
            return

        command = self.undo_stack.pop()
        self.redo_stack.append(command)

        action_path = command['path']
        old_data = command['old']

        if old_data is None:
            if action_path in self.manual_annotations:
                del self.manual_annotations[action_path]
        else:
            self.manual_annotations[action_path] = copy.deepcopy(old_data)

        self._refresh_ui_after_undo_redo(action_path)
        self._update_undo_redo_buttons()
        self._show_temp_message_box("Undo", "Action undone.", duration_ms=500)

    def perform_redo(self):
        if not self.redo_stack:
            return

        command = self.redo_stack.pop()
        self.undo_stack.append(command)

        action_path = command['path']
        new_data = command['new']

        if new_data is None:
            if action_path in self.manual_annotations:
                del self.manual_annotations[action_path]
        else:
            self.manual_annotations[action_path] = copy.deepcopy(new_data)

        self._refresh_ui_after_undo_redo(action_path)
        self._update_undo_redo_buttons()
        self._show_temp_message_box("Redo", "Action redone.", duration_ms=500)

    def _refresh_ui_after_undo_redo(self, action_path):
        self.update_action_item_status(action_path)
        
        # If possible, select the item in the tree to show the change
        if action_path in self.action_item_map:
             item = self.action_item_map[action_path]
             self.ui.left_panel.action_tree.setCurrentItem(item)

        current_path = self._get_current_action_path()
        if current_path == action_path:
            self.display_manual_annotation(action_path)
            
        self.is_data_dirty = True
        self.update_save_export_button_state()

    def _update_undo_redo_buttons(self):
        self.ui.left_panel.undo_button.setEnabled(len(self.undo_stack) > 0)
        self.ui.left_panel.redo_button.setEnabled(len(self.redo_stack) > 0)

    # -------------------------

    def _handle_add_label_head(self, head_name):
        clean_name = head_name.strip().replace(' ', '_').lower()
        if not clean_name:
            self._show_temp_message_box("Warning", "Category name cannot be empty.", QMessageBox.Icon.Warning, 1500)
            return
        if clean_name in self.label_definitions:
            self._show_temp_message_box("Warning", f"Category '{head_name}' already exists.", QMessageBox.Icon.Warning, 1500)
            return

        # --- TYPE SELECTION DIALOG ---
        msg = QMessageBox(self)
        msg.setWindowTitle("Select Category Type")
        msg.setText(f"Select the annotation type for the new category: '{head_name}'")
        msg.setIcon(QMessageBox.Icon.Question)
        
        btn_single = msg.addButton("Single Label", QMessageBox.ButtonRole.ActionRole)
        btn_multi = msg.addButton("Multi Label", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg.exec()
        clicked = msg.clickedButton()
        
        selected_type = None
        if clicked == btn_single:
            selected_type = "single_label"
        elif clicked == btn_multi:
            selected_type = "multi_label"
        else:
            return 

        new_head_definition = {
            "type": selected_type, 
            "labels": [] 
        }
        self.label_definitions[clean_name] = new_head_definition
        self.ui.right_panel.new_head_input.clear()
        
        self._setup_dynamic_ui()
        
        type_display = "Single Label" if selected_type == "single_label" else "Multi Label"
        self._show_temp_message_box("Success", f"Added '{head_name}' as {type_display}.", QMessageBox.Icon.Information, 2000)
        self.is_data_dirty = True
        self.update_save_export_button_state()

    def _handle_remove_label_head(self, head_name):
        clean_name = head_name.strip().replace(' ', '_').lower()
        if clean_name not in self.label_definitions:
            self._show_temp_message_box("Warning", f"Category '{head_name}' not found.", QMessageBox.Icon.Warning, 1500)
            return
        if clean_name in self.DEFAULT_LABEL_DEFINITIONS:
            self._show_temp_message_box("Warning", f"Cannot remove default imported category '{head_name}'.", QMessageBox.Icon.Warning, 2500)
            return

        reply = QMessageBox.question(self, 'Confirm Removal',
            f"Are you sure you want to remove the category '{head_name}'? All annotations will be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.No:
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
            except (TypeError, AttributeError):
                pass 
            
            # 1. Connect Add Label
            group.add_btn.clicked.connect(lambda _, h=head_name: self.add_custom_type(h))
            
            # 2. Connect Remove Label (Label Trash Button)
            # The signal is emitted from the group with the label name string
            group.remove_label_signal.connect(lambda label_name, h=head_name: self.remove_custom_type(h, label_name))

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

    def remove_custom_type(self, head_name, type_to_remove):
        # Updated signature to accept specific label name from signal
        group = self.ui.right_panel.label_groups.get(head_name)
        if not group: return
        
        definition = self.label_definitions[head_name]
        type_set = set(definition['labels'])

        if len(definition['labels']) <= 1:
             self._show_temp_message_box("Warning", f"Cannot remove the last label in {head_name}.", QMessageBox.Icon.Warning, 1500)
             return

        if type_to_remove in type_set:
            self.label_definitions[head_name]['labels'].remove(type_to_remove)
            
        if isinstance(group, DynamicSingleLabelGroup):
            group.update_radios(self.label_definitions[head_name]['labels'])
        elif isinstance(group, DynamicMultiLabelGroup):
            group.update_checkboxes(self.label_definitions[head_name]['labels'])
            
        paths_to_update = set()
        keys_to_delete = []
        for path, anno in self.manual_annotations.items():
            # Handle single label removal
            if definition['type'] == 'single_label' and anno.get(head_name) == type_to_remove:
                anno[head_name] = None
                paths_to_update.add(path)
            # Handle multi label removal
            elif definition['type'] == 'multi_label' and head_name in anno:
                if isinstance(anno[head_name], list) and type_to_remove in anno[head_name]:
                    anno[head_name].remove(type_to_remove)
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
        current_path = self._get_current_action_path()
        if current_path:
             self.display_manual_annotation(current_path)

        self.is_data_dirty = True
        self._show_temp_message_box("Success", f"'{type_to_remove}' removed.", QMessageBox.Icon.Information, 1000)
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
            is_done = (action_path in self.manual_annotations and bool(self.manual_annotations[action_path]))
            if current_filter == self.FILTER_DONE:
                item.setHidden(not is_done)
            elif current_filter == self.FILTER_NOT_DONE:
                item.setHidden(is_done)

    # --- Data Import Logic ---
    def _dynamic_data_import(self):
        if not self.json_loaded:
             self._show_temp_message_box("Action Blocked", "Please import or create a GAC JSON project first.", QMessageBox.Icon.Warning, 2000)
             return
             
        if not self.current_working_directory:
             pass
                 
        has_video = 'video' in self.modalities
        has_image_or_audio = any(m in ['image', 'audio'] for m in self.modalities)

        if has_video and not has_image_or_audio:
            self._show_temp_message_box("Import Mode", "Detected: Video-Only.", QMessageBox.Icon.Information, 1500)
            self._prompt_media_import_options()
        elif has_video and has_image_or_audio:
            self._show_temp_message_box("Import Mode", "Detected: Multi-Modal.", QMessageBox.Icon.Information, 1500)
            self._prompt_multi_modal_directory_import()
        else:
             self._show_temp_message_box("Import Blocked", "Unsupported modalities.", QMessageBox.Icon.Warning, 2500)

    def _prompt_media_import_options(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Video File Import Options")
        msg.setText("How do you want to import video files?")
        
        btn_link = msg.addButton("Link / Reference Only (Recommended)", QMessageBox.ButtonRole.ActionRole)
        btn_copy = msg.addButton("Copy Files (Legacy)", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg.setIcon(QMessageBox.Icon.Question)
        msg.exec()
        
        clicked = msg.clickedButton()
        
        if clicked == btn_link:
            self._import_files_as_virtual_actions(copy_mode=False)
        elif clicked == btn_copy:
            if not self.current_working_directory:
                 self.current_working_directory = QFileDialog.getExistingDirectory(self, "Select Working Directory to Store Copies")
                 if not self.current_working_directory: return
            self._import_files_as_virtual_actions(copy_mode=True)
            
    def _import_files_as_virtual_actions(self, copy_mode=False):
        video_ext_str = ' '.join(ext for ext in SUPPORTED_EXTENSIONS if ext in ('.mp4', '.avi', '.mov')).replace('.', '*')
        video_formats = f"Video Files ({video_ext_str})" 
        
        start_dir = self.current_working_directory if self.current_working_directory else ""
        files, _ = QFileDialog.getOpenFileNames(self, "Select Video Files", start_dir, video_formats)
        if not files: return

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
        
        added_count = 0
        
        for fpath in files:
            action_name = f"{self.SINGLE_VIDEO_PREFIX}{counter:03d}"
            
            if copy_mode:
                virtual_action_path = os.path.join(self.current_working_directory, action_name)
                try:
                    os.makedirs(virtual_action_path, exist_ok=True)
                    shutil.copy2(fpath, os.path.join(virtual_action_path, os.path.basename(fpath)))
                    
                    self.action_item_data.append({'name': action_name, 'path': virtual_action_path})
                    self.action_path_to_name[virtual_action_path] = action_name
                    added_count += 1
                except Exception as e:
                    print(f"Copy failed: {e}")
            else:
                virtual_key = f"VIRTUAL_ID::{action_name}"
                
                self.action_item_data.append({
                    'name': action_name, 
                    'path': virtual_key,
                    'source_files': [fpath] 
                })
                self.action_path_to_name[virtual_key] = action_name
                added_count += 1

            counter += 1

        if added_count > 0:
            self._populate_action_tree()
            self.is_data_dirty = True
            self.update_save_export_button_state()
            mode_text = "Linked" if not copy_mode else "Copied"
            self._show_temp_message_box("Import Complete", f"Successfully {mode_text} {added_count} videos.", QMessageBox.Icon.Information)

    def _prompt_multi_modal_directory_import(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Multi-modal Scene Import")
        msg.setText("How do you want to import the scene folders?")
        
        btn_batch = msg.addButton("Batch Import (Select Root Folder)", QMessageBox.ButtonRole.ActionRole)
        btn_single = msg.addButton("Import Single Scene Folder", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg.setIcon(QMessageBox.Icon.Question)
        msg.exec()
        
        clicked = msg.clickedButton()
        
        if clicked == btn_batch:
            root_dir_path = QFileDialog.getExistingDirectory(self, "Select Root Directory", self.current_working_directory or "")
            if not root_dir_path: return

            dir_paths = [
                os.path.join(root_dir_path, name) 
                for name in os.listdir(root_dir_path)
                if os.path.isdir(os.path.join(root_dir_path, name))
            ]
            if not dir_paths: return
            self._process_multi_modal_directories(dir_paths)
            
        elif clicked == btn_single:
            specific_dir_path = QFileDialog.getExistingDirectory(self, "Select Scene Directory", self.current_working_directory or "")
            if not specific_dir_path: return
            self._process_multi_modal_directories([specific_dir_path])

    def _process_multi_modal_directories(self, dir_paths):
        all_added_actions = []
        total_dirs = len(dir_paths)
        
        progress = QProgressDialog(f"Processing {total_dirs} directories...", "Cancel", 0, total_dirs, self)
        progress.setWindowTitle("Importing")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(0)
        progress.show()

        for i, dir_path in enumerate(dir_paths):
            if progress.wasCanceled(): break
            progress.setLabelText(f"Processing: {os.path.basename(dir_path)}...")
            QApplication.processEvents()

            action_name = os.path.basename(dir_path)
            self.action_item_data.append({'name': action_name, 'path': dir_path})
            self.action_path_to_name[dir_path] = action_name
            all_added_actions.append(True)

            progress.setValue(i + 1)

        progress.close()
        
        if all_added_actions:
            self._populate_action_tree()
            self.is_data_dirty = True
            self.update_save_export_button_state()

    def _populate_action_tree(self):
        self.ui.left_panel.action_tree.clear()
        self.action_item_map.clear()
        
        def sort_key(d):
            try:
                parts = d['name'].split('_')
                if len(parts) > 1 and parts[-1].isdigit():
                    return int(parts[-1])
                return float('inf')
            except:
                return float('inf')

        sorted_list = sorted(self.action_item_data, key=sort_key)

        for data in sorted_list:
            explicit_files = data.get('source_files', None)
            
            action_item = self.ui.left_panel.add_action_item(
                data['name'], 
                data['path'], 
                explicit_files=explicit_files
            )
            self.action_item_map[data['path']] = action_item
            
        for path in self.action_item_map.keys():
            self.update_action_item_status(path)
        self.apply_action_filter()
            
    def _validate_gac_json(self, data):
        if 'modalities' not in data:
            return False, "Missing 'modalities' field."
        if not isinstance(data['modalities'], list):
            return False, "'modalities' must be a list."
        if 'labels' not in data:
            return False, "Missing 'labels' field."
        if not isinstance(data['labels'], dict):
            return False, "'labels' must be a dictionary."
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
            
            inputs = item.get('inputs', [])
            is_virtual = False
            explicit_files = []
            
            for inp in inputs:
                path_str = inp.get('path', '')
                if os.path.isabs(path_str) and os.path.exists(path_str):
                    explicit_files.append(path_str)
                    is_virtual = True
                else:
                    full_path = os.path.join(self.current_working_directory, path_str)
                    if os.path.exists(full_path) and not is_virtual:
                        pass 

            action_key = None
            if is_virtual:
                action_key = f"VIRTUAL_ID::{action_id}"
                self.action_item_data.append({
                    'name': action_id,
                    'path': action_key,
                    'source_files': explicit_files
                })
            else:
                potential_dir = os.path.join(self.current_working_directory, action_id)
                if os.path.isdir(potential_dir):
                    action_key = potential_dir
                    self.action_item_data.append({'name': action_id, 'path': action_key})
                else:
                    action_key = f"VIRTUAL_ID::{action_id}"
                    self.action_item_data.append({'name': action_id, 'path': action_key, 'source_files': []})
            
            self.action_path_to_name[action_key] = action_id
            self.imported_action_metadata[action_key] = item.get('metadata', {})

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
            
            if has_label:
                self.manual_annotations[action_key] = manual_labels
                imported_count += 1
        
        self.current_json_path = file_path
        self._populate_action_tree()
        self.json_loaded = True
        self.is_data_dirty = False 
        self.ui.right_panel.manual_group_box.setEnabled(True)
        self.toggle_annotation_view() 
        self.update_save_export_button_state()
        self._show_temp_message_box("Import Complete", f"Imported {imported_count} annotations.", QMessageBox.Icon.Information, 2000)

    def create_new_project(self):
        if self.is_data_dirty:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes in the current project. Creating a new project will clear them.\nDo you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        dialog = CreateProjectDialog(self)
        if dialog.exec():
            new_project_data = dialog.get_data()
            self.clear_action_list(clear_working_dir=False)
            
            self.current_task_name = new_project_data['task']
            self.modalities = new_project_data['modalities']
            self.label_definitions = new_project_data['labels']
            self.project_description = new_project_data['description']
            
            self.json_loaded = True
            self.current_json_path = None 
            self.is_data_dirty = True 
            
            self._setup_dynamic_ui()
            self.update_save_export_button_state()
            self.toggle_annotation_view()
            
            self._show_temp_message_box(
                "Project Created", 
                f"Project '{self.current_task_name}' created.\nYou can now Add Data.", 
                QMessageBox.Icon.Information, 
                2500
            )

    def clear_action_list(self, clear_working_dir=True):
        self.ui.left_panel.action_tree.clear()
        self.manual_annotations.clear()
        
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._update_undo_redo_buttons()
        
        self.action_item_map.clear()
        self.action_item_data.clear()
        self.action_path_to_name.clear()
        self.modalities.clear() 
        self.imported_action_metadata.clear() 
        self.imported_input_metadata.clear()  
        self.current_json_path = None
        self.json_loaded = False 
        self.is_data_dirty = False 
        self.project_description = "" 
        if clear_working_dir:
            self.current_working_directory = None
        self.update_save_export_button_state()
        self.ui.right_panel.manual_group_box.setEnabled(False) 
        self.current_task_name = RightPanel.DEFAULT_TASK_NAME
        self.label_definitions = self.DEFAULT_LABEL_DEFINITIONS.copy()
        self._setup_dynamic_ui()

    def toggle_annotation_view(self):
        can_annotate = False 
        current_item = self.ui.left_panel.action_tree.currentItem()
        if current_item and current_item.childCount() > 0 and self.json_loaded:
            can_annotate = True
        self.ui.right_panel.manual_group_box.setEnabled(bool(can_annotate))

    def on_item_selected(self, current_item, _):
        if not current_item:
            self.toggle_annotation_view() 
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
        
        cleaned_data = {}
        for k, v in data.items():
            if isinstance(v, list) and v: 
                cleaned_data[k] = v
            elif isinstance(v, str) and v: 
                cleaned_data[k] = v
        
        if not cleaned_data:
            cleaned_data = None

        old_data = None
        if action_path in self.manual_annotations:
            old_data = copy.deepcopy(self.manual_annotations[action_path])
        
        self._push_undo_command(action_path, old_data, cleaned_data)

        if cleaned_data:
            self.manual_annotations[action_path] = cleaned_data
            self.is_data_dirty = True
            self._show_temp_message_box("Success", f"Annotation saved for {action_name}.", QMessageBox.Icon.Information, 1000)
        elif action_path in self.manual_annotations:
            del self.manual_annotations[action_path]
            self.is_data_dirty = True
            self._show_temp_message_box("Success", f"Annotation cleared for {action_name}.", QMessageBox.Icon.Information, 1000)
        else:
            self._show_temp_message_box("No Selection", "Please select at least one label.", QMessageBox.Icon.Warning, 1500)
            
        self.update_save_export_button_state()
        self.update_action_item_status(action_path)

    def clear_current_manual_annotation(self):
        action_path = self._get_current_action_path()
        if not action_path: return
        
        old_data = None
        if action_path in self.manual_annotations:
            old_data = copy.deepcopy(self.manual_annotations[action_path])
            
        if old_data is None:
             self.ui.right_panel.clear_manual_selection()
             return

        self._push_undo_command(action_path, old_data, None)

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

    def update_save_export_button_state(self):
        can_export = self.json_loaded and bool(self.manual_annotations)
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
            "labels": self.label_definitions.copy(),
            "data": []
        }

        path_to_item_map = {}
        root = self.ui.left_panel.action_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            path_to_item_map[item.data(0, Qt.ItemDataRole.UserRole)] = item

        all_keys = set(self.action_path_to_name.keys())
        all_keys.update(self.manual_annotations.keys())
        
        sorted_keys = sorted(list(all_keys), key=lambda p: self.action_path_to_name.get(p, ""))

        for action_key in sorted_keys:
            action_name = self.action_path_to_name.get(action_key)
            if not action_name: continue
                
            manual_result = self.manual_annotations.get(action_key, {})
            stored_metadata = self.imported_action_metadata.get(action_key, {})
            
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
                    if final_label:
                        data_item["labels"][head_name] = {"label": final_label}
                elif definition['type'] == 'multi_label':
                    final_label_list = []
                    if manual_result and manual_result.get(head_name) and isinstance(manual_result.get(head_name), list):
                        final_label_list = manual_result[head_name]
                    data_item["labels"][head_name] = {"labels": final_label_list}

            action_item = path_to_item_map.get(action_key)
            if action_item:
                for j in range(action_item.childCount()):
                    clip_item = action_item.child(j)
                    abs_clip_path = clip_item.data(0, Qt.ItemDataRole.UserRole)
                    clip_name = os.path.basename(abs_clip_path)
                    
                    file_ext = os.path.splitext(clip_name)[1].lower()
                    modality_type = "unknown"
                    if file_ext in ('.mp4', '.avi', '.mov'): modality_type = "video"
                    elif file_ext in ('.jpg', '.jpeg', '.png'): modality_type = "image"
                    elif file_ext in ('.wav', '.mp3'): modality_type = "audio"
                    
                    input_meta = self.imported_input_metadata.get((action_key, clip_name), {})
                    
                    data_item["inputs"].append({
                        "type": modality_type,
                        "path": abs_clip_path, 
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
