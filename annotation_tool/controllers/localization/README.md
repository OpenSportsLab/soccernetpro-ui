# 📍 Localization Controllers

This module contains the business logic specifically designed for the **Action Spotting (Localization)** task. It handles the "timestamp-based" annotation workflow, bridging the gap between the complex Localization UI and the data model.

## 📂 Module Contents

### 1. `loc_file_manager.py`
**Responsibility:** Data Persistence & Project Lifecycle.

This controller manages the loading, saving, and creation of localization project files (`.json`). It ensures data integrity and handles file path resolution.

* **Project Loading**: Validates the JSON schema (checking for `events` and `inputs` fields) before loading data into the `AppStateModel`.
* **Path Resolution**: Implements smart path fallback mechanisms. If an absolute path to a video is missing (e.g., when moving projects between computers), it attempts to resolve the video path relative to the JSON file.
* **Exporting**: Converts the internal data model into the standardized JSON format required for the SoccerNet ecosystem.
* **Workspace Management**: Handles the logic for clearing the interface (resetting the player, table, and lists) when closing a project.

### 2. `localization_manager.py`
**Responsibility:** User Interaction & Logic Orchestration.

This is the central "brain" for the localization view. It connects the visual components (Player, Timeline, Table) with the data model.

* **Event Spotting**: Captures the current timestamp from the media player when a user clicks a label button or uses a hotkey, creating a new event in the model.
* **Synchronization**: Keeps the three main views in sync:
    * **Media Player**: Seeks to the specific timestamp when a table row is clicked.
    * **Timeline**: Draws visual markers (red lines) on the custom timeline widget corresponding to event times.
    * **Table**: Updates the list of events dynamically as users add or remove annotations.
* **Dynamic Schema Handling**: Manages the logic for adding, removing, or renaming "Heads" (Categories) via the Tab interface.
* **Undo/Redo Integration**: Wraps user actions (adding/deleting events) into Command objects to support the global Undo/Redo history.

---

## 🔄 Workflow Diagram

1.  **User Action**: User clicks "Goal" button at `00:15`.
2.  **`localization_manager.py`**: 
    * Gets current time `15000ms`.
    * Creates event object: `{'head': 'Action', 'label': 'Goal', 'position_ms': 15000}`.
    * Updates `AppStateModel`.
    * Triggers UI refresh.
3.  **UI Update**: 
    * `TimelineWidget` paints a red line at 15s.
    * `AnnotationTableWidget` inserts a new row.
4.  **Save**: User clicks Save.
5.  **`loc_file_manager.py`**: Writes the model state to disk as JSON.
