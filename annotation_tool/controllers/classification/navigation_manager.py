import os
from PyQt6.QtWidgets import QMessageBox, QFileDialog
from PyQt6.QtCore import Qt
from utils import SUPPORTED_EXTENSIONS

class NavigationManager:
    """
    Handles file navigation (action tree), adding videos, and playback flow 
    for the Classification mode.
    """
    def __init__(self, main_window):
        self.main = main_window
        self.model = main_window.model
        self.ui = main_window.ui

    def add_items_via_dialog(self):
        """
        Allows user to add video/image files to the project.
        """
        if not self.model.json_loaded:
            QMessageBox.warning(self.main, "Warning", "Please create or load a project first.")
            return

        filters = "Media Files (*.mp4 *.avi *.mov *.mkv *.jpg *.jpeg *.png *.bmp);;All Files (*)"
        start_dir = self.model.current_working_directory or ""
        
        files, _ = QFileDialog.getOpenFileNames(self.main, "Select Data to Add", start_dir, filters)
        if not files: return
        
        if not self.model.current_working_directory:
            self.model.current_working_directory = os.path.dirname(files[0])

        added_count = 0
        for file_path in files:
            # Duplicate check
            if any(d['path'] == file_path for d in self.model.action_item_data):
                continue
            
            name = os.path.basename(file_path)
            self.model.action_item_data.append({'name': name, 'path': file_path, 'source_files': [file_path]})
            # Create mapping for quick lookup
            item = self.ui.classification_ui.left_panel.add_tree_item(name, file_path, [file_path])
            self.model.action_item_map[file_path] = item
            added_count += 1
            
        if added_count > 0:
            self.model.is_data_dirty = True
            self.apply_action_filter()
            self.main.show_temp_msg("Added", f"Added {added_count} items.")

    def remove_single_action_item(self, item):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        
        # 1. Remove from Data
        self.model.action_item_data = [d for d in self.model.action_item_data if d['path'] != path]
        
        if path in self.model.action_item_map:
            del self.model.action_item_map[path]
            
        # 2. Remove Annotation if exists
        if path in self.model.manual_annotations:
            del self.model.manual_annotations[path]
            
        # 3. Remove from UI
        index = self.ui.classification_ui.left_panel.tree.indexOfTopLevelItem(item)
        self.ui.classification_ui.left_panel.tree.takeTopLevelItem(index)
        
        self.model.is_data_dirty = True
        self.main.show_temp_msg("Removed", "Item removed.")
        self.main.update_save_export_button_state()

    def on_item_selected(self, current, previous):
        """
        Called when the user clicks a different item in the left tree.
        Loads the video and forces playback.
        """
        if not current: return
        
        path = current.data(0, Qt.ItemDataRole.UserRole)
        
        # Update Right Panel (Annotations)
        self.main.annot_manager.display_manual_annotation(path)
        self.ui.classification_ui.right_panel.manual_box.setEnabled(True)
        
        
        # Update Center Panel (Video)
        self.ui.classification_ui.center_panel.show_single_view(path)
        
        # [Fix] Force play when switching clips
        # Use QTimer with 0ms to ensure the event loop processes the load before playing
        self.ui.classification_ui.center_panel.single_view_widget.player.play()
        
    def play_video(self):
        """Toggle Play/Pause"""
        self.ui.classification_ui.center_panel.toggle_play_pause()

    def show_all_views(self):
        curr = self.ui.classification_ui.left_panel.tree.currentItem()
        if not curr or curr.childCount() == 0: return
        paths = [curr.child(i).data(0, Qt.ItemDataRole.UserRole) for i in range(curr.childCount())]
        self.ui.classification_ui.center_panel.show_all_views([p for p in paths if p.lower().endswith(SUPPORTED_EXTENSIONS[:3])])

    def apply_action_filter(self):
        """Filters the tree items based on Done/Not Done status."""
        idx = self.ui.classification_ui.left_panel.filter_combo.currentIndex()
        root = self.ui.classification_ui.left_panel.tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            path = item.data(0, Qt.ItemDataRole.UserRole)
            is_done = (path in self.model.manual_annotations and bool(self.model.manual_annotations[path]))
            
            should_hide = False
            if idx == self.main.FILTER_DONE and not is_done: should_hide = True
            elif idx == self.main.FILTER_NOT_DONE and is_done: should_hide = True
            
            item.setHidden(should_hide)

    def nav_prev_action(self): self._nav_tree(step=-1, level='top')
    def nav_next_action(self): self._nav_tree(step=1, level='top')
    def nav_prev_clip(self): self._nav_tree(step=-1, level='child')
    def nav_next_clip(self): self._nav_tree(step=1, level='child')
    
    def _nav_tree(self, step, level):
        tree = self.ui.classification_ui.left_panel.tree
        curr = tree.currentItem()
        if not curr: return
        
        if level == 'top':
            # Navigate Top Level Items
            item = curr if curr.parent() is None else curr.parent()
            idx = tree.indexOfTopLevelItem(item)
            new_idx = idx + step
            
            # Find next visible item (respecting filter)
            while 0 <= new_idx < tree.topLevelItemCount():
                nxt = tree.topLevelItem(new_idx)
                if not nxt.isHidden():
                    tree.setCurrentItem(nxt); tree.scrollToItem(nxt)
                    break
                new_idx += step
        else:
            # Navigate Children (if applicable)
            parent = curr.parent()
            if not parent:
                # If currently on top level, try to go to child
                if step == 1 and curr.childCount() > 0:
                    nxt = curr.child(0)
                    tree.setCurrentItem(nxt); tree.scrollToItem(nxt)
            else:
                idx = parent.indexOfChild(curr)
                new_idx = idx + step
                if 0 <= new_idx < parent.childCount():
                    nxt = parent.child(new_idx)
                    tree.setCurrentItem(nxt); tree.scrollToItem(nxt)