# 📍 Localization UI Module

This directory contains the user interface components specifically designed for the **Action Spotting (Localization)** task. In this mode, users identify specific timestamps (events) within a video timeline, and can now leverage AI inference models to automatically spot actions.

## 📂 Directory Structure

```text
ui/localization/
├── panels.py               # High-level 3-column layout container
├── media_player/           # Center area components
│   ├── __init__.py         # Assembles the LocCenterPanel
│   ├── preview.py          # Legacy/Standalone QVideoWidget player
│   ├── player_panel.py     # Unified MediaPreview using shared VideoSurface
│   ├── controls.py         # Playback buttons (speed, step, next/prev)
│   └── timeline.py         # Custom zoomable timeline with event markers
├── event_editor/           # Right sidebar components
│   ├── __init__.py         # Assembles the tabbed LocRightPanel
│   ├── smart_spotting.py   # AI Inference UI (Range selectors, Dual tables)
│   ├── spotting_controls.py# Manual spotting buttons & Schema tabs
│   └── annotation_table.py # Data grid for event review and cell editing
└── __init__.py
```

---

## 📝 Module Breakdown

### 1. `media_player/` (Center Area)
**Purpose:** Video Playback, Navigation, and Visualization.

* **`player_panel.py`**: Contains `MediaPreviewWidget`. This acts as a wrapper that delegates actual video rendering to the shared, unified `VideoSurface` (preventing ghost frames), while exposing standard player controls to the Localization Manager.
* **`timeline.py`**: A highly customized `QSlider` replacement built with `QPainter`.
  * **Visual Markers**: Draws colored lines indicating events (e.g., Deep Sky Blue for confirmed events, Gold for pending AI predictions).
  * **Zoom Engine**: Supports dynamic zooming (`+`/`-`) with a horizontal scroll area to allow precise, frame-level interaction.
  * **Auto-Follow**: Intelligently pans the scrollbar to keep the playhead centered during playback.
* **`controls.py`**: The `PlaybackControlBar` provides granular navigation, including temporal stepping (`<< 1s`, `>> 5s`), variable playback speeds (`0.25x` to `4.0x`), and quick jumps between recorded events.

### 2. `event_editor/` (Right Sidebar)
**Purpose:** Data Entry, AI Inference, and Event Modification.

This module has been heavily upgraded into a **Tabbed Command Center** separating manual work from AI assistance.

* **`spotting_controls.py` (Tab 0: Hand Annotation)**: 
  * A tabbed schema interface allowing users to organize annotations by categories ("Heads"). 
  * Uses a Bin-Packing algorithm to dynamically arrange label buttons. Users click these buttons to instantly stamp the current video time.
* **`smart_spotting.py` (Tab 1: Smart Annotation) [NEW]**:
  * Hosts the AI Action Spotting interface.
  * Features custom `TimeLineEdit` widgets to set inference boundaries, a progress bar, and a dual-table layout to review pending predictions before committing them.
* **`annotation_table.py` (Bottom Area)**: 
  * A powerful `QTableView` detailing all recorded events.
  * Supports in-place text editing for timestamps and labels.
  * **[NEW] Sync Tool**: Includes a "Set to Current Video Time" utility to instantly snap an existing event to the player's active frame.
