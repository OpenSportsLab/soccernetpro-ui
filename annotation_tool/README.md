# Video Annotation Tool

This project is a professional video annotation desktop application built with **PyQt6**. It features a comprehensive **quad-mode** architecture supporting **Whole-Video Classification**, **Action Spotting (Localization)**, **Video Captioning (Description)**, and the newly integrated **Dense Video Captioning (Dense Description)**. 

With the latest update, both the **Classification** and **Localization** modes now feature **AI-Powered Smart Annotation and Training**. Users can leverage state-of-the-art models (e.g., `soccernetpro`, MViT) to automatically infer actions via single or batch processing, as well as configure model training directly through dedicated YAML configuration files.

The project follows a modular **MVC (Model-View-Controller)** design pattern to ensure strict separation of concerns. It leverages **Qt's Model/View architecture** for resource management and a unified **Media Controller** to ensure stable, high-performance video playback across all modalities.

---

## 📂 Project Structure Overview

```text
annotation_tool/
├── main.py                     # Application entry point
├── viewer.py                   # Main Window controller (Orchestrator)
├── utils.py                    # Helper functions and constants
├── class_config.yaml           # Training & Inference configuration for Classification
├── loc_config.yaml             # Inference configuration for Localization
├── __init__.py                 # Package initialization
│
├── models/                     # [Model Layer] Data Structures & State
│   ├── app_state.py            # Global State, Undo/Redo Stacks, & JSON Validation
│   └── project_tree.py         # Shared QStandardItemModel for the sidebar tree
│
├── controllers/                # [Controller Layer] Business Logic
│   ├── router.py               # Mode detection & Project lifecycle management
│   ├── history_manager.py      # Universal Undo/Redo system (Supports Batch AI Annotations)
│   ├── media_controller.py     # Unified playback logic (Anti-freeze/Visual clearing)
│   ├── classification/         # Logic for Classification mode
│   │   ├── class_annotation_manager.py # Manual & Smart label state management
│   │   ├── class_file_manager.py       # JSON I/O (Handles manual & smart labels)
│   │   ├── class_navigation_manager.py # Action tree navigation & AI 4-state filtering
│   │   ├── inference_manager.py        # AI Smart Annotation (Single/Batch Inference)
│   │   └── train_manager.py            # [NEW] AI Model Training Loop & Checkpointing
│   ├── localization/           # Logic for Action Spotting (Localization) mode
│   │   ├── loc_file_manager.py         # JSON I/O with absolute/relative path fallbacks
│   │   ├── localization_manager.py     # Manual Spotting & Dual-state Smart Event logic
│   │   └── loc_inference.py            # [NEW] AI Action Spotting & FFmpeg Sub-clipping
│   ├── description/            # Logic for Global Captioning (Description) mode
│   └── dense_description/      # Logic for Dense Captioning (Text-at-Timestamp)
│
├── ui/                         # [View Layer] Interface Definitions
│   ├── common/                 # Shared widgets (Main Window, Sidebar, Video Surface)
│   ├── classification/         # UI specific to Classification
│   │   ├── media_player/       # Unified VideoSurface + Action Controls
│   │   └── event_editor/       # [NEW] Tabbed UI (Hand Annotation | Smart Annotation | Train)
│   │       ├── dynamic_widgets.py # Single/Multi label dynamic radio & checkbox groups
│   │       └── editor.py          # NativeDonutChart, Batch Progress UI, & Training Console
│   ├── localization/           # UI specific to Localization
│   │   ├── media_player/       # Unified VideoSurface + Zoomable Auto-scrolling Timeline
│   │   └── event_editor/       # [NEW] Tabbed UI (Hand Spotting | Smart Spotting)
│   │       ├── annotation_table.py # Cell editing + "Sync-to-Current-Time" tool
│   │       ├── spotting_controls.py# Dynamic manual label grid (Bin-Packing layout)
│   │       └── smart_spotting.py   # AI Range Inference inputs & Dual Review Tables
│   ├── description/            # UI specific to Global Captioning (Full-video text)
│   └── dense_description/      # UI specific to Dense Description
│
└── style/                      # Visual theme assets
    └── style.qss               # Centralized Dark mode stylesheet
```
---

