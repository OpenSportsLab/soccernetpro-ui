## 🧭 How to Use **SoccerNetProAnalyzer**

### 🔹 Installation
1. **Download** the latest release of `SoccerNetProAnalyzer` as a `.zip` file from this repository.  
2. **Unzip** the downloaded file.  
3. **Drag** the extracted `.app` file into your **Applications** folder on macOS.  
4. **Double-click** the app icon to launch it.

---

### ⚙️ Usage Steps

#### 1. Import the JSON file  
- On the **left sidebar**, click **Import JSON** and select your annotation configuration file (e.g., GAC-style taxonomy JSON).  
- This file defines the label heads and available classes.
<img width="580" height="152" alt="d3ed5c54-6c8c-48dd-ac2e-555df2fd541a" src="https://github.com/user-attachments/assets/f796ed69-1e33-4122-9dbb-6951882c7dc8" />

#### 2. Import videos or multi-view clips  
- On the **left sidebar**, click **Add Video(s)**.  
- You can import either:  
  - A **single video clip**, or  
  - A **folder** containing multiple views of the same action.  
- The app will organize them as one unified action for annotation.

<img width="1072" height="354" alt="fa4ac01a-22ce-48f7-bbc3-25ce4a732805" src="https://github.com/user-attachments/assets/3fa8578a-8c4c-4a59-a60b-9c5e53325776" />

#### 3. Annotate actions (Manual or Automatic)  
- On the **right sidebar**, you can perform:  
  - **Manual labeling**: select labels for each head (e.g., foul type, severity, attributes).  
  - **Automatic analysis**: click **Start Analysis** to generate simulated model predictions.  
- You can save or export all annotations to a new JSON file at any time.
<img width="2800" height="1602" alt="42163459-85a1-4a9d-8f35-76390063ea07" src="https://github.com/user-attachments/assets/9be9c3ec-290a-4b76-940e-2fd9e61ba447" />

---

### 💡 Notes
- Large videos are **copied** into your working directory during import — this may take time and use disk space.  
- A progress bar and messages will indicate import status.  
- The app supports **dynamic label heads** defined by your JSON file.


## ⚙️ How to Run the Python Code

### 1. Download and Extract the Project
- Download the `.zip` file of **Tool** from the repository.
- Unzip it to your desired location (e.g., `~/Downloads/Tool`).

### 2. Open a Terminal and Navigate to the Project Directory
```bash
cd /path/to/Tool
```

### 3. Activate the Virtual Environment
If you already have a virtual environment inside the project (e.g., .venv):
```bash
source .venv/bin/activate
```
If you already have a virtual environment inside the project (e.g., .venv):
```bash
source .venv/bin/activate
```
If you dont have a virtual environment inside the project (e.g., .venv):
```bash
pip install -r requirements.txt
```

### 4. Run the Application
Once the environment is activated, start the app:
```bash
python main.py
```
