import os
from PyQt6.QtWidgets import QMessageBox, QFileDialog
from PyQt6.QtCore import Qt, QModelIndex, QTimer
# [Ref] Import from the correct models location
from models.project_tree import ProjectTreeModel
from utils import SUPPORTED_EXTENSIONS

class NavigationManager:
    """
    Handles file navigation (action tree), adding videos, and playback flow 
    for the Classification mode.
    Refactored for QTreeView (MV).
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
            
            # [MV Fix] Add to Model directly
            item = self.main.tree_model.add_entry(name, file_path, [file_path])
            self.model.action_item_map[file_path] = item
            added_count += 1
            
        if added_count > 0:
            self.model.is_data_dirty = True
            self.apply_action_filter()
            self.main.show_temp_msg("Added", f"Added {added_count} items.")

    def remove_single_action_item(self, index: QModelIndex):
        """
        Removes an item given its QModelIndex.
        """
        path = index.data(ProjectTreeModel.FilePathRole)
        
        # 1. Remove from Data
        self.model.action_item_data = [d for d in self.model.action_item_data if d['path'] != path]
        
        if path in self.model.action_item_map:
            del self.model.action_item_map[path]
            
        # 2. Remove Annotation if exists
        if path in self.model.manual_annotations:
            del self.model.manual_annotations[path]
            
        # 3. Remove from UI (Model)
        self.main.tree_model.removeRow(index.row(), index.parent())
        
        self.model.is_data_dirty = True
        self.main.show_temp_msg("Removed", "Item removed.")
        self.main.update_save_export_button_state()

    def on_item_selected(self, current, previous):
        """
        Called when the user clicks a different item in the left tree.
        Loads the video and forces playback.
        """
        if not current.isValid(): return
        
        path = current.data(ProjectTreeModel.FilePathRole)
        
        # Update Right Panel (Annotations)
        self.main.annot_manager.display_manual_annotation(path)
        self.ui.classification_ui.right_panel.manual_box.setEnabled(True)
        
        # [FIX] Get player instance
        player = self.ui.classification_ui.center_panel.single_view_widget.player
        
        # [FIX] Explicitly stop the player before loading a new source.
        # This helps reset the video pipeline and prevents black screens on some systems.
        player.stop()
        
        # Update Center Panel (Video) - This loads the new source
        self.ui.classification_ui.center_panel.show_single_view(path)
        
        # [FIX] Force play with increased delay (150ms).
        # 150ms-200ms is a safer buffer for PyQt6 QMediaPlayer.
        QTimer.singleShot(150, player.play)
        
    def play_video(self):
        """Toggle Play/Pause"""
        self.ui.classification_ui.center_panel.toggle_play_pause()

    def show_all_views(self):
        # [MV] Handle Multi-View
        tree_view = self.ui.classification_ui.left_panel.tree
        curr_idx = tree_view.currentIndex()
        if not curr_idx.isValid(): return
        
        # Check if item has children rows
        model = self.main.tree_model
        if model.rowCount(curr_idx) == 0: return
        
        paths = []
        for i in range(model.rowCount(curr_idx)):
            child_idx = model.index(i, 0, curr_idx)
            paths.append(child_idx.data(ProjectTreeModel.FilePathRole))
            
        self.ui.classification_ui.center_panel.show_all_views([p for p in paths if p.lower().endswith(SUPPORTED_EXTENSIONS[:3])])

    def apply_action_filter(self):
        """Filters the tree items based on Done/Not Done status using setRowHidden."""
        idx = self.ui.classification_ui.left_panel.filter_combo.currentIndex()
        tree_view = self.ui.classification_ui.left_panel.tree
        model = self.main.tree_model
        
        root = model.invisibleRootItem()
        for i in range(root.rowCount()):
            item = root.child(i)
            # We access data via the item (QStandardItem) or index
            path = item.data(ProjectTreeModel.FilePathRole)
            is_done = (path in self.model.manual_annotations and bool(self.model.manual_annotations[path]))
            
            should_hide = False
            if idx == self.main.FILTER_DONE and not is_done: should_hide = True
            elif idx == self.main.FILTER_NOT_DONE and is_done: should_hide = True
            
            tree_view.setRowHidden(i, QModelIndex(), should_hide)

    def nav_prev_action(self): self._nav_tree(step=-1, level='top')
    def nav_next_action(self): self._nav_tree(step=1, level='top')
    def nav_prev_clip(self): self._nav_tree(step=-1, level='child')
    def nav_next_clip(self): self._nav_tree(step=1, level='child')
    
    def _nav_tree(self, step, level):
        tree = self.ui.classification_ui.left_panel.tree
        curr = tree.currentIndex()
        if not curr.isValid(): return
        
        model = self.main.tree_model
        
        if level == 'top':
            # Navigate Top Level Items (Siblings)
            # If current is a child, get parent first
            if curr.parent().isValid():
                curr = curr.parent()
                
            new_row = curr.row() + step
            
            # Simple bounds check, logic can be improved to skip hidden items
            if 0 <= new_row < model.rowCount(QModelIndex()):
                # Check visibility (filter)
                while 0 <= new_row < model.rowCount(QModelIndex()):
                    if not tree.isRowHidden(new_row, QModelIndex()):
                        new_idx = model.index(new_row, 0, QModelIndex())
                        tree.setCurrentIndex(new_idx)
                        tree.scrollTo(new_idx)
                        break
                    new_row += step
        else:
            # Navigate Children
            parent = curr.parent()
            if not parent.isValid():
                # Currently on top, go to child 0 if step 1
                if step == 1 and model.rowCount(curr) > 0:
                    nxt = model.index(0, 0, curr)
                    tree.setCurrentIndex(nxt); tree.scrollTo(nxt)
            else:
                # Currently on child
                new_row = curr.row() + step
                if 0 <= new_row < model.rowCount(parent):
                    nxt = model.index(new_row, 0, parent)
                    tree.setCurrentIndex(nxt); tree.scrollTo(nxt)
