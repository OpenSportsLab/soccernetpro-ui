# SoccerNet Pro Annotation Tool

This project is a professional video annotation desktop application built with **PyQt6**. It features a dual-mode architecture supporting both **Whole-Video Classification** and **Action Spotting (Localization)** tasks.

The project follows a modular **MVC (Model-View-Controller)** design pattern to ensure separation of concerns between data handling, business logic, and user interface. Recent updates have unified the UI architecture using a composite design pattern.

## 📂 Project Structure Overview

```text
annotation_tool/
├── main.py                     # Application entry point
├── viewer.py                   # Main Window controller (orchestrates UI & Logic)
├── models.py                   # Data models, application state, and JSON validation
├── utils.py                    # Helper functions and constants
├── __init__.py                 # Package initialization
│
├── style/                      # Visual theme assets
│   └── style.qss               # Dark mode stylesheet (default)
│
├── controllers/                # [Logic Layer] Business logic
│   ├── __init__.py
│   ├── router.py               # Routing logic (Project loading & mode switching)
│   ├── history_manager.py      # Universal Undo/Redo system
│   │
│   ├── classification/         # Logic for Classification mode
│   │   ├── annotation_manager.py
│   │   ├── class_file_manager.py
│   │   └── navigation_manager.py
│   │
│   └── localization/           # Logic for Localization mode
│       ├── loc_file_manager.py
│       └── localization_manager.py
│
└── ui/                         # [View Layer] Interface definitions
    ├── common/                 # Shared widgets & layouts
    │   ├── main_window.py      # Main UI Assembler (Stacks Views)
    │   ├── workspace.py        # Generic 3-Column Layout (UnifiedTaskPanel)
    │   ├── clip_explorer.py    # Universal Left Sidebar (Tree & Filters)
    │   ├── project_controls.py # Unified control buttons (Save, Export, etc.)
    │   ├── dialogs.py          # Pop-up dialogs (Wizard, File Picker)
    │   └── welcome_widget.py   # Welcome screen
    │
    ├── classification/         # UI components for Classification
    │   ├── media_player/       # [Package] Center Panel components
    │   │   ├── preview.py      # Video player wrapper
    │   │   ├── controls.py     # Navigation toolbar
    │   │   └── __init__.py     # Exposes ClassificationMediaPlayer
    │   │
    │   └── event_editor/       # [Package] Right Panel components
    │       ├── dynamic_widgets.py # Schema-driven widgets (Radio/Check)
    │       ├── editor.py       # Layout container
    │       └── __init__.py     # Exposes ClassificationEventEditor
    │
    └── localization/           # UI components for Localization
        ├── media_player/       # [Package] Center Panel components
        │   ├── preview.py      # Video player wrapper
        │   ├── timeline.py     # Custom Zoomable Timeline
        │   ├── controls.py     # Playback control bar
        │   └── __init__.py     # Exposes LocCenterPanel
        │
        └── event_editor/       # [Package] Right Panel components
            ├── annotation_table.py  # Event list table
            ├── spotting_controls.py # Tabbed spotting interface
            └── __init__.py          # Exposes LocRightPanel

```

---

## 📝 File & Module Descriptions

### 1. Root Directory (Core Infrastructure)

These files form the backbone of the application infrastructure.

* **`main.py`**: The bootstrap script. Initializes the `QApplication` and launches the main window.
* **`viewer.py`**: Defines the `ActionClassifierApp` (Main Window). It acts as the primary bridge, initializing the UI layout and connecting UI signals to their respective Controllers.
* **`models.py`**: The **Model**. Stores runtime data (`manual_annotations`, `localization_events`), defines the Undo/Redo stacks, and contains strict JSON schema validation logic.
* **`utils.py`**: Utility functions for file handling, natural sorting, and icon generation.

### 2. Style (`/style`)

Contains the visual definitions for the application.

* **`style.qss`**: CSS-like definitions for the default **Dark Theme**.

### 3. Controllers (`/controllers`)

Pure Python logic handling business rules, data manipulation, and application flow.

#### Shared Controllers

* **`router.py`**: Handles project lifecycle. It determines whether to load the "Classification" view or "Localization" view based on the input JSON structure.
* **`history_manager.py`**: Manages the Command Pattern implementation for the Undo/Redo system, ensuring UI updates trigger correctly after history operations.

#### Classification Sub-module (`/controllers/classification`)

* **`class_file_manager.py`**: Handles JSON I/O for classification tasks, including relative path calculation and workspace clearing.
* **`navigation_manager.py`**: Manages the video list navigation, filtering (Done/Not Done), and playback flow for whole-video tasks.
* **`annotation_manager.py`**: Handles the logic for dynamic schema creation (adding/removing labels) and saving user selections to the model.

#### Localization Sub-module (`/controllers/localization`)

* **`loc_file_manager.py`**: Handles JSON I/O for localization tasks, including path fallback mechanisms for cross-device compatibility.
* **`localization_manager.py`**: The core logic for action spotting. It synchronizes the video player, timeline, and event table, handling timestamp capture and modification.

### 4. User Interface (`/ui`)

PyQt6 widgets and layout definitions. The UI structure has been refactored to be modular and flattened.

#### Common Components (`/ui/common`)

* **`main_window.py`**: The top-level UI container. It manages the `QStackedLayout` to switch between the Welcome Screen, Classification Interface, and Localization Interface.
* **`workspace.py`**: Defines `UnifiedTaskPanel`. This is a generic 3-column layout skeleton used by both modes to ensure a consistent "Left-Center-Right" look and feel.
* **`clip_explorer.py`**: Defines `CommonProjectTreePanel`. The universal left sidebar containing project control buttons, the file tree, and filter options.
* **`dialogs.py`**: Contains modal dialogs such as the **Project Creation Wizard** and custom **Folder Picker**.

#### Classification Components (`/ui/classification`)

* **`media_player/`**: Contains the **Center Panel** logic.
* `preview.py`: Video player with integrated slider.
* `controls.py`: Navigation buttons (Prev/Next Action/Clip).


* **`event_editor/`**: Contains the **Right Panel** logic.
* `dynamic_widgets.py`: Auto-generated Radio Button groups or Checkbox groups based on the JSON schema.
* `editor.py`: The container widget that holds task info, schema editor, and annotation inputs.



#### Localization Components (`/ui/localization`)

* **`media_player/`**: Contains the **Center Panel** logic.
* `timeline.py`: A complex, custom-drawn timeline widget supporting zooming, markers, and auto-scrolling.
* `controls.py`: Playback controls including frame stepping and playback speed adjustment.


* **`event_editor/`**: Contains the **Right Panel** logic.
* `spotting_controls.py`: Multi-tab interface for "spotting" actions (adding timestamps).
* `annotation_table.py`: Editable table view displaying the list of captured events.


