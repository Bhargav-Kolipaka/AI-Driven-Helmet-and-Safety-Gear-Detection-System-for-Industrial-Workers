"""
app.py — SafeGuard AI: Main Flask Web Application
Routes: /, /login, /dashboard, /video_feed, /admin, /register,
        /api/status, /api/stop_siren, /api/check_duplicate_face,
        /api/scan_ppe_once, /upload_video
"""

import os
import threading
from datetime import datetime
from flask import (Flask, render_template, request, redirect,
                   url_for, session, jsonify, Response, flash)
from werkzeug.utils import secure_filename

import config
import database as db
from alerts import stop_siren

# ─── App Setup ───────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Handle Vercel's read-only filesystem (only /tmp is writable)
UPLOAD_FOLDER = config.UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(config.SNAPSHOT_DIR, exist_ok=True)
os.makedirs(config.WORKER_FACES_DIR, exist_ok=True)

ALLOWED_VIDEO_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}

# ─── Global State ────────────────────────────────────────────────────────────
IS_VERCEL = os.environ.get("VERCEL") == "1"

detector  = None
tracker   = None

# Shared detection state (updated by camera thread, read by routes)
_state = {
    "active"        : False,
    "missing_ppe"   : [],
    "worker_name"   : "Unknown",
    "worker_id"     : None,
    "siren_active"  : False,
    "last_alert_ts" : 0,
    "alert_cooldown": config.EMAIL_COOLDOWN_S,
    "gear_status"   : {"helmet": True, "gloves": True, "vest": True},
    "login_scan_result": None,
    "is_mock"       : IS_VERCEL
}
_state_lock = threading.Lock()


def get_detector():
    global detector
    if detector is None:
        try:
            from detection import PPEDetector
            detector = PPEDetector()
        except Exception as e:
            print(f"[app] Error loading detector: {e}")
            if IS_VERCEL:
                print("[app] Falling back to Mock detector on Vercel")
                class MockDetector:
                    def detect(self, frame): return frame, []
                    def get_missing_ppe(self, dets): return {"missing": [], "found": []}
                    def get_gear_status(self, dets): return {"helmet":True, "gloves":True, "vest":True}
                    def detect_video(self, path, sample_every=15):
                        return {"missing_ppe": [], "frames_analysed": 0, "details": []}
                detector = MockDetector()
    return detector


def get_tracker():
    global tracker
    if tracker is None:
        if IS_VERCEL:
            class MockTracker:
                def update(self, detections, frame): return []
            tracker = MockTracker()
        else:
            from tracker import PPETracker
            tracker = PPETracker()
    return tracker


