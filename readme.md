# SoccerNetPro Analyzer (UI)

[![Documentation Status](https://img.shields.io/badge/docs-online-brightgreen)](https://opensportslab.github.io/soccernetpro-ui/)

A **PyQt6-based GUI** for analyzing and annotating **SoccerNetPro / action spotting** datasets (OpenSportsLab).

---

## Features

- Open and visualize SoccerNetPro-style data and annotations.
- Annotate and edit events/actions with a user-friendly GUI.
- Manage labels/categories and export results for downstream tasks.
- Easy to extend with additional viewers, overlays, and tools.

---

## 🔧 Environment Setup

We recommend using [Anaconda](https://www.anaconda.com/) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html) for managing your Python environment.

> **Note:** The GUI project lives in the `Tool/` subdirectory of this repository, and dependencies are defined in `Tool/requirements.txt`.

### Step 0 – Clone the repository

```bash
git clone https://github.com/OpenSportsLab/soccernetpro-ui.git
cd soccernetpro-ui
```


### Step 1 – Create a new Conda environment

```bash
conda create -n soccernetpro-ui python=3.9 -y
conda activate soccernetpro-ui
```


### Step 2 – Install dependencies
```bash
pip install -r Tool/requirements.txt
```
---

## 🚀 Run the GUI
From the repository root, launch the app with:
```bash
python Tool/main.py
```
A window will open where you can load your data and start working.


---


## 📦 Download Test Datasets

This project provides **test datasets** for two tasks: **Classification** and **Localization**.  
All test data are hosted directly in this GitHub repository and should be downloaded via command line.

> ⚠️ **Important**  
> For both tasks, the corresponding **JSON annotation file must be placed in the same directory**
> as the data folder (`classification/` or `england efl/`), otherwise the GUI will not load the data correctly.

---

### 🟦 Classification – Test Data

**Data location (GitHub):**  
https://github.com/OpenSportsLab/soccernetpro-ui/tree/main/Test%20Data/Classification_test/classification

This folder contains multiple action-category subfolders (e.g. `action_0`, `action_1`, …).

#### 📥 Download via command line

From the repository root:

```bash
mkdir -p "Test Data/Classification_test"
cd "Test Data/Classification_test"

git clone \
  https://github.com/OpenSportsLab/soccernetpro-ui.git \
  --depth 1 \
  --filter=blob:none \
  --sparse

cd soccernetpro-ui
git sparse-checkout init --cone
git sparse-checkout set "Test Data/Classification_test/classification"
```
After downloading, place the corresponding classification JSON annotation file in:

```bash
Test Data/Classification_test/
```
### 🟩 Localization – Test Data
**Data location (GitHub):**  

https://github.com/OpenSportsLab/soccernetpro-ui/tree/main/Test%20Data/Localization_test
Each folder (e.g. england efl/) contains video clips for localization testing.

#### 📥 Download via command line

From the repository root:

```bash
mkdir -p "Test Data/Localization_test"
cd "Test Data/Localization_test"

git clone \
  https://github.com/OpenSportsLab/soccernetpro-ui.git \
  --depth 1 \
  --filter=blob:none \
  --sparse

cd soccernetpro-ui
git sparse-checkout init --cone
git sparse-checkout set "Test Data/Localization_test"
```
After downloading, place the corresponding localization JSON annotation file in the same directory as the data folder, for example:
```bash
Test Data/Localization_test/
```


## 🧰 Build a standalone app (PyInstaller)
### **macOS (.app)**

From the repository root:
```bash
cd Tool
pyinstaller --noconfirm --clean --windowed \
  --name "SoccerNetProAnalyzer" \
  --add-data "style:style" \
  --add-data "ui:ui" \
  --add-data "ui2:ui2" \
  main.py
```

### **Windows / Linux** (one-file binary)

From the repository root:

```bash
cd Tool
pyinstaller --noconfirm --clean --windowed --onefile \
  --name "SoccerNetProAnalyzer" \
  --add-data "style:style" \
  --add-data "ui:ui" \
  --add-data "ui2:ui2" \
  main.py
```

In GitHub Actions, the Windows ```bash--add-data``` separator is ```;``` instead of ```:```.

---

## 📚 Build the docs
```bash
pip install mkdocs mkdocs-material mkdocstrings[python]
mkdocs gh-deploy --force
```

---


## 📜 License

This Soccernet Pro project offers two licensing options to suit different needs:

* **AGPL-3.0 License**: This open-source license is ideal for students, researchers, and the community. It supports open collaboration and sharing. See the [`LICENSE.txt`](https://github.com/OpenSportsLab/soccernetpro-ui/blob/main/LICENSE.txt) file for full details.
* **Commercial License**: Designed for [`commercial use`](https://github.com/OpenSportsLab/soccernetpro-ui/blob/main/COMMERCIAL_LICENSE.md
), this option allows you to integrate this software into proprietary products and services without the open-source obligations of GPL-3.0. If your use case involves commercial deployment, please contact the maintainers to obtain a commercial license.

**Contact:** OpenSportsLab / project maintainers.




