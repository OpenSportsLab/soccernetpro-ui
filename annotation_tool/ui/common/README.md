# 🛠️ Common UI Components

This directory contains **shared interface widgets and layout containers** used across the application. 

The goal of this module is to adhere to the **DRY (Don't Repeat Yourself)** principle, ensuring a consistent user experience and architecture for both **Classification** and **Localization** tasks.

## 📂 Structural Components

### 1. `main_window.py`
* **Purpose:** The top-level UI container for the application.
* **Key Class:** **`MainWindowUI`**
    * Uses a `QStackedLayout` to manage the high-level views.
    * **View 0:** `WelcomeWidget` (Entry screen).
    * **View 1:** `Classification` Interface (assembled via `UnifiedTaskPanel`).
    * **View 2:** `Localization` Interface (assembled via `UnifiedTaskPanel`).

### 2. `workspace.py`
* **Purpose:** Defines the generic layout skeleton used by specific tasks.
* **Key Class:** **`UnifiedTaskPanel`**
    * Implements the standard **3-Column Layout** strategy:
        * **Left (Fixed):** `CommonProjectTreePanel` (Shared resource list).
        * **Center (Expandable):** Task-specific visualizer (e.g., Media Player).
        * **Right (Fixed):** Task-specific editor (e.g., Annotation Editor).
    * This ensures both modes look visually consistent while hosting different logic.

---

## 📂 Widget Components

### 3. `clip_explorer.py`
* **Purpose:** The standardized **Left Sidebar** for resource management.
* **Key Class:** **`CommonProjectTreePanel`**
    * **Composition:**
        * Embeds `UnifiedProjectControls` at the top.
        * Contains a `QTreeWidget` to display videos/clips.
        * Contains a bottom row with a **Filter ComboBox** and a **Clear Button**.
    * **Customization:** Accepts parameters for `tree_title` and `filter_items` to adapt text for Classification ("Actions") vs. Localization ("Clips").
    * **Signals:**
        * `request_remove_item(QTreeWidgetItem)`: Emitted via context menu.

### 4. `project_controls.py`
* **Purpose:** A reusable button grid for project lifecycle management.
* **Key Class:** **`UnifiedProjectControls`**
    * **Layout:** A 3x2 Grid containing 6 essential buttons:
        * `New Project`, `Load Project`
        * `Add Data`, `Close Project`
        * `Save`, `Export`
    * **Signals:** `createRequested`, `loadRequested`, `addVideoRequested`, `closeRequested`, `saveRequested`, `exportRequested`.

### 5. `dialogs.py`
* **Purpose:** Modal dialogs for configuration and initialization.
* **Key Classes:**
    * **`ProjectTypeDialog`**: Selection window for choosing between Classification/Localization modes.
    * **`CreateProjectDialog`**: A wizard for setting up new projects (Task Name, Modality, Description, and **Dynamic Schema Editor**).
    * **`FolderPickerDialog`**: A custom file tree allowing multi-folder selection via checkboxes (optimizing UX over standard OS dialogs).

### 6. `welcome_widget.py`
* **Purpose:** The landing screen displayed when no project is open.
* **Features:** Provides large, clear entry points to **"Create New Project"** or **"Import Existing Project"**.
