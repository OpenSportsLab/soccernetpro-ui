# 📍 Localization UI Module

This directory contains the user interface components specifically designed for the **Action Spotting (Localization)** task. In this mode, users identify specific timestamps (events) within a video timeline, rather than categorizing the whole video.

The layout architecture relies on the **Unified Workspace** pattern, where specialized components defined here are injected into a common application skeleton.

<img width="2076" height="1094" alt="localization" src="https://github.com/user-attachments/assets/9220ed90-db63-410c-b277-422131a2a6bb" />

## 📂 Directory Structure

The structure has been modularized into packages to separate concerns (Playback vs. Data Entry).

```text
ui/localization/
├── media_player/           # [Package] Center Panel: Playback & Timeline logic
│   ├── __init__.py         # Assembles and exports LocCenterPanel
│   ├── preview.py          # Video surface (QVideoWidget wrapper)
│   ├── timeline.py         # Custom painted timeline, zooming, and slider logic
│   └── controls.py         # Playback buttons (Play, Pause, Speed, Seek)
│
└── event_editor/           # [Package] Right Panel: Data entry & Modification
    ├── __init__.py         # Assembles and exports LocRightPanel
    ├── spotting_controls.py# Tabbed interface for creating new events (Spotting)
    └── annotation_table.py # Table view for listing and editing existing events

```

---

## 📝 Component Descriptions

### 1. Left Sidebar (Common Component)

*Note: The left sidebar is now a shared component located in `ui/common/clip_explorer.py`.*

* **Function:** Displays the hierarchical list of "Clips / Sequences".
* **Features:** Handles filtering (Show Labelled/No Labelled) and standard project file operations (Save, Load, Export).

### 2. `media_player/` (Center Area)

This package defines the `LocCenterPanel`, handling all visual aspects of the video.

* **`preview.py` (MediaPreviewWidget)**:
* Handles the low-level `QMediaPlayer` and `QAudioOutput` logic.
* Ensures video rendering and audio synchronization.


* **`timeline.py` (TimelineWidget)**:
* **Core Feature**: A custom-painted widget representing the video duration.
* **Visual Markers**: Draws colored lines on the track where events have occurred.
* **Zoom System**: Supports dynamic zooming to expand the slider for frame-perfect navigation.
* **Auto-Scroll**: Logic to keep the playhead centered during playback when zoomed in.


* **`controls.py` (PlaybackControlBar)**:
* Provides granular navigation buttons: `<< 1s`, `>> 1s`, `Prev/Next Clip`.
* Variable playback speed controls (0.25x - 4.0x).



### 3. `event_editor/` (Right Sidebar)

This package defines the `LocRightPanel`, handling the data entry workflow.

* **`spotting_controls.py`**:
* **`AnnotationManagementWidget`**: A tabbed container generated dynamically from the project Schema (JSON).
* **`HeadSpottingPage`**: A grid of buttons inside each tab. Clicking a button triggers an event creation at the current timestamp.
* **Context Menus**: Supports right-clicking tabs to rename categories (Heads) or delete them.


* **`annotation_table.py`**:
* **`AnnotationTableWidget`**: Displays a detailed list of all recorded events for the active video.
* **In-place Editing**: Implements a custom Model (`AnnotationTableModel`) allowing users to double-click cells to directly edit the Time, Category, or Label.
* **Sync**: Selecting a row automatically seeks the video player to that timestamp.


