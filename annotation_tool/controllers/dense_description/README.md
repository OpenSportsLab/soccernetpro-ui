# 🧠 Controllers: Dense Description

This directory contains the business logic for the **Dense Description** mode (Timestamped Captioning).

This mode is a hybrid of **Localization** (time-based events) and **Description** (free-text generation). The controllers here manage the synchronization between the video playback, the scrolling timeline, and the text input field.

## 📂 Files

### `dense_manager.py`

**The Primary Orchestrator.**
This class connects the UI components (`DenseRightPanel`, `Timeline`, `MediaPlayer`) to the Data Model (`AppState`).

* **Key Responsibilities:**
* **Editor-Timeline Sync:** Uses a `QTimer` (`_sync_editor_to_timeline`) to continuously check the playback position. If the video hits an existing event, the text editor is automatically populated with that event's text.
* **CRUD Operations:** Handles creating, updating, and deleting events via `CmdType` for full **Undo/Redo** support.
* **Tree Management:** Populates the sidebar tree and handles filtering ("Show Annotated" vs "Not Annotated").
* **Navigation:** Implements logic to jump between text events (`_navigate_annotation`).



### `dense_file_manager.py`

**The I/O Handler.**
Manages the serialization and deserialization of the Dense JSON format.

* **Key Responsibilities:**
* **Strict Validation:** calls `AppState.validate_dense_json` before loading to prevent corruption.
* **Metadata Preservation:** Ensures Global Metadata (Dataset info) and Item-level Metadata are preserved during a Load -> Save cycle.
* **Path Resolution:** Converts absolute paths to relative paths upon Export for portability.
* **Data Structure:** Maps the flat JSON `dense_captions` list to the internal dictionary format:
```json
"dense_captions": [
    { "position_ms": 12500, "lang": "en", "text": "A player kicks the ball." }
]

```
