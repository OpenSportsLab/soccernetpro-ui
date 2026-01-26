# User Interface (UI) Module

This directory contains the **View layer** of the application's MVC architecture. It is responsible solely for the graphical presentation and user interaction components.

**Note:** No business logic or data manipulation is performed here. All user interactions (clicks, edits) are emitted as Qt Signals to be handled by the `controllers` module.

## 📂 Directory Structure

The UI is organized by functional domain rather than spatial position:

```text
ui/
├── common/             # Reusable widgets and dialogs shared across different tasks
│   ├── dialogs.py
│   └── project_controls.py
├── classification/     # UI components specific to the Classification task
└── localization/       # UI components specific to the Localization task

```

---

## 🧩 Modules Description

### 1. Common (`ui/common/`)

Contains widgets and windows that are standardized and used across multiple modes to ensure a consistent user experience.

* **`dialogs.py`**: Contains modal dialog windows used throughout the application lifecycle:
* `ProjectTypeDialog`: Forces the user to choose between Classification and Localization modes.
* `CreateProjectDialog`: A wizard for setting up new tasks and defining the initial Label Schema.
* `FolderPickerDialog`: A custom file tree that allows selecting multiple folders without holding the Ctrl key.


* **`project_controls.py`**:
* Defines the **Unified 3x2 Control Grid** (New, Load, Add Data, Close, Save, Export).
* Contains the **Unified Clip Explorer**, providing a consistent video list and filter interface for both modes.



### 2. Classification (`ui/classification/`)

Implements the interface for **Whole-Video Classification** (assigning global labels to an entire video clip).

* **`panels.py`**: Defines the high-level layout:
* `LeftPanel`: Navigation tree and Project Controls.
* `CenterPanel`: Video player and basic navigation controls.
* `RightPanel`: Dynamic form generation based on the project Schema.


* **`widgets.py`**: Contains specialized input widgets:
* `DynamicSingleLabelGroup`: Generates Radio Buttons for single-choice categories.
* `DynamicMultiLabelGroup`: Generates Checkboxes for multi-choice categories.
* `VideoViewAndControl`: A wrapper for the video player and slider.



### 3. Localization (`ui/localization/`)

Implements the interface for **Action Spotting** (identifying specific timestamps within a video).

* **`panels.py`**: The layout container that assembles the following functional widgets.
* **`clip_explorer.py`**:
* Displays the list of video clips (Sequences) using the shared explorer logic.
* Handles filtering (Done/Not Done) and visual status indicators.


* **`media_player.py`**:
* Contains the `MediaPreviewWidget`.
* Features a custom, zoomable **Timeline** with visual event markers.
* Includes frame-stepping and speed control playback tools.


* **`event_editor.py`**:
* `Spotting Tabs`: A multi-tab interface for defining different event categories (Heads).
* `Annotation Table`: A spreadsheet-like view for editing event timestamps and labels.



---

## 🎨 Design Principles

1. **Passive View**: These classes do not modify the `model` directly. They only display data provided by the controller and emit signals when the user acts.
2. **Dynamic Generation**: The annotation forms (buttons/checkboxes) are not hardcoded; they are generated dynamically based on the loaded JSON schema.
3. **Functional Naming**: Files are named after what they *do* (e.g., `media_player.py`), not where they are located (e.g., `center_widgets.py`), allowing for flexible layout changes in the future.


```
