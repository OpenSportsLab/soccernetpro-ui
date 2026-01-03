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

