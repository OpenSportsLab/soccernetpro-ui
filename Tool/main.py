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
from PyQt6.QtCore import Qt, QTimer, QPointF, QSize # Import QSize, Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen

# FIX: Explicitly import necessary components, including the globally defined SUPPORTED_EXTENSIONS 
from ui_components import MainWindowUI, RightPanel, DynamicSingleLabelGroup, DynamicMultiLabelGroup, LeftPanel, SUPPORTED_EXTENSIONS 

# --- NEW: PyInstaller Path Resolver ---
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # For development or when not running as frozen executable
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
# --- END NEW: PyInstaller Path Resolver ---

# --- Helper Function: Get Directory Size ---
def get_dir_size(start_path):
    """Recursively calculates the total size of all supported media files (in bytes)."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            # Use the imported constant
            if f.lower().endswith(SUPPORTED_EXTENSIONS): 
                fp = os.path.join(dirpath, f)
                # Ensure file exists and is not a symbolic link
                if not os.path.islink(fp) and os.path.exists(fp):
                    total_size += os.path.getsize(fp)
    return total_size

def format_size(size_bytes):
    """Converts bytes to human-readable KB, MB, GB format."""
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
    """
    Simulates running the model to generate a random distribution for each label head.
    """
    print(f"Analyzing Action: {os.path.dirname(action_clips[0]) if os.path.isdir(os.path.dirname(action_clips[0])) else os.path.basename(action_clips[0])}...")
    
    results = {}
    
    for head_name, definition in label_heads.items():
        if definition['type'] == 'single_label':
            labels = definition['labels']
            # Ensure at least 2 labels for top 2 prediction simulation
            if len(labels) < 2:
                labels = labels + ['Label B', 'Label C']
            
            label_probs = [random.random() for _ in labels]
            label_sum = sum(label_probs)
            normalized_probs = [p / label_sum for p in label_probs]
            
            results[head_name] = {
                "distribution": dict(zip(labels, normalized_probs))
            }
        # Multi-label analysis is skipped for simulation
            
    return results

def get_action_number(entry):
    try:
        # Try to parse the number after action_ or Annotation_
        parts = entry.name.split('_')
        if len(parts) > 1 and parts[-1].isdigit():
            return int(parts[-1])
        # Compatibility for older virtual_action_xxx
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
    
    # Renamed prefix
    SINGLE_VIDEO_PREFIX = "Annotation_" 
    
    # Initial label definitions
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
        
        # Dynamic label storage
        self.label_definitions = self.DEFAULT_LABEL_DEFINITIONS.copy()
        self.current_task_name = RightPanel.DEFAULT_TASK_NAME 
        
        self.action_item_map = {} 
        
        self.current_json_path = None
        self.json_loaded = False 
        
        # New: Track modalities from loaded JSON
        self.modalities = [] 
        
        # New: Data status tracker
        self.is_data_dirty = False 
        
        # Current style mode tracker
        self.current_style_mode = "Night"
        
        bright_blue = QColor("#00BFFF") 
        self.done_icon = self._create_checkmark_icon(bright_blue)
        self.empty_icon = QIcon() 
        
        self.connect_signals()
        self.apply_stylesheet(self.current_style_mode) # Initial load of Night mode style
        
        self.ui.right_panel.annotation_content_widget.setVisible(True) 
        self.ui.left_panel.filter_combo.setCurrentIndex(self.FILTER_ALL) 
        self.ui.right_panel.manual_group_box.setEnabled(False)
        self.ui.right_panel.start_button.setEnabled(False)
        
        self._setup_dynamic_ui()


    # --- New: Exit Confirmation Mechanism ---
    def closeEvent(self, event):
        """
        Overrides the standard window close event to ask for saving annotations.
        """
        # 检查是否有数据需要导出 (如果 JSON 未加载，也不需要保存)
        can_export = self.json_loaded and (bool(self.manual_annotations) or bool(self.analysis_results))
        
        # 只有在数据已更改 (dirty) 并且存在可导出的数据时，才弹出对话框
        if not self.is_data_dirty or not can_export:
            # 如果数据未更改或无可导出数据，允许直接关闭
            event.accept()
            return

        # English UI: Setup custom buttons for the confirmation dialog
        msg = QMessageBox(self)
        msg.setWindowTitle("Unsaved Annotations")
        msg.setText("Do you want to save your annotations before quitting?")
        msg.setIcon(QMessageBox.Icon.Question)
        
        # Define buttons
        save_btn = msg.addButton("Save & Exit", QMessageBox.ButtonRole.AcceptRole)
        discard_btn = msg.addButton("Discard & Exit", QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg.setDefaultButton(save_btn)
        
        msg.exec()
        
        clicked_button = msg.clickedButton()

        if clicked_button == save_btn:
            # Try to save the results before exiting
            if self._write_gac_json_wrapper():
                event.accept() # Save successful, proceed with exit
            else:
                event.ignore() # Save failed (e.g., user cancelled file dialog), do not exit
        
        elif clicked_button == discard_btn:
            # Proceed with exit without saving
            event.accept()
        
        elif clicked_button == cancel_btn:
            # Ignore the close event, stay in the application
            event.ignore()

        else:
            # Default fallback (shouldn't be reached if only custom buttons are used)
            event.ignore()

    def _write_gac_json_wrapper(self):
        """
        Wraps save/export logic for use in closeEvent. Returns True on successful write, False otherwise.
        """
        if not self.json_loaded:
            # If no JSON was loaded, prompt Save As
            path, _ = QFileDialog.getSaveFileName(self, "Save GAC JSON Annotation As...", "", "JSON Files (*.json)")
            if not path:
                return False # User cancelled Save As dialog
            try:
                self._write_gac_json(path)
                return True
            except Exception:
                return False
        else:
            # Save to the current loaded path
            try:
                self._write_gac_json(self.current_json_path)
                return True
            except Exception:
                return False

    # --- Status Indicator Helper Method ---
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
        # Annotation completion logic remains
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
        # Renamed button, connects to the new dynamic entry point
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
        
        # Connect dynamic label head management signal (NEW)
        self.ui.right_panel.add_head_clicked.connect(self._handle_add_label_head)
        self.ui.right_panel.remove_head_clicked.connect(self._handle_remove_label_head) # NEW REMOVE SIGNAL

        # Connect style toggle signal
        self.ui.right_panel.style_mode_changed.connect(self.change_style_mode)


    # --- New Feature: Add/Remove Label Head ---
    def _handle_add_label_head(self, head_name):
        """Handles adding a new top-level label category (Label Head)."""
        clean_name = head_name.strip().replace(' ', '_').lower()

        if not clean_name:
            self._show_temp_message_box("Warning", "Category name cannot be empty.", QMessageBox.Icon.Warning, 1500)
            return
            
        if clean_name in self.label_definitions:
            self._show_temp_message_box("Warning", f"Category '{head_name}' already exists.", QMessageBox.Icon.Warning, 1500)
            return

        # Initialize the new label head as a single_label type with one default option.
        new_head_definition = {
            "type": "single_label", 
            "labels": [] # Provide a default label
        }
        
        # Add the new head to the END of the dictionary.
        self.label_definitions[clean_name] = new_head_definition
        
        # Clear the input field in the UI
        self.ui.right_panel.new_head_input.clear()
        
        # Rebuild the dynamic UI to include the new head
        self._setup_dynamic_ui()
        
        self._show_temp_message_box("Success", 
                                    f"New category '{head_name}' added. You can now add specific labels to it.", 
                                    QMessageBox.Icon.Information, 2500)
        
        # Mark data as modified
        self.is_data_dirty = True
        self.update_save_export_button_state()

    def _handle_remove_label_head(self, head_name):
        """Handles removing an existing top-level label category (Label Head)."""
        clean_name = head_name.strip().replace(' ', '_').lower()

        if clean_name not in self.label_definitions:
            self._show_temp_message_box("Warning", f"Category '{head_name}' not found.", QMessageBox.Icon.Warning, 1500)
            # Reset combo box selection
            self.ui.right_panel.remove_head_combo.setCurrentIndex(0)
            return
            
        # Check if it was one of the default imported labels
        if clean_name in self.DEFAULT_LABEL_DEFINITIONS:
            self._show_temp_message_box("Warning", 
                                        f"Cannot remove default imported category '{head_name}'.", 
                                        QMessageBox.Icon.Warning, 2500)
            # Reset combo box selection
            self.ui.right_panel.remove_head_combo.setCurrentIndex(0)
            return

        # Confirmation dialog (English UI)
        reply = QMessageBox.question(self, 'Confirm Removal',
            f"Are you sure you want to remove the category '{head_name}'? "
            "This will delete ALL corresponding annotations across ALL scenes.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.No:
            # Reset combo box selection if cancelled
            self.ui.right_panel.remove_head_combo.setCurrentIndex(0)
            return

        try:
            # 1. Remove from label definitions
            del self.label_definitions[clean_name]

            # 2. Clean up manual annotations across all scenes
            paths_to_update = set()
            keys_to_delete = []
            
            for path, anno in list(self.manual_annotations.items()):
                if clean_name in anno:
                    del anno[clean_name]
                    paths_to_update.add(path)
                
                # Check if the annotation entry is now completely empty
                if not any(v for k, v in anno.items() if k in self.label_definitions and v):
                    keys_to_delete.append(path)

            for path in keys_to_delete:
                del self.manual_annotations[path]
                paths_to_update.add(path)

            # 3. Clean up analysis results
            for path, result in list(self.analysis_results.items()):
                if clean_name in result:
                    del result[clean_name]
                    paths_to_update.add(path)

            # 4. Update status icons for affected scenes
            for path in paths_to_update:
                self.update_action_item_status(path)

            # 5. Clear the input and rebuild the UI
            self.ui.right_panel.new_head_input.clear()
            self._setup_dynamic_ui() # This updates the remove_head_combo automatically
            
            # 6. Refresh current scene annotation if needed
            current_path = self._get_current_action_path()
            if current_path:
                 self.display_manual_annotation(current_path)

            self._show_temp_message_box("Success", 
                                        f"Category '{head_name}' and related annotations successfully removed.", 
                                        QMessageBox.Icon.Information, 2500)
            
            # Mark data as modified
            self.is_data_dirty = True
            self.update_save_export_button_state()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred during removal: {e}")
    # --- End New Feature ---
    
    def _connect_dynamic_type_buttons(self):
        """Connects Add/Remove buttons in all dynamically created DynamicLabelGroup widgets."""
        for head_name, group in self.ui.right_panel.label_groups.items():
            # Disconnect old connections to prevent duplication
            try:
                group.add_btn.clicked.disconnect()
                group.remove_btn.clicked.disconnect()
            except TypeError:
                pass 
            
            group.add_btn.clicked.connect(lambda _, h=head_name: self.add_custom_type(h))
            
            if isinstance(group, DynamicSingleLabelGroup):
                # Connect the remove button to the new logic using the combo box selection
                group.remove_btn.clicked.connect(lambda _, h=head_name: self.remove_custom_type(h))
            elif isinstance(group, DynamicMultiLabelGroup):
                # Connect 'Remove Checked' button for multi-label group
                group.remove_btn.clicked.connect(lambda _, h=head_name: self._remove_multi_labels_via_checkboxes(h))
                
    def _remove_multi_labels_via_checkboxes(self, head_name):
        group = self.ui.right_panel.label_groups.get(head_name)
        if not group or not isinstance(group, DynamicMultiLabelGroup): return

        labels_to_remove = group.get_checked_labels()
        
        if not labels_to_remove:
            # English UI
            self._show_temp_message_box("Warning", "Please check one or more labels to remove.", QMessageBox.Icon.Warning, 1500)
            return
            
        labels_removed = 0
        
        for type_to_remove in labels_to_remove:
            definition = self.label_definitions[head_name]
            
            # Check if it's the last label
            if len(definition['labels']) <= 1:
                 # English UI
                 self._show_temp_message_box("Warning", f"Cannot remove the last label in {head_name}.", QMessageBox.Icon.Warning, 1500)
                 continue

            # 1. Remove from definition
            self.label_definitions[head_name]['labels'].remove(type_to_remove)
            
            # 2. Remove reference from manual_annotations
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
            
        # 3. Update UI
        group.update_checkboxes(self.label_definitions[head_name]['labels'])
        
        current_path = self._get_current_action_path()
        if current_path:
             self.display_manual_annotation(current_path)

        if labels_removed > 0:
            # Mark data as modified
            self.is_data_dirty = True
        
        # English UI
        self._show_temp_message_box("Success", f"Successfully removed {labels_removed} label(s) from {head_name}.", QMessageBox.Icon.Information, 1000)
        self.update_save_export_button_state()
            
    def _setup_dynamic_ui(self):
        """Updates the UI based on current self.label_definitions."""
        # 1. Setup dynamic labels UI
        self.ui.right_panel.setup_dynamic_labels(self.label_definitions)
        
        # 2. Connect dynamic buttons
        self._connect_dynamic_type_buttons()
        
        # 3. Update Task Label
        self.ui.right_panel.task_label.setText(f"Task: {self.current_task_name}")
        # 4. Update Window Title
        self.setWindowTitle(f"SoccerNet Pro Analysis Tool ({self.current_task_name} Tool)")
        
    def apply_stylesheet(self, mode="Night"):
        """
        Loads style.qss or style_day.qss file.
        """
        qss_path_name = "style.qss" if mode == "Night" else "style_day.qss"
        
        # --- MODIFIED LINE ---
        qss_path = resource_path(qss_path_name) 
        # ---------------------
        
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
            self.current_style_mode = mode
            print(f"Applied style: {mode}")
        except FileNotFoundError:
             print(f"Warning: {qss_path_name} not found. Using default styles.")
        except Exception as e:
             print(f"Error loading stylesheet: {e}")

    def change_style_mode(self, mode):
        """Receives signal to apply new style mode."""
        self.apply_stylesheet(mode)
        

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

    # --- Data Import Logic ---

    def _dynamic_data_import(self):
        """
        New entry point for data import. 
        Automatically selects the import mode based on the loaded JSON's modalities.
        """
        if not self.json_loaded:
             # English UI
             self._show_temp_message_box("Action Blocked", 
                                        "Please import a GAC JSON file before adding data.", 
                                        QMessageBox.Icon.Warning, 2000)
             return
             
        # 1. Check or set working directory
        if not self.current_working_directory or not os.path.isdir(self.current_working_directory):
             # English UI
             self.current_working_directory = QFileDialog.getExistingDirectory(self, "Select Working Directory to Store New Data")
             
             if not self.current_working_directory:
                 # English UI
                 self._show_temp_message_box("Action Blocked", 
                                            "A working directory is required to store new data.", 
                                            QMessageBox.Icon.Warning, 2000)
                 return
                 
        # --- Modality-based Import Mode Selection ---
        has_video = 'video' in self.modalities
        has_image_or_audio = any(m in ['image', 'audio'] for m in self.modalities)

        if has_video and not has_image_or_audio:
            # Mode 1: Video-only -> Batch Import Single Video Files
            # English UI
            self._show_temp_message_box("Import Mode", 
                                        "Detected: Video-Only. Proceeding to Batch Import Single Video Files.", 
                                        QMessageBox.Icon.Information, 1500)
            self._prompt_media_import_options()
        elif has_video and has_image_or_audio:
            # Mode 2: Multi-modal -> Batch Import Directories
            # English UI
            self._show_temp_message_box("Import Mode", 
                                        "Detected: Multi-Modal. Proceeding to Batch Import Directories.", 
                                        QMessageBox.Icon.Information, 1500)
            self._prompt_multi_modal_directory_import()
        else:
             # English UI
             self._show_temp_message_box("Import Blocked", 
                                        "Unsupported modalities in JSON (Requires 'video' or 'video' + 'image'/'audio').", 
                                        QMessageBox.Icon.Warning, 2500)
             
    def handle_data_import(self):
         # Alias for backward compatibility with connect_signals
         self._dynamic_data_import() 

    def _prompt_media_import_options(self):
        """
        Provides options for Mode 1 (Video-Only): single file or multiple files.
        """
        msg = QMessageBox(self)
        # English UI + Renamed prefix
        msg.setWindowTitle("Single Video File Import (Mode 1)")
        msg.setText(f"How do you want to import video files?\n(Each file will be copied to a new '{self.SINGLE_VIDEO_PREFIX}XXX' folder)")
        
        # English UI
        btn_multi_files = msg.addButton("Import Multiple Files (Batch)", QMessageBox.ButtonRole.ActionRole)
        btn_single_file = msg.addButton("Import Single File", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg.setIcon(QMessageBox.Icon.Question)
        msg.exec()
        
        # --- Logic switch based on the order defined above ---
        if msg.clickedButton() == btn_multi_files:
            # Mode 1 (Batch) - First button
            self._import_files_as_virtual_actions(batch_mode=True)
        elif msg.clickedButton() == btn_single_file:
            # Mode 1 (Single) - Second button
            self._import_files_as_virtual_actions(batch_mode=False)
            
    def _import_files_as_virtual_actions(self, batch_mode=True):
        """
        Implements Mode 1: Imports one or more media files (video only in this mode), 
        creating a new Annotation_XXX action for each.
        """
        # We only allow video files in this mode based on the dynamic check in _dynamic_data_import
        video_ext_str = ' '.join(ext for ext in SUPPORTED_EXTENSIONS if ext in ('.mp4', '.avi', '.mov')).replace('.', '*')
        video_formats = f"Video Files ({video_ext_str})" 
        
        if batch_mode:
            # English UI
            original_file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Multiple Video Files", self.current_working_directory, video_formats)
        else:
            # English UI
            original_file_path, _ = QFileDialog.getOpenFileName(self, "Select Single Video File", self.current_working_directory, video_formats)
            original_file_paths = [original_file_path] if original_file_path else []

        if not original_file_paths:
            return

        total_files = len(original_file_paths)
        total_size_bytes = sum(os.path.getsize(f) for f in original_file_paths if os.path.exists(f))
        size_formatted = format_size(total_size_bytes)
        
        # --- Confirmation Dialog (English UI + Renamed prefix) ---
        confirm_msg = QMessageBox(self)
        confirm_msg.setWindowTitle(f"Confirm Batch Video Import (Mode 1)")
        confirm_msg.setText(f"You are about to import {total_files} video file(s).\n"
                            f"Each file will be copied into a new '{self.SINGLE_VIDEO_PREFIX}XXX' folder.\n\n"
                            f"Estimated total disk usage for copying: {size_formatted}\n\n"
                            f"Do you want to proceed?")
        confirm_msg.setIcon(QMessageBox.Icon.Information)
        confirm_msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        if confirm_msg.exec() == QMessageBox.StandardButton.Cancel:
            return
        # --- END Confirmation Dialog ---

        # --- Progress Bar (English UI) ---
        progress = QProgressDialog(f"Importing {total_files} video files...", "Cancel", 0, total_files, self)
        progress.setWindowTitle("Importing Media (Mode 1)")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(0)
        progress.show()

        # Calculate starting Action ID
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
            # English UI
            progress.setLabelText(f"Importing {i+1}/{total_files}: {media_name}...")
            QApplication.processEvents()

            # Renamed prefix
            # Ensure Action folder name is unique
            action_name = f"{self.SINGLE_VIDEO_PREFIX}{counter:03d}"
            virtual_action_path = os.path.join(self.current_working_directory, action_name)
            while os.path.exists(virtual_action_path):
                counter += 1
                action_name = f"{self.SINGLE_VIDEO_PREFIX}{counter:03d}"
                virtual_action_path = os.path.join(self.current_working_directory, action_name)
            
            try:
                os.makedirs(virtual_action_path)
                target_file_path = os.path.join(virtual_action_path, media_name)
                
                shutil.copy2(original_file_path, target_file_path) # Actual copy operation
                
                self.action_item_data.insert(0, {'name': action_name, 'path': virtual_action_path})
                self.action_path_to_name[virtual_action_path] = action_name
                added_actions.append({'name': action_name, 'path': virtual_action_path})
                counter += 1

            except Exception as e:
                 shutil.rmtree(virtual_action_path, ignore_errors=True)
                 # English UI
                 QMessageBox.critical(self, "File Error", f"Failed to copy file or create folder for {media_name}: {e}")
                 
            progress.setValue(i + 1)
            QApplication.processEvents()

        progress.close()
        
        if added_actions:
            self._populate_action_tree()
            
            # Try to select the last imported item
            last_item_path = added_actions[-1]['path']
            last_item = self.action_item_map.get(last_item_path)
            if last_item:
                self.ui.left_panel.action_tree.setCurrentItem(last_item)
            
            # Mark data as modified
            self.is_data_dirty = True
            self.update_save_export_button_state()
            # English UI
            self._show_temp_message_box("Import Complete", 
                                        f"Successfully imported {len(added_actions)} files as new actions.", 
                                        QMessageBox.Icon.Information, 2000)

    def _prompt_multi_modal_directory_import(self):
        """
        Implements the UI for selecting multiple multi-modal directories 
        by having the user select a parent root directory (Fixes AttributeError).
        """
        # 1. Use QFileDialog.getExistingDirectory (singular)
        # English UI: Select the root folder containing all action sub-directories
        root_dir_path = QFileDialog.getExistingDirectory(
            self, 
            "Select Root Directory Containing All Multi-view Scenes",
            self.current_working_directory
        )
        if not root_dir_path: return

        # 2. Get all immediate subdirectories within the selected root path
        dir_paths = [
            os.path.join(root_dir_path, name) 
            for name in os.listdir(root_dir_path)
            if os.path.isdir(os.path.join(root_dir_path, name))
        ]

        if not dir_paths:
            self._show_temp_message_box("Import Warning", 
                                        f"No subdirectories found in the selected root path: {root_dir_path}", 
                                        QMessageBox.Icon.Warning, 2500)
            return

        # 3. Start processing each directory
        all_added_actions = []
        total_dirs = len(dir_paths)
        
        # --- Progress Bar for overall process (English UI) ---
        progress = QProgressDialog(f"Processing {total_dirs} directories...", "Cancel", 0, total_dirs, self)
        progress.setWindowTitle("Importing Multi-modal Scenes (Mode 2)")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setValue(0)
        progress.show()

        for i, dir_path in enumerate(dir_paths):
            if progress.wasCanceled():
                break
            
            progress.setLabelText(f"Processing Directory {i+1}/{total_dirs}: {os.path.basename(dir_path)}...")
            QApplication.processEvents()

            # Check if directory contains supported media before trying to copy
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
            # === CRUCIAL FIX: Add collected data to the main application list ===
            self.action_item_data.extend(all_added_actions) 
            # ===================================================================
            self._populate_action_tree()

            # Try to select the last imported item
            last_item_path = all_added_actions[-1]['path']
            last_item = self.action_item_map.get(last_item_path)
            if last_item:
                self.ui.left_panel.action_tree.setCurrentItem(last_item)

            # Mark data as modified
            self.is_data_dirty = True
            self.update_save_export_button_state()
            # English UI
            self._show_temp_message_box("Import Complete", 
                                        f"Successfully imported {len(all_added_actions)} multi-modal scenes.", 
                                        QMessageBox.Icon.Information, 2000)

    def _import_single_directory_as_action(self, dir_path):
        """
        Core logic for Mode 2: Copies a single directory's content into a new Annotation_XXX folder.
        Returns {'name': action_name, 'path': virtual_action_path} or None on failure/skip.
        """
        
        file_paths = [os.path.join(dir_path, entry.name) for entry in os.scandir(dir_path) 
                      if entry.is_file() and entry.name.lower().endswith(SUPPORTED_EXTENSIONS)]
        
        if not file_paths:
            return None
        
        # Calculate new Action ID counter
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

        # Use Annotation_XXX prefix for the action name (Requirement 2)
        action_name = f"{self.SINGLE_VIDEO_PREFIX}{counter:03d}"
        virtual_action_path = os.path.join(self.current_working_directory, action_name)
        
        # Ensure final destination folder name is unique
        while os.path.exists(virtual_action_path):
             counter += 1
             action_name = f"{self.SINGLE_VIDEO_PREFIX}{counter:03d}"
             virtual_action_path = os.path.join(self.current_working_directory, action_name)

        try:
            os.makedirs(virtual_action_path)
            added_count = 0
            
            # Simple file copy loop
            for original_file_path in file_paths:
                media_name = os.path.basename(original_file_path)
                target_file_path = os.path.join(virtual_action_path, media_name)
                shutil.copy2(original_file_path, target_file_path)
                added_count += 1
            
            if added_count > 0:
                # Add data to global map for lookup/tracking, but main list is updated in batch
                self.action_path_to_name[virtual_action_path] = action_name
                return {'name': action_name, 'path': virtual_action_path}
            else:
                shutil.rmtree(virtual_action_path, ignore_errors=True)
                return None

        except Exception as e:
            shutil.rmtree(virtual_action_path, ignore_errors=True)
            # English UI
            QMessageBox.critical(self, "File Error (Mode 2)", f"Failed to copy files or create folder for {os.path.basename(dir_path)}: {e}")
            return None
            
    def _import_directory_as_single_action(self):
        """
        Kept for dynamic import entry point, redirects to batch selector.
        """
        self._prompt_multi_modal_directory_import()


    def _populate_action_tree(self):
        """Populates the QTreeWidget with pre-loaded data."""
        if not self.action_item_data:
            self.ui.left_panel.action_tree.clear() # Ensure clear
            self.action_item_map.clear()
            return

        self.ui.left_panel.action_tree.clear()
        self.action_item_map.clear()
        
        # Sorting Logic:
        action_folders = []
        virtual_actions = [] # Annotation_XXX
        # other_folders removed, now everything is categorized as action_folders or virtual_actions

        for data in self.action_item_data:
            name = data['name']
            if name.startswith("action_"):
                action_folders.append(data)
            elif name.startswith(self.SINGLE_VIDEO_PREFIX):
                virtual_actions.append(data)
            else:
                # If it doesn't match predefined prefixes, treat it as a standard action folder (though ideally, it should have a prefix)
                action_folders.append(data) 

        # Sort lists:
        sorted_virtual = sorted(virtual_actions, key=lambda d: get_action_number(type('MockEntry', (object,), {'name': d['name']})()))
        sorted_actions = sorted(action_folders, key=lambda d: get_action_number(type('MockEntry', (object,), {'name': d['name']})()))
        
        # Final list order: IMPORT01 + JSON/Directory Actions
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
            # English UI
            self._show_temp_message_box("Warning", "Type name cannot be empty.", QMessageBox.Icon.Warning, 1500)
            return
            
        type_set = set(self.label_definitions[head_name]['labels'])
        
        if new_type in type_set:
            # English UI
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
        
        # Mark data as modified
        self.is_data_dirty = True

        # English UI
        self._show_temp_message_box("Success", f"'{new_type}' added to {head_name} types.", QMessageBox.Icon.Information, 1000)
        group.input_field.clear()
        self.update_save_export_button_state()

    def remove_custom_type(self, head_name):
        # Only handles single_label removal (via the new combo box)
        group = self.ui.right_panel.label_groups.get(head_name)
        if not group or not isinstance(group, DynamicSingleLabelGroup): 
             return
        
        definition = self.label_definitions[head_name]
        type_set = set(definition['labels'])
        
        # Use the selection from the combo box
        type_to_remove = group.get_selected_label_to_remove()

        if not type_to_remove:
            # English UI
            self._show_temp_message_box("Warning", "Please select a label to remove from the dropdown.", QMessageBox.Icon.Warning, 1500)
            return
        
        # Check if it's the last label
        if len(definition['labels']) <= 1:
             # English UI
             self._show_temp_message_box("Warning", f"Cannot remove the last label in {head_name}.", QMessageBox.Icon.Warning, 1500)
             # Reset combo box selection
             group.remove_combo.setCurrentIndex(0)
             return

        # 1. Remove from definition
        if type_to_remove in type_set:
            self.label_definitions[head_name]['labels'].remove(type_to_remove)
            
        # 2. Update UI
        if isinstance(group, DynamicSingleLabelGroup):
            group.update_radios(self.label_definitions[head_name]['labels'])
            
        # 3. Remove reference from manual_annotations
        paths_to_update = set()
        keys_to_delete = []
        for path, anno in self.manual_annotations.items():
            if definition['type'] == 'single_label' and anno.get(head_name) == type_to_remove:
                anno[head_name] = None
                paths_to_update.add(path)
            
            # Check if all labels for the Action are now empty
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

        # Mark data as modified
        self.is_data_dirty = True
        
        # English UI
        self._show_temp_message_box("Success", f"'{type_to_remove}' removed.", QMessageBox.Icon.Information, 1000)
        self.update_save_export_button_state()
            
    # --- File and Data Loading ---

    def _validate_gac_json(self, data):
        """
        Validates the structure and types of the loaded GAC JSON data.
        Returns (True, None) on success, or (False, error_message) on failure.
        """
        # 1. 检查 modalities 字段
        if 'modalities' not in data:
            return False, "JSON file is missing the required 'modalities' field."
        if not isinstance(data['modalities'], list):
            return False, "The 'modalities' field must be a list (array)."
        
        # 2. 检查 labels 字段
        if 'labels' not in data:
            return False, "JSON file is missing the required 'labels' field."
        if not isinstance(data['labels'], dict):
            return False, "The 'labels' field must be a dictionary (object)."
        
        # 3. 检查 labels 结构完整性
        for head_name, definition in data['labels'].items():
            if not isinstance(definition, dict):
                 return False, f"Label head '{head_name}' must be an object (dictionary)."
                 
            label_type = definition.get('type')
            if label_type not in ['single_label', 'multi_label']:
                return False, f"Label head '{head_name}' is missing a valid 'type' field ('single_label' or 'multi_label')."
            
            labels_list = definition.get('labels')
            if not isinstance(labels_list, list):
                return False, f"Label head '{head_name}' is missing the required 'labels' list or it is not a list."

        # 4. 检查 data 字段 (可选，但建议)
        if 'data' not in data or not isinstance(data['data'], list):
            return False, "JSON file does not contain a 'data' key, or 'data' is not a list."

        return True, None


    def import_annotations(self):
        # 清理旧数据，但保留 working_dir 设置
        self.clear_action_list(clear_working_dir=False) 
        
        # English UI
        file_path, _ = QFileDialog.getOpenFileName(self, "Select GAC JSON Annotation File", "", "JSON Files (*.json)")
        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            # English UI
            QMessageBox.critical(self, "Import Error", f"Failed to read or parse JSON file: {e}")
            return
        
        # --- NEW: Validate JSON Structure ---
        is_valid, error_msg = self._validate_gac_json(data)
        if not is_valid:
            QMessageBox.critical(self, "JSON Format Error", f"The imported JSON file format is invalid.\nDetails: {error_msg}")
            self.clear_action_list() # 清理并回到初始状态
            return
        # --- END NEW VALIDATION ---

        
        imported_count = 0
        
        # New: Read Modalities
        self.modalities = data.get('modalities', [])
             
        # 1. Set working directory
        self.current_working_directory = os.path.dirname(file_path)
        
        # 2. Read Task Name
        self.current_task_name = data.get('task', RightPanel.DEFAULT_TASK_NAME)
        
        # 3. Process Dynamic Label Definitions
        self.label_definitions.clear()
        if 'labels' in data and isinstance(data['labels'], dict):
            # Use original loaded labels only
            for head_name, definition in data['labels'].items():
                # Since validation passed, we only need to extract and sort labels
                label_type = definition.get('type')
                if label_type in ['single_label', 'multi_label']:
                    labels = sorted(list(set(definition.get('labels', []))))
                    self.label_definitions[head_name] = {'type': label_type, 'labels': labels}

        # 4. Update UI
        self._setup_dynamic_ui()
        
        # 5. Iterate through JSON data
        for item in data['data']:
            action_id = item.get('id') 
            if not action_id:
                continue
            
            action_path = None
            
            # Check for media inputs to determine the Action directory
            for input_item in item.get('inputs', []):
                 if input_item.get('type') in ['video', 'image', 'audio'] and 'path' in input_item:
                      # Option 1: Assume Action ID is a folder name
                      potential_dir_path = os.path.join(self.current_working_directory, action_id)
                      if os.path.isdir(potential_dir_path):
                           action_path = potential_dir_path
                           break
                      
                      # Option 2: Legacy single-file structure (discouraged but supported)
                      media_file_name = os.path.basename(input_item['path'])
                      potential_clip_path = os.path.join(self.current_working_directory, media_file_name)
                      if os.path.isfile(potential_clip_path):
                           action_path = os.path.dirname(potential_clip_path) # i.e., working directory
                           break
                      # Option 3: Compatible single-file structure (e.g., Annot_001/clip.mp4)
                      elif os.path.isdir(os.path.join(self.current_working_directory, action_id)):
                           action_path = os.path.join(self.current_working_directory, action_id)
                           break
            
            if not action_path or not os.path.isdir(action_path):
                print(f"Warning: Action directory for ID '{action_id}' not found. Skipping.")
                continue 
            
            action_name = action_id 

            if action_path not in self.action_path_to_name:
                self.action_item_data.append({'name': action_name, 'path': action_path})
                self.action_path_to_name[action_path] = action_name

            # Import Annotations (based on dynamic label heads)
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
        
        # 重置脏数据状态：导入新文件后，当前数据是干净的
        self.is_data_dirty = False 
        
        self.ui.right_panel.manual_group_box.setEnabled(True)
        self.toggle_annotation_view() 
        
        for path in self.action_path_to_name.keys():
            self.update_action_item_status(path) 
        
        self.update_save_export_button_state()
        # English UI
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
        self.modalities.clear() # Clear modalities
        
        self.current_json_path = None
        self.json_loaded = False 
        
        # 清理数据后，数据状态恢复干净（如果文件已加载，此时也相当于已丢弃）
        self.is_data_dirty = False 

        if clear_working_dir:
            self.current_working_directory = None
            
        self.update_save_export_button_state()

        self.ui.right_panel.start_button.setEnabled(False)
        self.ui.right_panel.progress_bar.setVisible(False)
        self.ui.right_panel.results_widget.setVisible(False)
        self.ui.right_panel.auto_group_box.setChecked(False)
        
        self.ui.right_panel.manual_group_box.setEnabled(False) 
        
        # Reset Task Name, label definitions, and UI
        self.current_task_name = RightPanel.DEFAULT_TASK_NAME
        self.label_definitions = self.DEFAULT_LABEL_DEFINITIONS.copy()
        self._setup_dynamic_ui()


    def toggle_annotation_view(self):
        # Enables/disables annotation based on selected item and JSON load status
        can_annotate_and_analyze = False 
        current_item = self.ui.left_panel.action_tree.currentItem()
        
        # Enable if it's an Action folder (childCount > 0) AND JSON is loaded
        if current_item and current_item.childCount() > 0 and self.json_loaded:
            can_annotate_and_analyze = True
        
        self.ui.right_panel.manual_group_box.setEnabled(bool(can_annotate_and_analyze))
        self.ui.right_panel.start_button.setEnabled(bool(can_annotate_and_analyze))


    def on_item_selected(self, current_item, _):
        """
        Triggered when a user selects an Action/Clip in the Left Tree Widget.
        """
        if not current_item:
            self.toggle_annotation_view() 
            self.ui.right_panel.results_widget.setVisible(False)
            self.ui.right_panel.auto_group_box.setChecked(False)
            return
        
        # Determine if selected item is an Action folder (top level) or a media file (child)
        is_action_item = (current_item.childCount() > 0) or (current_item.parent() is None) 
        
        action_path = None
        
        if is_action_item:
            # Selected Action folder
            action_path = current_item.data(0, Qt.ItemDataRole.UserRole)
            first_media_path = None
            if current_item.childCount() > 0:
                # Preview the first child item (video, image, or audio)
                first_media_path = current_item.child(0).data(0, Qt.ItemDataRole.UserRole)
            
            self.ui.center_panel.show_single_view(first_media_path)
            self.ui.center_panel.multi_view_button.setEnabled(True) 

        else:
            # Selected media file (Clip)
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
            
        # Ensure we operate on the top-level Action
        if current_item.parent() is not None:
             current_item = current_item.parent()
            
        action_path = current_item.data(0, Qt.ItemDataRole.UserRole)
        
        if current_item.childCount() > 0:
            # Only include supported video files
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
             # English UI
             self._show_temp_message_box("Action Blocked", 
                                        "Please import a GAC JSON file before starting analysis.", 
                                        QMessageBox.Icon.Warning, 2000)
             return
             
        current_item = self.ui.left_panel.action_tree.currentItem()
        if not current_item:
            return
            
        # Ensure we operate on the top-level Action
        if current_item.parent() is not None:
             current_item = current_item.parent()

        if current_item.childCount() == 0:
            return

        self.ui.right_panel.start_button.setEnabled(False)
        self.ui.left_panel.action_tree.setEnabled(False)

        action_path = current_item.data(0, Qt.ItemDataRole.UserRole)
        
        # Only analyze video files
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

            # Core: Pass dynamic label definitions
            result = run_model_on_action(clip_paths, self.label_definitions)
            self.analysis_results[action_path] = result
            
            # Mark data as modified
            self.is_data_dirty = True

            self.ui.right_panel.export_button.setEnabled(True)
            self.display_analysis_results(action_path)
            self.update_action_item_status(action_path)
        else:
             # English UI
             self._show_temp_message_box("Analysis Skipped", 
                                        "No video files (.mp4, .avi, .mov) found in this action to analyze.", 
                                        QMessageBox.Icon.Warning, 2000)
        
        self.ui.right_panel.start_button.setEnabled(True)
        self.ui.left_panel.action_tree.setEnabled(True)
        self.update_save_export_button_state()

    def _get_current_action_path(self):
        current_item = self.ui.left_panel.action_tree.currentItem()
        if not current_item:
            return None
        # Return the path of the top-level Action
        if current_item.parent() is None:
            return current_item.data(0, Qt.ItemDataRole.UserRole)
        else:
            return current_item.parent().data(0, Qt.ItemDataRole.UserRole)

    def save_manual_annotation(self):
        if not self.json_loaded:
             # English UI
             self._show_temp_message_box("Action Blocked", 
                                        "Please import a GAC JSON file before saving annotations.", 
                                        QMessageBox.Icon.Warning, 2000)
             return
             
        action_path = self._get_current_action_path()
        if not action_path:
            return
        
        # Core: Get all dynamic label data
        data = self.ui.right_panel.get_manual_annotation()
        
        action_name = self.action_path_to_name.get(action_path)
        
        # Check if any label is non-empty/non-null
        is_annotated = False
        cleaned_data = {}
        for k, v in data.items():
            if isinstance(v, list) and v: # multi_label
                cleaned_data[k] = v
                is_annotated = True
            elif isinstance(v, str) and v: # single_label
                cleaned_data[k] = v
                is_annotated = True
            elif v is not None: # single_label can be None
                pass
        
        if is_annotated:
            self.manual_annotations[action_path] = cleaned_data
            
            # Mark data as modified
            self.is_data_dirty = True
            
            # English UI
            self._show_temp_message_box("Success", 
                                        f"Annotation saved for {action_name}.", 
                                        QMessageBox.Icon.Information, 1500)
        elif action_path in self.manual_annotations:
            del self.manual_annotations[action_path]
            
            # Mark data as modified
            self.is_data_dirty = True
            
            # English UI
            self._show_temp_message_box("Success", 
                                        f"Annotation cleared for {action_name}.", 
                                        QMessageBox.Icon.Information, 1500)
        else:
            # English UI
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
            
            # Mark data as modified
            self.is_data_dirty = True
            
            # English UI
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
        """Checks for exportable data and updates Save and Export buttons."""
        can_export = self.json_loaded and (bool(self.analysis_results) or bool(self.manual_annotations))
        # Save button also depends on the dirty state
        can_save = can_export and (self.current_json_path is not None) and self.is_data_dirty
        
        self.ui.right_panel.export_button.setEnabled(can_export)
        self.ui.right_panel.save_button.setEnabled(can_save)

    def save_results_to_json(self):
        if not self.json_loaded:
             # English UI
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
             # English UI
             self._show_temp_message_box("Action Blocked", 
                                        "Please import a GAC JSON file before exporting.", 
                                        QMessageBox.Icon.Warning, 2000)
             return
             
        # English UI
        path, _ = QFileDialog.getSaveFileName(self, "Save GAC JSON Annotation As...", "", "JSON Files (*.json)")
        if not path: 
            return

        self._write_gac_json(path)
        self.current_json_path = path
        # 导出后，数据仍然被视为已保存，但如果路径变了，我们只在 _write_gac_json 中处理 dirtiness。
        self.update_save_export_button_state()

    def _write_gac_json(self, file_path):
        """Writes all current annotations (manual and auto) to the specified file path in GAC JSON format."""
        all_action_paths = set(self.action_path_to_name.keys()) 
        all_action_paths.update(self.analysis_results.keys()) 
        all_action_paths.update(self.manual_annotations.keys()) 
        
        if not all_action_paths:
            # English UI
            self._show_temp_message_box("No Data", "There is no annotation data to save.", QMessageBox.Icon.Warning)
            return False # Return False if nothing was written

        # Construct basic JSON structure
        output_data = {
            "version": "1.0",
            "date": datetime.datetime.now().isoformat().split('T')[0],
            "dataset_name": "Dynamic Action Classification Export",
            "metadata": {
                "created_by": "SoccerNet Pro Analysis Tool"
            },
            "task": self.current_task_name, # Use dynamic Task Name
            "modalities": self.modalities, # Export current modalities
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
            
            data_item = {
                "id": action_name,
                "metadata": {"AnnotationSource": "None"}, 
                "inputs": [],
                "labels": {}
            }
            
            annotation_source = "None"
            
            # Populate labels dynamically
            for head_name, definition in self.label_definitions.items():
                
                # --- 1. Determine Final Label Value ---
                if definition['type'] == 'single_label':
                    final_label = None
                    # Prioritize manual annotation
                    if manual_result and manual_result.get(head_name) and isinstance(manual_result.get(head_name), str):
                        final_label = manual_result.get(head_name)
                        annotation_source = "Manual"
                    # Fallback to automated Top 1 result
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
                        if annotation_source != "Manual": annotation_source = "Manual"
                    else:
                        final_label_list = [] # Ensure empty list is exported
                    
                    data_item["labels"][head_name] = {"labels": final_label_list}

            data_item["metadata"]["AnnotationSource"] = annotation_source

            # Populate inputs (Multi-modality support)
            action_item = path_to_item_map.get(action_path)
            if action_item:
                for j in range(action_item.childCount()):
                    clip_item = action_item.child(j)
                    clip_path = clip_item.data(0, Qt.ItemDataRole.UserRole)
                    clip_name_with_ext = os.path.basename(clip_path)
                    
                    # Determine modality type
                    file_ext = os.path.splitext(clip_name_with_ext)[1].lower()
                    modality_type = "unknown"
                    if file_ext in ('.mp4', '.avi', '.mov'):
                        modality_type = "video"
                    elif file_ext in ('.jpg', '.jpeg', '.png', '.bmp'):
                        modality_type = "image"
                    elif file_ext in ('.wav', '.mp3', '.aac'):
                         modality_type = "audio"
                    
                    # Simulate GAC Path
                    url_path = f"Dataset/Test/{action_name}/{clip_name_with_ext}" 
                    data_item["inputs"].append({
                        "type": modality_type,
                        "path": url_path
                    })

            # Export item if it has inputs OR labels
            if data_item["labels"] or data_item["inputs"]: 
                output_data["data"].append(data_item)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=4, ensure_ascii=False)
            
            # 成功写入后，清除脏数据标记
            self.is_data_dirty = False
            
            # English UI
            self._show_temp_message_box("Save Complete", 
                                        f"Annotations successfully saved to:\n{os.path.basename(file_path)}",
                                        QMessageBox.Icon.Information, 2000)
            return True
        except Exception as e:
            # English UI
            QMessageBox.critical(self, "Save Error", f"Failed to write JSON file: {e}")
            print(f"Failed to export GAC JSON: {e}")
            return False

# --- Program Entry ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ActionClassifierApp()
    window.show()
    sys.exit(app.exec())
