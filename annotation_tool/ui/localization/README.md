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
