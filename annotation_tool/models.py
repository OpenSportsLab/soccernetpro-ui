import os
import copy
from enum import Enum, auto

class CmdType(Enum):
    # --- Classification Commands ---
    ANNOTATION_CONFIRM = auto()  # Confirming data to storage
    UI_CHANGE = auto()           # Fine-grained UI toggle (radio/checkbox)
    
    # --- Shared / Schema Commands (Used by both) ---
    SCHEMA_ADD_CAT = auto()      # Add Category (Head)
    SCHEMA_DEL_CAT = auto()      # Delete Category (Head)
    SCHEMA_REN_CAT = auto()      # [NEW] Rename Category (Head)
    
    SCHEMA_ADD_LBL = auto()      # Add Label option
    SCHEMA_DEL_LBL = auto()      # Delete Label option
    SCHEMA_REN_LBL = auto()      # [NEW] Rename Label option
    
    # --- Localization Commands ---
    LOC_EVENT_ADD = auto()       
    LOC_EVENT_DEL = auto()
    LOC_EVENT_MOD = auto()

class AppStateModel:
    """
    Manages the application state, data storage, and undo/redo stacks.
    Does NOT interact with UI widgets directly.
    """
    def __init__(self):
        # --- Project Metadata ---
        self.current_working_directory = None
        self.current_json_path = None
        self.json_loaded = False
        self.is_data_dirty = False
        self.project_description = "" # 防止 Classification 加载报错
        self.current_task_name = "Untitled Task"
        self.modalities = ["video"]

        # --- Schema / Labels ---
        # Structure: { "head_name": { "type": "single/multi", "labels": ["label1", ...] } }
        self.label_definitions = {} 
        
        # --- Classification Data ---
        # { "video_path": { "Head": "Label", "Head2": ["L1", "L2"] } }
        self.manual_annotations = {} 
        
        # Classification Import Metadata (防止报错)
        self.imported_input_metadata = {}   # Key: (action_id, filename)
        self.imported_action_metadata = {}  # Key: action_id

        # --- Localization / Action Spotting Data ---
        # { "video_path": [ { "head": "action", "label": "kick", "position_ms": 1500 }, ... ] }
        self.localization_events = {}
        
        # --- Common Video/Clip List ---
        # List of dicts: { "name": "...", "path": "...", "source_files": [...] }
        self.action_item_data = [] 
        self.action_item_map = {}      # path -> QTreeWidgetItem
        self.action_path_to_name = {}  # path -> name
        
        # --- Undo/Redo Stacks ---
        self.undo_stack = []
        self.redo_stack = []

    def reset(self, full_reset=False):
        self.current_json_path = None
        self.json_loaded = False
        self.is_data_dirty = False
        
        self.manual_annotations = {}
        self.localization_events = {}
        
        # 重置元数据
        self.imported_input_metadata = {}
        self.imported_action_metadata = {}
        
        self.action_item_data = []
        self.action_item_map = {}
        self.action_path_to_name = {}
        self.undo_stack = []
        self.redo_stack = []
        
        if full_reset:
            self.label_definitions = {}
            self.current_working_directory = None
            self.current_task_name = "Untitled Task"
            self.project_description = ""

    def push_undo(self, cmd_type, **kwargs):
        """Pushes a command to the undo stack and clears redo stack."""
        command = {'type': cmd_type, **kwargs}
        self.undo_stack.append(command)
        self.redo_stack.clear()
        self.is_data_dirty = True

    def validate_gac_json(self, data):
        """
        Placeholder for existing Classification JSON validation logic.
        Retained to match existing codebase.
        """
        return True, "", ""

    def validate_loc_json(self, data):
        """
        Strict Validation for Localization / Action Spotting JSON.
        Covers 19 specific error cases.
        Returns: (is_valid, error_msg, warning_msg)
        """
        errors = []
        warnings = []
        
        # --- Top Level Checks (Cases 1-4) ---
        if not isinstance(data, dict):
            return False, "Root JSON must be a dictionary.", ""

        # Case 1: Missing 'data'
        if "data" not in data:
            return False, "Critical: Missing top-level key 'data'.", ""
        
        # Case 2: 'data' is not a list
        if not isinstance(data["data"], list):
            return False, "Critical: Top-level 'data' must be a list.", ""

        # Case 3: Missing 'labels'
        if "labels" not in data:
            return False, "Critical: Missing top-level key 'labels'.", ""
        
        # Case 4: 'labels' is not a dict
        labels_def = data["labels"]
        if not isinstance(labels_def, dict):
            return False, "Critical: Top-level 'labels' must be a dictionary.", ""

        # --- Schema Validity (Case 5) ---
        valid_heads = set()
        head_label_map = {}
        
        for head, content in labels_def.items():
            if not isinstance(content, dict):
                 errors.append(f"Label definition for '{head}' must be a dict.")
                 continue
            
            # Case 5: labels[head]['labels'] is not a list
            if "labels" not in content or not isinstance(content["labels"], list):
                errors.append(f"Critical: 'labels' field for head '{head}' must be a list.")
                continue
            
            valid_heads.add(head)
            head_label_map[head] = set(content["labels"])

        if errors:
            return False, "\n".join(errors), ""

        # --- Data Items Iteration ---
        err_inputs_missing = []      # Case 6
        err_inputs_not_list = []     # Case 7
        err_inputs_empty = []        # Case 8
        err_input_type = []          # Case 9
        err_input_path = []          # Case 10
        err_input_fps = []           # Case 11
        
        err_events_missing = []      # Case 12
        err_events_not_list = []     # Case 13
        
        err_evt_missing_fields = []  # Case 14 (head/label/pos)
        err_evt_unknown_head = []    # Case 15
        err_evt_unknown_label = []   # Case 16 (includes Case 19: empty labels list)
        err_evt_pos_format = []      # Case 17 (not int)
        err_evt_pos_neg = []         # Case 18 (< 0)

        warn_duplicates = []
        
        items_list = data["data"]
        
        for i, item in enumerate(items_list):
            if not isinstance(item, dict):
                errors.append(f"Item #{i} is not a dictionary.")
                continue

            # --- Inputs Checks (Cases 6-11) ---
            # Case 6: Missing inputs
            if "inputs" not in item:
                err_inputs_missing.append(f"Item #{i}")
                # Cannot proceed with input checks, but check events? Usually stop here for this item.
                continue 
            
            inputs = item["inputs"]
            
            # Case 7: inputs not list
            if not isinstance(inputs, list):
                err_inputs_not_list.append(f"Item #{i}")
                continue
                
            # Case 8: inputs empty
            if len(inputs) == 0:
                err_inputs_empty.append(f"Item #{i}")
                continue # Skip inner checks
            
            # Input[0] checks
            first_inp = inputs[0]
            if isinstance(first_inp, dict):
                # Case 9: type != video
                if first_inp.get("type") != "video":
                    err_input_type.append(f"Item #{i} type='{first_inp.get('type')}'")
                
                # Case 10: missing path
                if "path" not in first_inp:
                    err_input_path.append(f"Item #{i}")
                
                # Case 11: fps invalid
                fps = first_inp.get("fps")
                if fps is None or not isinstance(fps, (int, float)) or fps <= 0:
                    err_input_fps.append(f"Item #{i} fps={fps}")
            else:
                 err_inputs_not_list.append(f"Item #{i} (inputs[0] not dict)")

            # --- Events Checks (Cases 12-19) ---
            # Case 12: Missing events
            if "events" not in item:
                err_events_missing.append(f"Item #{i}")
                continue
            
            events = item["events"]
            
            # Case 13: Events not list
            if not isinstance(events, list):
                err_events_not_list.append(f"Item #{i}")
                continue
            
            # Individual Event Checks
            seen_events = set()
            for j, evt in enumerate(events):
                if not isinstance(evt, dict):
                    continue

                # Case 14: Missing keys
                missing_fields = []
                if "head" not in evt: missing_fields.append("head")
                if "label" not in evt: missing_fields.append("label")
                if "position_ms" not in evt: missing_fields.append("position_ms")
                
                if missing_fields:
                    err_evt_missing_fields.append(f"Item #{i} Evt #{j} missing {missing_fields}")
                    continue # Cannot proceed logic checks if fields missing

                head = evt["head"]
                label = evt["label"]
                pos_val = evt["position_ms"]

                # Case 15: Unknown Head
                if head not in valid_heads:
                    err_evt_unknown_head.append(f"Item #{i} Evt #{j} head='{head}'")
                    continue

                # Case 16 & 19: Label not in head's label list
                # If head's labels list is empty (Case 19), this check will fail (Correct)
                allowed_labels = head_label_map[head]
                if label not in allowed_labels:
                    err_evt_unknown_label.append(f"Item #{i} Evt #{j} label='{label}' not in head '{head}'")
                    continue

                # Case 17: position_ms not convertible to int
                try:
                    pos_int = int(pos_val)
                    # Case 18: position_ms < 0
                    if pos_int < 0:
                        err_evt_pos_neg.append(f"Item #{i} Evt #{j} pos={pos_int}")
                except (ValueError, TypeError):
                    err_evt_pos_format.append(f"Item #{i} Evt #{j} pos='{pos_val}'")
                    continue

                # Duplicate check (Warning)
                sig = (head, label, int(pos_val) if isinstance(pos_val, (int, float, str)) and str(pos_val).isdigit() else pos_val)
                if sig in seen_events:
                    warn_duplicates.append(f"Item #{i} ({head}, {label}, {pos_val})")
                else:
                    seen_events.add(sig)

        # --- Aggregate Errors ---
        def _fmt(title, lst):
            if not lst: return None
            return f"{title} ({len(lst)}):\n  " + "\n  ".join(lst[:5]) + ("\n  ..." if len(lst)>5 else "")

        # Critical Errors (Return False)
        crit_errors = [
            _fmt("Data items missing 'inputs'", err_inputs_missing),
            _fmt("Data items 'inputs' not a list", err_inputs_not_list),
            _fmt("Data items 'inputs' is empty", err_inputs_empty),
            _fmt("Inputs type is not 'video'", err_input_type),
            _fmt("Inputs missing 'path'", err_input_path),
            _fmt("Inputs FPS invalid (<=0)", err_input_fps),
            
            _fmt("Data items missing 'events'", err_events_missing),
            _fmt("Data items 'events' not a list", err_events_not_list),
            
            _fmt("Events missing keys (head/label/pos)", err_evt_missing_fields),
            _fmt("Unknown Event Head (not in labels)", err_evt_unknown_head),
            _fmt("Unknown Event Label (not in schema)", err_evt_unknown_label),
            _fmt("Position invalid format (not int)", err_evt_pos_format),
            _fmt("Position negative", err_evt_pos_neg),
        ]
        
        final_errors = [e for e in crit_errors if e] + errors # Prepend schema errors
        
        if final_errors:
            return False, "\n\n".join(final_errors), ""

        # Warnings (Return True)
        if warn_duplicates:
            warnings.append(_fmt("Duplicate Events found", warn_duplicates))

        return True, "", "\n\n".join(warnings)
