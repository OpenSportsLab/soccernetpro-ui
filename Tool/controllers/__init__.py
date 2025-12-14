import sys
import os
import copy
import json
import datetime
import re
from PyQt6.QtWidgets import (
    QMainWindow, QFileDialog, QMessageBox, QProgressDialog, QApplication
)
from PyQt6.QtCore import Qt, QTimer, QDir
from PyQt6.QtGui import QKeySequence, QShortcut, QColor, QIcon

from models import AppStateModel, CmdType
from ui.panels import MainWindowUI
from ui.widgets import DynamicSingleLabelGroup, DynamicMultiLabelGroup
from dialogs import FolderPickerDialog, CreateProjectDialog
from utils import resource_path, create_checkmark_icon, SINGLE_VIDEO_PREFIX, SUPPORTED_EXTENSIONS, natural_sort_key

class ActionClassifierApp(QMainWindow):
    
    FILTER_ALL = 0
    FILTER_DONE = 1
    FILTER_NOT_DONE = 2
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SoccerNet Pro Analysis Tool")
        self.setGeometry(100, 100, 1400, 900)
        
        # 1. Init MVC
        self.ui = MainWindowUI()
        self.setCentralWidget(self.ui)
        self.model = AppStateModel()
        
        # 2. Local State
        self._is_undoing_redoing = False
        bright_blue = QColor("#00BFFF")
        self.done_icon = create_checkmark_icon(bright_blue)
        self.empty_icon = QIcon() # [修复] 初始化为空图标对象，防止闪退
        
        # 3. Setup
        self.connect_signals()
        self._setup_shortcuts()
        self.apply_stylesheet("Night")
        self.ui.right_panel.manual_box.setEnabled(False)
        self._setup_dynamic_ui()
        
        # Ensure we start at welcome screen (default behavior of UI class, but good to be explicit)
        self.ui.show_welcome_view()

    # --- Setup & Signals ---
    def connect_signals(self):
        # Welcome Screen Connections (Connect to same logic as Left Panel)
        self.ui.welcome_widget.import_btn.clicked.connect(self.import_annotations)
        self.ui.welcome_widget.create_btn.clicked.connect(self.create_new_project)

        # Left Panel
        self.ui.left_panel.clear_btn.clicked.connect(self.on_clear_list_clicked)
        self.ui.left_panel.import_btn.clicked.connect(self.import_annotations)
        self.ui.left_panel.create_btn.clicked.connect(self.create_new_project)
        self.ui.left_panel.add_data_btn.clicked.connect(self._dynamic_data_import)
        self.ui.left_panel.request_remove_item.connect(self.remove_single_action_item)
        self.ui.left_panel.action_tree.currentItemChanged.connect(self.on_item_selected)
        self.ui.left_panel.filter_combo.currentIndexChanged.connect(self.apply_action_filter)
        self.ui.left_panel.undo_btn.clicked.connect(self.perform_undo)
        self.ui.left_panel.redo_btn.clicked.connect(self.perform_redo)
        
        # Center Panel
        self.ui.center_panel.play_btn.clicked.connect(self.play_video)
        self.ui.center_panel.multi_view_btn.clicked.connect(self.show_all_views)
        self.ui.center_panel.prev_action.clicked.connect(self.nav_prev_action)
        self.ui.center_panel.prev_clip.clicked.connect(self.nav_prev_clip)
        self.ui.center_panel.next_clip.clicked.connect(self.nav_next_clip)
        self.ui.center_panel.next_action.clicked.connect(self.nav_next_action)
        
        # Right Panel
        self.ui.right_panel.save_btn.clicked.connect(self.save_results_to_json)
        self.ui.right_panel.export_btn.clicked.connect(self.export_results_to_json)
        self.ui.right_panel.confirm_btn.clicked.connect(self.save_manual_annotation)
        self.ui.right_panel.clear_sel_btn.clicked.connect(self.clear_current_manual_annotation)
        self.ui.right_panel.add_head_clicked.connect(self._handle_add_label_head)
        self.ui.right_panel.remove_head_clicked.connect(self._handle_remove_label_head)
        self.ui.right_panel.style_mode_changed.connect(self.apply_stylesheet)

    def _setup_shortcuts(self):
        self.undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        self.undo_shortcut.activated.connect(self.perform_undo)
        self.redo_shortcut = QShortcut(QKeySequence.StandardKey.Redo, self)
        self.redo_shortcut.activated.connect(self.perform_redo)

    def apply_stylesheet(self, mode):
        qss = "style.qss" if mode == "Night" else "style_day.qss"
        try:
            with open(resource_path(os.path.join("style", qss)), "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Style error: {e}")

    # --- Close Event & Project Check (Warning Mechanisms) ---
    def closeEvent(self, event):
        """[新增] 退出应用时的未保存警告"""
        can_export = self.model.json_loaded and bool(self.model.manual_annotations)
        
        # 如果数据未修改，或者没有可导出的数据，直接退出
        if not self.model.is_data_dirty or not can_export:
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
            if self.save_results_to_json(): 
                event.accept() 
            else:
                event.ignore() # 保存失败或取消，阻止退出
        elif clicked_button == discard_btn:
            event.accept()
        else:
            event.ignore()

    def check_and_close_current_project(self):
        """[新增] 在打开新项目前检查当前工作区"""
        if self.model.json_loaded:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Open New Project")
            msg_box.setText("Opening a new project will clear the current workspace. Continue?")
            msg_box.setIcon(QMessageBox.Icon.Warning)
            
            if self.model.is_data_dirty:
                msg_box.setInformativeText("You have unsaved changes in the current project.")
                
            btn_yes = msg_box.addButton("Yes", QMessageBox.ButtonRole.AcceptRole)
            btn_no = msg_box.addButton("No", QMessageBox.ButtonRole.RejectRole)
            msg_box.setDefaultButton(btn_no)
            msg_box.exec()
            
            if msg_box.clickedButton() == btn_yes:
                return True
            else:
                return False
        return True

    # --- UI Logic ---
    def _setup_dynamic_ui(self):
        self.ui.right_panel.setup_dynamic_labels(self.model.label_definitions)
        self.ui.right_panel.task_label.setText(f"Task: {self.model.current_task_name}")
        self._connect_dynamic_type_buttons()

    def _connect_dynamic_type_buttons(self):
        for head, group in self.ui.right_panel.label_groups.items():
            try: group.add_btn.clicked.disconnect()
            except: pass
            try: group.remove_label_signal.disconnect()
            except: pass
            try: group.value_changed.disconnect()
            except: pass
            
            group.add_btn.clicked.connect(lambda _, h=head: self.add_custom_type(h))
            group.remove_label_signal.connect(lambda lbl, h=head: self.remove_custom_type(h, lbl))
            group.value_changed.connect(self._handle_ui_selection_change)

    def update_action_item_status(self, action_path):
        item = self.model.action_item_map.get(action_path)
        if not item: return
        is_done = (action_path in self.model.manual_annotations and bool(self.model.manual_annotations[action_path]))
        item.setIcon(0, self.done_icon if is_done else self.empty_icon)
        self.apply_action_filter()

    def apply_action_filter(self):
        curr = self.ui.left_panel.filter_combo.currentIndex()
        for path, item in self.model.action_item_map.items():
            is_done = (path in self.model.manual_annotations and bool(self.model.manual_annotations[path]))
            if curr == self.FILTER_ALL: item.setHidden(False)
            elif curr == self.FILTER_DONE: item.setHidden(not is_done)
            elif curr == self.FILTER_NOT_DONE: item.setHidden(is_done)

    def _refresh_ui_after_undo_redo(self, action_path):
        if not action_path: return
        self.update_action_item_status(action_path)
        item = self.model.action_item_map.get(action_path)
        if item and self.ui.left_panel.action_tree.currentItem() != item:
            self.ui.left_panel.action_tree.setCurrentItem(item)
        
        current = self._get_current_action_path()
        if current == action_path: self.display_manual_annotation(action_path)
        self.update_save_export_button_state()

    def update_save_export_button_state(self):
        can_export = self.model.json_loaded and bool(self.model.manual_annotations)
        can_save = can_export and (self.model.current_json_path is not None) and self.model.is_data_dirty
        self.ui.right_panel.export_btn.setEnabled(can_export)
        self.ui.right_panel.save_btn.setEnabled(can_save)
        self.ui.left_panel.undo_btn.setEnabled(len(self.model.undo_stack) > 0)
        self.ui.left_panel.redo_btn.setEnabled(len(self.model.redo_stack) > 0)

    # --- Action Tree Management ---
    def _populate_action_tree(self):
        self.ui.left_panel.action_tree.clear()
        self.model.action_item_map.clear()
        
        sorted_list = sorted(self.model.action_item_data, key=lambda d: natural_sort_key(d.get('name', '')))
        for data in sorted_list:
            item = self.ui.left_panel.add_action_item(data['name'], data['path'], data.get('source_files'))
            self.model.action_item_map[data['path']] = item
            
        for path in self.model.action_item_map.keys():
            self.update_action_item_status(path)
        self.apply_action_filter()

    def remove_single_action_item(self, item):
        if not item: return
        target = item if item.parent() is None else item.parent()
        path = target.data(0, Qt.ItemDataRole.UserRole)
        name = target.text(0)
        
        reply = QMessageBox.question(self, 'Remove Item', f"Remove '{name}'? Annotations will be discarded.", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if path in self.model.manual_annotations: del self.model.manual_annotations[path]
            if path in self.model.action_item_map: del self.model.action_item_map[path]
            if path in self.model.action_path_to_name: del self.model.action_path_to_name[path]
            if path in self.model.imported_action_metadata: del self.model.imported_action_metadata[path]
            self.model.action_item_data = [d for d in self.model.action_item_data if d['path'] != path]
            
            root = self.ui.left_panel.action_tree.invisibleRootItem()
            root.removeChild(target)
            self.model.is_data_dirty = True
            self.update_save_export_button_state()
            if self.ui.left_panel.action_tree.topLevelItemCount() == 0:
                self.ui.center_panel.show_single_view(None)
                self.ui.right_panel.manual_box.setEnabled(False)

    def on_clear_list_clicked(self):
        if not self.model.json_loaded and not self.model.action_item_data: return
        msg = QMessageBox(self)
        msg.setWindowTitle("Clear Workspace")
        msg.setText("Clear workspace? Unsaved changes will be lost.")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        if msg.exec() == QMessageBox.StandardButton.Yes:
            self.clear_action_list(clear_working_dir=True, full_reset=True)

    def clear_action_list(self, clear_working_dir=True, full_reset=False):
        self.ui.left_panel.action_tree.clear()
        self.model.reset(full_reset)
        self.update_save_export_button_state()
        self.ui.right_panel.manual_box.setEnabled(False)
        self.ui.center_panel.show_single_view(None)
        if full_reset: 
            self._setup_dynamic_ui()
            # If we fully reset (close project), go back to Welcome Screen
            self.ui.show_welcome_view()

    # --- Data Operations (Import/Export) ---
    def import_annotations(self):
        # [修改] 使用新的项目检查逻辑
        if not self.check_and_close_current_project(): return
        
        file_path, _ = QFileDialog.getOpenFileName(self, "Select JSON", "", "JSON Files (*.json)")
        if not file_path: return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f: data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Invalid JSON: {e}"); return
            
        valid, err, warn = self.model.validate_gac_json(data)
        if not valid:
            QMessageBox.critical(self, "JSON Error", err); return
        if warn:
            QMessageBox.warning(self, "Warnings", warn)
            
        self.clear_action_list(clear_working_dir=False, full_reset=True)
        self.model.current_working_directory = os.path.dirname(file_path)
        self.model.current_task_name = data.get('task', "N/A")
        self.model.modalities = data.get('modalities', [])
        
        # Parse Labels
        self.model.label_definitions = {}
        if 'labels' in data:
            for k, v in data['labels'].items():
                clean_k = k.strip().replace(' ', '_').lower()
                self.model.label_definitions[clean_k] = {'type': v['type'], 'labels': sorted(list(set(v.get('labels', []))))}
        self._setup_dynamic_ui()
        
        # Parse Data
        count = 0
        for item in data.get('data', []):
            aid = item.get('id')
            if not aid: continue
            
            src_files = []
            for inp in item.get('inputs', []):
                p = inp.get('path', '')
                fp = p if os.path.isabs(p) else os.path.normpath(os.path.join(self.model.current_working_directory, p))
                src_files.append(fp)
                self.model.imported_input_metadata[(aid, os.path.basename(fp))] = inp.get('metadata', {})
            
            self.model.action_item_data.append({'name': aid, 'path': aid, 'source_files': src_files})
            self.model.action_path_to_name[aid] = aid
            self.model.imported_action_metadata[aid] = item.get('metadata', {})
            
            # Parse Manual Annotations
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
                self.model.manual_annotations[aid] = manual
                count += 1

        self.model.current_json_path = file_path
        self.model.json_loaded = True
        self._populate_action_tree()
        self.update_save_export_button_state()
        self._show_temp_msg("Imported", f"Loaded {len(self.model.action_item_data)} items.")
        
        # Switch to Main View on success
        self.ui.show_main_view()

    def create_new_project(self):
        # [修改] 使用新的项目检查逻辑
        if not self.check_and_close_current_project(): return
        
        dlg = CreateProjectDialog(self)
        if dlg.exec():
            self.clear_action_list(clear_working_dir=False, full_reset=True)
            data = dlg.get_data()
            self.model.current_task_name = data['task']
            self.model.modalities = data['modalities']
            self.model.label_definitions = data['labels']
            self.model.project_description = data['description']
            self.model.json_loaded = True
            self.model.is_data_dirty = True
            self._setup_dynamic_ui()
            self.update_save_export_button_state()
            
            # Switch to Main View on success
            self.ui.show_main_view()

    def _dynamic_data_import(self):
        if not self.model.json_loaded:
            QMessageBox.warning(self, "Warning", "Please import/create project first."); return
        
        has_vid = 'video' in self.model.modalities
        has_others = any(x in ['image', 'audio'] for x in self.model.modalities)
        
        if has_vid and not has_others:
            self._import_video_files_only()
        elif has_vid and has_others:
            self._import_multi_modal()
        else:
            QMessageBox.warning(self, "Warning", "Unsupported modality combination.")

    def _import_video_files_only(self):
        start = self.model.current_working_directory or ""
        files, _ = QFileDialog.getOpenFileNames(self, "Select Video", start, "Video (*.mp4 *.avi *.mov)")
        if not files: return
        
        # Calc counter
        ctr = 1
        for name in self.model.action_path_to_name.values():
            if name.startswith(SINGLE_VIDEO_PREFIX):
                try: ctr = max(ctr, int(name.split('_')[-1]) + 1)
                except: pass
        
        added = 0
        for fp in files:
            aid = f"{SINGLE_VIDEO_PREFIX}{ctr:03d}"
            self.model.action_item_data.append({'name': aid, 'path': aid, 'source_files': [fp]})
            self.model.action_path_to_name[aid] = aid
            added += 1; ctr += 1
            
        if added:
            self._populate_action_tree()
            self.model.is_data_dirty = True
            self.update_save_export_button_state()

    def _import_multi_modal(self):
        dlg = FolderPickerDialog(self.model.current_working_directory or "", self)
        if dlg.exec():
            dirs = dlg.get_selected_paths()
            if dirs: self._process_dirs(dirs)

    def _process_dirs(self, dirs):
        if not self.model.current_working_directory and dirs:
            self.model.current_working_directory = os.path.dirname(dirs[0])
            
        prog = QProgressDialog("Importing...", "Cancel", 0, len(dirs), self)
        prog.setWindowModality(Qt.WindowModality.WindowModal)
        prog.show()
        
        added = False
        for i, d in enumerate(dirs):
            if prog.wasCanceled(): break
            prog.setValue(i)
            
            srcs = []
            try:
                for e in os.scandir(d):
                    if e.is_file() and e.name.lower().endswith(SUPPORTED_EXTENSIONS):
                        srcs.append(e.path)
            except: continue
            
            if not srcs: continue
            srcs.sort()
            
            try: rel = os.path.relpath(d, self.model.current_working_directory).replace(os.sep, '/')
            except: rel = os.path.basename(d)
            
            self.model.action_item_data.append({'name': rel, 'path': rel, 'source_files': srcs})
            self.model.action_path_to_name[rel] = rel
            added = True
            
        prog.close()
        if added:
            self._populate_action_tree()
            self.model.is_data_dirty = True
            self.update_save_export_button_state()

    # --- Save & Export Methods (Updated for boolean return) ---
    def save_results_to_json(self):
        if self.model.current_json_path: 
            return self._write_gac_json(self.model.current_json_path)
        else: 
            return self.export_results_to_json()

    def export_results_to_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save JSON", "", "JSON (*.json)")
        if path:
            result = self._write_gac_json(path)
            if result:
                self.model.current_json_path = path
                self.update_save_export_button_state()
            return result
        return False

    def _write_gac_json(self, path):
        out = {
            "version": "2.0",
            "date": datetime.datetime.now().isoformat().split('T')[0],
            "task": self.model.current_task_name,
            "description": self.model.project_description,
            "modalities": self.model.modalities,
            "labels": self.model.label_definitions,
            "data": []
        }
        
        root = self.ui.left_panel.action_tree.invisibleRootItem()
        path_map = {}
        for i in range(root.childCount()):
            it = root.child(i)
            path_map[it.data(0, Qt.ItemDataRole.UserRole)] = it
            
        sorted_keys = sorted(self.model.action_path_to_name.keys(), 
                             key=lambda k: natural_sort_key(self.model.action_path_to_name.get(k, "")))
        
        json_dir = os.path.dirname(path)
        
        for k in sorted_keys:
            name = self.model.action_path_to_name.get(k)
            if not name: continue
            
            man = self.model.manual_annotations.get(k, {})
            labels_out = {}
            for head, dfn in self.model.label_definitions.items():
                if dfn['type'] == 'single_label':
                    if man.get(head): labels_out[head] = {"label": man[head]}
                elif dfn['type'] == 'multi_label':
                    if man.get(head): labels_out[head] = {"labels": man[head]}
            
            inps = []
            item = path_map.get(k)
            if item:
                for j in range(item.childCount()):
                    clip = item.child(j)
                    abs_p = clip.data(0, Qt.ItemDataRole.UserRole)
                    bn = os.path.basename(abs_p)
                    ext = os.path.splitext(bn)[1].lower()
                    
                    mtype = "unknown"
                    if ext in ('.mp4', '.avi', '.mov'): mtype = "video"
                    elif ext in ('.jpg', '.png'): mtype = "image"
                    elif ext in ('.wav', '.mp3'): mtype = "audio"
                    
                    try: rel = os.path.relpath(abs_p, json_dir).replace(os.sep, '/')
                    except: rel = abs_p
                    
                    iobj = {"type": mtype, "path": rel}
                    meta = self.model.imported_input_metadata.get((k, bn))
                    if meta: iobj["metadata"] = meta
                    inps.append(iobj)
            
            entry = {
                "id": name,
                "inputs": inps,
                "labels": labels_out,
                "metadata": self.model.imported_action_metadata.get(k, {})
            }
            out["data"].append(entry)
            
        try:
            with open(path, 'w', encoding='utf-8') as f: json.dump(out, f, indent=2, ensure_ascii=False)
            self.model.is_data_dirty = False
            self.update_save_export_button_state()
            self._show_temp_msg("Saved", f"Saved to {os.path.basename(path)}")
            return True # [修复] 返回 True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Save failed: {e}")
            return False # [修复] 返回 False

    # --- Interaction Logic ---
    def on_item_selected(self, current, _):
        if not current:
            self.ui.right_panel.manual_box.setEnabled(False)
            return
        
        is_action = (current.childCount() > 0 or current.parent() is None)
        path = None
        
        if is_action:
            path = current.data(0, Qt.ItemDataRole.UserRole)
            media = None
            if current.childCount() > 0:
                media = current.child(0).data(0, Qt.ItemDataRole.UserRole)
            self.ui.center_panel.show_single_view(media)
            self.ui.center_panel.multi_view_btn.setEnabled(True)
        else:
            media = current.data(0, Qt.ItemDataRole.UserRole)
            self.ui.center_panel.show_single_view(media)
            if current.parent():
                path = current.parent().data(0, Qt.ItemDataRole.UserRole)
            self.ui.center_panel.multi_view_btn.setEnabled(False)
            
        can_annotate = (path is not None) and self.model.json_loaded
        self.ui.right_panel.manual_box.setEnabled(can_annotate)
        if path: self.display_manual_annotation(path)

    def display_manual_annotation(self, path):
        self._is_undoing_redoing = True
        data = self.model.manual_annotations.get(path, {})
        self.ui.right_panel.set_annotation(data)
        self._is_undoing_redoing = False

    def save_manual_annotation(self):
        path = self._get_current_action_path()
        if not path: return
        
        raw = self.ui.right_panel.get_annotation()
        cleaned = {k: v for k, v in raw.items() if v}
        if not cleaned: cleaned = None
        
        old = copy.deepcopy(self.model.manual_annotations.get(path))
        self.model.push_undo(CmdType.ANNOTATION_CONFIRM, path=path, old_data=old, new_data=cleaned)
        
        if cleaned:
            self.model.manual_annotations[path] = cleaned
            self._show_temp_msg("Saved", "Annotation saved.", 1000)
        else:
            if path in self.model.manual_annotations: del self.model.manual_annotations[path]
            self._show_temp_msg("Cleared", "Annotation cleared.", 1000)
            
        self.update_action_item_status(path)
        self.update_save_export_button_state()
        
        # Auto Jump
        tree = self.ui.left_panel.action_tree
        curr = tree.currentItem()
        nxt = tree.itemBelow(curr)
        if nxt:
            QTimer.singleShot(500, lambda: [tree.setCurrentItem(nxt), tree.scrollToItem(nxt)])

    def clear_current_manual_annotation(self):
        path = self._get_current_action_path()
        if not path: return
        
        old = copy.deepcopy(self.model.manual_annotations.get(path))
        if old:
            self.model.push_undo(CmdType.ANNOTATION_CONFIRM, path=path, old_data=old, new_data=None)
            if path in self.model.manual_annotations: del self.model.manual_annotations[path]
            self.update_action_item_status(path)
            self.update_save_export_button_state()
            self._show_temp_msg("Cleared", "Selection cleared.")
        self.ui.right_panel.clear_selection()

    def _get_current_action_path(self):
        curr = self.ui.left_panel.action_tree.currentItem()
        if not curr: return None
        if curr.parent() is None: return curr.data(0, Qt.ItemDataRole.UserRole)
        return curr.parent().data(0, Qt.ItemDataRole.UserRole)

    def play_video(self): self.ui.center_panel.toggle_play_pause()
    def show_all_views(self):
        curr = self.ui.left_panel.action_tree.currentItem()
        if not curr: return
        if curr.parent(): curr = curr.parent()
        paths = [curr.child(i).data(0, Qt.ItemDataRole.UserRole) for i in range(curr.childCount())]
        self.ui.center_panel.show_all_views([p for p in paths if p.lower().endswith(SUPPORTED_EXTENSIONS[:3])])

    # --- Navigation ---
    def nav_prev_action(self): self._nav_tree(step=-1, level='top')
    def nav_next_action(self): self._nav_tree(step=1, level='top')
    def nav_prev_clip(self): self._nav_tree(step=-1, level='child')
    def nav_next_clip(self): self._nav_tree(step=1, level='child')
    
    def _nav_tree(self, step, level):
        tree = self.ui.left_panel.action_tree
        curr = tree.currentItem()
        if not curr: return
        
        if level == 'top':
            item = curr if curr.parent() is None else curr.parent()
            idx = tree.indexOfTopLevelItem(item)
            new_idx = idx + step
            if 0 <= new_idx < tree.topLevelItemCount():
                nxt = tree.topLevelItem(new_idx)
                tree.setCurrentItem(nxt); tree.scrollToItem(nxt)
        else:
            parent = curr.parent()
            if not parent:
                if step == 1 and curr.childCount() > 0:
                    nxt = curr.child(0)
                    tree.setCurrentItem(nxt); tree.scrollToItem(nxt)
            else:
                idx = parent.indexOfChild(curr)
                new_idx = idx + step
                if 0 <= new_idx < parent.childCount():
                    nxt = parent.child(new_idx)
                    tree.setCurrentItem(nxt); tree.scrollToItem(nxt)

    # --- Dynamic Schema Editing ---
    def _handle_add_label_head(self, name):
        clean = name.strip().replace(' ', '_').lower()
        if not clean or clean in self.model.label_definitions: return
        
        msg = QMessageBox(self); msg.setText(f"Type for '{name}'?")
        b1 = msg.addButton("Single Label", QMessageBox.ButtonRole.ActionRole)
        b2 = msg.addButton("Multi Label", QMessageBox.ButtonRole.ActionRole)
        msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        
        type_str = "single_label" if msg.clickedButton() == b1 else "multi_label" if msg.clickedButton() == b2 else None
        if not type_str: return
        
        defn = {"type": type_str, "labels": []}
        self.model.push_undo(CmdType.SCHEMA_ADD_CAT, head=clean, definition=defn)
        self.model.label_definitions[clean] = defn
        self.ui.right_panel.new_head_edit.clear()
        self._setup_dynamic_ui()

    def _handle_remove_label_head(self, head):
        if head not in self.model.label_definitions: return
        if QMessageBox.question(self, "Remove", f"Remove '{head}'?") == QMessageBox.StandardButton.No: return
        
        affected = {}
        for k, v in self.model.manual_annotations.items():
            if head in v: affected[k] = copy.deepcopy(v[head])
            
        self.model.push_undo(CmdType.SCHEMA_DEL_CAT, head=head, definition=copy.deepcopy(self.model.label_definitions[head]), affected_data=affected)
        
        del self.model.label_definitions[head]
        for k in affected: 
            del self.model.manual_annotations[k][head]
            if not self.model.manual_annotations[k]: del self.model.manual_annotations[k]
            self.update_action_item_status(k)
            
        self._setup_dynamic_ui()
        self.display_manual_annotation(self._get_current_action_path())

    def add_custom_type(self, head):
        group = self.ui.right_panel.label_groups.get(head)
        txt = group.input_field.text().strip()
        if not txt: return
        
        labels = self.model.label_definitions[head]['labels']
        if any(l.lower() == txt.lower() for l in labels):
            self._show_temp_msg("Duplicate", "Label exists.", icon=QMessageBox.Icon.Warning)
            return
            
        self.model.push_undo(CmdType.SCHEMA_ADD_LBL, head=head, label=txt)
        labels.append(txt); labels.sort()
        if isinstance(group, DynamicSingleLabelGroup): group.update_radios(labels)
        else: group.update_checkboxes(labels)
        group.input_field.clear()

    def remove_custom_type(self, head, lbl):
        defn = self.model.label_definitions[head]
        if len(defn['labels']) <= 1: return
        
        affected = {}
        for k, v in self.model.manual_annotations.items():
            if defn['type'] == 'single_label' and v.get(head) == lbl: affected[k] = lbl
            elif defn['type'] == 'multi_label' and lbl in v.get(head, []): affected[k] = copy.deepcopy(v[head])
            
        self.model.push_undo(CmdType.SCHEMA_DEL_LBL, head=head, label=lbl, affected_data=affected)
        
        if lbl in defn['labels']: defn['labels'].remove(lbl)
        
        for k, val in self.model.manual_annotations.items():
            if defn['type'] == 'single_label' and val.get(head) == lbl: val[head] = None
            elif defn['type'] == 'multi_label' and lbl in val.get(head, []): val[head].remove(lbl)
            
        # UI Refresh
        group = self.ui.right_panel.label_groups.get(head)
        if isinstance(group, DynamicSingleLabelGroup): group.update_radios(defn['labels'])
        else: group.update_checkboxes(defn['labels'])
        self.display_manual_annotation(self._get_current_action_path())

    def _handle_ui_selection_change(self, head, new_val):
        if self._is_undoing_redoing: return
        path = self._get_current_action_path()
        if not path: return
        
        # Find old val from undo stack or current data
        old_val = self.model.manual_annotations.get(path, {}).get(head)
        for cmd in reversed(self.model.undo_stack):
            if cmd['type'] == CmdType.UI_CHANGE and cmd['path'] == path and cmd['head'] == head:
                old_val = cmd['new_val']; break
                
        self.model.push_undo(CmdType.UI_CHANGE, path=path, head=head, old_val=old_val, new_val=new_val)

    # --- Undo/Redo Exec ---
    def perform_undo(self):
        if not self.model.undo_stack: return
        self._is_undoing_redoing = True
        cmd = self.model.undo_stack.pop()
        self.model.redo_stack.append(cmd)
        self._apply_state_change(cmd, is_undo=True)
        self.update_save_export_button_state()
        self._is_undoing_redoing = False

    def perform_redo(self):
        if not self.model.redo_stack: return
        self._is_undoing_redoing = True
        cmd = self.model.redo_stack.pop()
        self.model.undo_stack.append(cmd)
        self._apply_state_change(cmd, is_undo=False)
        self.update_save_export_button_state()
        self._is_undoing_redoing = False

    def _apply_state_change(self, cmd, is_undo):
        ctype = cmd['type']
        
        if ctype == CmdType.ANNOTATION_CONFIRM:
            path = cmd['path']
            data = cmd['old_data'] if is_undo else cmd['new_data']
            if data is None:
                if path in self.model.manual_annotations: del self.model.manual_annotations[path]
            else: self.model.manual_annotations[path] = copy.deepcopy(data)
            self._refresh_ui_after_undo_redo(path)
            
        elif ctype == CmdType.UI_CHANGE:
            path = cmd['path']
            if self._get_current_action_path() == path:
                val = cmd['old_val'] if is_undo else cmd['new_val']
                grp = self.ui.right_panel.label_groups.get(cmd['head'])
                if isinstance(grp, DynamicSingleLabelGroup): grp.set_checked_label(val)
                else: grp.set_checked_labels(val)
                
        elif ctype == CmdType.SCHEMA_ADD_CAT:
            head = cmd['head']
            if is_undo:
                del self.model.label_definitions[head]
            else:
                self.model.label_definitions[head] = cmd['definition']
            self._setup_dynamic_ui()
            self._refresh_ui_after_undo_redo(self._get_current_action_path())
            
        elif ctype == CmdType.SCHEMA_DEL_CAT:
            head = cmd['head']
            if is_undo:
                self.model.label_definitions[head] = cmd['definition']
                for k, v in cmd['affected_data'].items():
                    if k not in self.model.manual_annotations: self.model.manual_annotations[k] = {}
                    self.model.manual_annotations[k][head] = v
            else:
                del self.model.label_definitions[head]
                for k in cmd['affected_data']:
                    if head in self.model.manual_annotations.get(k, {}): del self.model.manual_annotations[k][head]
            self._setup_dynamic_ui()
            self._refresh_ui_after_undo_redo(self._get_current_action_path())
            
        elif ctype == CmdType.SCHEMA_ADD_LBL:
            head = cmd['head']; lbl = cmd['label']
            lst = self.model.label_definitions[head]['labels']
            if is_undo:
                if lbl in lst: lst.remove(lbl)
            else:
                if lbl not in lst: lst.append(lbl); lst.sort()
            
            grp = self.ui.right_panel.label_groups.get(head)
            if isinstance(grp, DynamicSingleLabelGroup): grp.update_radios(lst)
            else: grp.update_checkboxes(lst)
            
        elif ctype == CmdType.SCHEMA_DEL_LBL:
            head = cmd['head']; lbl = cmd['label']
            lst = self.model.label_definitions[head]['labels']
            affected = cmd['affected_data']
            
            if is_undo:
                if lbl not in lst: lst.append(lbl); lst.sort()
                for k, v in affected.items():
                    if k not in self.model.manual_annotations: self.model.manual_annotations[k] = {}
                    if self.model.label_definitions[head]['type'] == 'single_label':
                        self.model.manual_annotations[k][head] = v
                    else:
                        cur = self.model.manual_annotations[k].get(head, [])
                        if lbl not in cur: cur.append(lbl)
                        self.model.manual_annotations[k][head] = cur
            else:
                if lbl in lst: lst.remove(lbl)
                for k in affected:
                    anno = self.model.manual_annotations.get(k, {})
                    if self.model.label_definitions[head]['type'] == 'single_label':
                        if anno.get(head) == lbl: anno[head] = None
                    else:
                        if lbl in anno.get(head, []): anno[head].remove(lbl)
                        
            grp = self.ui.right_panel.label_groups.get(head)
            if isinstance(grp, DynamicSingleLabelGroup): grp.update_radios(lst)
            else: grp.update_checkboxes(lst)
            self._refresh_ui_after_undo_redo(self._get_current_action_path())

    def _show_temp_msg(self, title, msg, duration=1500, icon=QMessageBox.Icon.Information):
        m = QMessageBox(self); m.setWindowTitle(title); m.setText(msg); m.setIcon(icon)
        m.setStandardButtons(QMessageBox.StandardButton.NoButton)
        QTimer.singleShot(duration, m.accept)
        m.exec()