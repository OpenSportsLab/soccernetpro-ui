# 🛠️ Common UI Components

This directory contains **shared interface widgets** that are used across multiple modes of the application (both Classification and Localization). 

The goal of this module is to adhere to the **DRY (Don't Repeat Yourself)** principle and ensure a consistent user experience regardless of the active task.

## 📂 Files

### 1. `dialogs.py`

* **Purpose:** Contains modal dialog windows used during project initialization and configuration.
* **Key Classes:**
    * **`ProjectTypeDialog`**: A simple selection window asking the user to choose between "Classification" or "Localization" modes.
    * **`CreateProjectDialog`**: A comprehensive wizard for setting up new projects. It handles:
        * Task Name and Description input.
        * Modality selection (Video/Image/Audio).
        * **Dynamic Schema Creation**: Allows users to define Categories (Heads) and Labels interactively.
    * **`FolderPickerDialog`**: A specialized file tree widget that allows selecting multiple folders via checkboxes (solving the UX issue of requiring `Ctrl+Click` in standard dialogs).

---

### 2. `project_controls.py`

This file contains widgets responsible for the control and navigation of the project workspace.

#### **Class: `UnifiedProjectControls`**
* **Purpose:** Provides a standardized **Project Management Panel** to handle the application lifecycle.
* **Layout:** A 3x2 Grid Layout containing the following essential buttons:
    * **Row 1:** `New Project`, `Load Project`
    * **Row 2:** `Add Data`, `Close Project`
    * **Row 3:** `Save`, `Export`
* **Signal Interface:**
    * `createRequested`, `loadRequested`, `addVideoRequested`
    * `closeRequested`, `saveRequested`, `exportRequested`

#### **Class: `UnifiedClipExplorer`**
* **Purpose:** A unified widget to display and manage the list of imported video clips/actions.
* **Components:**
    * **Clip Tree:** Displays the file list with status icons (Done/Not Done).
    * **Filter:** A ComboBox to filter the list by status.
    * **Clear Button:** Allows removing all items from the workspace.
* **Signal Interface:**
    * `requestRemoveItem(QTreeWidgetItem)`: Triggered via right-click context menu.
    * `filterChanged(int)`: Triggered when the filter combo box is changed.
    * `clearRequested()`: Triggered when the "Clear List" button is clicked.
