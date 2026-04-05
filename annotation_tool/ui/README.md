# 🎨 User Interface (UI) Module

This directory contains the **View layer** of the application's MVC architecture. It is responsible solely for graphical presentation, user interaction, and data visualization.

**Note:** No business logic, AI inference, or data manipulation is performed here. All user interactions (clicks, edits, playback controls) are emitted as **Qt Signals** to be handled by the `controllers` module.

## 📂 Directory Structure

The UI is organized by functional domain, with a robust **Common** library supporting four distinct annotation modes, two of which are supercharged with AI capabilities:

```text
ui/
├── common/               # Shared architecture (Main Window, Workspace Skeleton, Dialogs)
│   ├── main_window.py    # Top-level Stacked Layout orchestrator
│   ├── workspace.py      # Unified 3-column layout skeleton
│   ├── video_surface.py  # Shared video rendering widget (Anti-ghost frame)
│   └── ...
│
├── classification/       # [Mode 1] Whole-Video Classification & AI Training
├── localization/         # [Mode 2] Action Spotting & AI Smart Spotting
├── description/          # [Mode 3] Global Description (Captions)
└── dense_description/    # [Mode 4] Dense Description (Timestamped Text)
```

---

## 🧩 Modules Description

### 1. Common (`ui/common/`)

The backbone of the application, ensuring a consistent user experience and stable video rendering across all modes.

* **`main_window.py`**: The application entry point. It manages a `QStackedLayout` to switch between the **Welcome Screen** and the four **Workspaces** without destroying state.
* **`workspace.py`**: Defines the `UnifiedTaskPanel`. This is the generic 3-column skeleton (Left Tree | Center Player | Right Editor) used by **every** mode to maintain layout consistency.
* **`video_surface.py`**: A pure rendering widget wrapping `QMediaPlayer` and `QVideoWidget`. It provides a clean slate for the centralized `MediaController` to manage playback.
* **`clip_explorer.py`**: The **Left Sidebar**. Uses **Qt Model/View** (`QTreeView`) for high performance. It handles file navigation and advanced filtering (e.g., "Hand Labelled", "Smart Labelled").
* **`dialogs.py`**: 
  * `ProjectTypeDialog`: Wizard allowing selection of the four working modes.
  * `ClassificationTypeDialog`: Asks user to specify Single-View or Multi-View formats.

---

### 2. Classification (`ui/classification/`)

Implements the interface for **Whole-Video Classification** and Model Training.

* **`media_player/`**: Combines the shared `VideoSurface` with high-level dataset navigation controls (`<< Prev Action`, `Next Clip >`).
* **`event_editor/`**: Upgraded into a **Tabbed Command Center**:
  * **Hand Annotation**: Dynamically generated Radio/Checkbox groups based on the JSON schema.
  * **Smart Annotation**: UI for single/batch AI inference, featuring dynamic range dropdowns and a highly optimized `NativeDonutChart` built with `QPainter` for interactive confidence visualization.
  * **Train**: In-app fine-tuning UI with hyperparameter inputs, real-time terminal console, and progress bars.

---

### 3. Localization (`ui/localization/`)

Implements the interface for **Action Spotting** (identifying specific timestamps).

* **`media_player/`**:
  * Features the **Zoomable Timeline** that draws multi-colored visual markers (Blue for manual/confirmed, Gold for pending AI predictions) and auto-follows the playhead.
* **`event_editor/`**: Upgraded into a **Tabbed Command Center**:
  * **Hand Spotting**: Rapid-fire grid buttons using Bin-Packing layouts for defining event categories.
  * **Smart Spotting**: Custom `TimeLineEdit` widgets to set inference ranges, and a dual-table layout to review pending AI predictions vs. confirmed events.
  * **Annotation Table**: A spreadsheet view for editing events, including a new "Set to Current Video Time" button.

---

### 4. Description (`ui/description/`)

Implements the interface for **Global Captioning** (one text description per video).

* **`media_player/`**:
  * **Composite Player**: Combines the video surface with a specialized navigation toolbar. Defaults to **Infinite Loop** to allow repeated viewing while typing.
* **`event_editor/`**:
  * **Text Input**: A large `QTextEdit` for free-form text. Parses JSON questions into readable Q&A formats dynamically.

---

### 5. Dense Description (`ui/dense_description/`)

Implements the interface for **Dense Captioning** (text descriptions anchored to specific timestamps).

* **`event_editor/`**:
  * **Input Widget**: A specialized panel showing the current video time alongside a text input area.
  * **Dense Table**: A subclass of the Localization table. It replaces the "Label" column with a "Description" column and auto-sizes to a **2:1:4 ratio** (Time : Lang : Text).
* **Reuse**: This mode shares the **Localization Center Panel** (Timeline + Player) to allow precise temporal navigation between text events.

---

## 🎨 Design Principles

1. **Passive View**: These classes do not modify data directly. They display data provided by the controller and emit signals (e.g., `smart_confirm_requested`, `annotation_deleted`) when the user acts.
2. **Unified Skeleton**: All modes inherit the same `UnifiedTaskPanel` structure. This ensures that the Sidebar and Media Player always appear in the same relative locations, reducing cognitive load.
3. **Tabbed Contexts (Progressive Disclosure)**: Advanced AI features are tucked into logical tabs. This ensures manual annotators are not overwhelmed by training parameters or inference controls unless they explicitly need them.
4. **Dynamic Generation**: Where possible, forms, buttons, and tables adjust their content dynamically based on the loaded JSON schema or data model.
