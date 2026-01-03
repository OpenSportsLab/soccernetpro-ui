# Batch Tools

## Dataset Downloader

The Dataset Downloader tool lets you easily fetch sports video datasets from online sources (such as Hugging Face) directly to your computer for annotation.

### How to Use

1. Open the Dataset Downloader from the menu or use the shortcut **Ctrl+D**.
2. Enter the URL of the dataset you want to download. For example:
  - `https://huggingface.co/datasets/OpenSportsLab/SoccerNet-ActionSpotting-Videos/blob/main/224p/test/annotations.json` for the test split of the SoccerNetv2 dataset.
- Choose the output directory where the dataset should be saved. For example:
  - `/Users/<username>/Documents/SoccerNet/`
4. Click the download button to start.
5. **Dry Run:** By default, the tool performs a dry run, listing the files that would be downloaded and the total storage required. Uncheck the dry run option to actually download the files.
6. If you cancel the download, the current file will finish downloading before the process stops.

**Note:** To download from Hugging Face, you need an API key. Create one at [https://huggingface.co/settings/tokens/new?tokenType=read](https://huggingface.co/settings/tokens/new?tokenType=read). The key should look like `hf_xxxxx`.

This tool helps you quickly set up new annotation projects by fetching datasets in the correct format, so you can start annotating right away.
