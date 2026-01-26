# 🏷️ Classification UI Module

This directory contains the specific user interface components designed for the **Whole-Video Classification** task.

Unlike the previous monolithic structure, this module is split into two specialized sub-packages (`event_editor` and `media_player`) that plug into the application's common workspace.

## 📂 Directory Structure & Modules

### 1. `event_editor/` (The Right Panel)
**Responsible for:** Dynamic annotation forms, Schema management, and Task controls.

* **`editor.py`**:
    * Defines **`ClassificationEventEditor`**: The main container for the right side of the screen.
    * Hosts the **Undo/Redo** buttons specific to classification.
    * Contains the **Schema Editor** (Add Head) and the **Manual Annotation Box** (Confirm/Clear).
* **`dynamic_widgets.py`**:
    * Contains the logic to programmatically generate UI elements based on the JSON schema:
        * **`DynamicSingleLabelGroup`**: Generates Radio Buttons for mutually exclusive categories.
        * **`DynamicMultiLabelGroup`**: Generates Checkboxes for multi-select categories.
* **`__init__.py`**: Exposes `ClassificationEventEditor` for external use.

### 2. `media_player/` (The Center Panel)
**Responsible for:** Video rendering, playback controls, and navigation.

* **`preview.py`**:
    * Defines **`MediaPreview`**: A wrapper around `QMediaPlayer` and `QVideoWidget`.
    * Includes the custom **`ClickableSlider`** for instant seeking and time labels (e.g., `00:05 / 01:30`).
* **`controls.py`**:
    * Defines **`NavigationToolbar`**: Hosts the buttons for navigating between clips (Previous/Next Clip) and actions (Previous/Next Action).
* **`__init__.py`**:
    * Exposes **`ClassificationMediaPlayer`**: The assembled widget that combines the preview area and the navigation toolbar into a vertical layout.

---

## 🏗️ Architecture Changes

### Where is `panels.py`?
The specific `LeftPanel`, `CenterPanel`, and `RightPanel` classes have been refactored:
1.  **Left Panel**: Now uses the generic **`CommonProjectTreePanel`** (located in `ui/common/clip_explorer.py`).
2.  **Center & Right Panels**: Now reside in the `media_player` and `event_editor` folders described above.
3.  **Assembly**: The overall layout is now handled by the **`UnifiedTaskPanel`** (in `ui/common/workspace.py`), which composes these components dynamically.

### Dynamic UI Generation
The **`event_editor`** module retains the core capability of adapting to the project's data model. It reads `label_definitions` from the Model and instantiates `Dynamic...LabelGroup` widgets at runtime, ensuring the tool works with any classification schema without code changes.
