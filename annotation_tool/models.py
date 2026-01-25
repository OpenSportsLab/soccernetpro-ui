import os
import copy
from enum import Enum, auto


class CmdType(Enum):
    """Command types recorded in the undo/redo history."""

    # --- Classification commands ---
    ANNOTATION_CONFIRM = auto()  # Persist a user-confirmed annotation to the model
    UI_CHANGE = auto()           # Fine-grained UI toggle (radio/checkbox changes)

    # --- Shared schema commands (used by both modes) ---
    SCHEMA_ADD_CAT = auto()      # Add a category/head
    SCHEMA_DEL_CAT = auto()      # Delete a category/head
    SCHEMA_REN_CAT = auto()      # Rename a category/head

    SCHEMA_ADD_LBL = auto()      # Add a label option under a head
    SCHEMA_DEL_LBL = auto()      # Delete a label option under a head
    SCHEMA_REN_LBL = auto()      # Rename a label option under a head

    # --- Localization commands ---
    LOC_EVENT_ADD = auto()
    LOC_EVENT_DEL = auto()
    LOC_EVENT_MOD = auto()


class AppStateModel:
    """
   Centralized application state container.
    - Owns project metadata, schema, annotations/events, and undo/redo stacks.
    - Does not touch UI widgets (UI is managed elsewhere).
    """

    def __init__(self):
        # --- Project metadata ---
        self.current_working_directory = None
        self.current_json_path = None
        self.json_loaded = False
        self.is_data_dirty = False
        self.project_description = ""  # Keep a default to avoid missing-field issues
        self.current_task_name = "Untitled Task"
        self.modalities = ["video"]

        # --- Schema / labels ---
        # Format: { head_name: { "type": "single|multi", "labels": [..] } }
        self.label_definitions = {}

        # --- Classification data ---
        # Format: { video_path: { "Head": "Label", "Head2": ["L1", "L2"] } }
        self.manual_annotations = {}

        # Classification import metadata (kept for backward compatibility)
        self.imported_input_metadata = {}   # key: (action_id, filename)
        self.imported_action_metadata = {}  # key: action_id

        # --- Localization / action spotting data ---
        # Format: { video_path: [ { "head": ..., "label": ..., "position_ms": ... }, ... ] }
        self.localization_events = {}

        # --- Common clip list ---
        # Each item: { "name": "...", "path": "...", "source_files": [...] }
        self.action_item_data = []
        self.action_item_map = {}      # path -> QTreeWidgetItem (populated by UI layer)
        self.action_path_to_name = {}  # path -> name

        # --- Undo/redo stacks ---
        self.undo_stack = []
        self.redo_stack = []

    def reset(self, full_reset: bool = False):
        """Reset runtime state. If full_reset is True, also clears schema and project metadata."""
        self.current_json_path = None
        self.json_loaded = False
        self.is_data_dirty = False

        self.manual_annotations = {}
        self.localization_events = {}

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

    def push_undo(self, cmd_type: CmdType, **kwargs):
        """Push a command onto the undo stack and clear the redo stack."""
        command = {"type": cmd_type, **kwargs}
        self.undo_stack.append(command)
        self.redo_stack.clear()
        self.is_data_dirty = True

    def validate_gac_json(self, data):
        """
        Placeholder for Classification JSON validation.
        Kept to match the existing codebase interface.
        """
        return True, "", ""

    def validate_loc_json(self, data):
        """
        Strict validation for Localization / Action Spotting JSON.

        Returns:
            (is_valid, error_msg, warning_msg)
        """
        errors = []
        warnings = []

        # --- Top-level checks ---
        if not isinstance(data, dict):
            return False, "Root JSON must be a dictionary.", ""

        if "data" not in data:
            return False, "Critical: Missing top-level key 'data'.", ""

        if not isinstance(data["data"], list):
            return False, "Critical: Top-level 'data' must be a list.", ""

        if "labels" not in data:
            return False, "Critical: Missing top-level key 'labels'.", ""

        labels_def = data["labels"]
        if not isinstance(labels_def, dict):
            return False, "Critical: Top-level 'labels' must be a dictionary.", ""

        # --- Schema checks ---
        valid_heads = set()
        head_label_map = {}

        for head, content in labels_def.items():
            if not isinstance(content, dict):
                errors.append(f"Label definition for '{head}' must be a dictionary.")
                continue

            lbls = content.get("labels")
            if not isinstance(lbls, list):
                errors.append(f"Critical: 'labels' field for head '{head}' must be a list.")
                continue

            valid_heads.add(head)
            head_label_map[head] = set(lbls)

        if errors:
            return False, "\n".join(errors), ""

        # --- Per-item checks ---
        err_inputs_missing = []
        err_inputs_not_list = []
        err_inputs_empty = []
        err_input_type = []
        err_input_path = []
        err_input_fps = []

        err_events_missing = []
        err_events_not_list = []

        err_evt_missing_fields = []
        err_evt_unknown_head = []
        err_evt_unknown_label = []
        err_evt_pos_format = []
        err_evt_pos_neg = []

        warn_duplicates = []

        items_list = data["data"]

        for i, item in enumerate(items_list):
            if not isinstance(item, dict):
                errors.append(f"Item #{i} is not a dictionary.")
                continue

            # Inputs
            if "inputs" not in item:
                err_inputs_missing.append(f"Item #{i}")
                continue

            inputs = item["inputs"]
            if not isinstance(inputs, list):
                err_inputs_not_list.append(f"Item #{i}")
                continue

            if len(inputs) == 0:
                err_inputs_empty.append(f"Item #{i}")
                continue

            first_inp = inputs[0]
            if not isinstance(first_inp, dict):
                err_inputs_not_list.append(f"Item #{i} (inputs[0] is not a dict)")
                continue

            if first_inp.get("type") != "video":
                err_input_type.append(f"Item #{i} type='{first_inp.get('type')}'")

            if "path" not in first_inp:
                err_input_path.append(f"Item #{i}")

            fps = first_inp.get("fps")
            if fps is None or not isinstance(fps, (int, float)) or fps <= 0:
                err_input_fps.append(f"Item #{i} fps={fps}")

            # Events
            if "events" not in item:
                err_events_missing.append(f"Item #{i}")
                continue

            events = item["events"]
            if not isinstance(events, list):
                err_events_not_list.append(f"Item #{i}")
                continue

            seen_events = set()
            for j, evt in enumerate(events):
                if not isinstance(evt, dict):
                    continue

                missing_fields = []
                if "head" not in evt:
                    missing_fields.append("head")
                if "label" not in evt:
                    missing_fields.append("label")
                if "position_ms" not in evt:
                    missing_fields.append("position_ms")

                if missing_fields:
                    err_evt_missing_fields.append(f"Item #{i} Evt #{j} missing {missing_fields}")
                    continue

                head = evt["head"]
                label = evt["label"]
                pos_val = evt["position_ms"]

                if head not in valid_heads:
                    err_evt_unknown_head.append(f"Item #{i} Evt #{j} head='{head}'")
                    continue

                allowed_labels = head_label_map[head]  # may be empty; then all labels are invalid
                if label not in allowed_labels:
                    err_evt_unknown_label.append(
                        f"Item #{i} Evt #{j} label='{label}' not in head '{head}'"
                    )
                    continue

                try:
                    pos_int = int(pos_val)
                    if pos_int < 0:
                        err_evt_pos_neg.append(f"Item #{i} Evt #{j} pos={pos_int}")
                except (ValueError, TypeError):
                    err_evt_pos_format.append(f"Item #{i} Evt #{j} pos='{pos_val}'")
                    continue

                # Duplicate detection is a warning (same head/label/time within an item)
                sig = (head, label, pos_int)
                if sig in seen_events:
                    warn_duplicates.append(f"Item #{i} ({head}, {label}, {pos_val})")
                else:
                    seen_events.add(sig)

        # --- Formatting helpers ---
        def _fmt(title, lst):
            if not lst:
                return None
            preview = "\n  ".join(lst[:5]) + ("\n  ..." if len(lst) > 5 else "")
            return f"{title} ({len(lst)}):\n  {preview}"

        # Critical errors -> return False
        crit_errors = [
            _fmt("Data items missing 'inputs'", err_inputs_missing),
            _fmt("Data items 'inputs' is not a list", err_inputs_not_list),
            _fmt("Data items 'inputs' is empty", err_inputs_empty),
            _fmt("Inputs type is not 'video'", err_input_type),
            _fmt("Inputs missing 'path'", err_input_path),
            _fmt("Inputs FPS invalid (<= 0)", err_input_fps),
            _fmt("Data items missing 'events'", err_events_missing),
            _fmt("Data items 'events' is not a list", err_events_not_list),
            _fmt("Events missing keys (head/label/position_ms)", err_evt_missing_fields),
            _fmt("Unknown event head (not in labels)", err_evt_unknown_head),
            _fmt("Unknown event label (not in schema)", err_evt_unknown_label),
            _fmt("Position invalid format (not int)", err_evt_pos_format),
            _fmt("Position is negative", err_evt_pos_neg),
        ]

        final_errors = [e for e in crit_errors if e] + errors
        if final_errors:
            return False, "\n\n".join(final_errors), ""

        # Warnings -> return True
        if warn_duplicates:
            warnings.append(_fmt("Duplicate events found", warn_duplicates))

        return True, "", "\n\n".join(warnings)
