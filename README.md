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

## 💎 Full Feature Specifications

### 🛰️ 1. Core Monitoring Engine (The Heart)
*   **Multi-Protocol Surveillance**:
    *   **HTTP/HTTPS**: Monitor availability, response time, and status codes.
    *   **ICMP (Ping)**: High-precision latency and packet loss tracking.
    *   **SSL/TLS Guardian**: Monitors SSL certificate validity and sends automated alerts before expiration.
    *   **TCP Port Scanner**: Monitors specific open ports on the target server.
*   **Massive Concurrency**: Powered by Python `asyncio` and `aiohttp`, capable of handling hundreds of monitors simultaneously with extremely efficient system resource usage.
*   **Smart Background Task**: The engine runs as a lifespan background service, ensuring continuous monitoring as long as the server is active.

### 🛡️ 2. Cyber-Security & Threat Intelligence (The Shield)
*   **Web Defacement Detection**: Advanced **Content Locking** feature that stores SHA-256 hashes of web pages. Sends instant alerts if page content is altered by hackers or defacers.
*   **Security Baseline Port Locking**: Locks a whitelist of legal ports. The system automatically detects any new, suspicious ports (backdoors) that suddenly open.
*   **DDoS Early Warning System**: Automated latency anomaly analysis using spike detection (3x baseline) to warn of potential flooding attacks.
*   **GHOST Path Detection**: Protects servers from sensitive path exposure or GHOST vulnerabilities unintentionally left open to the public.
*   **Phishing Intelligence**: Integration with global phishing databases to ensure your domain is not being impersonated or misused.

### 📊 3. Geographical Visualization (The Eye)
*   **Interactive 3D Global Map**: Stunning 3D dashboard visualization using React-Three-Fiber for an immersive telemetry experience.
*   **Real-time Traffic Intercept**: Visualizes inbound visitor traffic flows using simulated satellite sensors moving from Geo-IP source to target server.
*   **Cyber-HUD Interface**: A futuristic cyber-surveillance UI with dynamic animations, providing a premium NOC (Network Operations Center) operational experience.
*   **Geo-IP Automatic Resolution**: Automatically resolves physical coordinates (Latitude, Longitude, Country, City) for every monitored IP or Domain.

### 🛠️ 4. Advanced Networking Toolkit (The Tools)
*   **Geographical Traceroute**: Tracks hop-by-hop routing paths and visualizes them on a global map to identify ISP bottlenecks.
*   **Enterprise Speedtest**: Integrated *Speedtest-cli* engine to measure real-time bandwidth (Download, Upload, Ping) with historical logging.
*   **NOC-Style Analytics**: High-resolution latency performance graphs to monitor network stability over time.

### 📈 5. Reporting & Analytics (The Brain)
*   **Automated SLA Reporting**: Accurate network availability (Uptime %) calculations across daily, weekly, and monthly ranges.
*   **PDF Export Engine**: Instantly generates professional SLA reports with MatEl branding in PDF format using *ReportLab*.
*   **Data Portability**: Export historical monitoring data to **CSV** for further analysis in tools like Excel or Power BI.
*   **Incident Timeline**: Chronological logs that detail every downtime event, recovery, and system status change.

### 🔐 6. Enterprise-Grade Security
*   **JWT Authentication**: Secure access control using *JSON Web Tokens* with configurable expiry.
*   **Argon2 Password Hashing**: Utilizes the industry-standard Argon2 algorithm for maximum password protection.
*   **Verified Signup Workflow**: Robust registration process featuring automated email verification via universal UUID tokens.
*   **Email & Telegram Alerting**: Multi-channel notification integration sending critical alerts directly to your Telegram Bot or SMTP Email.

### 📦 7. Production-Ready Infrastructure
*   **SQLite with WAL Mode**: Uses *Write-Ahead Logging* to ensure database stability during high-concurrency background monitoring tasks.
*   **Binary Protected Distribution**: Public releases are compiled using **Cython (C-Extensions)**, providing code obfuscation and up to 30% performance improvement over standard Python.
*   **SPA React Frontend**: Minified and bundled React application served directly by the backend, eliminating the need for an external web server.

---
<p align="center">
  <b>MataElang OS v1.0.0 - Professional Network Surveillance</b><br>
  <i>Designed for High-Reliability Operations.</i>
</p>
