![MatEl Dashboard Preview](https://raw.githubusercontent.com/MosesDevone/MataElang-Network-Monitoring/main/preview.png)

# 🦅 MataElang (MatEl) OS - Release Distribution

This directory contains the **Public Stable Release** of MataElang OS. This version is optimized for performance and security, using encrypted binary modules to protect the application's core logic.

---

## 🚀 How to Run (Step-by-Step)

### 1. Prerequisites
Ensure you have **Python 3.11+** installed on your system. You can check this by running:
```bash
python --version
```

### 2. Install Dependencies
Open a terminal in this folder and run the following command to install the required libraries:
```bash
python -m pip install -r requirements.txt
```

### 3. Configuration (Optional)
Look for the `.env.example` file. 
- Rename it to `.env`.
- You can adjust the settings (like ports or alert tokens) inside this file if needed.

### 4. Launch MatEl
Start the command center by running:
```bash
python run_matel.py
```

One launched, open your browser and navigate to:
**`http://localhost:8000`**

---

## 🛡️ Security Note
This distribution uses **Cython-compiled binaries (`.pyd`)**. 
- These files are machine-code extensions that provide significant speed improvements and protect the intellectual property of the project.
- You do **not** need the original source code (`.py`) files to run this application.

## 🛠️ Components Included
- **Binary Backend**: High-performance monitoring engine.
- **Minified Frontend**: 3D globe and Cyber-HUD assets in the `static/` folder.
- **Automated Launcher**: Simple entry point via `run_matel.py`.

---
<p align="center">
  <b>MataElang OS v1.0.0 - Professional Network Surveillance</b><br>
  <i>Designed for High-Reliability Operations.</i>
</p>
