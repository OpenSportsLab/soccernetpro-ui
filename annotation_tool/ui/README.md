# User Interface (UI) Module

This directory contains the **View layer** of the application's MVC architecture. It is responsible solely for graphical presentation and user interaction.

> **Architecture Note:** This module follows the **Passive View** pattern. No business logic or data manipulation is performed here. All user interactions (clicks, edits) are emitted as Qt Signals to be handled by the `controllers` module. The Left Panel specifically implements the **Qt Model/View** architecture.

## 📂 Directory Structure

The UI is organized by functional domain, with a unified common layer and symmetrical structures for specific tasks:

```text
ui/
├── common/                 # Core layout, dialogs, and reusable widgets
│   ├── main_window.py      # The top-level application container
│   ├── workspace.py        # The generic 3-column layout skeleton
│   ├── clip_explorer.py    # The SHARED left-side project tree (MV Architecture)
│   ├── project_controls.py # The shared 3x2 button grid
│   └── dialogs.py          # Pop-up dialogs (New Project, Folder Picker)
│
├── classification/         # Components for Whole-Video Classification
│   ├── media_player/       # Video preview and navigation controls
│   └── event_editor/       # Dynamic form generation for labeling
│
└── localization/           # Components for Temporal Action Spotting
    ├── media_player/       # Video preview, timeline, and zoom controls
    └── event_editor/       # Annotation tables and spotting tabs

```

---

## 🧩 Structural Components (Common)

These components form the backbone of the application, ensuring a consistent user experience across different modes.

### 1. `main_window.py`

* **Purpose:** The top-level UI container.
* **Key Class:** `MainWindowUI`
* **Function:** Uses a `QStackedLayout` to switch between:
* **View 0:** `WelcomeWidget` (Entry screen).
* **View 1:** Classification Interface.
* **View 2:** Localization Interface.



### 2. `workspace.py`

* **Purpose:** Defines the generic layout skeleton used by specific tasks.
* **Key Class:** `UnifiedTaskPanel`
* **Layout Strategy:** Implements a standard **3-Column Layout**:
* **Left (Fixed):** `CommonProjectTreePanel` (Shared resource list).
* **Center (Expandable):** Task-specific visualizer (injected at runtime).
* **Right (Fixed):** Task-specific editor (injected at runtime).



---

## 🛠️ Shared Widget Components

### 3. `clip_explorer.py` (Model/View Refactored)

* **Purpose:** The standardized **Left Sidebar** for resource management.
* **Key Class:** `CommonProjectTreePanel`
* **Architecture:** **Qt Model/View Pattern**.
* Uses **`QTreeView`** instead of `QTreeWidget`.
* **Decoupled:** It does not store data. It displays data provided by the shared `ProjectTreeModel` (located in the `models` package).


* **Composition:**
* **Top:** Embeds `UnifiedProjectControls`.
* **Middle:** The `QTreeView` displaying the clip hierarchy.
* **Bottom:** A Filter ComboBox and Clear Button.


* **Signals:**
* `request_remove_item(QModelIndex)`: Emitted via context menu for the Controller to handle data deletion.



### 4. `project_controls.py`

* **Purpose:** A reusable button grid for project lifecycle management.
* **Key Class:** `UnifiedProjectControls`
* **Layout:** A 3x2 Grid containing 6 essential buttons: `New`, `Load`, `Add Data`, `Close`, `Save`, `Export`.

### 5. `dialogs.py`

* **Purpose:** Modal dialogs for configuration.
* **Includes:**
* `ProjectTypeDialog`: Selection window for Classification vs. Localization.
* `CreateProjectDialog`: Wizard for setting up new tasks and Schema.
* `FolderPickerDialog`: Custom file tree for efficient multi-folder selection.



---

## 🎯 Task-Specific Modules

### Classification (`ui/classification/`)

Implements the interface for **Whole-Video Classification** (assigning global labels to an entire video clip).

* **`media_player/`**: Standard video player with `ClickableSlider` for absolute positioning and navigation buttons.
* **`event_editor/`**: Contains `dynamic_widgets.py`, which generates `RadioButtons` (single-label) or `Checkboxes` (multi-label) at runtime based on the JSON schema.

### Localization (`ui/localization/`)

Implements the interface for **Action Spotting** (identifying specific timestamps within a video).

* **`media_player/`**: Includes a custom-drawn **`timeline.py`** widget supporting zooming, panning, and visual event markers.
* **`event_editor/`**:
* `spotting_controls.py`: Multi-tab interface for quick timestamp marking.
* `annotation_table.py`: Spreadsheet-like view (`QTableView`) for editing specific timestamps.



---

## 🎨 Design Principles

1. **DRY (Don't Repeat Yourself)**: The Left Panel and Workspace layout are implemented once and reused across both modes.
2. **Model/View Separation**: The file tree strictly separates data (Model) from presentation (View), allowing efficient updates and data sharing.
3. **Composition over Inheritance**: The `UnifiedTaskPanel` injects specific widgets rather than hardcoding them, making the system flexible.
4. **Dynamic Generation**: Annotation forms are not hardcoded; they are generated dynamically based on the loaded project Schema.

