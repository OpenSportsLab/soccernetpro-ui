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
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen

from ui_components import MainWindowUI, RightPanel, DynamicSingleLabelGroup, DynamicMultiLabelGroup

# --- Resource Path Helper ---
def resource_path(relative_path):
    """
    Get the absolute path to resource, works for dev and for PyInstaller.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # For development environment (or if not bundled)
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
# --- End Resource Path Helper ---

# --- Size Calculation Helpers ---
def get_dir_size(start_path):
    """Recursively calculates the total size of all video files in a directory (in bytes)."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            if f.lower().endswith(('.mp4', '.avi', '.mov')):
                fp = os.path.join(dirpath, f)
                # Ensure file exists and is not a symbolic link
                if not os.path.islink(fp) and os.path.exists(fp):
                    total_size += os.path.getsize(fp)
    return total_size

def format_size(size_bytes):
    """Converts bytes to a human-readable KB, MB, or GB format."""
    if size_bytes >= 1024**3:
        return f"{size_bytes / 1024**3:.2f} GB"
    elif size_bytes >= 1024**2:
        return f"{size_bytes / 1024**2:.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes} Bytes"
# --- End Size Calculation Helpers ---


# --- Mock AI Model and Sorting Helpers ---
def run_model_on_action(action_clips, label_heads):
    """
    Simulates running an AI model, generating a random probability distribution 
    for each 'single_label' head.
    """
    print(f"Analyzing Action: {os.path.dirname(action_clips[0]) if os.path.isdir(os.path.dirname(action_clips[0])) else os.path.basename(action_clips[0])}...")
    
    results = {}
    
    for head_name, definition in label_heads.items():
        if definition['type'] == 'single_label':
            labels = definition['labels']
            # Ensure at least 2 labels for top 2 prediction visualization
            if len(labels) < 2:
                labels = labels + ['Label B', 'Label C']
            
            label_probs = [random.random() for _ in labels]
            label_sum = sum(label_probs)
            normalized_probs = [p / label_sum for p in label_probs]
            
            results[head_name] = {
                "distribution": dict(zip(labels, normalized_probs))
            }
        # Multi-label prediction simulation is skipped for now
            
    return results

