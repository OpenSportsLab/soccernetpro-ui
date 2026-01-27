# SoccerNet Pro Annotation Tool

This project is a professional video annotation desktop application built with **PyQt6**. It features a dual-mode architecture supporting both **Whole-Video Classification** and **Action Spotting (Localization)** tasks.

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
│   │   └── navigation_manager.py # Handles interaction with the shared Tree Model
│   │
│   └── localization/           # Logic for Localization mode
│       ├── loc_file_manager.py
│       └── localization_manager.py # Handles interaction with the shared Tree Model
│
└── ui/                         # [View Layer] Interface definitions
    ├── common/                 # Shared widgets & layouts
    │   ├── main_window.py      # Main UI Assembler (Stacks Views)
    │   ├── workspace.py        # Generic 3-Column Layout (UnifiedTaskPanel)
    │   ├── clip_explorer.py    # Universal Left Sidebar (QTreeView implementation)
    │   ├── project_controls.py # Unified control buttons (Save, Export, etc.)
    │   ├── dialogs.py          # Pop-up dialogs (Wizard, File Picker)
    │   └── welcome_widget.py   # Welcome screen
    │
    ├── classification/         # UI components for Classification
    │   ├── media_player/       # [Widget] Center Panel components
    │   │   ├── preview.py      # Video player wrapper
    │   │   ├── controls.py     # Navigation toolbar
    │   │   └── __init__.py     # Exposes ClassificationMediaPlayer
    │   │
    │   └── event_editor/       # [Widget] Right Panel components
    │       ├── dynamic_widgets.py # Schema-driven widgets (Radio/Check)
    │       ├── editor.py       # Layout container
    │       └── __init__.py     # Exposes ClassificationEventEditor
    │
    └── localization/           # UI components for Localization
        ├── media_player/       # [Widget] Center Panel components
        │   ├── preview.py      # Video player wrapper
        │   ├── timeline.py     # Custom Zoomable Timeline
        │   ├── controls.py     # Playback control bar
        │   └── __init__.py     # Exposes LocCenterPanel
        │
        └── event_editor/       # [Widget] Right Panel components
            ├── annotation_table.py  # Event list table
            ├── spotting_controls.py # Tabbed spotting interface
            └── __init__.py          # Exposes LocRightPanel
```
---

## 📝 File & Module Descriptions

### 1. Root Directory (Core Infrastructure)

These files form the backbone of the application infrastructure.

* **`main.py`**: The bootstrap script. Initializes the `QApplication` and launches the main window.
* **`viewer.py`**: Defines the `ActionClassifierApp` (Main Window). It acts as the primary **Controller**, initializing the shared `ProjectTreeModel` and connecting UI signals to specific Logic Controllers.
* **`utils.py`**: Utility functions for file handling, natural sorting, and icon generation.

### 2. Models (`/models`)

The **Data Layer**. These files handle the application state, data structures, and validation logic. They are completely decoupled from the UI.

* **`app_state.py`** (formerly `models.py`): The core Application State. Stores runtime data (`manual_annotations`, `localization_events`), defines Undo/Redo stacks (`CmdType`), and contains strict JSON schema validation logic.
* **`project_tree.py`**: The **Qt Standard Item Model**. This is the data source for the project tree. It inherits from `QStandardItemModel` and manages the hierarchical data of clips and source files using standard Qt roles.
* **`__init__.py`**: Exposes the models as a package.

### 3. User Interface (`/ui`)

The **View Layer**. Contains PyQt6 widgets and layout definitions. The UI structure uses **Passive Views**—widgets generally do not contain business logic.

#### Common Components (`/ui/common`)

* **`main_window.py`**: The top-level UI container. Manages the `QStackedLayout` to switch between Welcome, Classification, and Localization views.
* **`workspace.py`**: Defines `UnifiedTaskPanel`. A generic 3-column skeleton that embeds the shared `CommonProjectTreePanel` on the left.
* **`clip_explorer.py`**: Defines `CommonProjectTreePanel`. The **Shared View** for the project list.
* *MVC Update*: Now uses `QTreeView` instead of `QTreeWidget`. It acts purely as a viewer for `ProjectTreeModel` and does not store data itself.


* **`dialogs.py`**: Contains modal dialogs such as the **Project Creation Wizard** and custom **Folder Picker**.
* **`project_controls.py`**: Unified control buttons (Save, Export, Add Video) used in the sidebar.

#### Classification Components (`/ui/classification`)

* **`media_player/`**: Contains the **Center Panel** widgets (Video Player, Slider).
* **`event_editor/`**: Contains the **Right Panel** widgets (Dynamic Radio/Checkbox groups driven by Schema).

#### Localization Components (`/ui/localization`)

* **`media_player/`**: Contains the **Center Panel** widgets (Timeline, Custom Video Player).
* **`event_editor/`**: Contains the **Right Panel** widgets (Tabbed Spotting Interface, Annotation Table).

### 4. Controllers (`/controllers`)

The **Logic Layer**. Pure Python logic handling business rules, data manipulation, and bridging Models and Views.

#### Shared Controllers

* **`router.py`**: Handles project lifecycle (Load/Create/Close). Determines which mode to launch and manages the global state reset.
* **`history_manager.py`**: Manages the Command Pattern implementation for the Undo/Redo system.

#### Classification Sub-module (`/controllers/classification`)

* **`class_file_manager.py`**: Handles JSON I/O for classification. Clears the **Model** (`ProjectTreeModel`) directly upon workspace reset.
* **`navigation_manager.py`**: Manages video navigation.
* *MVC Update*: Manipulates the `ProjectTreeModel` (e.g., adding/removing rows) instead of the UI widget. Filters are applied via `setRowHidden` on the View based on Model data.


* **`annotation_manager.py`**: Handles schema logic and saving user selections. Adapts UI signals to update the `AppStateModel`.

#### Localization Sub-module (`/controllers/localization`)

* **`loc_file_manager.py`**: Handles JSON I/O for localization.
* **`localization_manager.py`**: Core logic for action spotting.
* *MVC Update*: Listens to `selectionModel().currentChanged` from the View to trigger video loading. Updates the `ProjectTreeModel` directly when clips are added or removed.



### 5. Style (`/style`)

* **`style.qss`**: CSS-like definitions for the default **Dark Theme**.


