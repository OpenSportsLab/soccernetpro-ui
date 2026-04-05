# 🏷️ Classification Event Editor

**Path:** `ui/classification/event_editor/`

## Overview

The **Event Editor** package is responsible for the **Right Panel** of the Classification Mode. Originally serving as the interface for manual data annotation, it has been massively expanded into a **Tabbed Command Center**. 

It now handles three distinct workflows: **Hand Annotation** (dynamic schema-driven UI), **Smart Annotation** (AI-powered single/batch inference with native visualizations), and **Model Training** (hyperparameter configuration and live console monitoring).

## ✨ Key Features

* **Tabbed Interface:** Seamlessly separates the workflows into `Hand Annotation`, `Smart Annotation`, and `Train` tabs.
* **Smart Contextual Controls:** The bottom "Confirm" and "Clear" buttons are tab-aware, executing different logic depending on whether the user is working with manual labels or AI predictions.
* **Native Data Visualization:** Includes a custom `NativeDonutChart` built from scratch using `QPainter` to elegantly display AI confidence scores and probabilities with interactive hover tooltips.
* **Batch Inference Control:** Provides dynamic start/end comboboxes that validate sequence logic, allowing users to run AI predictions over a specific subset of videos.
* **In-App Training Monitor:** Hosts a complete UI for fine-tuning models, featuring hyperparameter inputs (Epochs, LR, Batch, Device), a live progress bar, and a real-time terminal console.
* **Dynamic Rendering:** Automatically generates UI groups (Radio/Checkboxes) based on the label definition (Schema) for manual annotation.

---

## 📂 File Structure

```text
event_editor/
├── __init__.py           # Package entry point; exports the main classes.
├── editor.py             # Defines the main container widget & Native Donut Chart.
└── dynamic_widgets.py    # Defines the atomic UI components (Label Groups).
```

---

## 📝 Module Descriptions

### 1. `editor.py`
Contains the core interface components for the right panel.

**`NativeDonutChart` (New):**
* A highly optimized, custom PyQT component that draws interactive pie/donut charts.
* Calculates angles and colors dynamically based on the AI's confidence dictionary (`conf_dict`).
* Features math-driven collision detection to show specific probabilities when the user hovers over a slice.

**`ClassificationEventEditor` (formerly `ClassRightPanel`):**
* **Top Section**: Undo/Redo history controls and Task name display.
* **Category Editor**: Global input field to add new Schema Heads.
* **Tab 1 - Hand Annotation**: Holds the `QScrollArea` populated by dynamic Radio/Checkbox widgets for traditional manual labeling.
* **Tab 2 - Smart Annotation**: Hosts the Single and Batch inference buttons, progress bars, the Donut Chart, and a text output area for batch prediction summaries.
* **Tab 3 - Train**: Collects parameters (Device, Workers, Epochs) and provides "Start/Stop" controls tied to a live-updating `QTextEdit` console.
* **Bottom Section**: Houses the global `Confirm` and `Clear Selection` buttons, which intelligently emit different signals (`hand_clear_requested` vs. `smart_clear_requested`) based on the active tab.

### 2. `dynamic_widgets.py`
Contains the reusable widgets that represent a single Label Head (Category) inside the Hand Annotation tab.

* **`DynamicSingleLabelGroup`**:
  * Used when the schema type is `single_label`.
  * Renders a tightly controlled `QButtonGroup` with `QRadioButton`s.
  * Allows adding/removing individual labels or the entire category dynamically.

* **`DynamicMultiLabelGroup`**:
  * Used when the schema type is `multi_label`.
  * Renders a list of independent `QCheckBox`es.
  * Allows multiple selections simultaneously.

### 3. `__init__.py`
Exposes the classes to the rest of the application and handles legacy aliasing.

```python
from .editor import ClassificationEventEditor
from .dynamic_widgets import DynamicSingleLabelGroup, DynamicMultiLabelGroup

ClassRightPanel = ClassificationEventEditor # Legacy support alias
```

---

## 🚀 Usage Example

This module is typically instantiated by the main workspace layout.

```python
# In ui/classification/widgets/workspace.py
from ui.classification.event_editor import ClassificationEventEditor

self.right_panel = ClassificationEventEditor()

# To populate the Hand Annotation Tab based on JSON schema:
self.right_panel.setup_dynamic_labels(label_definitions_dict)

# Connect tab-aware signals to the Controller Logic:
self.right_panel.annotation_saved.connect(self.manager.save_manual_annotation)
self.right_panel.smart_confirm_requested.connect(self.manager.confirm_smart_prediction)
