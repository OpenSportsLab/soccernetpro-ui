import os
import json
from PyQt6.QtWidgets import QMessageBox, QFileDialog, QTreeWidgetItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from utils import natural_sort_key

class LocalizationManager:
    """
    Manages logic for the UI2 Localization Interface.
    """
    def __init__(self, main_window):
        self.main = main_window
        self.model = main_window.model
        self.ui_root = main_window.ui.localization_ui
        
        self.left_panel = self.ui_root.left_panel
        self.center_panel = self.ui_root.center_panel
        self.right_panel = self.ui_root.right_panel
        
        self.current_video_path = None
        self.current_head = "action" 
        self.current_label = None

    def setup_connections(self):
        # --- Left Panel ---
        pc = self.left_panel.project_controls
        pc.loadRequested.connect(self._on_load_clicked)
        pc.addVideoRequested.connect(self._on_add_video_clicked)
        pc.saveRequested.connect(self._on_save_clicked)
        pc.exportRequested.connect(self._on_export_clicked)
        
        self.left_panel.clip_tree.currentItemChanged.connect(self.on_clip_selected)
        self.left_panel.filter_combo.currentIndexChanged.connect(self._apply_clip_filter)
        
        # --- Center Panel ---
        media = self.center_panel.media_preview
        timeline = self.center_panel.timeline
        pb = self.center_panel.playback
        
        media.positionChanged.connect(timeline.set_position)
        media.durationChanged.connect(timeline.set_duration)
        timeline.seekRequested.connect(media.set_position)
        
        pb.stopRequested.connect(media.stop)
        pb.playbackRateRequested.connect(media.set_playback_rate)
        pb.seekRelativeRequested.connect(lambda d: media.set_position(media.player.position() + d))
        pb.playPauseRequested.connect(media.toggle_play_pause)
        pb.nextPrevClipRequested.connect(self._navigate_clip)
        pb.nextPrevAnnotRequested.connect(self._navigate_annotation)
        
        # --- Right Panel ---
        self.right_panel.label_editor.newLabelAdded.connect(self._on_add_new_label)
        self.right_panel.annot_mgmt.labelActionTriggered.connect(self._on_label_action_triggered)
        self.right_panel.annot_mgmt.labelRemoveTriggered.connect(self._on_label_remove_triggered)
        self.right_panel.annot_mgmt.undoRequested.connect(self._on_undo)
        
        self.right_panel.table.annotationSelected.connect(lambda ms: media.set_position(ms))
        self.right_panel.table.annotationDeleted.connect(self._on_delete_single_annotation)

    # --- Video & Project Logic ---

    def _on_load_clicked(self):
        self.main.router.import_annotations()

    def _on_add_video_clicked(self):
        start_dir = self.model.current_working_directory or ""
        files, _ = QFileDialog.getOpenFileNames(self.main, "Select Video(s)", start_dir, "Video (*.mp4 *.avi *.mov *.mkv)")
        if not files: return
        
        if not self.model.current_working_directory:
            self.model.current_working_directory = os.path.dirname(files[0])
            
        added_count = 0
        for file_path in files:
            if any(d['path'] == file_path for d in self.model.action_item_data):
                continue
            name = os.path.basename(file_path)
            self.model.action_item_data.append({'name': name, 'path': file_path, 'source_files': [file_path]})
            self.model.action_path_to_name[file_path] = name
            added_count += 1
            
        if added_count > 0:
            self.model.is_data_dirty = True
            self.populate_tree()
            self.main.show_temp_msg("Videos Added", f"Added {added_count} clips.")

    def populate_tree(self):
        self.left_panel.clip_tree.clear()
        sorted_list = sorted(self.model.action_item_data, key=lambda d: natural_sort_key(d.get('name', '')))
        for data in sorted_list:
            name = data['name']
            path = data['path']
            item = QTreeWidgetItem(self.left_panel.clip_tree, [name])
            item.setData(0, Qt.ItemDataRole.UserRole, path)
            events = self.model.localization_events.get(path, [])
            item.setIcon(0, self.main.done_icon if events else self.main.empty_icon)
        
        self.left_panel.project_controls.set_project_loaded_state(True)
        self.right_panel.annot_mgmt.update_schema(self.model.label_definitions)
        self.right_panel.label_editor.set_current_head(self.current_head)
        self._apply_clip_filter(self.left_panel.filter_combo.currentIndex())

    def _apply_clip_filter(self, index):
        root = self.left_panel.clip_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            path = item.data(0, Qt.ItemDataRole.UserRole)
            events = self.model.localization_events.get(path, [])
            has_anno = len(events) > 0
            
            should_hide = False
            if index == 1 and not has_anno: should_hide = True
            elif index == 2 and has_anno: should_hide = True
            item.setHidden(should_hide)

    def on_clip_selected(self, current, previous):
        if not current: return
        path = current.data(0, Qt.ItemDataRole.UserRole)
        if path and os.path.exists(path):
            self.current_video_path = path
            self.center_panel.media_preview.load_video(path)
            self._display_events_for_item(path)
        else:
            if path: QMessageBox.warning(self.main, "Error", f"File not found: {path}")

    def _navigate_clip(self, step):
        tree = self.left_panel.clip_tree
        curr = tree.currentItem()
        if not curr: return
        
        visible_items = []
        root = tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if not item.isHidden():
                visible_items.append(item)
                
        if not visible_items: return
        try:
            curr_idx = visible_items.index(curr)
            new_idx = curr_idx + step
            if 0 <= new_idx < len(visible_items):
                tree.setCurrentItem(visible_items[new_idx])
        except ValueError:
            pass

    def _navigate_annotation(self, step):
        if not self.current_video_path: return
        events = self.model.localization_events.get(self.current_video_path, [])
        if not events: return
        
        sorted_events = sorted(events, key=lambda x: x.get('position_ms', 0))
        current_pos = self.center_panel.media_preview.player.position()
        target_time = None
        
        if step > 0:
            for e in sorted_events:
                if e.get('position_ms', 0) > current_pos + 100:
                    target_time = e.get('position_ms')
                    break
        else:
            for e in reversed(sorted_events):
                if e.get('position_ms', 0) < current_pos - 100:
                    target_time = e.get('position_ms')
                    break
        if target_time is not None:
            self.center_panel.media_preview.set_position(target_time)
            self._select_row_by_time(target_time)

    def _select_row_by_time(self, time_ms):
        model = self.right_panel.table.model
        for row in range(model.rowCount()):
            item = model.get_annotation_at(row)
            if item and abs(item.get('position_ms', 0) - time_ms) < 10:
                idx = model.index(row, 0)
                self.right_panel.table.table.selectRow(row)
                self.right_panel.table.table.scrollTo(idx)
                break

    # --- Label & Annotation Logic ---

    def _on_add_new_label(self, head, label):
        if not head: head = "action"
        if head not in self.model.label_definitions:
            self.model.label_definitions[head] = {"type": "single_label", "labels": []}
            
        labels_list = self.model.label_definitions[head].get('labels', [])
        if label and label not in labels_list:
            labels_list.append(label)
            self.model.is_data_dirty = True
            self.right_panel.annot_mgmt.update_schema(self.model.label_definitions)
        
        self._on_label_action_triggered(head, label)

    def _on_label_action_triggered(self, head, label):
        if not self.current_video_path:
            QMessageBox.warning(self.main, "Warning", "No video selected.")
            return
        
        self.current_head = head 
        self.right_panel.label_editor.set_current_head(head)
        
        pos_ms = self.center_panel.media_preview.player.position()
        
        new_event = {
            "head": head,
            "label": label,
            "position_ms": pos_ms,
        }
        
        if self.current_video_path not in self.model.localization_events:
            self.model.localization_events[self.current_video_path] = []
            
        self.model.localization_events[self.current_video_path].append(new_event)
        self.model.is_data_dirty = True
        
        self._display_events_for_item(self.current_video_path)
        self.populate_tree() 
        self.main.show_temp_msg("Event Marked", f"{label} @ {self._fmt_ms(pos_ms)}")

    def _on_label_remove_triggered(self, head, label):
        if QMessageBox.question(self.main, "Remove Label", f"Delete '{label}' from schema?") == QMessageBox.StandardButton.Yes:
            if head in self.model.label_definitions:
                labels = self.model.label_definitions[head].get('labels', [])
                if label in labels:
                    labels.remove(label)
                    self.model.is_data_dirty = True
                    self.right_panel.annot_mgmt.update_schema(self.model.label_definitions)

    def _on_delete_single_annotation(self, item_data):
        events = self.model.localization_events.get(self.current_video_path, [])
        if item_data in events:
            events.remove(item_data)
            self.model.is_data_dirty = True
            self._display_events_for_item(self.current_video_path)
            self.populate_tree()

    def _display_events_for_item(self, path):
        events = self.model.localization_events.get(path, [])
        display_data = []
        clip_name = os.path.basename(path)
        for e in events:
            d = e.copy()
            d['clip'] = clip_name
            display_data.append(e) 
        
        display_data.sort(key=lambda x: x.get('position_ms', 0))
        self.right_panel.table.set_data(display_data)
        
        markers = [{'start_ms': e.get('position_ms', 0), 'color': QColor("#00BFFF")} for e in events]
        self.center_panel.timeline.set_markers(markers)

    def _on_save_clicked(self):
        # [修改] 调用 overwrite_json
        self.main.router.loc_fm.overwrite_json()

    def _on_export_clicked(self):
        # [修改] 调用 export_json
        self.main.router.loc_fm.export_json()

    def _on_undo(self):
        pass

    def _fmt_ms(self, ms):
        s = ms // 1000
        return f"{s//60:02}:{s%60:02}.{ms%1000:03}"