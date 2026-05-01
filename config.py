"""
config.py — Central configuration for SafeGuard AI
Edit the values below before running the application.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # optionally use a .env file
IS_VERCEL = os.environ.get("VERCEL") == "1"

# ─── Email Configuration ──────────────────────────────────────────────────────
EMAIL_SENDER      = os.getenv("EMAIL_SENDER", "sharadagnihotri197@gmail.com")
EMAIL_PASSWORD    = os.getenv("EMAIL_PASSWORD", "rpqv vpun dzpa amaa")
EMAIL_RECIPIENT   = os.getenv("EMAIL_RECIPIENT", "sharadagnihotri197@gmail.com")
EMAIL_COOLDOWN_S  = 30   # seconds between repeat alerts for the same worker

# ─── Model Configuration ──────────────────────────────────────────────────────
MODEL_PATH        = os.path.join("models", "ppe_yolov11.pt")
PRETRAINED_MODEL  = "yolo11n.pt"   # fallback pretrained weights
CONFIDENCE_THRESH = 0.35           # Lowered from 0.50 for better recall
IOU_THRESH        = 0.45           

# Required PPE classes that must be present for a safe worker
REQUIRED_PPE = ["helmet", "gloves", "vest", "mask", "boots", "body-suit"]

# Class names mapping from Roboflow indices
CLASS_NAMES = {
    0: "helmet",
    1: "no-helmet",
    2: "vest",
    3: "gloves",
    4: "no-vest",
    5: "person",
}

# Classes that indicate MISSING equipment
VIOLATION_CLASSES = ["no-helmet", "no-gloves", "no-vest"]

# ─── DeepSort Configuration ───────────────────────────────────────────────────
MAX_AGE          = 30    # frames before track is deleted
N_INIT           = 3     # frames before track is confirmed
MAX_IOU_DISTANCE = 0.7

# ─── Face Recognition ─────────────────────────────────────────────────────────
FACE_DETECTOR_MODEL  = os.path.join("models", "yunet.onnx")
FACE_RECOGNIZER_MODEL = os.path.join("models", "sface.onnx")
FACE_TOLERANCE       = 0.36  # Cosine similarity threshold for SFace (0.0 to 1.0)
FACE_TOLERANCE_REG   = 0.40  # Duplicate check threshold

if IS_VERCEL:
    WORKER_FACES_DIR = "/tmp/worker_faces"
    SNAPSHOT_DIR     = "/tmp/snapshots"
    DATABASE_PATH    = "/tmp/safeguard.db"
    UPLOAD_FOLDER    = "/tmp/uploads"
else:
    WORKER_FACES_DIR = "worker_faces"
    SNAPSHOT_DIR     = os.path.join("static", "snapshots")
    DATABASE_PATH    = "safeguard.db"
    UPLOAD_FOLDER    = os.path.join("static", "uploads")

# ─── Flask / App ──────────────────────────────────────────────────────────────
SECRET_KEY        = os.getenv("SECRET_KEY", "safeguard-ai-secret-2024")
DEBUG             = True
HOST              = "0.0.0.0"
PORT              = 5000

# ─── Roboflow Dataset ─────────────────────────────────────────────────────────
# ─── Roboflow Dataset (User Cloned: tilaks-workspace/ppe-qyupq-hpq7k) 
ROBOFLOW_API_KEY  = os.getenv("ROBOFLOW_API_KEY", "xodLx3bvnpULzY2qfv6L")
ROBOFLOW_WORKSPACE = "tilaks-workspace"
ROBOFLOW_PROJECT   = "ppe-qyupq-hpq7k"
ROBOFLOW_VERSION   = 1  # Standard first version
ROBOFLOW_PUBLISHABLE_KEY = "rf_wNwcWlX4CFdr8NloCjKYC45tXAU2"

# ─── Sound ────────────────────────────────────────────────────────────────────
SIREN_SOUND_PATH  = os.path.join("static", "sounds", "siren.wav")
SIREN_VOLUME      = 0.8   # 0.0 – 1.0
