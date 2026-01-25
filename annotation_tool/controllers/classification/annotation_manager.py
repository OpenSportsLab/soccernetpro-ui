import copy
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QTimer
from models import CmdType

class AnnotationManager:
    def __init__(self, main_window):
        self.main = main_window
        self.model = main_window.model
        self.ui = main_window.ui

    def save_manual_annotation(self):
        path = self.main.get_current_action_path()
        if not path: return
        
        raw = self.ui.right_panel.get_annotation()
        cleaned = {k: v for k, v in raw.items() if v}
        if not cleaned: cleaned = None
        
        old = copy.deepcopy(self.model.manual_annotations.get(path))
        self.model.push_undo(CmdType.ANNOTATION_CONFIRM, path=path, old_data=old, new_data=cleaned)
        
        if cleaned:
            self.model.manual_annotations[path] = cleaned
            self.main.show_temp_msg("Saved", "Annotation saved.", 1000)
        else:
            if path in self.model.manual_annotations: del self.model.manual_annotations[path]
            self.main.show_temp_msg("Cleared", "Annotation cleared.", 1000)
            
        self.main.update_action_item_status(path)
        self.main.update_save_export_button_state()
        
        tree = self.ui.left_panel.action_tree
        curr = tree.currentItem()
        nxt = tree.itemBelow(curr)
        if nxt:
            QTimer.singleShot(500, lambda: [tree.setCurrentItem(nxt), tree.scrollToItem(nxt)])

    def clear_current_manual_annotation(self):
        path = self.main.get_current_action_path()
        if not path: return
        
        old = copy.deepcopy(self.model.manual_annotations.get(path))
        if old:
            self.model.push_undo(CmdType.ANNOTATION_CONFIRM, path=path, old_data=old, new_data=None)
            if path in self.model.manual_annotations: del self.model.manual_annotations[path]
            self.main.update_action_item_status(path)
            self.main.update_save_export_button_state()
            self.main.show_temp_msg("Cleared", "Selection cleared.")
        self.ui.right_panel.clear_selection()

    def display_manual_annotation(self, path):
        data = self.model.manual_annotations.get(path, {})
        self.ui.right_panel.set_annotation(data)

    def handle_ui_selection_change(self, head, new_val):
        if self.main.history_manager._is_undoing_redoing: 
            return

        path = self.main.get_current_action_path()
        if not path: return
        
        old_val = self.model.manual_annotations.get(path, {}).get(head)
        for cmd in reversed(self.model.undo_stack):
            if cmd['type'] == CmdType.UI_CHANGE and cmd['path'] == path and cmd['head'] == head:
                old_val = cmd['new_val']; break
                
        self.model.push_undo(CmdType.UI_CHANGE, path=path, head=head, old_val=old_val, new_val=new_val)

    def handle_add_label_head(self, name):
        clean = name.strip().replace(' ', '_').lower()
        if not clean or clean in self.model.label_definitions: return
        
        msg = QMessageBox(self.main); msg.setText(f"Type for '{name}'?")
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
        self.main.setup_dynamic_ui()

    def handle_remove_label_head(self, head):
        if head not in self.model.label_definitions: return
        if QMessageBox.question(self.main, "Remove", f"Remove '{head}'?") == QMessageBox.StandardButton.No: return
        
        affected = {}
        for k, v in self.model.manual_annotations.items():
            if head in v: affected[k] = copy.deepcopy(v[head])
            
        self.model.push_undo(CmdType.SCHEMA_DEL_CAT, head=head, definition=copy.deepcopy(self.model.label_definitions[head]), affected_data=affected)
        
        del self.model.label_definitions[head]
        for k in affected: 
            del self.model.manual_annotations[k][head]
            if not self.model.manual_annotations[k]: del self.model.manual_annotations[k]
            self.main.update_action_item_status(k)
            
        self.main.setup_dynamic_ui()
        self.display_manual_annotation(self.main.get_current_action_path())

    def add_custom_type(self, head):
        group = self.ui.right_panel.label_groups.get(head)
        txt = group.input_field.text().strip()
        if not txt: return
        
        labels = self.model.label_definitions[head]['labels']
        if any(l.lower() == txt.lower() for l in labels):
            self.main.show_temp_msg("Duplicate", "Label exists.", icon=QMessageBox.Icon.Warning)
            return
            
        self.model.push_undo(CmdType.SCHEMA_ADD_LBL, head=head, label=txt)
        labels.append(txt); labels.sort()
        
        # Update UI directly
        from ui.classification.widgets import DynamicSingleLabelGroup
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
            
        from ui.classification.widgets import DynamicSingleLabelGroup
        group = self.ui.right_panel.label_groups.get(head)
        if isinstance(group, DynamicSingleLabelGroup): group.update_radios(defn['labels'])
        else: group.update_checkboxes(defn['labels'])
        self.display_manual_annotation(self.main.get_current_action_path())