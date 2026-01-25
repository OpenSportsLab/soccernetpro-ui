# 🛠️ Common UI Components

This directory contains **shared interface widgets** that are used across multiple modes of the application (both Classification and Localization). 

The goal of this module is to adhere to the **DRY (Don't Repeat Yourself)** principle and ensure a consistent user experience regardless of the active task.

## 📂 Files

### `project_controls.py`

* **Class:** `UnifiedProjectControls`
* **Purpose:** Provides a standardized **Project Management Panel** to handle the application lifecycle.
* **Layout:** A 3x2 Grid Layout containing the following essential buttons:
    * **Row 1:** `New Project`, `Load Project`
    * **Row 2:** `Add Data`, `Close Project`
    * **Row 3:** `Save`, `Export`

#### 📡 Signal Interface
This widget contains **no business logic**. It strictly forwards user interactions to the Controllers via Qt Signals:

| Signal | Description |
| :--- | :--- |
| `createRequested` | Triggered when "New Project" is clicked. |
| `loadRequested` | Triggered when "Load Project" is clicked. |
| `addVideoRequested`| Triggered when "Add Data" is clicked. |
| `closeRequested` | Triggered when "Close Project" is clicked. |
| `saveRequested` | Triggered when "Save" is clicked. |
| `exportRequested` | Triggered when "Export" is clicked. |
