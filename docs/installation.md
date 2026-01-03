# Installation

**Quick option:**

Pre-built binaries for Windows, macOS, and Linux are available on the [GitHub Releases page](https://github.com/OpenSportsLab/DatasetAnnotationTool/releases). Download the latest release for your platform and run the executable—no installation required.

---

## Requirements

- Python 3.9 or later
- PyQt6
- Other dependencies (see `requirements.txt`)

## Steps

1. **Clone the repository:**
    ```bash
    git clone https://github.com/OpenSportsLab/DatasetAnnotationTool.git
    cd DatasetAnnotationTool
    ```

2. **(Recommended) Create a Conda environment:**
    ```bash
    conda create -n osl-visualizer python=3.9 -y
    conda activate osl-visualizer
    ```

3. **Install dependencies:**
    The main dependencies are:
    - pyqt6
    - opencv-python (optional, for video rendering/computer vision)
    - See `requirements.txt` for the full list
    
    Install with pip:
    ```bash
    pip install pyqt6
    # Optional, for video rendering/computer vision:
    pip install opencv-python
    # Or install all dependencies:
    pip install -r requirements.txt
    ```

4. **Run the tool:**
    ```bash
    python osl_visualizer/main.py
    ```

## Troubleshooting

- If you have issues with Qt or video playback, check [Troubleshooting](troubleshooting.md).
