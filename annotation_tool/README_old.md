# SoccerNet Pro Annotation Tool

This project is a professional video annotation desktop application built with **PyQt6**. It features a comprehensive tri-mode architecture supporting **Whole-Video Classification**, **Action Spotting (Localization)**, and **Video Captioning (Description)** tasks.

The project follows a modular **MVC (Model-View-Controller)** design pattern to ensure separation of concerns between data handling, business logic, and user interface. Recent updates have unified the UI architecture using a composite design pattern, migrated resource management to a robust **Qt Model/View** architecture, and standardized video playback logic to prevent rendering race conditions.

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
│   ├── app_state.py            # Global Application State & Undo/Redo Stack (CmdType for all modes)
│   └── project_tree.py         # Shared QStandardItemModel for File Tree (MV Pattern)
│
├── style/                      # Visual theme assets
│   └── style.qss               # Centralized Dark mode stylesheet (ID-based styling)
│
├── controllers/                # [Controller Layer] Business logic
│   ├── __init__.py
│   ├── router.py               # Routing logic (View-First loading strategy)
│   ├── history_manager.py      # Universal Undo/Redo system (Supports Class, Loc, and Desc)
│   ├── media_controller.py     # Unified Media Playback Logic (Anti-freeze/Black screen fix)
│   │
│   ├── classification/         # Logic for Classification mode
│   │   ├── class_annotation_manager.py # Handles schema logic & manual annotation saving
│   │   ├── class_file_manager.py       # Handles JSON I/O for classification
│   │   └── class_navigation_manager.py # Manages video navigation & playback integration
│   │
│   ├── localization/           # Logic for Localization mode
│   │   ├── loc_file_manager.py
│   │   └── localization_manager.py
│   │
│   └── description/            # Logic for Description/Captioning mode
│       ├── desc_annotation_manager.py  # Handles text edits & Undo command generation
│       ├── desc_file_manager.py        # JSON I/O & Tree population for Description
│       └── desc_navigation_manager.py  # Video playback & tree navigation logic
│
└── ui/                         # [View Layer] Interface definitions
    ├── common/                 # Shared widgets & layouts
    │   ├── main_window.py      # Main UI Assembler (Stacks Views)
    │   ├── workspace.py        # Generic 3-Column Layout (UnifiedTaskPanel)
    │   ├── clip_explorer.py    # Universal Sidebar (Project Tree View)
    │   ├── project_controls.py # Unified control buttons (Save, Export, etc.)
    │   ├── video_surface.py    # Universal Pure Video Rendering Widget (Shared)
    │   ├── dialogs.py          # Pop-up dialogs (Wizard, File Picker)
    │   └── welcome_widget.py   # Welcome screen
    │
    ├── classification/         # UI components for Classification
    │   ├── media_player/       # Video Playback widgets
    │   │   ├── player_panel.py  # Container using shared video_surface + controls
    │   │   └── controls.py      # Playback buttons
    │   └── event_editor/       # Dynamic Radio/Checkbox Schema Editor
    │
    ├── localization/           # UI components for Localization
    │   ├── media_player/       # Video Playback widgets
    │   │   ├── player_panel.py  # Wrapper for shared video_surface
    │   │   └── timeline.py      # Custom scalable timeline
    │   └── event_editor/       # Spotting Interface & Annotation Table
    │
    └── description/            # UI components for Description
        ├── media_player/       # Video Playback widgets
        │   ├── player_panel.py  # Container using shared video_surface + slider (Styled via QSS)
        │   └── controls.py      # Navigation controls
        └── event_editor/       # Text-based Caption Editor (Styled via QSS)


