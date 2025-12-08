import copy
from enum import Enum, auto

class CmdType(Enum):
    ANNOTATION_CONFIRM = auto()  # Confirming data to storage
    UI_CHANGE = auto()           # Fine-grained UI toggle (radio/checkbox)
    SCHEMA_ADD_CAT = auto()      # Add Category
    SCHEMA_DEL_CAT = auto()      # Delete Category
    SCHEMA_ADD_LBL = auto()      # Add Label option
    SCHEMA_DEL_LBL = auto()      # Delete Label option

class AppStateModel:
    """
    Manages the application state, data storage, and undo/redo stacks.
    Does NOT interact with UI widgets directly.
    """
    DEFAULT_LABEL_DEFINITIONS = {
        "label_type": {"type": "single_label", "labels": []}, 
    }

    def __init__(self):
        # --- Core Data ---
        self.manual_annotations = {}
        self.action_item_data = []      # List of dicts [{'name':.., 'path':.., 'source_files':..}]
        self.action_path_to_name = {}
        self.action_item_map = {}       # Optional: Map IDs to UI items (if needed by controller)
        
        # --- Metadata ---
        self.imported_action_metadata = {}
        self.imported_input_metadata = {}
        self.modalities = []
        self.current_task_name = "N/A"
        self.project_description = ""
        self.current_working_directory = None
        
        # --- Schema ---
        self.label_definitions = self.DEFAULT_LABEL_DEFINITIONS.copy()
        
        # --- File State ---
        self.current_json_path = None
        self.json_loaded = False
        self.is_data_dirty = False
        
        # --- Undo/Redo Stacks ---
        self.undo_stack = []
        self.redo_stack = []

    def reset(self, full_reset=False):
        """Clears data for new project or list clear."""
        self.manual_annotations.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        
        self.action_item_data.clear()
        self.action_path_to_name.clear()
        self.imported_action_metadata.clear()
        self.imported_input_metadata.clear()
        self.action_item_map.clear()
        
        self.current_json_path = None
        self.is_data_dirty = False
        self.current_working_directory = None

        if full_reset:
            self.json_loaded = False
            self.label_definitions = self.DEFAULT_LABEL_DEFINITIONS.copy()
            self.current_task_name = "N/A"
            self.project_description = ""
            self.modalities = []

    def validate_gac_json(self, data):
        """
        Validates JSON structure.
        Returns: (is_valid, error_msg, warning_msg)
        """
        errors = []
        warnings = []
        
        # 1. Structure Check
        if 'modalities' not in data:
            errors.append("Critical: Missing 'modalities' key.")
        elif not isinstance(data['modalities'], list):
            errors.append("Critical: 'modalities' must be a list.")
        elif len(data['modalities']) == 0:
             errors.append("Critical: 'modalities' list is empty. You cannot proceed without defining data types.")

        # 2. Labels Check
        if 'labels' not in data:
            errors.append("Critical: Missing 'labels' definition.")
        elif not isinstance(data['labels'], dict):
            errors.append("Critical: 'labels' must be a dictionary.")
        
        if isinstance(data.get('labels'), dict):
            for head_name, definition in data['labels'].items():
                if not isinstance(definition, dict):
                    errors.append(f"Critical: Definition for category '{head_name}' is malformed.")
                    continue
                
                lbl_list = definition.get('labels')
                if not isinstance(lbl_list, list):
                    errors.append(f"Critical: Category '{head_name}' missing 'labels' list.")
                elif len(lbl_list) == 0:
                    errors.append(f"Critical: Category '{head_name}' has an empty label list.")

        if errors:
            return False, "\n".join(errors), None

        # 3. Consistency Check (Warnings)
        items = data.get('data', [])
        if not isinstance(items, list):
             return False, "'data' field must be a list.", None

        missing_labels_key = 0
        empty_annotations = 0

        for item in items:
            if 'labels' not in item:
                missing_labels_key += 1
                continue
            lbls = item['labels']
            if not lbls or not isinstance(lbls, dict):
                empty_annotations += 1
            else:
                for head, val in lbls.items():
                    is_empty_val = False
                    if val is None: is_empty_val = True
                    elif isinstance(val, dict):
                        if 'label' in val and not val['label']: is_empty_val = True
                        if 'labels' in val and not val['labels']: is_empty_val = True
                    if is_empty_val: empty_annotations += 1

        if missing_labels_key > 0:
            warnings.append(f"Label Inconsistency: Found {missing_labels_key} items missing the 'labels' key entirely.")
        if empty_annotations > 0:
            warnings.append(f"Label Inconsistency: Found {empty_annotations} items with 'labels' keys that are empty/null.")

        warning_msg = "\n".join(warnings) if warnings else None
        return True, None, warning_msg

    def push_undo(self, cmd_type, **kwargs):
        """Pushes a command to the undo stack and clears redo stack."""
        command = {'type': cmd_type, **kwargs}
        self.undo_stack.append(command)
        self.redo_stack.clear()
        self.is_data_dirty = True