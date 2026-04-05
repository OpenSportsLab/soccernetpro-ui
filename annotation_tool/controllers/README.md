# ⚙️ Controllers Module (Logic Layer)

This directory contains the business logic of the **SoccerNet Pro Annotation Tool**. Following the **MVC (Model-View-Controller)** architecture, these scripts act as the bridge between the central data (`models.py`) and the user interface (`ui/`). They handle user input, data processing, file I/O, application state management, and the newly integrated **AI Model Inference & Training**.

## 📂 Directory Structure

```text
controllers/
├── media_controller.py     # Unified Video Playback Manager (Anti-freeze logic)
├── history_manager.py      # Universal Undo/Redo logic (Supports Batch AI Actions)
├── router.py               # Application routing and mode switching
├── classification/         # Logic specific to Whole-Video Classification & AI
├── localization/           # Logic specific to Action Spotting (Timestamps) & AI
├── description/            # Logic specific to Global Captioning (Text)
└── dense_description/      # Logic specific to Dense Captioning (Timestamped Text)
```

---

## 📦 Module Details

### 1. Core Controllers (Root)

These controllers provide foundational functionality used across the entire application to ensure stability and consistency.

* **`media_controller.py`**
  * **Role**: The centralized video playback engine used by all modes.
  * **Responsibilities**:
    * **Robust State Management**: Implements a strict `Stop -> Clear -> Load -> Delay -> Play` sequence to prevent black screens and buffer artifacts.
    * **Race Condition Prevention**: Uses an internal `QTimer` that is explicitly cancelled upon stop, preventing videos from starting in the background after a user has closed a project.
    * **Visual Clearing**: Forces the `QVideoWidget` to repaint/update on stop, ensuring no "stuck frames" remain visible.

* **`router.py`**
  * **Role**: The "Traffic Cop" of the application.
  * **Responsibilities**:
    * Handles the "Create Project" and "Load Project" flows.
    * Analyzes input JSON files (keys like `events`, `captions`, `labels`, `smart_labels`) to automatically detect the project mode.
    * Initializes the appropriate specific managers and switches the UI view.

* **`history_manager.py`**
  * **Role**: The "Time Machine" (Undo/Redo System).
  * **Responsibilities**:
    * Implements the **Command Pattern** to manage the Undo/Redo stacks in `AppStateModel`.
    * **[NEW] AI Batch Support**: Handles complex state reversions for massive batch smart annotations across multiple videos simultaneously.
    * Executes operations and triggers the necessary UI refreshes (`_refresh_active_view`) for all four modes.

---

### 2. Classification Controllers (`controllers/classification/`)

Logic dedicated to the **Whole-Video Classification** task, now supercharged with AI workflows.

* **`inference_manager.py` [NEW]**: Orchestrates AI predictions via `soccernetpro`. Dynamically parses `config.yaml`, handles background threading (`QThread`), and manages both Single and Batch video inference without freezing the UI.
* **`train_manager.py` [NEW]**: Manages the background training loop. Injects user-defined UI hyperparameters into a runtime config, runs `myModel.train()`, and intercepts PyTorch logs to drive the UI progress bar and console.
* **`class_file_manager.py`**: Handles JSON I/O, relative path calculations, and the seamless preservation of `smart_labels` and confidence scores.
* **`class_navigation_manager.py`**: Manages the dataset tree, playback synchronization, and advanced 4-state AI visibility filtering (All / Hand Labelled / Smart Labelled / No Labelled).
* **`class_annotation_manager.py`**: Manages dynamic schema logic, saves manual class selections, and handles the confirmation workflow for AI-generated batch predictions.

---

### 3. Localization Controllers (`controllers/localization/`)

Logic dedicated to the **Action Spotting** task, utilizing temporal AI models.

* **`loc_inference.py` [NEW]**: Runs the heavy OpenSportsLib AI localization models in the background. Features dynamic FFmpeg sub-clipping to speed up targeted inference, automatic CPU fallback configuration, and absolute timestamp compensation.
* **`loc_file_manager.py`**: Handles JSON I/O with path fallback logic (checking local directories if absolute paths fail) and preserves `smart_localization_events` during export.
* **`localization_manager.py`**: 
  * Synchronizes the Video Player, Timeline Widget, and Event Table.
  * **[NEW] Smart Spotting Flow**: Manages the dual-state UI of unconfirmed AI predictions (Gold markers) vs. confirmed/manual events (Blue markers), including batch confirmations.

---

### 4. Description Controllers (`controllers/description/`)

Logic dedicated to the **Global Captioning** task (one text description per video action).

* **`desc_navigation_manager.py`**:
  * Manages **Multi-Clip Actions** (navigating logical "Actions" that may contain multiple video files).
  * Wraps the `MediaController` to ensure smooth loading of large video files.
* **`desc_annotation_manager.py`**:
  * Handles **Q&A Formatting**: Parses JSON "questions" into a readable Q&A format in the editor.
  * **Flattening**: Consolidates text into a single description block upon save.
* **`desc_file_manager.py`**:
  * Manages JSON I/O specific to the captioning schema, ensuring `inputs` and `captions` fields are preserved correctly.

---

### 5. Dense Description Controllers (`controllers/dense_description/`)

Logic dedicated to the **Dense Captioning** task (text descriptions anchored to specific timestamps).

* **`dense_manager.py`**:
  * **Editor-Timeline Sync**: Continuously synchronizes the text input field with the video playback position. If the video hits an event, the text loads automatically.
  * **CRUD**: Handles creating, updating, and deleting timestamped text events.
* **`dense_file_manager.py`**:
  * **Metadata Preservation**: Ensures global and item-level metadata is retained during Load/Save cycles.
  * **Data Mapping**: Maps the flat `dense_captions` JSON list to the internal application model.
