
# SoccerNet Pro Annotation Tool

This project is a professional video annotation desktop application built with **PyQt6**. It features a dual-mode architecture supporting both **Whole-Video Classification** and **Action Spotting (Localization)** tasks.

The project follows a modular **MVC (Model-View-Controller)** design pattern to ensure separation of concerns between data handling, business logic, and user interface.

## 📂 Project Structure Overview

```text
annotation_tool/
├── main.py                     # Application entry point
├── viewer.py                   # Main Window controller (orchestrates UI & Logic)
├── models.py                   # Data models, application state, and JSON validation
├── router.py                   # Routing logic (Project loading & mode switching)
├── history_manager.py          # Universal Undo/Redo system
├── dialogs.py                  # Custom pop-up dialogs (Project creation, file picking)
├── utils.py                    # Helper functions and constants
├── style.qss / style_day.qss   # Theme stylesheets (Dark/Light mode)
│
├── controllers/                # [Logic Layer] Business logic separated by task
│   ├── classification/         # Logic for Classification mode
│   │   ├── annotation_manager.py
│   │   ├── class_file_manager.py
│   │   └── navigation_manager.py
│   └── localization/           # Logic for Localization mode
│       ├── loc_file_manager.py
│       └── localization_manager.py
│
└── ui/                         # [View Layer] Interface definitions
    ├── common/                 # Shared widgets used by both modes
    │   └── project_controls.py
    ├── classification/         # UI specific to Classification task
    │   ├── panels.py
    │   └── widgets.py
    └── localization/           # UI specific to Localization task
        ├── panels.py
        └── widgets/
            ├── clip_explorer.py
            ├── media_player.py
            └── event_editor.py

```

---

## 📝 File & Module Descriptions

### 1. Core Components (Root Directory)

These files form the backbone of the application infrastructure.

* **`main.py`**: The bootstrap script. Initializes the `QApplication` and launches the main window.
* **`viewer.py`**: Defines the `ActionClassifierApp` (Main Window). It acts as the primary bridge, initializing the UI layout and connecting UI signals to their respective Controllers.
* **`models.py`**: The **Model**. Stores runtime data (`manual_annotations`, `localization_events`), defines the Undo/Redo stacks, and contains strict JSON schema validation logic.
* **`router.py`**: Handles project lifecycle. It determines whether to load the "Classification" view or "Localization" view based on the input JSON structure.
* **`history_manager.py`**: Manages the Command Pattern implementation for the Undo/Redo system, ensuring UI updates trigger correctly after history operations.
* **`dialogs.py`**: Contains modal dialogs such as the **Project Creation Wizard** and the custom **Folder Picker**.
* **`utils.py`**: Utility functions for file handling, natural sorting, and icon generation.

### 2. Controllers (`/controllers`)

Pure Python logic handling business rules and data manipulation.

#### Classification

* **`class_file_manager.py`**: Handles JSON I/O for classification tasks, including relative path calculation and workspace clearing.
* **`navigation_manager.py`**: Manages the video list navigation, filtering (Done/Not Done), and playback flow for whole-video tasks.
* **`annotation_manager.py`**: Handles the logic for dynamic schema creation (adding/removing labels) and saving user selections to the model.

#### Localization

* **`loc_file_manager.py`**: Handles JSON I/O for localization tasks, including path fallback mechanisms for cross-device compatibility.
* **`localization_manager.py`**: The core logic for action spotting. It synchronizes the video player, timeline, and event table, handling timestamp capture and modification.

### 3. User Interface (`/ui`)

PyQt6 widgets and layout definitions. Contains no business logic.

#### Common (`/ui/common`)

* **`project_controls.py`**: A unified 3x2 control panel (Create, Load, Add, Close, Save, Export) shared by both modes to ensure consistent UX.

#### Classification (`/ui/classification`)

* **`panels.py`**: Defines the `LeftPanel` (List), `CenterPanel` (Player), and `RightPanel` (Annotation inputs) layouts.
* **`widgets.py`**: Custom widgets including `DynamicSingleLabelGroup` (Radio buttons) and `DynamicMultiLabelGroup` (Checkboxes) generated from the project schema.

#### Localization (`/ui/localization`)

* **`panels.py`**: Defines the layout containers for the localization interface.
* **`widgets/clip_explorer.py`**: The left sidebar widget for managing the list of video clips.
* **`widgets/media_player.py`**: The center widget containing the video player, custom zoomable timeline, and playback controls.
* **`widgets/event_editor.py`**: The right sidebar widget containing the multi-tab spotting interface and the editable event table.
