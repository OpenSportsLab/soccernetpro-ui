# 🏷️ Classification Controllers

This module contains the business logic specifically designed for the **Whole-Video Classification** task.

In this mode, the goal is to assign global attributes (labels) to an entire video clip (e.g., "Weather: Sunny", "Action: Goal"). These controllers bridge the gap between the Classification UI (`ui/classification/`) and the central data model (`models.py`).

## 📂 Module Contents

```text
controllers/classification/
├── annotation_manager.py   # Labeling logic & Dynamic Schema handling
├── class_file_manager.py   # I/O operations (Save/Load/Create)
└── navigation_manager.py   # Video list navigation & Playback flow

```

---

## 📝 File Descriptions

### 1. `annotation_manager.py`

**Responsibility:** Manages the labeling process and schema modifications.

* **Dynamic Schema Management**: Handles adding, renaming, or deleting Categories ("Heads") and Labels directly from the UI.
* **Annotation Saving**: Captures the user's selection from the UI (Right Panel), validates it, and commits it to the `AppStateModel`.
* **Undo/Redo Integration**: Pushes commands to the `HistoryManager` when annotations are changed or when the schema structure is modified.

### 2. `class_file_manager.py`

**Responsibility:** Handles file input/output and project lifecycle for Classification projects.

* **Project Creation**: Orchestrates the "New Project" wizard dialog and initializes the model with the chosen schema.
* **JSON Loading**: Parses existing Classification JSON files, validating that they match the expected format.
* **JSON Saving**: Writes the current state to disk. It handles the critical logic of converting absolute file paths to **relative paths** to ensure portability between different computers.
* **Workspace Management**: Handles clearing the current data when closing a project.

### 3. `navigation_manager.py`

**Responsibility:** Manages the list of video clips and the user's movement through them.

* **Tree Interaction**: Connects the `QTreeWidget` (Left Panel) to the media player, ensuring the correct video loads when clicked.
* **Smart Navigation**: Implements logic for "Next Action" (jump to next parent item) and "Next Clip" (jump to next file), skipping items based on filters.
* **Filtering**: Applies logic to show only "Done", "Not Done", or "All" videos in the list.
* **Media Control**: Triggers video playback and synchronizes the player state with the selected item.

