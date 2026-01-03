# GUI Overview

This page provides an overview of the main interface elements:
- Video player
- Annotation list
- Label management
- Navigation controls

Refer to the screenshots below for a visual guide.

The OSL Annotation Tool is organized in three main panels:

![GUI Layout](assets/screenshot_layout.png)

## Left Panel: Video Management

- **Video List:** Displays all loaded videos or games. Each entry shows the filename and the number of annotated events.
- **Add Video:** Use the button to add new video files to your project.
- **Remove Video:** Remove the selected video from the list and the project.
- **Selection:** Clicking a video loads it into the player and displays its annotations in the right panel.
- **Load/Save Buttons:** Quickly load or save your annotation project (OSL JSON format).

## Center Panel: Video Player & Controls

- **Video Display:** Shows the currently selected video. You can play, pause, and seek through the video.
- **Playback Controls:**
  - Play/Pause, step forward/backward by frame or by time (1s, 5s)
  - Change playback speed (1x, 2x, 4x, 8x, and slower speeds)
  - Timeline slider for quick navigation
- **Status Bar:** Shows the current time, total duration, and status messages.

## Right Panel: Annotation Management

- **Annotation List:** Shows all annotations for the selected video, including timestamp and label.
- **Add Annotation:** 
  - Add a new annotation at the current video time.
- **Remove Annotation:** 
  - Remove the currently selected annotation.
- **Edit Annotation:**
  - Select an annotation to edit its label or timestamp
  - Use "Set to Current Video Time" to update the annotation time
- **Label Management:**
  - Add new labels or remove existing ones
  - Assign labels to annotations
- **Metadata:**
  - View or edit additional metadata for each annotation (if supported)
- **Navigation:**
  - Quickly jump to previous or next annotation using navigation buttons

For details on annotating, see [Annotating Actions](annotating.md).