## 📝 Detailed Module Descriptions

### 1. Core Infrastructure & Routing

* **`main.py` & `viewer.py`**: Initializes the application, connects signals between UI components and Logic Controllers, and prevents resource leaks during mode switching.
* **`router.py`**: Features a heuristic detection engine that identifies project types from JSON keys to automatically load the correct UI mode.
* **`media_controller.py`**: A centralized video engine managing the strict "Stop -> Load -> Delay -> Play" sequence to eliminate black screens and GPU buffer artifacts across all modes.

### 2. Modality Logic (`/controllers`)

* **Classification AI Managers**: 
  * `inference_manager.py` dynamically parses `class_config.yaml` to run background PyTorch inferences without freezing the UI.
  * `train_manager.py` runs fine-tuning loops, intercepting logs to drive the UI progress bar.
* **Localization AI Managers**: 
  * `loc_inference.py` handles temporal AI spotting. It utilizes FFmpeg to extract precise sub-clips for faster processing and compensates absolute timestamps automatically.
* **Smart UI Sync**: Controllers now manage complex "Unconfirmed" vs "Confirmed" AI data states, enabling users to review batch predictions before merging them into the core JSON state.

### 3. The View Layer (`/ui`)

* **Tabbed Command Centers**: Both Classification and Localization now feature robust Tabbed interfaces in their right panels, securely isolating manual data entry from AI inference and model training workflows.
* **`NativeDonutChart`**: A highly optimized, custom `QPainter` widget in the Classification UI that visualizes AI confidence scores interactively.
* **`SmartSpottingWidget`**: Features dual-tables for Localization, allowing users to compare AI-predicted timestamps alongside their manual/confirmed annotations on the fly.
* **Shared `video_surface.py`**: A universal rendering component used by every mode to ensure ghost-frame-free video performance.

---

## 🔄 Reusability & Modality Comparison

The application is built on a "Composite Design" strategy. While each mode serves a different task, they share significant architectural DNA.

### Is Dense Description a reuse of Localization?

**Yes.** The Dense Description modality is essentially a **specialized evolution** of the Localization mode.

* **Shared Center Panel**: Both use the `LocCenterPanel`, which includes the zoomable `TimelineWidget` and `VideoSurface`.
* **Shared Data Logic**: Both are "Event-based" (data is tied to a `position_ms`) rather than "Clip-based".
* **Shared Table Interface**: The `DenseTableModel` is a direct subclass of `AnnotationTableModel`, inheriting all natural sorting and timestamp-parsing logic.

### Modality Feature Matrix

| Feature | Classification | Localization | Global Description | Dense Description |
| --- | --- | --- | --- | --- |
| **Primary Data** | Multi-choice Labels | Timestamped Labels | Global Video Text | Timestamped Text |
| **Center UI** | Multi-view Player | Timeline + Player | Slider + Player | Timeline + Player |
| **Right UI** | Tabbed (Hand/Smart/Train) | Tabbed (Hand/Smart) | Text Editor | Text Input + Table |
| **Code Base** | Unique | Shared with Dense | Unique | Shared with Loc |

---

## 🚀 Getting Started

1. **Select Mode**: Launch the app and use the "New Project" wizard to select one of the four modes.
2. **Import**: The `AppRouter` will automatically detect the correct modality if you import an existing JSON.
3. **Annotate Manually**:
   * Use the **Hand Annotation** tabs to create data manually.
   * In Localization/Dense modes, use the timeline markers and tables to jump directly to specific timestamps.
4. **AI Inference & Training**:
   * Navigate to the **Smart Annotation** or **Train** tabs in the Right Panel (available in Classification and Localization).
   * Ensure your model parameters are properly set in `class_config.yaml` or `loc_config.yaml`.
   * Run single/batch inferences, review the predictions visually, and click "Confirm" to merge them into your dataset.
