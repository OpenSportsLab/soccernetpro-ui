# User Interface (UI) Module

This directory contains the **View layer** of the application's MVC architecture. It is responsible solely for the graphical presentation and user interaction components.

**Note:** No business logic or data manipulation is performed here. All user interactions (clicks, edits) are emitted as Qt Signals to be handled by the `controllers` module.

## 📂 Directory Structure

The UI is organized by functional domain, with a unified common layer and symmetrical structures for specific tasks:

```text
ui/
├── common/             # Core layout, dialogs, and reusable widgets
│   ├── main_window.py      # The top-level application container
│   ├── workspace.py        # The unified 3-column layout skeleton
│   ├── clip_explorer.py    # The shared left-side project tree
│   ├── project_controls.py # The shared 3x2 button grid
│   └── dialogs.py          # Pop-up dialogs (New Project, Folder Picker)
│
├── classification/     # Components for Whole-Video Classification
│   ├── media_player/       # Video preview and navigation controls
│   └── event_editor/       # Dynamic form generation for labeling
│
└── localization/       # Components for Temporal Action Spotting
    ├── media_player/       # Video preview, timeline, and zoom controls
    └── event_editor/       # Annotation tables and spotting tabs

```

---

## 🧩 Modules Description

### 1. Common (`ui/common/`)

Contains the structural backbone of the application to ensure a consistent user experience across different modes.

* **`main_window.py`**:
* The entry point for the GUI.
* Uses a `QStackedLayout` to switch between the Welcome Screen, Classification View, and Localization View.
* Composes the views by injecting specific widgets into the generic `UnifiedTaskPanel`.


* **`workspace.py`**:
* Defines the **`UnifiedTaskPanel`**: A generic shell that enforces the standard "Left-Center-Right" layout.
* Standardizes the look and feel so both Classification and Localization modes appear consistent.


* **`clip_explorer.py`**:
* Implements the **Left Panel** used in both modes.
* Contains the project tree (Clips/Actions), filter dropdowns, and the Unified Project Controls.


* **`dialogs.py`**:
* `ProjectTypeDialog`: Forces the user to choose between Classification and Localization modes.
* `CreateProjectDialog`: A wizard for setting up new tasks and defining the initial Label Schema.
* `FolderPickerDialog`: A custom file tree for efficient multi-folder selection.



### 2. Classification (`ui/classification/`)

Implements the interface for **Whole-Video Classification** (assigning global labels to an entire video clip).

* **`media_player/`** (Center Panel):
* **`preview.py`**: A standard video player with a `ClickableSlider` for absolute positioning.
* **`controls.py`**: Basic navigation buttons (Next/Prev Clip, Play/Pause).


* **`event_editor/`** (Right Panel):
* **`editor.py`**: The container for the schema editor and annotation forms.
* **`dynamic_widgets.py`**: Logic to generate `RadioButtons` (single-label) or `Checkboxes` (multi-label) dynamically based on the JSON schema.



### 3. Localization (`ui/localization/`)

Implements the interface for **Action Spotting** (identifying specific timestamps within a video).

* **`media_player/`** (Center Panel):
* **`preview.py`**: Handles video rendering.
* **`timeline.py`**: A complex, custom-drawn widget that supports **zooming**, **panning**, and visual event markers.
* **`controls.py`**: Advanced playback controls, including playback speed (0.25x - 4.0x) and frame stepping.


* **`event_editor/`** (Right Panel):
* **`spotting_controls.py`**: A multi-tab interface ("Heads") containing grids of buttons for quick timestamp marking.
* **`annotation_table.py`**: A spreadsheet-like view (`QTableView`) for viewing and editing specific timestamps and labels.



---

## 🎨 Design Principles

1. **Composition over Inheritance**: The application uses a generic `UnifiedTaskPanel` (Workspace) and injects specific functional widgets (Media Players/Editors) into it, rather than creating separate hardcoded layouts.
2. **Passive View**: These classes do not modify the `model` directly. They only display data provided by the controller and emit signals when the user acts.
3. **Dynamic Generation**: The annotation forms (buttons/checkboxes/tabs) are not hardcoded; they are generated dynamically at runtime based on the loaded JSON schema.
4. **Functional Sphericity**: Components are grouped by what they *are* (e.g., `media_player`), creating self-contained packages that handle their own logic.

