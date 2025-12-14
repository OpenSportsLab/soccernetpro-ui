from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import Qt
from utils import SUPPORTED_EXTENSIONS

class NavigationManager:
    def __init__(self, main_window):
        self.main = main_window
        self.model = main_window.model
        self.ui = main_window.ui

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
        if path: 
            self.main.annot_manager.display_manual_annotation(path)

    def remove_single_action_item(self, item):
        if not item: return
        target = item if item.parent() is None else item.parent()
        path = target.data(0, Qt.ItemDataRole.UserRole)
        name = target.text(0)
        
        reply = QMessageBox.question(self.main, 'Remove Item', f"Remove '{name}'? Annotations will be discarded.", 
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
            self.main.update_save_export_button_state()
            if self.ui.left_panel.action_tree.topLevelItemCount() == 0:
                self.ui.center_panel.show_single_view(None)
                self.ui.right_panel.manual_box.setEnabled(False)

    def apply_action_filter(self):
        curr = self.ui.left_panel.filter_combo.currentIndex()
        for path, item in self.model.action_item_map.items():
            is_done = (path in self.model.manual_annotations and bool(self.model.manual_annotations[path]))
            if curr == self.main.FILTER_ALL: item.setHidden(False)
            elif curr == self.main.FILTER_DONE: item.setHidden(not is_done)
            elif curr == self.main.FILTER_NOT_DONE: item.setHidden(is_done)

    def play_video(self): 
        self.ui.center_panel.toggle_play_pause()

    def show_all_views(self):
        curr = self.ui.left_panel.action_tree.currentItem()
        if not curr: return
        if curr.parent(): curr = curr.parent()
        paths = [curr.child(i).data(0, Qt.ItemDataRole.UserRole) for i in range(curr.childCount())]
        self.ui.center_panel.show_all_views([p for p in paths if p.lower().endswith(SUPPORTED_EXTENSIONS[:3])])

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