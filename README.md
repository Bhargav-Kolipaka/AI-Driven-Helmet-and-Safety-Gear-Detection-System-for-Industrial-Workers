<div align="center">

# 🛡️ SafeGuard AI
### Smart PPE Detection System
**AI-Powered Safety Monitoring for Industrial & Construction Sites**

![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-Web_App-black?style=flat-square&logo=flask)
![YOLO](https://img.shields.io/badge/YOLO-Object_Detection-red?style=flat-square)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer_Vision-green?style=flat-square&logo=opencv)
![License](https://img.shields.io/badge/License-Academic-orange?style=flat-square)

</div>

---

## 📌 Project Overview

**SafeGuard AI** is an intelligent safety monitoring system that uses **Computer Vision** and **Deep Learning** to detect whether workers are wearing proper Personal Protective Equipment (PPE) — such as helmets, gloves, and safety vests.

The system processes real-time video streams or uploaded videos, detects violations, triggers alerts, and logs results for analysis.

---

## 🎯 Key Objectives

- ✅ Automate PPE compliance monitoring
- ✅ Detect helmets, gloves, and safety vests in real-time
- ✅ Reduce human error in safety supervision
- ✅ Generate instant alerts for violations
- ✅ Maintain violation logs for analysis

---

## ✨ Features

| Feature | Description |
|--------|-------------|
| 🎥 Real-Time Detection | Live PPE monitoring using YOLO |
| 📂 Video Upload Analysis | Analyze pre-recorded footage |
| 🚨 Siren Alert System | Instant audio alerts on violations |
| 📧 Email Notifications | Automated violation email alerts |
| 📊 Admin Dashboard | Analytics and compliance overview |
| 📁 Violation Logs | History tracking & export |
| 🌐 Web Application | Flask-based browser interface |

---

## 🖥️ System Screenshots

<table>
  <tr>
    <td align="center"><b>🏠 Home Page</b></td>
    <td align="center"><b>📊 Admin Dashboard</b></td>
  </tr>
  <tr>
    <td><img src="assets/screenshots/home.png" alt="Home Page" width="400"/></td>
    <td><img src="assets/screenshots/admin.png" alt="Admin Dashboard" width="400"/></td>
  </tr>
  <tr>
    <td align="center"><b>📂 Upload Page</b></td>
    <td align="center"><b>⚠️ Detection Result</b></td>
  </tr>
  <tr>
    <td><img src="assets/screenshots/upload.png" alt="Upload Page" width="400"/></td>
    <td><img src="assets/screenshots/result.png" alt="Detection Result" width="400"/></td>
  </tr>
</table>

---

## ⚙️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python, Flask |
| **AI / ML** | YOLO (Object Detection), OpenCV, NumPy |
| **Frontend** | HTML, CSS, JavaScript |
| **Database** | SQLite |

---

## 🧠 System Workflow

```
1. 📹 Capture video (live stream or uploaded file)
2. 🔄 Preprocess frames (resize, normalize)
3. 🤖 Detect objects using YOLO
4. 🦺 Identify PPE (helmet, gloves, vest, boots)
5. 🏷️ Classify → ✅ Compliant | ❌ Non-Compliant
6. 🚨 Generate alerts (siren + email notification)
7. 💾 Store results in database
8. 📊 Display results on admin dashboard
```

---

## 📁 Project Structure

```
SafeGuard-AI/
│
├── app.py                  # Main Flask application
├── alerts.py               # Alert system (siren + email)
├── detection.py            # YOLO PPE detection logic
├── tracker.py              # Object tracking module
├── database.py             # Database operations
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── safeguard.db            # SQLite database
├── README.md
│
├── models/                 # YOLO model weights
├── static/                 # CSS, JS, images
├── templates/              # HTML templates
├── worker_faces/           # Worker face data
└── assets/
    └── screenshots/        # UI screenshots
```

---

## 💻 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/safeguard-ai.git
cd safeguard-ai
```

### 2. Create & Activate Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python app.py
```

---

## 🚀 Usage

1. Open your browser and go to: **`http://127.0.0.1:5000`**
2. Navigate to the **Admin Panel**
3. **Upload a video** or start **live monitoring**
4. View **PPE compliance status** and **violation alerts**

---

## 📊 Output Example

```
Worker Detection Result:
─────────────────────────
Helmet   : ✅ Worn
Gloves   : ❌ Missing
Vest     : ✅ Worn
Boots    : ❌ Missing
─────────────────────────
Status   : ⚠️ VIOLATION DETECTED
➡️  Alert triggered → Siren + Email notification sent
```

---

## 🔔 Alert System

When a PPE violation is detected, the system automatically:

- 🚨 **Triggers a siren alert**
- 📧 **Sends an email notification** to supervisors
- 💾 **Logs the violation** in the database with timestamp

---

## 🔮 Future Enhancements

- [ ] 👤 Face recognition for worker identification
- [ ] 📱 Mobile app integration
- [ ] 📷 Multi-camera support
- [ ] ☁️ Cloud deployment
- [ ] 🧠 Behavior anomaly detection

---

## 📜 License

This project is developed for **academic purposes**.  
Free to use with proper attribution.

---

## ⭐ Acknowledgement

Special thanks to our **project guide** and **institution** for their continuous support and guidance throughout this project.

---

<div align="center">

Made with ❤️ for workplace safety

</div>
