import os
import copy
from PyQt6.QtWidgets import QMessageBox, QInputDialog, QTreeWidgetItem, QFileDialog, QMenu
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QColor
from PyQt6.QtMultimedia import QMediaPlayer # [新增] 必须引入 QMediaPlayer
from utils import natural_sort_key
from models import CmdType 

class LocalizationManager:
    """
    Manages logic for the UI2 Localization Interface.
    Redesigned to support Multi-Head Tabs, Integrated Label Management, and Table Interaction.
    """
    def __init__(self, main_window):
        self.main = main_window
        self.model = main_window.model
        self.ui_root = main_window.ui.localization_ui
        
        self.left_panel = self.ui_root.left_panel
        self.center_panel = self.ui_root.center_panel
        self.right_panel = self.ui_root.right_panel
        
        self.current_video_path = None
        self.current_head = None 

    def setup_connections(self):
        # --- Left Panel ---
        pc = self.left_panel.project_controls
        pc.loadRequested.connect(self._on_load_clicked)
        pc.addVideoRequested.connect(self._on_add_video_clicked)
        pc.saveRequested.connect(self._on_save_clicked)
        pc.exportRequested.connect(self._on_export_clicked)
        
        # Tree Interactions
        self.left_panel.clip_tree.currentItemChanged.connect(self.on_clip_selected)
        
        # Right Click Context Menu
        self.left_panel.clip_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.left_panel.clip_tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        
        self.left_panel.filter_combo.currentIndexChanged.connect(self._apply_clip_filter)
        
        # Clear All Button
        self.left_panel.btn_clear_all.clicked.connect(self._on_clear_all_clicked)
        
        # --- Center Panel ---
        media = self.center_panel.media_preview
        timeline = self.center_panel.timeline
        pb = self.center_panel.playback
        
        media.positionChanged.connect(self._on_media_position_changed)
        media.durationChanged.connect(timeline.set_duration)
        timeline.seekRequested.connect(media.set_position)
        
        pb.stopRequested.connect(media.stop)
        pb.playbackRateRequested.connect(media.set_playback_rate)
        pb.seekRelativeRequested.connect(lambda d: media.set_position(media.player.position() + d))
        pb.playPauseRequested.connect(media.toggle_play_pause)
        pb.nextPrevClipRequested.connect(self._navigate_clip)
        pb.nextPrevAnnotRequested.connect(self._navigate_annotation)
        
        # --- Right Panel ---
        tabs = self.right_panel.annot_mgmt.tabs
        table = self.right_panel.table
        
        # Head Management (Tabs)
        tabs.headAdded.connect(self._on_head_added)
        tabs.headRenamed.connect(self._on_head_renamed)
        tabs.headDeleted.connect(self._on_head_deleted)
        tabs.headSelected.connect(self._on_head_selected)
        
        # Label & Spotting Logic (From inside Tabs)
        tabs.spottingTriggered.connect(self._on_spotting_triggered)
        tabs.labelAddReq.connect(self._on_label_add_req)
        tabs.labelRenameReq.connect(self._on_label_rename_req)
        tabs.labelDeleteReq.connect(self._on_label_delete_req)
        
        # Table Logic
        table.annotationSelected.connect(lambda ms: media.set_position(ms))
        table.annotationDeleted.connect(self._on_delete_single_annotation)
        table.annotationModified.connect(self._on_annotation_modified)

    # --- Media Sync ---
    def _on_media_position_changed(self, ms):
        self.center_panel.timeline.set_position(ms)
        time_str = self._fmt_ms_full(ms)
        self.right_panel.annot_mgmt.tabs.update_current_time(time_str)

    # --- Head Management (Tab Operations) ---
    def _on_head_selected(self, head_name):
        self.current_head = head_name

    def _on_head_added(self, head_name):
        if any(h.lower() == head_name.lower() for h in self.model.label_definitions):
            self.main.show_temp_msg("Error", f"Head '{head_name}' already exists!", icon=QMessageBox.Icon.Warning)
            return
            
        definition = {"type": "single_label", "labels": []}
        
        # 1. Push Undo
        self.model.push_undo(CmdType.SCHEMA_ADD_CAT, head=head_name, definition=definition)
        
        # 2. Execute
        self.model.label_definitions[head_name] = definition
        self.model.is_data_dirty = True
        
        self._refresh_schema_ui()
        self.right_panel.annot_mgmt.tabs.set_current_head(head_name)
        self.main.show_temp_msg("Head Added", f"Created '{head_name}'")
        self.main.update_save_export_button_state() 

    def _on_head_renamed(self, old_name, new_name):
        if old_name == new_name: return
        
        if any(h.lower() == new_name.lower() for h in self.model.label_definitions):
            self.main.show_temp_msg("Error", "Name already exists!", icon=QMessageBox.Icon.Warning)
            return
            
        # 1. Push Undo
        self.model.push_undo(CmdType.SCHEMA_REN_CAT, old_name=old_name, new_name=new_name)
            
        # 2. Execute (Update Defs)
        self.model.label_definitions[new_name] = self.model.label_definitions.pop(old_name)
        
        # Execute (Update Events)
        count = 0
        for vid_path, events in self.model.localization_events.items():
            for evt in events:
                if evt.get('head') == old_name:
                    evt['head'] = new_name
                    count += 1
                    
        self.model.is_data_dirty = True
        self._refresh_schema_ui()
        self.right_panel.annot_mgmt.tabs.set_current_head(new_name)
        self._refresh_current_clip_events()
        self.main.show_temp_msg("Head Renamed", f"Updated {count} events.")
        self.main.update_save_export_button_state() 

    def _on_head_deleted(self, head_name):
        display_name = head_name.replace('_', ' ')
        res = QMessageBox.warning(
            self.main, "Delete Head", 
            f"Delete head '{display_name}'? ALL associated events will be deleted.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        if res != QMessageBox.StandardButton.Yes: return
        
        # 1. Capture Affected Data for Undo
        loc_affected = {}
        removed_count = 0
        for vid_path, events in self.model.localization_events.items():
            affected_evts = [copy.deepcopy(e) for e in events if e.get('head') == head_name]
            if affected_evts:
                loc_affected[vid_path] = affected_evts
                removed_count += len(affected_evts)
        
        definition = copy.deepcopy(self.model.label_definitions.get(head_name))
        
        # 2. Push Undo
        self.model.push_undo(
            CmdType.SCHEMA_DEL_CAT, 
            head=head_name, 
            definition=definition, 
            loc_affected_events=loc_affected
        )
        
        # 3. Execute
        if head_name in self.model.label_definitions:
            del self.model.label_definitions[head_name]
            
        for vid_path in self.model.localization_events:
            self.model.localization_events[vid_path] = [
                e for e in self.model.localization_events[vid_path] 
                if e.get('head') != head_name
            ]
            
        self.model.is_data_dirty = True
        self._refresh_schema_ui()
        self._refresh_current_clip_events()
        self.main.show_temp_msg("Head Deleted", f"Removed {removed_count} events.")
        self.main.update_save_export_button_state() 

    # --- Label Management ---
    def _on_label_add_req(self, head):
        """
        [修改] 暂停视频 -> 获取时间 -> 输入标签 -> 添加Schema & 打点 -> 恢复播放
        """
        # 1. 获取播放器状态并暂停
        player = self.center_panel.media_preview.player
        was_playing = (player.playbackState() == QMediaPlayer.PlaybackState.PlayingState)
        if was_playing:
            player.pause()
            
        current_pos = player.position()
        time_str = self._fmt_ms(current_pos)

        # 2. 弹出对话框
        text, ok = QInputDialog.getText(
            self.main, 
            "Add New Label & Spot", 
            f"Add new label to '{head}' and spot at {time_str}?"
        )
        
        if not ok or not text.strip():
            # 取消则恢复播放
            if was_playing: player.play()
            return
            
        label_name = text.strip()
        labels_list = self.model.label_definitions[head].get('labels', [])
        
        if any(l.lower() == label_name.lower() for l in labels_list):
            self.main.show_temp_msg("Error", "Label exists!", icon=QMessageBox.Icon.Warning)
            if was_playing: player.play()
            return
            
        # 3. 动作 1: 修改 Schema (添加标签)
        self.model.push_undo(CmdType.SCHEMA_ADD_LBL, head=head, label=label_name)
        labels_list.append(label_name)
        self.model.label_definitions[head]['labels'] = labels_list
        self.model.is_data_dirty = True
        
        # 4. 动作 2: 修改 Data (打点)
        if self.current_video_path:
            new_event = {
                "head": head,
                "label": label_name,
                "position_ms": current_pos
            }
            # 注意：Undo Stack 此时会有两个操作，按 Undo 两次才能完全撤销，符合直觉
            self.model.push_undo(CmdType.LOC_EVENT_ADD, video_path=self.current_video_path, event=new_event)
            
            if self.current_video_path not in self.model.localization_events:
                self.model.localization_events[self.current_video_path] = []
            self.model.localization_events[self.current_video_path].append(new_event)
        
        # 5. 刷新 UI
        self._refresh_schema_ui()
        self.right_panel.annot_mgmt.tabs.set_current_head(head) # 保持 Tab 选中
        self._display_events_for_item(self.current_video_path)
        self.populate_tree() 
        self.main.show_temp_msg("Added & Spotted", f"{head}: {label_name} at {time_str}")
        self.main.update_save_export_button_state()

        # 6. 恢复播放
        if was_playing:
            player.play()

    def _on_label_rename_req(self, head, old_label):
        new_label, ok = QInputDialog.getText(self.main, "Rename Label", f"Rename '{old_label}' to:", text=old_label)
        if not ok or not new_label.strip() or new_label == old_label: return
        new_label = new_label.strip()
        labels_list = self.model.label_definitions[head].get('labels', [])
        
        if any(l.lower() == new_label.lower() for l in labels_list if l != old_label):
             self.main.show_temp_msg("Error", "Label exists!", icon=QMessageBox.Icon.Warning); return
        
        # 1. Push Undo
        self.model.push_undo(CmdType.SCHEMA_REN_LBL, head=head, old_lbl=old_label, new_lbl=new_label)
             
        # 2. Execute
        index = labels_list.index(old_label)
        labels_list[index] = new_label
        
        count = 0
        for vid_path, events in self.model.localization_events.items():
            for evt in events:
                if evt.get('head') == head and evt.get('label') == old_label:
                    evt['label'] = new_label
                    count += 1
                    
        self.model.is_data_dirty = True
        self._refresh_schema_ui()
        self.right_panel.annot_mgmt.tabs.set_current_head(head)
        self._refresh_current_clip_events()
        self.main.update_save_export_button_state() 

    def _on_label_delete_req(self, head, label):
        res = QMessageBox.warning(
            self.main, "Delete Label",
            f"Delete label '{label}'? ALL associated events will be deleted.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        if res != QMessageBox.StandardButton.Yes: return
        
        # 1. Capture Affected Data
        loc_affected = {}
        removed_count = 0
        for vid_path, events in self.model.localization_events.items():
            aff = [copy.deepcopy(e) for e in events if e.get('head') == head and e.get('label') == label]
            if aff:
                loc_affected[vid_path] = aff
                removed_count += len(aff)
        
        # 2. Push Undo
        self.model.push_undo(
            CmdType.SCHEMA_DEL_LBL, 
            head=head, 
            label=label, 
            loc_affected_events=loc_affected
        )

        # 3. Execute
        labels_list = self.model.label_definitions[head].get('labels', [])
        if label in labels_list:
            labels_list.remove(label)
            
        for vid_path in self.model.localization_events:
            events = self.model.localization_events[vid_path]
            new_events = [e for e in events if not (e.get('head') == head and e.get('label') == label)]
            self.model.localization_events[vid_path] = new_events
            
        self.model.is_data_dirty = True
        self._refresh_schema_ui()
        self.right_panel.annot_mgmt.tabs.set_current_head(head)
        self._refresh_current_clip_events()
        self.main.update_save_export_button_state() 

    # --- Spotting (Data Creation) ---
    def _on_spotting_triggered(self, head, label):
        if not self.current_video_path:
            QMessageBox.warning(self.main, "Warning", "No video selected."); return
        pos_ms = self.center_panel.media_preview.player.position()
        
        new_event = {
            "head": head,
            "label": label,
            "position_ms": pos_ms
        }
        
        # 1. Push Undo
        self.model.push_undo(CmdType.LOC_EVENT_ADD, video_path=self.current_video_path, event=new_event)
        
        # 2. Execute
        if self.current_video_path not in self.model.localization_events:
            self.model.localization_events[self.current_video_path] = []
        self.model.localization_events[self.current_video_path].append(new_event)
        
        self.model.is_data_dirty = True
        self._display_events_for_item(self.current_video_path)
        self.populate_tree() 
        self.main.show_temp_msg("Event Created", f"{head}: {label}")
        self.main.update_save_export_button_state() 

    # --- Table Modification (New Logic) ---
    def _on_annotation_modified(self, old_event, new_event):
        events = self.model.localization_events.get(self.current_video_path, [])
        try:
            index = events.index(old_event)
        except ValueError:
            return 

        # 1. Push Undo
        self.model.push_undo(
            CmdType.LOC_EVENT_MOD, 
            video_path=self.current_video_path, 
            old_event=copy.deepcopy(old_event), 
            new_event=new_event
        )

        # 2. Execute
        new_head = new_event['head']
        new_label = new_event['label']
        schema_changed = False
        
        # Logic to auto-create schema if edited via Table (Optional but good UX)
        if new_head not in self.model.label_definitions:
            self.model.label_definitions[new_head] = {"type": "single_label", "labels": []}
            schema_changed = True
            
        if new_label and new_label != "???":
            labels_list = self.model.label_definitions[new_head]['labels']
            if not any(l.lower() == new_label.lower() for l in labels_list):
                labels_list.append(new_label)
                schema_changed = True
        
        events[index] = new_event
        self.model.is_data_dirty = True
        
        if schema_changed:
            self._refresh_schema_ui()
            self.right_panel.annot_mgmt.tabs.set_current_head(new_head)
            
        self._display_events_for_item(self.current_video_path)
        self.populate_tree()
        self.main.show_temp_msg("Event Updated", "Modified")
        self.main.update_save_export_button_state() 

    def _on_delete_single_annotation(self, item_data):
        events = self.model.localization_events.get(self.current_video_path, [])
        if item_data not in events: return

        reply = QMessageBox.question(
            self.main, "Delete Event", "Delete this event?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes: return

        # 1. Push Undo
        self.model.push_undo(CmdType.LOC_EVENT_DEL, video_path=self.current_video_path, event=copy.deepcopy(item_data))

        # 2. Execute
        events.remove(item_data)
        self.model.is_data_dirty = True
        self._display_events_for_item(self.current_video_path)
        self.populate_tree()
        self.main.update_save_export_button_state() 

    # --- Helper Refresh Methods ---
    def _refresh_schema_ui(self):
        self.right_panel.table.set_schema(self.model.label_definitions)
        self.right_panel.annot_mgmt.update_schema(self.model.label_definitions)

    def _refresh_current_clip_events(self):
        if self.current_video_path:
            self._display_events_for_item(self.current_video_path)

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

    # --- Clear All & Remove Video Logic ---

    def _on_clear_all_clicked(self):
        """Removes all videos, clears player, and clears right panel including Schema."""
        if not self.model.action_item_data:
            return

        res = QMessageBox.question(
            self.main, "Clear All", 
            "Are you sure you want to remove ALL videos and clear the workspace?\n"
            "This will remove all videos and RESET the label schema.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res != QMessageBox.StandardButton.Yes:
            return

        # 1. Clear Data (Includes Schema/Label Definitions)
        self.model.action_item_data = []
        self.model.action_path_to_name = {}
        self.model.localization_events = {}
        self.model.label_definitions = {} # 清空 Schema
        self.model.is_data_dirty = False 
        self.current_video_path = None
        self.current_head = None 
        
        # Undo stack should probably be cleared on full reset
        self.model.undo_stack.clear()
        self.model.redo_stack.clear()

        # 2. Clear Player
        self.center_panel.media_preview.stop()
        self.center_panel.media_preview.player.setSource(QUrl())
        self.center_panel.media_preview.video_widget.update()
        self.center_panel.timeline.set_markers([])

        # 3. Clear Tree
        self.left_panel.clip_tree.clear()
        
        # 4. Clear Right Panel (Top & Bottom)
        self._refresh_schema_ui() 
        self.right_panel.table.set_data([]) 
        
        self.main.show_temp_msg("Cleared", "Workspace reset.")
        self.main.update_save_export_button_state() 

    def _on_tree_context_menu(self, pos):
        item = self.left_panel.clip_tree.itemAt(pos)
        if not item: return

        path = item.data(0, Qt.ItemDataRole.UserRole)
        name = item.text(0)

        menu = QMenu(self.left_panel.clip_tree)
        remove_action = menu.addAction(f"Remove '{name}'")
        
        action = menu.exec(self.left_panel.clip_tree.mapToGlobal(pos))
        
        if action == remove_action:
            self._remove_single_video(path)

    def _remove_single_video(self, path):
        # 1. Remove from Model
        self.model.action_item_data = [d for d in self.model.action_item_data if d['path'] != path]
        if path in self.model.action_path_to_name:
            del self.model.action_path_to_name[path]
        if path in self.model.localization_events:
            del self.model.localization_events[path]
            
        self.model.is_data_dirty = True

        # 2. If removing the CURRENTLY playing video
        if self.current_video_path == path:
            self.current_video_path = None
            self.center_panel.media_preview.stop()
            self.center_panel.media_preview.player.setSource(QUrl())
            self.right_panel.table.set_data([])
            self.center_panel.timeline.set_markers([])

        # 3. Refresh Tree
        self.populate_tree()
        self.main.show_temp_msg("Removed", "Video removed from list.")
        self.main.update_save_export_button_state() 

    # ----------------------------------------------

    def populate_tree(self):
        """
        Refreshes the clip tree.
        Blocks signals throughout the entire process to prevent
        accidental triggering of on_clip_selected (which resets video playback).
        """
        previous_path = self.current_video_path
        
        # 1. Start blocking signals BEFORE clearing
        self.left_panel.clip_tree.blockSignals(True) 
        
        self.left_panel.clip_tree.clear()
        
        sorted_list = sorted(self.model.action_item_data, key=lambda d: natural_sort_key(d.get('name', '')))
        item_to_restore = None
        first_item = None
        
        for i, data in enumerate(sorted_list):
            name = data['name']
            path = data['path']
            item = QTreeWidgetItem(self.left_panel.clip_tree, [name])
            item.setData(0, Qt.ItemDataRole.UserRole, path)
            events = self.model.localization_events.get(path, [])
            item.setIcon(0, self.main.done_icon if events else self.main.empty_icon)
            
            if i == 0: first_item = item
            if path == previous_path: item_to_restore = item
        
        self.left_panel.project_controls.set_project_loaded_state(True)
        self._refresh_schema_ui()
        
        if self.current_head:
             self.right_panel.annot_mgmt.tabs.set_current_head(self.current_head)
        
        self._apply_clip_filter(self.left_panel.filter_combo.currentIndex())
        
        # 2. Restore Selection Logic
        if item_to_restore:
            self.left_panel.clip_tree.setCurrentItem(item_to_restore)
        elif previous_path is None and first_item:
            self.left_panel.clip_tree.setCurrentItem(first_item)
        
        # 3. Finally Unblock Signals
        self.left_panel.clip_tree.blockSignals(False)

        # 4. Handle the "New Load" case manually
        if not item_to_restore and previous_path is None and first_item:
             self.on_clip_selected(first_item, None)

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
        if not current: 
            self.current_video_path = None
            return
        path = current.data(0, Qt.ItemDataRole.UserRole)
        
        if path == self.current_video_path: 
            return
            
        if path and os.path.exists(path):
            self.current_video_path = path
            self.center_panel.media_preview.load_video(path)
            self._display_events_for_item(path)
        else:
            if path: QMessageBox.warning(self.main, "Error", f"File not found: {path}")

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
        self.main.router.loc_fm.overwrite_json()

    def _on_export_clicked(self):
        self.main.router.loc_fm.export_json()

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

    def _fmt_ms(self, ms):
        s = ms // 1000
        return f"{s//60:02}:{s%60:02}.{ms%1000:03}"
    
    def _fmt_ms_full(self, ms):
        s = ms // 1000
        m = s // 60
        h = m // 60
        return f"{h:02}:{m%60:02}:{s%60:02}.{ms%1000:03}"
