
# 🎨 Application Stylesheets (QSS)

This directory contains the **Qt Style Sheets (.qss)** that define the visual appearance of the application. The tool currently ships with a single default theme: **Dark Mode**.

## 📂 Files

### 1. `style.qss` (Dark Mode)
* **Type:** Default Theme.
* **Palette:**
    * **Backgrounds:** Deep Grays (`#2E2E2E`, `#3C3C3C`).
    * **Text:** Off-White (`#F0F0F0`).
    * **Accents:** Bright Blue (`#00BFFF`) and darker greys for borders.
* **Usage:** Optimized for long annotation sessions to reduce eye strain in low-light environments.

> Note: `style_day.qss` (Light/Day Mode) has been removed. The application no longer supports theme switching out of the box.

---

## 🛠 Technical Details

These files use standard CSS-like syntax adapted for Qt Widgets (`QWidget`, `QPushButton`, `QTreeWidget`, etc.).

### Key Styling Features
1. **Collapsible Group Boxes**
   * We utilize a CSS trick to animate the `QGroupBox` folding mechanism.
   * The selector `QGroupBox::checkable:checked > QWidget` controls the `max-height` property to hide or show content without requiring complex Python animation code.

2. **Custom Indicators**
   * `QRadioButton` and `QCheckBox` indicators are customized to match the theme colors.
   * `QTreeWidget` headers are styled to blend seamlessly with the panel backgrounds.

3. **Interactive States**
   * Buttons define specific styles for `:hover`, `:pressed`, and `:disabled` states to provide immediate visual feedback to the user.

## 🔄 Loading Logic
The stylesheet is loaded during application startup (typically in `main.py` or `viewer.py`). The application reads the `.qss` file content and applies it via `setStyleSheet(...)`.
