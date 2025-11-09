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

#### 2. Import videos or multi-view clips  
- On the **left sidebar**, click **Add Video(s)**.  
- You can import either:  
  - A **single video clip**, or  
  - A **folder** containing multiple views of the same action.  
- The app will organize them as one unified action for annotation.

#### 3. Annotate actions (Manual or Automatic)  
- On the **right sidebar**, you can perform:  
  - **Manual labeling**: select labels for each head (e.g., foul type, severity, attributes).  
  - **Automatic analysis**: click **Start Analysis** to generate simulated model predictions.  
- You can save or export all annotations to a new JSON file at any time.

---

### 💡 Notes
- Large videos are **copied** into your working directory during import — this may take time and use disk space.  
- A progress bar and messages will indicate import status.  
- The app supports **dynamic label heads** defined by your JSON file.
