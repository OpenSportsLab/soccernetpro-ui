# 🏷️ Classification UI Module

This directory contains the user interface components specifically designed for the **Whole-Video Classification** task.

In this mode, users assign attributes (labels) to an entire video clip rather than specific timestamps. The UI is designed to dynamically adapt to the project's JSON schema.

## 📂 File Descriptions

### `panels.py`

This file defines the structural containers for the classification interface. It arranges the screen into three distinct areas:

* **`LeftPanel`**:
    * Hosts the **Project Controls** (imported from `ui/common`).
    * Displays the **Action Clip List** (File Tree).
    * Manages filtering options (All / Done / Not Done).
* **`CenterPanel`**:
    * Contains the video player (`VideoViewAndControl`).
    * Hosts navigation buttons (Previous/Next Action, Previous/Next Clip).
* **`RightPanel`**:
    * **Dynamic Form Area**: Automatically generates input fields based on the project Schema.
    * **Manual Annotation Box**: Displays the current selection state and confirmation buttons.

### `widgets.py`
**Task-Specific Components**

This file contains specialized widgets that are mostly generated programmatically based on the user's label definitions:

* **`DynamicSingleLabelGroup`**: A `QGroupBox` containing **Radio Buttons**. Used when the schema defines a "single_label" type (Mutually exclusive).
* **`DynamicMultiLabelGroup`**: A `QGroupBox` containing **Checkboxes**. Used when the schema defines a "multi_label" type (Multiple selections allowed).
* **`VideoViewAndControl`**: A wrapper widget combining `QVideoWidget`, a custom clickable seek slider, and time labels specific to the classification workflow.

### `__init__.py`
* Exposes the classes from `panels` and `widgets` to the rest of the application, simplifying import statements.

---

## 💡 Key Concepts

1.  **Dynamic UI Generation**: The **RightPanel** does not have hardcoded buttons for labels (e.g., "Goal", "Foul"). Instead, it reads the `label_definitions` from the Model and instantiates the appropriate `Dynamic...LabelGroup` widgets from `widgets.py` at runtime.
2.  **Shared Controls**: The **LeftPanel** embeds the `UnifiedProjectControls` from the `../common/` directory to ensure the "Save/Load/Export" experience is consistent with the Localization mode.
