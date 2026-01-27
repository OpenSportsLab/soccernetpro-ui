# 🏷️ Classification UI Module

This directory contains the specific user interface components designed for the **Whole-Video Classification** task.

Unlike the previous monolithic structure, this module is split into two specialized sub-packages (`event_editor` and `media_player`) that plug into the application's common workspace.
<img width="2096" height="976" alt="10dcdefb36c63c4a33002f85d0f53ae1" src="https://github.com/user-attachments/assets/7983f1a6-281a-45c4-8fff-ec4092460b60" />


## 📂 Directory Structure

```text
ui/classification/
├── event_editor/       # The "Right Panel" logic
│   ├── __init__.py     # Exposes ClassificationEventEditor
│   ├── editor.py       # Main container layout
│   └── dynamic_widgets.py # Radio buttons & Checkboxes generators
│
└── media_player/       # The "Center Panel" logic
    ├── __init__.py     # Exposes ClassificationMediaPlayer
    ├── preview.py      # Video widget, Slider, Audio logic
    └── controls.py     # Navigation buttons

```

---

## 🧩 Modules Detail

### 1. `event_editor/` (The Right Panel)

**Responsible for:** Dynamic annotation forms, Schema management, and Task controls.

* **`editor.py`**:
* Defines **`ClassificationEventEditor`**: The main container for the right side of the screen.
* Hosts the **Undo/Redo** buttons specific to classification tasks.
* Contains the **Schema Editor** (Text input to add new Heads) and the **Manual Annotation Box** (Save/Clear buttons).


* **`dynamic_widgets.py`**:
* Contains the logic to programmatically generate UI elements based on the JSON schema loaded in the Model:
* **`DynamicSingleLabelGroup`**: Generates Radio Buttons for mutually exclusive categories.
* **`DynamicMultiLabelGroup`**: Generates Checkboxes for multi-select categories.




* **`__init__.py`**:
* Exposes `ClassificationEventEditor` for external use by the Main Window.



### 2. `media_player/` (The Center Panel)

**Responsible for:** Video rendering, playback controls, and navigation.

* **`preview.py`**:
* Defines **`MediaPreview`**: A wrapper around `QMediaPlayer`, `QAudioOutput`, and `QVideoWidget`.
* Includes the custom **`ClickableSlider`** for instant seeking and time labels (e.g., `00:05 / 01:30`).


* **`controls.py`**:
* Defines **`NavigationToolbar`**: Hosts the buttons for navigating between clips (Previous/Next Clip) and actions (Previous/Next Action).


* **`__init__.py`**:
* Exposes **`ClassificationMediaPlayer`**: The assembled widget that combines the preview area and the navigation toolbar into a vertical layout.

### 3.Left Sidebar (Clip / Sequence Explorer)
Clip Explorer Sidebar: Displays the hierarchical list of `Clips/Sequences`, supports filtering (`Labelled/Not Labelled`) and project operations (`Save/Load/Export`). This UI is provided and driven by `ui/common/clip_explorer.py`.

---

## 🏗️ Architecture Integration

### Integration with `UnifiedTaskPanel`

This module no longer defines the overall layout (Left/Center/Right). Instead, it provides the components that are injected into the **`UnifiedTaskPanel`** (located in `ui/common/workspace.py`).

1. **Left Panel**: Uses the generic **`CommonProjectTreePanel`** (shared with Localization).
2. **Center Panel**: Uses `ClassificationMediaPlayer` from this module.
3. **Right Panel**: Uses `ClassificationEventEditor` from this module.

### Dynamic UI Generation

The **`event_editor`** module retains the core capability of adapting to the project's data model. It reads `label_definitions` from the global `AppStateModel` and instantiates `Dynamic...LabelGroup` widgets at runtime. This ensures the tool works with any classification schema (e.g., Soccer, Basketball, Surveillance) without requiring code changes.