```

---

## 📝 File & Module Descriptions

### 1. Root Directory (Core Infrastructure)

These files form the backbone of the application infrastructure.

* **`main.py`**: The bootstrap script. Initializes the `QApplication` and launches the main window.
* **`viewer.py`**: Defines the `ActionClassifierApp` (Main Window). It acts as the primary **Controller**, initializing the shared `ProjectTreeModel` and connecting UI signals to specific Logic Controllers.
* *Update:* Implements `stop_all_players()` to forcefully release media resources during mode switching, preventing "ghost frames" and black screens. Handles refresh logic for Description mode Undo/Redo.
* **`utils.py`**: Utility functions for file handling, natural sorting, and icon generation.

### 2. Models (`/models`)

The **Data Layer**. These files handle the application state, data structures, and validation logic. They are completely decoupled from the UI.

* **`app_state.py`**: The core Application State. Stores runtime data (`manual_annotations`, `localization_events`, `action_item_data`), defines Undo/Redo stacks (now including `DESC_EDIT` for description mode), and contains strict JSON schema validation logic for all three modes.
* **`project_tree.py`**: The **Qt Standard Item Model**. This is the data source for the project tree. It inherits from `QStandardItemModel` and manages the hierarchical data of clips and source files using standard Qt roles.

### 3. User Interface (`/ui`)

The **View Layer**. Contains PyQt6 widgets and layout definitions. The UI structure uses **Passive Views**—widgets generally do not contain business logic.

#### Common Components (`/ui/common`)

* **`main_window.py`**: The top-level UI container. Manages the `QStackedLayout` to switch between Welcome, Classification, Localization, and Description views.
* **`workspace.py`**: Defines `UnifiedTaskPanel`. A generic 3-column skeleton that embeds the shared `CommonProjectTreePanel`.
* **`clip_explorer.py`**: Defines `CommonProjectTreePanel`. The **Shared View** for the project list using `QTreeView`.
* **`video_surface.py`**: The **Shared Video Renderer**. A clean `QVideoWidget` + `QMediaPlayer` implementation used by all three modes to ensure consistent rendering performance and behavior across the application.
* **`project_controls.py`**: Unified control buttons (Save, Export, Add Video) used in the sidebar.

#### Classification Components (`/ui/classification`)

* **`media_player/`**:
* **`player_panel.py`**: The media container. Instances the shared `ui.common.VideoSurface` and adds a progress slider underneath.
* **`controls.py`**: The bottom navigation toolbar (Play/Pause, Prev/Next, Multi-view).


* **`event_editor/`**: Dynamic Radio/Checkbox groups driven by the JSON schema.

#### Localization Components (`/ui/localization`)

* **`media_player/`**:
* **`player_panel.py`**: Acts as a wrapper for the shared `VideoSurface`, exposing APIs compatible with the Localization Manager.
* **`timeline.py`**: A custom-drawn, zoomable timeline widget for precise action spotting.


* **`event_editor/`**: Tabbed Spotting Interface and Annotation Table.

#### Description Components (`/ui/description`)

* **`media_player/`**:
* **`player_panel.py`**: Instances the shared `VideoSurface` and adds a simple slider. Visual styling is now decoupled into `style.qss`.
* **`controls.py`**: Navigation buttons specific to the Action/Clip hierarchy.


* **`event_editor/`**: Text Editor for Q&A/Descriptions with Confirm/Clear controls. Now uses ID-based styling (`descCaptionEdit`, `descConfirmBtn`) defined in `style.qss`.

### 4. Controllers (`/controllers`)

The **Logic Layer**. Pure Python logic handling business rules, data manipulation, and bridging Models and Views.

#### Shared Controllers

* **`router.py`**: Handles project lifecycle (Load/Create/Close). Determines which mode to launch based on JSON structure.
* *Update:* Implements a "View-First" loading strategy to ensure video widgets are visible and initialized *before* media loading begins, preventing initialization failures on macOS.


* **`history_manager.py`**: Manages the Command Pattern implementation for the Undo/Redo system.
* *Update:* Now supports **Description Mode** (`DESC_EDIT` command), handling text reversion and UI refreshing.


* **`media_controller.py`**: A unified controller for managing video playback logic across all modes.
* Enforces a standardized playback sequence (Stop -> Clear -> Load -> Delay -> Play) to eliminate black screens.
* Handles timer cancellation to prevent race conditions during rapid project switching.
* Forces UI repaints to clear "stuck frames" from video memory.



#### Classification Sub-module (`/controllers/classification`)

* **`class_file_manager.py`**: Handles JSON I/O for classification tasks.
* **`class_navigation_manager.py`**: Manages video navigation. Integrated with `media_controller` for robust playback.
* **`class_annotation_manager.py`**: Handles schema logic and saving user selections via Command pattern.

#### Localization Sub-module (`/controllers/localization`)

* **`loc_file_manager.py`**: Handles JSON I/O for localization tasks.
* **`localization_manager.py`**: Core logic for action spotting, timestamp recording, and timeline synchronization. Integrated with `media_controller`.

#### Description Sub-module (`/controllers/description`)

* **`desc_file_manager.py`**: Handles JSON I/O for captioning tasks.
* **`desc_navigation_manager.py`**: Manages file navigation and playback logic specific to description tasks.
* *Update:* Integrated with `media_controller` (disabled looping to match Classification stability) and fixed auto-selection logic for new items.


* **`desc_annotation_manager.py`**: Handles the Q&A text formatting logic.
* *Update:* Implements `push_undo` logic to support full Undo/Redo capabilities for text edits.



### 5. Style (`/style`)

* **`style.qss`**: CSS-like definitions for the default **Dark Theme**.
* *Update:* Contains centralized styling for Description components (Buttons, Text Editor, Labels) using Object ID selectors, keeping Python UI code clean.
