import copy
from models import CmdType
from ui.classification.event_editor import DynamicSingleLabelGroup, DynamicMultiLabelGroup

class HistoryManager:
    """
    General History Manager: Responsible for handling operations on the Undo/Redo stack.
    Supports both Classification and Localization modes.
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

    def _refresh_active_view(self):
        """
        Refresh: Depending on whether the current interface is Classification or Localization, invoke the corresponding refresh logic.
        """
        current_widget = self.main.ui.stack_layout.currentWidget()
        
        # 1. Localization Mode
        if current_widget == self.main.ui.localization_ui:
            # Refresh Schema (Tabs)
            self.main.loc_manager._refresh_schema_ui()
            # Refresh Events (Table & Timeline)
            self.main.loc_manager._refresh_current_clip_events()
            # Refresh left side
            self.main.loc_manager.populate_tree()
            
        # 2. Classification Mode
        else:
            # Rebuild the right-side dynamic control
            self.main.setup_dynamic_ui()
            # Refresh the left and annotation status
            self.main.refresh_ui_after_undo_redo(self.main.get_current_action_path())

    def _apply_state_change(self, cmd, is_undo):
        ctype = cmd['type']
        
        # =========================================================
        # 1. Classification Specific
        # =========================================================
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


        # =========================================================
        # 2. Localization Specific (Events)
        # =========================================================
        elif ctype == CmdType.LOC_EVENT_ADD:
            # Add: Undo -> Remove; Redo -> Add
            path = cmd['video_path']
            evt = cmd['event']
            events = self.model.localization_events.get(path, [])
            
            if is_undo:
                if evt in events: events.remove(evt)
            else:
                events.append(evt)
            
            self.model.localization_events[path] = events
            self._refresh_active_view()
            
        elif ctype == CmdType.LOC_EVENT_DEL:
            # Del: Undo -> Add back; Redo -> Remove
            path = cmd['video_path']
            evt = cmd['event']
            events = self.model.localization_events.get(path, [])
            
            if is_undo:
                events.append(evt)
                if path not in self.model.localization_events: self.model.localization_events[path] = events
            else:
                if evt in events: events.remove(evt)
            
            self._refresh_active_view()
            
        elif ctype == CmdType.LOC_EVENT_MOD:
            # Mod: Swap old/new
            path = cmd['video_path']
            old_e = cmd['old_event']
            new_e = cmd['new_event']
            events = self.model.localization_events.get(path, [])
            
            target = new_e if is_undo else old_e
            replacement = old_e if is_undo else new_e
            
            try:
                idx = events.index(target)
                events[idx] = replacement
            except ValueError:
                pass # Event not found, possibly concurrent edit?
            
            self._refresh_active_view()

        # =========================================================
        # 3. Schema Changes (Shared but handled differently)
        # =========================================================
        elif ctype == CmdType.SCHEMA_ADD_CAT:
            head = cmd['head']
            if is_undo:
                if head in self.model.label_definitions:
                    del self.model.label_definitions[head]
            else:
                self.model.label_definitions[head] = cmd['definition']
            self._refresh_active_view()
            
        elif ctype == CmdType.SCHEMA_DEL_CAT:
            head = cmd['head']
            if is_undo:
                # Restore Definition
                self.model.label_definitions[head] = cmd['definition']
                
                # Restore Classification Data
                if 'affected_data' in cmd:
                    for k, v in cmd['affected_data'].items():
                        if k not in self.model.manual_annotations: self.model.manual_annotations[k] = {}
                        self.model.manual_annotations[k][head] = v
                
                # Restore Localization Data
                if 'loc_affected_events' in cmd:
                    for vid, events_list in cmd['loc_affected_events'].items():
                        if vid not in self.model.localization_events: self.model.localization_events[vid] = []
                        self.model.localization_events[vid].extend(events_list)
            else:
                # Delete Definition
                if head in self.model.label_definitions:
                    del self.model.label_definitions[head]
                
                # Delete Classification Data
                if 'affected_data' in cmd:
                    for k in cmd['affected_data']:
                        if head in self.model.manual_annotations.get(k, {}): 
                            del self.model.manual_annotations[k][head]
                            
                # Delete Localization Data
                if 'loc_affected_events' in cmd:
                    for vid in self.model.localization_events:
                        self.model.localization_events[vid] = [
                            e for e in self.model.localization_events[vid] 
                            if e.get('head') != head
                        ]

            self._refresh_active_view()

        elif ctype == CmdType.SCHEMA_REN_CAT:
            old_n = cmd['old_name']
            new_n = cmd['new_name']
            
            src = new_n if is_undo else old_n
            dst = old_n if is_undo else new_n
            
            # 1. Rename Definition Key
            if src in self.model.label_definitions:
                self.model.label_definitions[dst] = self.model.label_definitions.pop(src)
            
            # 2. Update Classification Annotations
            # (Loop through all annotations and rename keys)
            for anno in self.model.manual_annotations.values():
                if src in anno:
                    anno[dst] = anno.pop(src)
            
            # 3. Update Localization Events
            for events in self.model.localization_events.values():
                for evt in events:
                    if evt.get('head') == src:
                        evt['head'] = dst
            
            self._refresh_active_view()
            
        elif ctype == CmdType.SCHEMA_ADD_LBL:
            head = cmd['head']; lbl = cmd['label']
            if head in self.model.label_definitions:
                lst = self.model.label_definitions[head]['labels']
                if is_undo:
                    if lbl in lst: lst.remove(lbl)
                else:
                    if lbl not in lst: lst.append(lbl); lst.sort()
            
            # Refresh Specific UI Component if possible, else full refresh
            # Localization UI needs full refresh to update Tab buttons
            self._refresh_active_view()
            
        elif ctype == CmdType.SCHEMA_DEL_LBL:
            head = cmd['head']; lbl = cmd['label']
            if head in self.model.label_definitions:
                lst = self.model.label_definitions[head]['labels']
                
                if is_undo:
                    if lbl not in lst: lst.append(lbl); lst.sort()
                    # Restore Classif
                    if 'affected_data' in cmd:
                        for k, v in cmd['affected_data'].items():
                            if k not in self.model.manual_annotations: self.model.manual_annotations[k] = {}
                            if self.model.label_definitions[head]['type'] == 'single_label':
                                self.model.manual_annotations[k][head] = v
                            else:
                                cur = self.model.manual_annotations[k].get(head, [])
                                if lbl not in cur: cur.append(lbl)
                                self.model.manual_annotations[k][head] = cur
                                
                    # Restore Loc
                    if 'loc_affected_events' in cmd:
                        for vid, events_list in cmd['loc_affected_events'].items():
                            if vid not in self.model.localization_events: self.model.localization_events[vid] = []
                            self.model.localization_events[vid].extend(events_list)
                            
                else:
                    if lbl in lst: lst.remove(lbl)
                    # Delete Classif
                    if 'affected_data' in cmd:
                        for k in cmd['affected_data']:
                            anno = self.model.manual_annotations.get(k, {})
                            if self.model.label_definitions[head]['type'] == 'single_label':
                                if anno.get(head) == lbl: anno[head] = None
                            else:
                                if lbl in anno.get(head, []): anno[head].remove(lbl)
                    
                    # Delete Loc
                    if 'loc_affected_events' in cmd:
                        for vid in self.model.localization_events:
                            self.model.localization_events[vid] = [
                                e for e in self.model.localization_events[vid]
                                if not (e.get('head') == head and e.get('label') == lbl)
                            ]

            self._refresh_active_view()
            
        elif ctype == CmdType.SCHEMA_REN_LBL:
            head = cmd['head']
            old_l = cmd['old_lbl']
            new_l = cmd['new_lbl']
            
            src = new_l if is_undo else old_l
            dst = old_l if is_undo else new_l
            
            if head in self.model.label_definitions:
                lst = self.model.label_definitions[head]['labels']
                if src in lst:
                    idx = lst.index(src)
                    lst[idx] = dst
                    
            # Rename in Classif
            for anno in self.model.manual_annotations.values():
                val = anno.get(head)
                if isinstance(val, str) and val == src:
                    anno[head] = dst
                elif isinstance(val, list) and src in val:
                    val[val.index(src)] = dst
                    
            # Rename in Loc
            for events in self.model.localization_events.values():
                for evt in events:
                    if evt.get('head') == head and evt.get('label') == src:
                        evt['label'] = dst
                        
            self._refresh_active_view()
