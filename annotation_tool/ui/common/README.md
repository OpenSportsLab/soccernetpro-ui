# Common UI Components

This directory contains shared UI components used by the main application workspace.

## Current Structure

```text
ui/common/
├── dataset_explorer_panel/   # Left dock panel (UI + view logic)
├── media_player/             # Center media panel (UI + view logic)
├── welcome_widget/           # Landing screen view (UI + view logic)
├── dialogs.py                # Shared dialogs
└── README.md
```

## Components

### `dataset_explorer_panel/`

- **Primary class:** `DatasetExplorerPanel`
- **Model:** `DatasetExplorerTreeModel`
- **Purpose:** Left sidebar for dataset items, filtering, add-data trigger, and context-menu remove actions.
- **Implementation:** Package-style module with:
  - `__init__.py`
  - `dataset_explorer_panel.ui`
  - local `README.md`
- **Controller pair:** `controllers/common/dataset_explorer_controller.py`

### `media_player/`

- **Primary class:** `MediaCenterPanel`
- **Purpose:** Unified center media area (video surface, timeline, playback controls).
- **Implementation:** Package-style module with:
  - `__init__.py`
  - `media_center_panel.ui`
  - local `README.md`
- **Notes:** Exposes direct media/timeline/playback API used by `main_window.py` and mode managers.

### `welcome_widget/`

- **Primary class:** `WelcomeWidget`
- **Purpose:** Landing screen with project entry actions (create/import) and external links.
- **Implementation:** Package-style module with:
  - `__init__.py`
  - `welcome_widget.ui`
  - local `README.md`
- **Controller pair:** `controllers/common/welcome_controller.py`
- **Notes:** View emits signals only; routing/open-link behavior is controller-owned.

### `dialogs.py`

- Shared dialogs used by controllers/router flows (project mode selection, picker dialogs, and media error dialog).

## Architecture Notes

- Views in `ui/common/*` focus on UI composition and signal emission.
- Application and routing logic are handled in `controllers/*`.
- `main_window.py` composes these common UI modules into the dock-based workspace.