def _allowed_video(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/logout")
def logout():
    session.clear()
    with _state_lock:
        _state["worker_name"] = "Unknown"
        _state["worker_id"]   = None
        _state["login_scan_result"] = None
    stop_siren()
    return redirect(url_for("home"))


@app.route("/dashboard")
def dashboard():
    if "worker_id" not in session and "admin" not in session:
        return redirect(url_for("login"))
    violations = db.get_recent_violations(20)
    stats      = db.get_stats()
    worker = {
        "name": session.get("worker_name", "Unknown"),
        "role": session.get("worker_role", "Worker"),
        "id"  : session.get("worker_id"),
    }
    with _state_lock:
        login_scan = _state.get("login_scan_result")
    return render_template("dashboard.html",
                           worker=worker, violations=violations,
                           stats=stats, login_scan=login_scan)


@app.route("/api/status")
def api_status():
    """Polling endpoint — returns current detection state as JSON."""
    with _state_lock:
        return jsonify({
            "missing_ppe"  : _state["missing_ppe"],
            "siren_active" : _state["siren_active"],
            "worker_name"  : _state["worker_name"],
            "gear_status"  : _state["gear_status"],
            "login_scan"   : _state.get("login_scan_result"),
        })


@app.route("/api/stop_siren", methods=["POST"])
def api_stop_siren():
    stop_siren()
    with _state_lock:
        _state["siren_active"] = False
    return jsonify({"success": True})


# ─── Admin: check duplicate face before registering ────────────────────────


@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == "admin123":   # change this in production!
            session["admin"] = True
            return redirect(url_for("admin"))
        flash("Invalid admin password", "error")
    return render_template("admin_login.html")


@app.route("/admin")
def admin():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    violations = db.get_recent_violations(100)
    stats      = db.get_stats()
    return render_template("admin.html",
                        violations=violations, stats=stats)


@app.route("/admin_logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("home"))


# ─── Video Upload PPE Analysis ───────────────────────────────────────────────

@app.route("/upload_video", methods=["GET", "POST"])
def upload_video():
    """
    Allows admin or logged-in worker to upload a video.
    Analyses the video with the PPE detector and returns
    which gears (Helmet, Gloves, Safety Vest) are missing.
    """
    if "worker_id" not in session and "admin" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        if "video" not in request.files:
            return jsonify({"success": False, "message": "No video file uploaded"}), 400

        f = request.files["video"]
        if f.filename == "":
            return jsonify({"success": False, "message": "No file selected"}), 400

        if not _allowed_video(f.filename):
            return jsonify({"success": False,
                            "message": "Invalid file type. Allowed: mp4, avi, mov, mkv, webm"}), 400

        filename  = secure_filename(f.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        f.save(save_path)

        # Run PPE analysis on the video
        det = get_detector()
        try:
            # On Vercel, we need to be very aggressive with sampling to avoid 10s timeouts
            sample_rate = 30 if IS_VERCEL else 15
            result = det.detect_video(save_path, sample_every=sample_rate)
        except IOError as e:
            return jsonify({"success": False, "message": f"Analysis Error: {str(e)}"}), 500
        except Exception as e:
            return jsonify({"success": False, "message": f"Server processing timeout or memory issue: {str(e)}"}), 500

        missing    = result["missing_ppe"]
        found      = result.get("found_ppe", [])
        frames_det = result.get("frames_with_detections", 0)

        print("🔍 FOUND PPE:", found)
        print("❌ MISSING PPE:", missing)

        if frames_det == 0:
            # Model saw nothing at all — inconclusive video
            gear_summary = "⚠️ No gear or people detected in video."
            compliant    = False
        elif missing:
            gear_summary = "Missing: " + ", ".join(missing)
            compliant    = False
        else:
            # Something was detected and nothing was reported missing
            if found:
                gear_summary = "✅ All gear worn: " + ", ".join(found)
            else:
                gear_summary = "✅ No violations detected."
            compliant = True

        # Log if there are violations in the video
        worker_id   = session.get("worker_id")
        worker_name = session.get("worker_name", "Video Upload")
        if missing:
            gear_status = det.get_gear_status([]) # We already have 'missing', but we want the full dict
            # Refined status calculation based on the 'missing' list from analysis
            status_map = {m.lower().replace(" ", "-"): False for m in missing}
            for req in config.REQUIRED_PPE:
                if req not in status_map:
                    status_map[req] = True
            
            db.log_violation(worker_id, worker_name, missing,
                             save_path, False, gear_status=status_map)

        return jsonify({
            "success"        : True,
            "compliant"      : compliant,
            "missing_ppe"    : missing,
            "found_ppe"      : found,
            "gear_summary"   : gear_summary,
            "frames_analysed": result["frames_analysed"],
            "details"        : result["details"],
        })

    return render_template("upload_video.html")


# ─── Entry Point ─────────────────────────────────────────────────────────────
# Initialize database on startup (crucial for Vercel cold starts)
db.init_db()

if __name__ == "__main__":
    print("=" * 60)
    print("  SafeGuard AI — Construction Safety System")
    print(f"  Running at http://{config.HOST}:{config.PORT}")
    print("=" * 60)
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG, threaded=True)
