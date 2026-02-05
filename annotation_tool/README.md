# SoccerNet Pro Annotation Tool

This project is a professional video annotation desktop application built with **PyQt6**. It features a **triple-mode** architecture supporting:

1.  **Whole-Video Classification**
2.  **Action Spotting (Localization)**
3.  **Video Description (Captioning)** [NEW]

The project follows a modular **MVC (Model-View-Controller)** design pattern to ensure separation of concerns between data handling, business logic, and user interface. Recent updates have unified the UI architecture using a composite design pattern and migrated the resource management to a robust **Qt Model/View** architecture.

## 📂 Project Structure Overview

```text
annotation_tool/
├── main.py                     # Application entry point
├── viewer.py                   # Main Window controller (orchestrates UI & Logic)
├── utils.py                    # Helper functions and constants
├── __init__.py                 # Package initialization
│
├── models/                     # [Model Layer] Data Structures & State
│   ├── __init__.py
│   ├── app_state.py            # Global Application State & Undo/Redo Stack & Data Validation
│   └── project_tree.py         # Shared QStandardItemModel for File Tree (MV Pattern)
│
├── style/                      # Visual theme assets
│   └── style.qss               # Dark mode stylesheet (default)
│
├── controllers/                # [Controller Layer] Business logic
│   ├── __init__.py
│   ├── router.py               # Routing logic (Project loading & mode switching)
│   ├── history_manager.py      # Universal Undo/Redo system
│   │
│   ├── classification/         # Logic for Classification mode
│   │   ├── annotation_manager.py
│   │   ├── class_file_manager.py
│   │   └── navigation_manager.py
│   │
│   ├── localization/           # Logic for Localization mode
│   │   ├── loc_file_manager.py
│   │   └── localization_manager.py
│   │
│   └── description/            # [NEW] Logic for Description mode
│       ├── desc_annotation_manager.py # Handles text editor & save logic
│       ├── desc_file_manager.py       # Handles JSON I/O for description
│       └── desc_navigation_manager.py # Handles interaction with shared Tree Model
│
└── ui/                         # [View Layer] Interface definitions
    ├── common/                 # Shared widgets & layouts
    │   ├── main_window.py      # Main UI Assembler (Stacks Views)
    │   ├── workspace.py        # Generic 3-Column Layout (UnifiedTaskPanel)
    │   ├── clip_explorer.py    # Universal Left Sidebar (QTreeView)
    │   ├── project_controls.py # Unified control buttons (Save, Export, etc.)
    │   ├── dialogs.py          # Pop-up dialogs (Wizard, File Picker)
    │   └── welcome_widget.py   # Welcome screen
    │
    ├── classification/         # UI components for Classification
    │   ├── media_player/       # [Widget] Center Panel components
    │   │   ├── preview.py
    │   │   ├── controls.py
    │   │   └── __init__.py
    │   └── event_editor/       # [Widget] Right Panel components
    │       ├── dynamic_widgets.py
    │       ├── editor.py
    │       └── __init__.py
    │
    ├── localization/           # UI components for Localization
    │   ├── media_player/       # [Widget] Center Panel components
    │   │   ├── preview.py
    │   │   ├── timeline.py
    │   │   ├── controls.py
    │   │   └── __init__.py
    │   └── event_editor/       # [Widget] Right Panel components
    │       ├── annotation_table.py
    │       ├── spotting_controls.py
    │       └── __init__.py
    │
    └── description/            # [NEW] UI components for Description
        ├── media_player/       # [Widget] Center Panel components
        │   ├── preview.py      # Video player with robust loading logic
        │   ├── controls.py     # Simple playback controls
        │   └── __init__.py
        └── event_editor/       # [Widget] Right Panel components
            ├── editor.py       # Text editor for Captions/Q&A
            └── __init__.py

```

---

## 📝 File & Module Descriptions

### 1. Root Directory (Core Infrastructure)

These files form the backbone of the application infrastructure.

* **`main.py`**: The bootstrap script. Initializes the `QApplication` and launches the main window.
* **`viewer.py`**: Defines the `ActionClassifierApp` (Main Window). It acts as the primary **Controller**, initializing the shared `ProjectTreeModel` and connecting UI signals to specific Logic Controllers based on the active mode.
* **`utils.py`**: Utility functions for file handling, natural sorting, and icon generation.

