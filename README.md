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
    *   **SSL/TLS Guardian**: Monitoring validitas sertifikat SSL dan peringatan otomatis sebelum masa berlaku habis.
    *   **TCP Port Scanner**: Memantau port spesifik yang terbuka pada server target.
*   **Massive Concurrency**: Ditenagai oleh Python `asyncio` dan `aiohttp`, mampu menghandle ratusan monitor secara simultan dengan penggunaan resource sistem yang sangat efisien.
*   **Smart Background Task**: Engine berjalan di background sebagai *lifespan service*, memastikan monitoring tetap aktif selama server menyala.

### 🛡️ 2. Cyber-Security & Threat Intelligence (The Shield)
*   **Web Defacement Detection**: Fitur **Content Locking** yang menyimpan hash SHA-256 dari halaman web. Memberi peringatan instan jika konten diubah oleh hacker/defacer.
*   **Security Baseline Port Locking**: Mengunci daftar port legal. Sistem akan mendeteksi jika ada port baru (backdoor) yang tiba-tiba terbuka.
*   **DDoS Early Warning System**: Analisis anomali latensi otomatis menggunakan deteksi spike (3x baseline) untuk memperingatkan potensi serangan flooding.
*   **GHOST Path Detection**: Melindungi server dari eksposur path sensitif atau kerentanan GHOST yang tidak sengaja terbuka ke publik.
*   **Phishing Intelligence**: Integrasi pengecekan target terhadap database phishing global untuk memastikan domain Anda tidak disalahgunakan.

### 📊 3. Geographical Visualization (The Eye)
*   **Interactive 3D Global Map**: Visualisasi dashboard menggunakan React-Three-Fiber untuk menampilkan globe 3D interaktif.
*   **Real-time Traffic Intercept**: Visualisasi arus traffic pengunjung menggunakan sensor satelit simulasi yang bergerak dari lokasi asal (Geo-IP) menuju server target.
*   **Cyber-HUD Interface**: UI bertema *Cyber-Surveillance* dengan animasi futuristik, memberikan pengalaman operasional NOC (Network Operations Center) kelas atas.
*   **Geo-IP Automatic Resolution**: Resolusi otomatis lokasi fisik (Latitude, Longitude, Country, City) berdasarkan IP atau Domain target.

### 🛠️ 4. Advanced Networking Toolkit (The Tools)
*   **Geographical Traceroute**: Melacak rute koneksi antar hop router dan memvisualisasikannya di atas peta dunia untuk mengidentifikasi titik kemacetan ISP.
*   **Enterprise Speedtest**: Integrasi engine *Speedtest-cli* untuk mengukur bandwidth (Download, Upload, Ping) secara real-time dan menyimpan riwayatnya.
*   **NOC-Style Analytics**: Grafik performa latensi dalam format *High-Resolution* untuk memantau stabilitas jaringan tiap jam.

### 📈 5. Reporting & Analytics (The Brain)
*   **Automated SLA Reporting**: Pembuatan laporan ketersediaan jaringan (Uptime %) yang dihitung secara akurat dalam rentang waktu harian, mingguan, hingga bulanan.
*   **PDF Export Engine**: Generate laporan SLA profesional secara instan dengan logo MatEl dalam format PDF menggunakan *ReportLab*.
*   **Data Portability**: Export riwayat data monitoring ke format **CSV** untuk kebutuhan analisis lebih lanjut menggunakan tools seperti Excel atau Power BI.
*   **Incident Timeline**: Log kronologis otomatis yang mencatat setiap kejadian downtime, uptime, dan perubahan status sistem secara detail.

### 🔐 6. Enterprise-Grade Security
*   **JWT Authentication**: Keamanan akses menggunakan *JSON Web Tokens* dengan masa berlaku yang dapat dikonfigurasi.
*   **Argon2 Password Hashing**: Menggunakan algoritma hashing paling aman di industri saat ini untuk melindungi password user.
*   **Verified Signup Workflow**: Sistem pendaftaran user dengan verifikasi email otomatis berbasis token UUID universal.
*   **Email & Telegram Alerting**: Integrasi notifikasi multi-channel yang mengirimkan alert kritis langsung ke saku Anda melalui Telegram Bot atau Email SMTP.

### 📦 7. Production-Ready Infrastructure
*   **SQLite with WAL Mode**: Menggunakan mode *Write-Ahead Logging* untuk menjamin stabilitas database saat banyak task monitoring menulis data secara bersamaan.
*   **Binary Protected Distribution**: Versi release dikompilasi menggunakan **Cython (C-Extensions)**, memberikan proteksi kode sumber dan peningkatan kecepatan eksekusi hingga 30% dibanding Python biasa.
*   **SPA React Frontend**: Aplikasi frontend yang sudah di-minify dan di-bundle ke dalam folder static, siap di-serve langsung oleh backend tanpa butuh web server tambahan.

---
<p align="center">
  <b>MataElang OS v1.0.0 - Professional Network Surveillance</b><br>
  <i>Designed for High-Reliability Operations.</i>
</p>