def get_action_number(entry):
    """Tries to parse the numeric part of action_xxx or virtual_action_xxx."""
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
    
    SINGLE_VIDEO_PREFIX = "virtual_action_" 
    
    # Initial dynamic label definitions
    DEFAULT_LABEL_DEFINITIONS = {
        "foul_type": {"type": "single_label", "labels": ["Undefined"]}, 
    }
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"SoccerNet Pro Analysis Tool ({RightPanel.DEFAULT_TASK_NAME} Tool)")
        self.setGeometry(100, 100, 1400, 900)
        
        self.ui = MainWindowUI()
        self.setCentralWidget(self.ui)

        self.analysis_results = {} 
        # Structure: {action_path: {head_name: label_name/label_list, ...}}
        self.manual_annotations = {} 
        
        self.action_path_to_name = {}
        self.action_item_data = [] 
        self.current_working_directory = None
        
        self.label_definitions = self.DEFAULT_LABEL_DEFINITIONS.copy()
        self.current_task_name = RightPanel.DEFAULT_TASK_NAME 
        
        self.action_item_map = {} 
        
        self.current_json_path = None
        self.json_loaded = False 
        
        bright_blue = QColor("#00BFFF") 
        self.done_icon = self._create_checkmark_icon(bright_blue)
        self.empty_icon = QIcon() 
        
        self.connect_signals()
        self.apply_stylesheet()
        
        self.ui.right_panel.annotation_content_widget.setVisible(True) 
        self.ui.left_panel.filter_combo.setCurrentIndex(self.FILTER_ALL) 
        self.ui.right_panel.manual_group_box.setEnabled(False)
        self.ui.right_panel.start_button.setEnabled(False)
        
        self._setup_dynamic_ui()


    # --- Status Indicator Helpers ---
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
        """Connects all UI element signals to the application's logic methods."""
        self.ui.left_panel.clear_button.clicked.connect(self.clear_action_list)
        self.ui.left_panel.import_button.clicked.connect(self.import_annotations) 
        self.ui.left_panel.add_video_button.clicked.connect(self.handle_video_import) 
        
        self.ui.left_panel.action_tree.currentItemChanged.connect(self.on_item_selected)
        self.ui.left_panel.filter_combo.currentIndexChanged.connect(self.apply_action_filter)
        
        self.ui.center_panel.play_button.clicked.connect(self.play_video)
        self.ui.center_panel.multi_view_button.clicked.connect(self.show_all_views)
        
        self.ui.right_panel.start_button.clicked.connect(self.start_analysis)
        self.ui.right_panel.save_button.clicked.connect(self.save_results_to_json)
        self.ui.right_panel.export_button.clicked.connect(self.export_results_to_json)
        self.ui.right_panel.confirm_manual_button.clicked.connect(self.save_manual_annotation)
        self.ui.right_panel.clear_manual_button.clicked.connect(self.clear_current_manual_annotation)
        
        # Dynamic connection for label management buttons handled in _setup_dynamic_ui

    def _connect_dynamic_type_buttons(self):
        """Connects Add/Remove buttons for all dynamically created label groups."""
        for head_name, group in self.ui.right_panel.label_groups.items():
            # Disconnect previous signals to avoid duplicates
            try:
                group.add_btn.clicked.disconnect()
                group.remove_btn.clicked.disconnect()
            except TypeError:
                pass 
            
            group.add_btn.clicked.connect(lambda _, h=head_name: self.add_custom_type(h))
            
            if isinstance(group, DynamicSingleLabelGroup):
                group.remove_btn.clicked.connect(lambda _, h=head_name: self.remove_custom_type(h))
            elif isinstance(group, DynamicMultiLabelGroup):
                # Connect Multi-label 'Remove Checked' button
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
                 self._show_temp_message_box("Warning", f"Cannot remove the last label in {head_name} ({type_to_remove}).", QMessageBox.Icon.Warning, 1500)
                 continue

            # 1. Remove from definition
            self.label_definitions[head_name]['labels'].remove(type_to_remove)
            
            # 2. Remove reference from manual_annotations
            keys_to_delete = []
            for path, anno in self.manual_annotations.items():
                if head_name in anno:
                    anno[head_name] = [label for label in anno[head_name] if label != type_to_remove]
                    if not anno[head_name]:
                        anno[head_name] = None
                
                if not any(v for k, v in anno.items() if k in self.label_definitions and v):
                     keys_to_delete.append(path)

            for path in keys_to_delete:
                del self.manual_annotations[path]
                self.update_action_item_status(path)

            labels_removed += 1
            
        # 3. Update UI
        group.update_checkboxes(self.label_definitions[head_name]['labels'])
        
        current_path = self._get_current_action_path()
        if current_path:
             self.display_manual_annotation(current_path)

        self._show_temp_message_box("Success", f"Successfully removed {labels_removed} label(s) from {head_name}.", QMessageBox.Icon.Information, 1000)
        self.update_save_export_button_state()
            
    def _setup_dynamic_ui(self):
        """Updates the UI based on current label definitions and task name."""
        # 1. Set dynamic labels UI
        self.ui.right_panel.setup_dynamic_labels(self.label_definitions)
        
        # 2. Connect dynamic buttons
        self._connect_dynamic_type_buttons()
        
        # 3. Update Task Label
        self.ui.right_panel.task_label.setText(f"Task: {self.current_task_name}")
        # 4. Update Window Title
        self.setWindowTitle(f"SoccerNet Pro Analysis Tool ({self.current_task_name} Tool)")
        
    def apply_stylesheet(self):
        """Loads the style.qss file, compatible with PyInstaller."""
        try:
            qss_path = resource_path("style.qss")
            with open(qss_path, "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
             print("Warning: style.qss not found. Using default styles.")
        except Exception as e:
             print(f"Error loading stylesheet: {e}") 


    def apply_action_filter(self):
        """Hides or shows action items based on the filter selection."""
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

    def handle_video_import(self):
        """
        Handles video import by asking the user if they want to import a single file 
        or a multi-view directory, and sets up the working directory.
        """
        if not self.json_loaded:
             self._show_temp_message_box("Action Blocked", 
                                        "Please import a GAC JSON file before adding videos.", 
                                        QMessageBox.Icon.Warning, 2000)
             return
             
        # 1. Check or set working directory
        if not self.current_working_directory or not os.path.isdir(self.current_working_directory):
             self.current_working_directory = QFileDialog.getExistingDirectory(self, "Select Working Directory to Store Videos")
             
             if not self.current_working_directory:
                 self._show_temp_message_box("Action Blocked", 
                                            "A working directory is required to store new videos.", 
                                            QMessageBox.Icon.Warning, 2000)
                 return

        # 2. Ask for import type
        msg = QMessageBox(self)
        msg.setWindowTitle("Video Import Type")
        msg.setText("Do you want to import a single video file or all videos from a directory (Multi-view/Clips)?")
        
        btn_file = msg.addButton("Import Single File", QMessageBox.ButtonRole.ActionRole)
        btn_dir = msg.addButton("Import Directory (Multi-view)", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg.setIcon(QMessageBox.Icon.Question)
        msg.exec()
        
        if msg.clickedButton() == btn_file:
            self._import_files_as_virtual_actions(single_action_per_file=True)
        elif msg.clickedButton() == btn_dir:
            self._import_files_as_virtual_actions(single_action_per_file=False)

    def _import_files_as_virtual_actions(self, single_action_per_file):
        """
        Core import logic that copies files and updates the application state.
        Includes mandatory user confirmation and progress bars.
        """
        video_formats = "Video Files (*.mp4 *.avi *.mov)" 
        
        if single_action_per_file:
            # Mode 1: Single File -> Single Virtual Action Folder
            file_paths = []
            original_file_path, _ = QFileDialog.getOpenFileName(self, "Select Single Video File", "", video_formats)
            if original_file_path:
                file_paths.append(original_file_path)
            
            if not file_paths: return

            # --- Pre-calculation & Confirmation ---
            original_file_path = file_paths[0]
            size_bytes = os.path.getsize(original_file_path)
            size_formatted = format_size(size_bytes)
            
            confirm_msg = QMessageBox(self)
            confirm_msg.setWindowTitle("Confirm Video Import")
            confirm_msg.setText(f"You are about to copy one video file ({os.path.basename(original_file_path)}).\n\nEstimated disk usage for copying: {size_formatted}\n\nDo you want to proceed?")
            confirm_msg.setIcon(QMessageBox.Icon.Information)
            confirm_msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
            if confirm_msg.exec() == QMessageBox.StandardButton.Cancel:
                return
            # --- End Confirmation ---

            # Calculate new Action ID
            max_counter = 0
            for name in self.action_path_to_name.values():
                if name.startswith(self.SINGLE_VIDEO_PREFIX):
                    try:
                        parts = name.split('_')
                        if len(parts) > 2 and parts[-1].isdigit():
                            max_counter = max(max_counter, int(parts[-1]))
                    except ValueError:
                        continue
            counter = max_counter + 1
            
            added_count = 0
            original_file_path = file_paths[0]
            
            # Ensure Action folder name is unique
            while True:
                action_name = f"{self.SINGLE_VIDEO_PREFIX}{counter:03d}"
                virtual_action_path = os.path.join(self.current_working_directory, action_name)
                if not os.path.exists(virtual_action_path):
                    break
                counter += 1
            
            video_name = os.path.basename(original_file_path)
            
            # --- Progress Bar for Single File Copy (Simulated) ---
            progress = QProgressDialog(f"Copying {video_name} ({size_formatted})...", "Cancel", 0, 100, self)
            progress.setWindowTitle("Importing Video")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setValue(0)
            progress.show()
            
            try:
                os.makedirs(virtual_action_path)
                target_file_path = os.path.join(virtual_action_path, video_name)
                
                # Simulate progress while copying in the background
                shutil.copy2(original_file_path, target_file_path) # Actual copy
                
                # Update simulated progress bar (for UX after the operation is complete)
                for i in range(1, 101):
                    time.sleep(0.001) 
                    progress.setValue(i)
                    QApplication.processEvents()
                    if progress.wasCanceled():
                        shutil.rmtree(virtual_action_path, ignore_errors=True)
                        return

                self.action_item_data.insert(0, {'name': action_name, 'path': virtual_action_path})
                self.action_path_to_name[virtual_action_path] = action_name
                added_count = 1
                progress.close()

            except Exception as e:
                 progress.close()
                 shutil.rmtree(virtual_action_path, ignore_errors=True)
                 QMessageBox.critical(self, "File Error", f"Failed to copy video or create folder: {e}")
                 return

        else:
            # Mode 2: Single Directory -> Single Virtual Action Folder (Multi-view)
            dir_path = QFileDialog.getExistingDirectory(self, "Select Directory (Containing Multi-view Clips)")
            if not dir_path: return
            
            file_paths = [os.path.join(dir_path, entry.name) for entry in os.scandir(dir_path) 
                          if entry.is_file() and entry.name.lower().endswith(('.mp4', '.avi', '.mov'))]
            
            if not file_paths:
                self._show_temp_message_box("No Videos Found", 
                                            f"No video files found in the selected directory: {dir_path}", 
                                            QMessageBox.Icon.Warning, 2000)
                return
            
            total_files = len(file_paths)
            size_bytes = get_dir_size(dir_path)
            size_formatted = format_size(size_bytes)
            
            # --- Confirmation ---
            confirm_msg = QMessageBox(self)
            confirm_msg.setWindowTitle("Confirm Multi-view Import")
            confirm_msg.setText(f"You are about to copy {total_files} clips into one new Action.\n\nEstimated total disk usage: {size_formatted}\n\nDo you want to proceed?")
            confirm_msg.setIcon(QMessageBox.Icon.Information)
            confirm_msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
            if confirm_msg.exec() == QMessageBox.StandardButton.Cancel:
                return
            # --- End Confirmation ---


            # Calculate new Action ID
            max_counter = 0
            for name in self.action_path_to_name.values():
                if name.startswith(self.SINGLE_VIDEO_PREFIX):
                    try:
                        parts = name.split('_')
                        if len(parts) > 2 and parts[-1].isdigit():
                            max_counter = max(max_counter, int(parts[-1]))
                    except ValueError:
                        continue
            counter = max_counter + 1

            # Create new Action folder name
            action_name = f"{self.SINGLE_VIDEO_PREFIX}{counter:03d}"
            virtual_action_path = os.path.join(self.current_working_directory, action_name)

            # --- Progress Bar for Directory Copy (File Count) ---
            progress = QProgressDialog(f"Copying {total_files} clips ({size_formatted}) to Action '{action_name}'...", "Cancel", 0, total_files, self)
            progress.setWindowTitle("Importing Videos (Multi-view)")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setValue(0)
            progress.show()

            try:
                os.makedirs(virtual_action_path)
                added_count = 0
                for i, original_file_path in enumerate(file_paths):
                    if progress.wasCanceled():
                        shutil.rmtree(virtual_action_path, ignore_errors=True)
                        return
                        
                    video_name = os.path.basename(original_file_path)
                    target_file_path = os.path.join(virtual_action_path, video_name)
                    
                    progress.setLabelText(f"Copying clip {i+1}/{total_files}: {video_name}...")
                    QApplication.processEvents()
                    
                    shutil.copy2(original_file_path, target_file_path)
                    added_count += 1
                    progress.setValue(i + 1)
                    QApplication.processEvents()

                self.action_item_data.insert(0, {'name': action_name, 'path': virtual_action_path})
                self.action_path_to_name[virtual_action_path] = action_name
                progress.close()

            except Exception as e:
                progress.close()
                shutil.rmtree(virtual_action_path, ignore_errors=True)
                QMessageBox.critical(self, "File Error", f"Failed to copy videos or create folder: {e}")
                return

        if added_count > 0:
            self._populate_action_tree()
            
            # Try to select the new Action Item
            new_item_path = os.path.join(self.current_working_directory, action_name)
            new_item = self.action_item_map.get(new_item_path)
            if new_item:
                self.ui.left_panel.action_tree.setCurrentItem(new_item)
                
            self.update_save_export_button_state()
            self._show_temp_message_box("Import Complete", 
                                        f"Successfully added {added_count} clip(s) to Action '{action_name}'.", 
                                        QMessageBox.Icon.Information, 2000)


    def _populate_action_tree(self):
        """Populates the QTreeWidget with preloaded data."""
        if not self.action_item_data:
            self.ui.left_panel.action_tree.clear() 
            self.action_item_map.clear()
            return

        self.ui.left_panel.action_tree.clear()
        self.action_item_map.clear()
        
        # Separate virtual actions and normal actions for ordering
        action_folders = [data for data in self.action_item_data if data['name'].startswith("action_")]
        virtual_actions = [data for data in self.action_item_data if data['name'].startswith(self.SINGLE_VIDEO_PREFIX)]

        # Sort based on numeric part
        sorted_virtual = sorted(virtual_actions, key=lambda d: get_action_number(type('MockEntry', (object,), {'name': d['name']})()))
        sorted_actions = sorted(action_folders, key=lambda d: get_action_number(type('MockEntry', (object,), {'name': d['name']})()))
        
        final_list = sorted_virtual + sorted_actions

        for data in final_list:
            action_item = self.ui.left_panel.add_action_item(data['name'], data['path'])
            self.action_item_map[data['path']] = action_item
            
        # Update status and apply filter
        for path in self.action_item_map.keys():
            self.update_action_item_status(path)
            
        self.apply_action_filter()

    # --- Label Management Logic ---
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
        
        # 1. Add to definition
        self.label_definitions[head_name]['labels'].append(new_type)
        self.label_definitions[head_name]['labels'].sort()
        
        # 2. Update UI
        if isinstance(group, DynamicSingleLabelGroup):
             group.update_radios(self.label_definitions[head_name]['labels'])
        elif isinstance(group, DynamicMultiLabelGroup):
             group.update_checkboxes(self.label_definitions[head_name]['labels'])
        
        self._show_temp_message_box("Success", f"'{new_type}' added to {head_name} types.", QMessageBox.Icon.Information, 1000)
        group.input_field.clear()

    def remove_custom_type(self, head_name):
        # Handles removal for single_label only (via radio button selection)
        group = self.ui.right_panel.label_groups.get(head_name)
        if not group or not isinstance(group, DynamicSingleLabelGroup): 
             return
        
        definition = self.label_definitions[head_name]
        type_set = set(definition['labels'])
        type_to_remove = None

        checked_button = group.button_group.checkedButton()
        if not checked_button:
            self._show_temp_message_box("Warning", "Please select a type to remove first.", QMessageBox.Icon.Warning, 1500)
            return
        type_to_remove = checked_button.text()
        

        if len(definition['labels']) <= 1:
             self._show_temp_message_box("Warning", f"Cannot remove the last label in {head_name}.", QMessageBox.Icon.Warning, 1500)
             return

        # 1. Remove from definition
        if type_to_remove in type_set:
            self.label_definitions[head_name]['labels'].remove(type_to_remove)
            
        # 2. Update UI
        if isinstance(group, DynamicSingleLabelGroup):
            group.update_radios(self.label_definitions[head_name]['labels'])
            
        # 3. Remove reference from manual_annotations
        keys_to_delete = []
        for path, anno in self.manual_annotations.items():
            if definition['type'] == 'single_label' and anno.get(head_name) == type_to_remove:
                anno[head_name] = None
            
            if not any(v for k, v in anno.items() if k in self.label_definitions and v):
                 keys_to_delete.append(path)

        for path in keys_to_delete:
            del self.manual_annotations[path]
            self.update_action_item_status(path)
            
        current_path = self._get_current_action_path()
        if current_path:
             self.display_manual_annotation(current_path)

        self._show_temp_message_box("Success", f"'{type_to_remove}' removed.", QMessageBox.Icon.Information, 1000)
        self.update_save_export_button_state()
            
    # --- File and Data Loading ---
    def import_annotations(self):
        self.clear_action_list(clear_working_dir=False) 
        
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
        
        # 1. Set working directory
        self.current_working_directory = os.path.dirname(file_path)
        
        # 2. Read Task Name
        self.current_task_name = data.get('task', RightPanel.DEFAULT_TASK_NAME)
        
        # 3. Process Dynamic Label Definitions
        self.label_definitions.clear()
        if 'labels' in data and isinstance(data['labels'], dict):
            for head_name, definition in data['labels'].items():
                label_type = definition.get('type')
                if label_type in ['single_label', 'multi_label']:
                    labels = sorted(list(set(definition.get('labels', []))))
                    self.label_definitions[head_name] = {'type': label_type, 'labels': labels}

        if not self.label_definitions:
             QMessageBox.critical(self, "Import Error", "JSON file does not contain any 'single_label' or 'multi_label' definitions in 'labels'.")
             self.clear_action_list()
             return

        # 4. Update UI for new labels and Task Name
        self._setup_dynamic_ui()
        
        # 5. Iterate through JSON data, load Actions and annotations
        for item in data['data']:
            action_id = item.get('id') 
            if not action_id:
                continue
            
            # --- Compatibility Check: Find the corresponding local directory ---
            action_path = None
            
            for input_item in item.get('inputs', []):
                 if input_item.get('type') == 'video' and 'path' in input_item:
                      # Scenario 1: Assume Action ID is a folder name
                      potential_dir_path = os.path.join(self.current_working_directory, action_id)
                      if os.path.isdir(potential_dir_path):
                           action_path = potential_dir_path
                           break
                      
                      # Scenario 2: Assume file is directly in working dir or sub-dir, and action_path is the directory
                      video_file_name = os.path.basename(input_item['path'])
                      potential_clip_path = os.path.join(self.current_working_directory, video_file_name)
                      if os.path.isfile(potential_clip_path):
                           action_path = os.path.dirname(potential_clip_path) # i.e., working directory
                           break
                      
            if not action_path or not os.path.isdir(action_path):
                print(f"Warning: Action directory for ID '{action_id}' not found. Skipping.")
                continue 
            
            action_name = action_id 

            if action_path not in self.action_path_to_name:
                self.action_item_data.append({'name': action_name, 'path': action_path})
                self.action_path_to_name[action_path] = action_name

            # Import Annotations (based on dynamic heads)
            item_labels = item.get('labels', {})
            manual_labels = {}
            has_label = False
            
            for head_name, definition in self.label_definitions.items():
                if head_name in item_labels:
                    label_data = item_labels[head_name]
                    
                    if definition['type'] == 'single_label' and 'label' in label_data:
                        label = label_data['label']
                        if label in definition['labels']:
                            manual_labels[head_name] = label
                            has_label = True
                            
                    elif definition['type'] == 'multi_label' and 'labels' in label_data:
                        # Only import labels present in current definition
                        labels = [l for l in label_data['labels'] if l in definition['labels']]
                        if labels:
                            manual_labels[head_name] = labels
                            has_label = True
            
            if has_label:
                self.manual_annotations[action_path] = manual_labels
                imported_count += 1
        
        self.current_json_path = file_path
        self._populate_action_tree()
        self.json_loaded = True
        
        self.ui.right_panel.manual_group_box.setEnabled(True)
        self.toggle_annotation_view() 
        
        for path in self.action_path_to_name.keys():
            self.update_action_item_status(path) 
        
        self.update_save_export_button_state()
        self._show_temp_message_box("Import Complete", 
                                    f"Successfully imported {imported_count} annotations from JSON.", 
                                    QMessageBox.Icon.Information, 2000)

        current_item = self.ui.left_panel.action_tree.currentItem()
        if current_item:
            self.on_item_selected(current_item, None) 


    def clear_action_list(self, clear_working_dir=True):
        self.ui.left_panel.action_tree.clear()
        self.analysis_results.clear()
        self.manual_annotations.clear()
        self.action_item_map.clear()
        self.action_item_data.clear()
        self.action_path_to_name.clear()
        
        self.current_json_path = None
        self.json_loaded = False 
        if clear_working_dir:
            self.current_working_directory = None
            
        self.update_save_export_button_state()

        self.ui.right_panel.start_button.setEnabled(False)
        self.ui.right_panel.results_widget.setVisible(False)
        self.ui.right_panel.auto_group_box.setChecked(False)
        
        self.ui.right_panel.manual_group_box.setEnabled(False) 
        
        # Reset Task Name, label definitions, and UI
        self.current_task_name = RightPanel.DEFAULT_TASK_NAME
        self.label_definitions = self.DEFAULT_LABEL_DEFINITIONS.copy()
        self._setup_dynamic_ui()


    def toggle_annotation_view(self):
        # Enable/disable based on selected item and JSON load status
        can_annotate_and_analyze = False 
        current_item = self.ui.left_panel.action_tree.currentItem()
            
        if current_item and current_item.childCount() > 0 and self.json_loaded:
            can_annotate_and_analyze = True
        
        self.ui.right_panel.manual_group_box.setEnabled(bool(can_annotate_and_analyze))
        self.ui.right_panel.start_button.setEnabled(bool(can_annotate_and_analyze))


    def on_item_selected(self, current_item, _):
        """
        Triggers when an Action/Clip is selected in the Tree Widget.
        """
        if not current_item:
            self.toggle_annotation_view() 
            self.ui.right_panel.results_widget.setVisible(False)
            self.ui.right_panel.auto_group_box.setChecked(False)
            return
        
        is_action_item = current_item.childCount() > 0 
        self.ui.center_panel.multi_view_button.setEnabled(is_action_item)
        
        if is_action_item:
            # Selected Action folder
            if current_item.childCount() > 0:
                first_clip_path = current_item.child(0).data(0, Qt.ItemDataRole.UserRole)
            else:
                first_clip_path = None
            self.ui.center_panel.show_single_view(first_clip_path)
            action_path = current_item.data(0, Qt.ItemDataRole.UserRole)
        else:
            # Selected Clip
            clip_path = current_item.data(0, Qt.ItemDataRole.UserRole)
            self.ui.center_panel.show_single_view(clip_path)
            action_path = current_item.parent().data(0, Qt.ItemDataRole.UserRole)
            
        self.toggle_annotation_view()
        
        self.display_analysis_results(action_path)
        self.display_manual_annotation(action_path)
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
        if not self.json_loaded:
             self._show_temp_message_box("Action Blocked", 
                                        "Please import a GAC JSON file before starting analysis.", 
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

            result = run_model_on_action(clip_paths, self.label_definitions)
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
        if current_item.childCount() > 0 or current_item.parent() is None:
            return current_item.data(0, Qt.ItemDataRole.UserRole)
        else:
            return current_item.parent().data(0, Qt.ItemDataRole.UserRole)

    def save_manual_annotation(self):
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
        
        # Check if any label or label list is non-empty
        is_annotated = False
        cleaned_data = {}
        for k, v in data.items():
            if isinstance(v, list) and v: # multi_label
                cleaned_data[k] = v
                is_annotated = True
            elif isinstance(v, str) and v: # single_label
                cleaned_data[k] = v
                is_annotated = True
            elif v is not None: 
                pass
        
        if is_annotated:
            self.manual_annotations[action_path] = cleaned_data
            self._show_temp_message_box("Success", 
                                        f"Annotation saved for {action_name}.", 
                                        QMessageBox.Icon.Information, 1500)
        elif action_path in self.manual_annotations:
            del self.manual_annotations[action_path]
            self._show_temp_message_box("Success", 
                                        f"Annotation cleared for {action_name}.", 
                                        QMessageBox.Icon.Information, 1500)
        else:
            self._show_temp_message_box("No Selection", 
                                        "Please select at least one label to save.",
                                        QMessageBox.Icon.Warning, 1500)

        self.update_save_export_button_state()
        self.update_action_item_status(action_path)

    def clear_current_manual_annotation(self):
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
        """Checks if there is any data to export and updates Save and Export button states."""
        can_export = self.json_loaded and (bool(self.analysis_results) or bool(self.manual_annotations))
        self.ui.right_panel.export_button.setEnabled(can_export)
        can_save = can_export and (self.current_json_path is not None)
        self.ui.right_panel.save_button.setEnabled(can_save)

    def save_results_to_json(self):
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
        """Writes all current annotations to the specified file path in GAC JSON format."""
        all_action_paths = set(self.action_path_to_name.keys()) 
        all_action_paths.update(self.analysis_results.keys()) 
        all_action_paths.update(self.manual_annotations.keys()) 
        
        if not all_action_paths:
            self._show_temp_message_box("No Data", "There is no annotation data to save.", QMessageBox.Icon.Warning)
            return

        # Construct base JSON structure
        output_data = {
            "version": "1.0",
            "date": datetime.datetime.now().isoformat().split('T')[0],
            "dataset_name": "Dynamic Action Classification Export",
            "metadata": {
                "created_by": "SoccerNet Pro Analysis Tool"
            },
            "task": self.current_task_name, 
            "labels": self.label_definitions.copy()
        }

        output_data["data"] = []
        path_to_item_map = {}
        root = self.ui.left_panel.action_tree.invisibleRootItem()

        if self.json_loaded:
            for i in range(root.childCount()):
                item = root.child(i)
                path_to_item_map[item.data(0, Qt.ItemDataRole.UserRole)] = item

        for action_path in all_action_paths:
            action_name = self.action_path_to_name.get(action_path)
            if not action_name:
                continue
                
            auto_result = self.analysis_results.get(action_path, {})
            manual_result = self.manual_annotations.get(action_path, {})
            
            if not auto_result and not manual_result:
                continue

            data_item = {
                "id": action_name,
                "metadata": {"AnnotationSource": "None"}, 
                "inputs": [],
                "labels": {}
            }
            
            annotation_source = "None"
            
            # Dynamically fill labels
            for head_name, definition in self.label_definitions.items():
                
                # --- 1. Determine final label value ---
                if definition['type'] == 'single_label':
                    final_label = None
                    # Prioritize manual annotation
                    if manual_result and manual_result.get(head_name) and isinstance(manual_result.get(head_name), str):
                        final_label = manual_result.get(head_name)
                        annotation_source = "Manual"
                    # Fallback to automated top-1 prediction
                    elif auto_result and head_name in auto_result and 'distribution' in auto_result[head_name]:
                        dist = auto_result[head_name]['distribution']
                        predicted_label = max(dist, key=dist.get)
                        if predicted_label in definition['labels']:
                            final_label = predicted_label
                            if annotation_source == "None": annotation_source = "Automated"
                    
                    if final_label:
                        data_item["labels"][head_name] = {"label": final_label}
                        
                elif definition['type'] == 'multi_label':
                    # Multi-label only supports manual export
                    if manual_result and manual_result.get(head_name) and isinstance(manual_result.get(head_name), list):
                        final_label_list = manual_result[head_name]
                        annotation_source = "Manual"
                    else:
                        final_label_list = [] 
                    
                    data_item["labels"][head_name] = {"labels": final_label_list}

            data_item["metadata"]["AnnotationSource"] = annotation_source

            # Fill inputs
            action_item = path_to_item_map.get(action_path)
            if action_item:
                for j in range(action_item.childCount()):
                    clip_item = action_item.child(j)
                    clip_path = clip_item.data(0, Qt.ItemDataRole.UserRole)
                    clip_name_no_ext = os.path.splitext(os.path.basename(clip_path))[0]
                    
                    url_path = f"Dataset/Test/{action_name}/{clip_name_no_ext}" 
                    data_item["inputs"].append({
                        "type": "video",
                        "path": url_path
                    })

            if data_item["labels"]: # Only export if there is at least one label
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


# --- Program Entry Point ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ActionClassifierApp()
    window.show()
    sys.exit(app.exec())