### 2. Models (`/models`)

The **Data Layer**. These files handle the application state, data structures, and validation logic. They are completely decoupled from the UI.

* **`app_state.py`**: The core Application State. Stores runtime data (`manual_annotations`, `localization_events`, `action_item_data`), defines Undo/Redo stacks, and contains strict JSON schema validation logic for all three modes.
* **`project_tree.py`**: The **Qt Standard Item Model**. This is the data source for the project tree. It inherits from `QStandardItemModel` and manages the hierarchical data of clips and source files using standard Qt roles.

### 3. User Interface (`/ui`)

The **View Layer**. Contains PyQt6 widgets and layout definitions. The UI structure uses **Passive Views**—widgets generally do not contain business logic.

#### Common Components (`/ui/common`)

* **`main_window.py`**: The top-level UI container. Manages the `QStackedLayout` to switch between Welcome, Classification, Localization, and Description views.
* **`workspace.py`**: Defines `UnifiedTaskPanel`. A generic 3-column skeleton that embeds the shared `CommonProjectTreePanel` on the left.
* **`clip_explorer.py`**: Defines `CommonProjectTreePanel`. The **Shared View** for the project list. Uses `QTreeView` to visualize `ProjectTreeModel`.
* **`project_controls.py`**: Unified control buttons (Save, Export, Add Video) used in the sidebar.

#### Classification Components (`/ui/classification`)

* **`media_player/`**: Contains the **Center Panel** widgets (Video Player, Slider).
* **`event_editor/`**: Contains the **Right Panel** widgets (Dynamic Radio/Checkbox groups driven by Schema).

#### Localization Components (`/ui/localization`)

* **`media_player/`**: Contains the **Center Panel** widgets (Timeline, Custom Video Player).
* **`event_editor/`**: Contains the **Right Panel** widgets (Tabbed Spotting Interface, Annotation Table).

#### Description Components (`/ui/description`) [NEW]

* **`media_player/`**: Contains the **Center Panel** widgets. Features a specialized video player with explicit "Stop-Load-Delay-Play" logic to prevent black screens during rapid navigation.
* **`event_editor/`**: Contains the **Right Panel** widgets. A streamlined text editor that formats `questions` and `captions` metadata into a unified "Q: ... A: ..." block for editing.

### 4. Controllers (`/controllers`)

The **Logic Layer**. Pure Python logic handling business rules, data manipulation, and bridging Models and Views.

#### Shared Controllers

* **`router.py`**: Handles project lifecycle (Load/Create/Close). Determines which mode to launch (Classification/Localization/Description) based on JSON structure.
* **`history_manager.py`**: Manages the Command Pattern implementation for the Undo/Redo system.

#### Classification Sub-module (`/controllers/classification`)

* **`class_file_manager.py`**: Handles JSON I/O. Clears the **Model** directly upon workspace reset.
* **`navigation_manager.py`**: Manages video navigation and filtering via `setRowHidden`.
* **`annotation_manager.py`**: Handles schema logic and saving user selections.

#### Localization Sub-module (`/controllers/localization`)

* **`loc_file_manager.py`**: Handles JSON I/O for localization.
* **`localization_manager.py`**: Core logic for action spotting. Listens to View selection changes to trigger video loading.

#### Description Sub-module (`/controllers/description`) [NEW]

* **`desc_file_manager.py`**: Handles JSON I/O for description/captioning. Parses the `Action -> Inputs` hierarchy and populates the tree.
* **`desc_navigation_manager.py`**: Manages file navigation.
* Implements logic to automatically play child video clips when a parent Action node is selected.
* Includes robust playback logic (Stop -> Load -> Delay -> Play) to ensure stability.
* Handles adding new video files to the project.


* **`desc_annotation_manager.py`**: Manages the right-hand text editor.
* Loads metadata questions and formats them with existing captions.
* Saves edited text back to the model, flattening the structure (removing explicit question keys) upon confirmation.
* Implements auto-advance logic after saving.



### 5. Style (`/style`)

* **`style.qss`**: CSS-like definitions for the default **Dark Theme**.
