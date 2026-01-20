## Tools Directory Usage

The `tools` directory contains utility scripts to help you work with OSL (Open Sports Lab) datasets, particularly for downloading annotated datasets and associated videos from Hugging Face. Below you'll find an explanation and usage instructions.

---

### 1. Download OSL Dataset and Videos from Hugging Face

**Script:** `tools/download_osl_hf.py`

This script automates the download of an OSL-format JSON file (annotation file) and all referenced videos from a Hugging Face dataset repository.

#### **Features:**

* Downloads a specific OSL JSON annotation file.
* Parses the JSON to identify referenced video files and downloads them as well.
* Can perform a “dry run” to show which files would be downloaded and their total size, without actually downloading.

#### **Requirements**

* Python 3.x
* `huggingface_hub` Python package (install with `pip install huggingface_hub`)

#### **Usage**

**Basic Command:**

```bash
python tools/download_osl_hf.py \
  --url https://huggingface.co/datasets/<user>/<dataset>/blob/main/<file.json> \
  --output-dir <output_directory>
```

**Example:**

```bash
python tools/download_osl_hf.py \
  --url https://huggingface.co/datasets/OpenSportsLab/HistWC/blob/main/HistWC-finals.json \
  --output-dir /Users/giancos/Documents/HistWC/
```

**Arguments:**

* `--url`: (required) The direct Hugging Face URL of the OSL JSON file (should be in “blob/main/...” form, like you see in the web interface).
* `--output-dir`: (optional) Path to the directory where the dataset and videos should be downloaded. Defaults to `downloaded_data` if not specified.
* `--dry-run`: (optional) If provided, lists all files that would be downloaded and total size, but does not actually download any files.

**Dry Run Example:**

```bash
python tools/download_osl_hf.py \
  --url https://huggingface.co/datasets/OpenSportsLab/HistWC/blob/main/HistWC-finals.json \
  --output-dir /Users/giancos/Documents/HistWC/ \
  --dry-run
```

---

### 2. Zip the folder

```bash
zip -r DatasetAnnotationTool.zip *
```

---

### **Notes**

* The script automatically converts Hugging Face “blob” URLs to the proper “resolve” format for direct file access.
* After downloading, the output directory will contain the JSON annotation and all video files referenced in it, keeping the original folder structure.
* For datasets with a large number of videos, downloads will be parallelized for efficiency.
* If a video is missing in the repo, it will be reported (especially useful in dry run mode).
