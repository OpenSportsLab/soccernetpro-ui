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


## 📦 Download a dataset
Use the provided tool script to download a dataset file and run the GUI with it:
```bash
python Tool/tools/download_osl_hf.py \
  --url https://huggingface.co/datasets/OpenSportsLab/HistWC/blob/main/HistWC-finals.json \
  --output-dir ./Test\ Data/

python Tool/main.py --data_file ./Test\ Data/HistWC-finals.json
```
Adjust ```bash--data_file``` to match the CLI argument name used by your Tool/main.py (e.g., --osl_file if that is what your entry point expects).

---


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

In GitHub Actions, the Windows ```bash--add-data``` separator is ; instead of :.

---

## 📚 Build the docs
```bash
pip install mkdocs mkdocs-material mkdocstrings[python]
mkdocs gh-deploy --force
```

---

## 📄 License

This project is open source and free to use under the MIT License.








