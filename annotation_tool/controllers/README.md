# ⚙️ Controllers Module (Logic Layer)

This directory contains the business logic of the **SoccerNet Pro Annotation Tool**. 
Following the **MVC (Model-View-Controller)** architecture, these scripts act as the bridge between the data (`models.py`) and the interface (`ui/`). They handle user input, data processing, file I/O, and application state management.

## 📂 Directory Structure

```text
controllers/
├── history_manager.py      # Universal Undo/Redo logic
├── router.py               # Application routing and mode switching
├── classification/         # Logic specific to Whole-Video Classification
└── localization/           # Logic specific to Action Spotting (Localization)

```

---

## 📦 Module Details

### 1. Core Controllers (Root)

These controllers provide foundational functionality used across the entire application.

* **`router.py`**
* **Role**: The "Traffic Cop" of the application.
* **Responsibilities**:
  * Handles the "Create Project" and "Load Project" flows.
  * Analyzes input JSON files to determine if the project is **Classification** or **Localization**.
  * Initializes the appropriate specific managers and switches the UI view accordingly.




* **`history_manager.py`**
* **Role**: The "Time Machine" (Undo/Redo System).
* **Responsibilities**:
  * Implements the **Command Pattern** to manage the Undo/Redo stacks in `AppStateModel`.
  * Executes undo/redo operations and triggers the necessary UI refreshes (`_refresh_active_view`) depending on whether the user is in Classification or Localization mode.





### 2. Classification Controllers (`controllers/classification/`)

Logic dedicated to the **Whole-Video Classification** task (assigning attributes to an entire video clip).

* **`class_file_manager.py`**
  * Handles JSON I/O for classification projects.
  * Manages relative path calculations for portability.
  * Resets the workspace when closing projects.


* **`navigation_manager.py`**
  * Manages the "Action List" (Left Panel) interactions.
  * Handles video playback flow, including auto-playing the next video and filtering the list (Done/Not Done).


* **`annotation_manager.py`**
  * Manages the dynamic schema logic (adding/removing Label Heads and Label Options).
  * Processes user input from the Right Panel and saves annotations to the `AppStateModel`.



### 3. Localization Controllers (`controllers/localization/`)

Logic dedicated to the **Action Spotting** task (pinpointing specific timestamps within a video).

* **`loc_file_manager.py`**
  * Handles JSON I/O for localization projects.
  * Includes **Path Fallback** logic: if an absolute path in the JSON is missing, it attempts to find the video in the local directory to support cross-device collaboration.


* **`localization_manager.py`**
  * **Role**: The central hub for the Localization UI.
  * **Responsibilities**:
    * Synchronizes the **Video Player**, **Timeline Widget**, and **Event Table**.
    * Captures timestamps when users trigger a spotting event.
    * Manages the Multi-Tab interface for different event categories.
