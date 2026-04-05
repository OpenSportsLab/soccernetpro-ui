# 📍 Event Editor Widget

## Overview

This module is responsible for the **Right Panel** of the Localization (Action Spotting) interface. With the latest updates, it has evolved from a purely manual tool into a **Tabbed Command Center** supporting both manual spotting and AI-powered batch inference. 

It provides the primary mechanisms for users to:
1.  **Hand Annotation**: "Spot" actions at specific timestamps using dynamic category buttons.
2.  **Smart Annotation**: Select a time range, run AI inference, and review predicted events before confirming them.
3.  **Manage Schema**: Add, rename, or delete annotation categories (Heads) and labels dynamically.
4.  **Edit & Sync Events**: View, sort, and modify existing events in a detailed table view, including a new feature to instantly snap an existing event to the player's current timestamp.
5.  **Control History**: Access global Undo/Redo functionality for the localization task.

## 📂 Directory Structure

```text
ui/localization/event_editor/
├── __init__.py             # Package entry point; assembles the tabbed LocRightPanel.
├── smart_spotting.py       # [NEW] Interface for AI inference & prediction review.
├── spotting_controls.py    # Tabbed interface for dynamic action spotting buttons.
└── annotation_table.py     # Data grid showing the list of events (with cell editing).
```

## 🧩 Components Breakdown

### 1. `__init__.py`

**Main Class:** `LocRightPanel`

* **Role**: The main container widget that acts as the "Right Panel" in the Localization layout.
* **Composition**:
    * **Header**: Contains the "Annotation Controls" label and the global **Undo/Redo** buttons.
    * **Main Tabs**: A `QTabWidget` that strictly separates workflows:
        * **Tab 0 (Hand Annotation)**: Stacks `AnnotationManagementWidget` (Top) and `AnnotationTableWidget` (Bottom).
        * **Tab 1 (Smart Annotation)**: Hosts the `SmartSpottingWidget`.

### 2. `smart_spotting.py` (⭐ NEW)

**Role**: Handles the UI for the AI-powered Action Spotting workflow.

**Key Classes:**

* **`SmartSpottingWidget`**:
    * **Inference Range**: Provides custom inputs to set the start and end boundaries for the AI model using the player's current time.
    * **Execution**: Hosts the "Run Smart Inference" button and progress bar.
    * **Dual Tables**: Displays unconfirmed AI predictions in a top table (allowing users to clear or confirm them) and confirmed/manual events in a bottom table.
* **`TimeLineEdit`**:
    * A highly customized `QLineEdit` tailored for `MM:SS.mmm` formatting. Supports free typing and keyboard arrow integration (Up/Down) to smoothly increment or decrement milliseconds/seconds.

### 3. `spotting_controls.py`

**Role**: Handles the dynamic creation of buttons based on the JSON schema for manual spotting. 

**Key Classes:**

* **`SpottingTabWidget`**:
    * A `QTabWidget` where each tab represents a **Head** (Category, e.g., "Pass", "Shot").
    * Supports context menus on tabs to **Rename** or **Delete** heads.
    * Contains a special `+` tab to add new heads dynamically.
* **`HeadSpottingPage`**:
    * The widget inside each tab.
    * Displays a grid of `LabelButton`s using an optimized **Bin Packing** layout to maximize horizontal space.
    * Includes a live-updating "Current Time" label and an "Add new label" button.
* **`LabelButton`**:
    * A custom `QPushButton` that emits signals for Right-Click (Context Menu) and Double-Click (Rename) events.

### 4. `annotation_table.py`

**Role**: Displays the list of recorded events. It supports direct cell editing and timeline synchronization.

**Key Classes:**

* **`AnnotationTableModel` (`QAbstractTableModel`)**:
    * The underlying data model connecting the UI to the list of events.
    * Columns: **Time** (formatted `MM:SS.mmm`), **Head**, **Label**.
    * Implements `setData` to allow users to double-click a cell and modify the time or label directly.
* **`AnnotationTableWidget`**:
    * Wraps the `QTableView`.
    * **[NEW] Time Sync Tool**: Includes a "Set to Current Video Time" button that allows users to select an existing event and instantly update its timestamp to the current player position.
    * Handles row selection (syncs with the video player seek) and provides a context menu to **Delete** events.

## 🔄 Interaction Flows

### Hand Spotting Flow
1.  **Initialization**: The `LocalizationManager` builds the tabs in `spotting_controls` based on the JSON schema.
2.  **Spotting**: User clicks a category button; a signal bubbles up to the Manager to grab the player time and add an event.
3.  **Editing**: User selects a row in the `AnnotationTableWidget` and clicks "Set to Current Video Time", instantly snapping the event's timestamp to the current video frame.

### Smart Spotting Flow
1.  **Range Selection**: User navigates to the "Smart Annotation" tab and sets the Start/End boundaries using the `TimeLineEdit` widgets.
2.  **Inference**: User clicks "Run Smart Inference". A background thread clips the video and runs the AI model.
3.  **Review**: Predictions populate the "Predicted Events List". The user can click rows to seek to those timestamps and verify the action.
4.  **Confirmation**: Clicking "Confirm Predictions" merges the AI events into the core application memory (pushing an Undo command) and moves them to the "Confirmed Events List".

## 🛠️ Dependencies

* **PyQt6**: `QtWidgets`, `QtCore`, `QtGui`.
* **Project Utils**: Standard signal/slot mechanisms defined in the Controller layer.
