# 🎨 Application Stylesheets (QSS)

This directory contains the **Qt Style Sheets (.qss)** that define the visual appearance of the application. The tool supports dynamic theme switching between **Dark Mode** (default) and **Light Mode**.

## 📂 Files

### 1. `style.qss` (Night Mode)
* **Type:** Default Theme.
* **Palette:**
    * **Backgrounds:** Deep Grays (`#2E2E2E`, `#3C3C3C`).
    * **Text:** Off-White (`#F0F0F0`).
    * **Accents:** Bright Blue (`#00BFFF`) and Darker Greys for borders.
* **Usage:** Optimized for long annotation sessions to reduce eye strain in low-light environments.

### 2. `style_day.qss` (Day Mode)
* **Type:** Alternative Theme.
* **Palette:**
    * **Backgrounds:** Light Grays (`#E0E0E0`, `#F0F0F0`).
    * **Text:** Dark Charcoal (`#1E1E1E`) for high contrast.
    * **Accents:** Teal/Cyan (`#00AACC`) and Blue (`#0088CC`).
* **Usage:** Optimized for bright environments, presentations, or projectors.

---

## 🛠 Technical Details

These files use standard CSS-like syntax adapted for Qt Widgets (`QWidget`, `QPushButton`, `QTreeWidget`, etc.).

### Key Styling Features
1.  **Collapsible Group Boxes**:
    * We utilize a CSS trick to animate the `QGroupBox` folding mechanism.
    * The selector `QGroupBox::checkable:checked > QWidget` controls the `max-height` property to hide or show content without requiring complex Python animation code.

2.  **Custom Indicators**:
    * `QRadioButton` and `QCheckBox` indicators are customized to match the theme colors.
    * `QTreeWidget` headers are styled to blend seamlessly with the panel backgrounds.

3.  **Interactive States**:
    * All buttons define specific styles for `:hover`, `:pressed`, and `:disabled` states to provide immediate visual feedback to the user.

## 🔄 Loading Logic
The themes are loaded dynamically in `viewer.py` (or `main_window.py`). When the user toggles the mode, the application reads the text content of the target `.qss` file and applies it via `self.setStyleSheet(...)`.
