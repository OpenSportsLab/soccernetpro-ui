import copy
from models import CmdType
from ui.widgets import DynamicSingleLabelGroup, DynamicMultiLabelGroup

class HistoryManager:
    """
    通用历史管理器：负责处理 Undo/Redo 栈的操作。
    目前包含 Classification 的具体恢复逻辑。
    """
    def __init__(self, main_window):
        self.main = main_window
        self.model = main_window.model
        self.ui = main_window.ui
        self._is_undoing_redoing = False

    def perform_undo(self):
        if not self.model.undo_stack: return
        self._is_undoing_redoing = True
        
        cmd = self.model.undo_stack.pop()
        self.model.redo_stack.append(cmd)
        
        self._apply_state_change(cmd, is_undo=True)
        
        self.main.update_save_export_button_state()
        self._is_undoing_redoing = False

    def perform_redo(self):
        if not self.model.redo_stack: return
        self._is_undoing_redoing = True
        
        cmd = self.model.redo_stack.pop()
        self.model.undo_stack.append(cmd)
        
        self._apply_state_change(cmd, is_undo=False)
        
        self.main.update_save_export_button_state()
        self._is_undoing_redoing = False

    def _apply_state_change(self, cmd, is_undo):
        ctype = cmd['type']
        
        # --- Classification Related Logic ---
        if ctype == CmdType.ANNOTATION_CONFIRM:
            path = cmd['path']
            data = cmd['old_data'] if is_undo else cmd['new_data']
            if data is None:
                if path in self.model.manual_annotations: del self.model.manual_annotations[path]
            else: self.model.manual_annotations[path] = copy.deepcopy(data)
            self.main.refresh_ui_after_undo_redo(path)
            
        elif ctype == CmdType.UI_CHANGE:
            path = cmd['path']
            if self.main.get_current_action_path() == path:
                val = cmd['old_val'] if is_undo else cmd['new_val']
                grp = self.ui.right_panel.label_groups.get(cmd['head'])
                if grp:
                    if isinstance(grp, DynamicSingleLabelGroup): grp.set_checked_label(val)
                    else: grp.set_checked_labels(val)
                
        elif ctype == CmdType.SCHEMA_ADD_CAT:
            head = cmd['head']
            if is_undo:
                del self.model.label_definitions[head]
            else:
                self.model.label_definitions[head] = cmd['definition']
            self.main.setup_dynamic_ui()
            self.main.refresh_ui_after_undo_redo(self.main.get_current_action_path())
            
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
            self.main.setup_dynamic_ui()
            self.main.refresh_ui_after_undo_redo(self.main.get_current_action_path())
            
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
            self.main.refresh_ui_after_undo_redo(self.main.get_current_action_path())