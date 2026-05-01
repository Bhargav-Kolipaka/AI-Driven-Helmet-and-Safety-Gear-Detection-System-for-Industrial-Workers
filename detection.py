"""
detection.py — PPE Detection Engine for SafeGuard AI
Uses Roboflow Hosted Inference API (primary) with local YOLO fallback.
Detects: Helmet, Gloves, Vest (and violations: no-helmet, no-gloves, no-vest)
"""

import cv2
import numpy as np
import os
import base64
import requests
import config

# ─── Colors (BGR) ────────────────────────────────────────────────────────────
COLOR_SAFE    = (0, 220, 80)     # green
COLOR_DANGER  = (0, 50, 255)     # red
COLOR_PERSON  = (255, 180, 0)    # blue-ish
COLOR_TEXT_BG = (15, 15, 15)

# No longer a global constant — constructed dynamically below

# Labels in Roboflow model mapped to canonical names
_LABEL_MAP = {
    # klema-ai/ppe-yolo-jrblc (and user cloned variants)
    "helmet": "helmet",
    "Helmet": "helmet",
    "no helmet": "no-helmet",
    "No helmet": "no-helmet",
    "no_helmet": "no-helmet",
    "safety-helmet": "helmet",
    "Safety-Helmet": "helmet",
    
    "vest": "vest",
    "Vest": "vest",
    "no vest": "no-vest",
    "No vest": "no-vest",
    "no_vest": "no-vest",
    "safety-vest": "vest",
    "Safety-Vest": "vest",
    
    "glove": "gloves",
    "gloves": "gloves",
    "Glove": "gloves",
    "Gloves": "gloves",
    "no glove": "no-gloves",
    "No glove": "no-gloves",
    "no_gloves": "no-gloves",
    "no gloves": "no-gloves",
    "No gloves": "no-gloves",
    
    # Extra classes from ppe-qyupq-hpq7k
    "Mask": "mask",
    "mask": "mask",
    "Boots": "boots",
    "boots": "boots",
    "Safety-Wearpack": "body-suit",
    "safety-wearpack": "body-suit",
    
    "Person": "person",
}


# The _normalize_label function is no longer needed as mapping is done directly in detect()
# def _normalize_label(raw: str) -> str:
#     """Normalize Roboflow class label to a canonical form."""
#     return _LABEL_MAP.get(raw, raw.lower())


class PPEDetector:
    def __init__(self, model_path: str = None):
        """Initialize detector — Roboflow API is primary, local YOLO as fallback."""
        self._use_roboflow = True
        self._local_model  = None

        # Try loading local YOLO as backup only
        try:
            from ultralytics import YOLO
            path = model_path or config.MODEL_PATH
            if not os.path.exists(path):
                path = config.PRETRAINED_MODEL
            self._local_model = YOLO(path)
            print(f"[PPEDetector] Local YOLO loaded as fallback: {path}")
        except Exception as e:
            print(f"[PPEDetector] Could not load local YOLO (fallback unavailable): {e}")

        self.api_url = (
            f"https://detect.roboflow.com/{config.ROBOFLOW_PROJECT}/{config.ROBOFLOW_VERSION}"
            f"?api_key={config.ROBOFLOW_API_KEY}&confidence=25&overlap=30"
        )
        print(f"[PPEDetector] Roboflow API ready: {config.ROBOFLOW_PROJECT} v{config.ROBOFLOW_VERSION}")

    # ─── Roboflow Inference ──────────────────────────────────────────────────

    def _detect_roboflow(self, frame: np.ndarray):
        """
        Call Roboflow Hosted Inference API on a single frame.
        Returns list of raw detection dicts from the API.
        """
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

        try:
            resp = requests.post(
                self.api_url,
                data=b64,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=5,
            )
            if resp.status_code == 200:
                preds = resp.json().get("predictions", [])
                if preds:
                    # Log raw detections to help verify mapping
                    p_info = []
                    for p in preds[:5]:
                        raw = p.get('class', 'unknown')
                        cid = p.get('class_id', '?')
                        conf = p.get('confidence', 0.0)
                        mapped = _LABEL_MAP.get(str(cid), _LABEL_MAP.get(raw.lower(), raw.lower()))
                        p_info.append(f"[{cid}]{raw[:15]}...->{mapped} ({conf:.2f})")
                    print(f"[PPEDetector] Roboflow raw: {', '.join(p_info)}")
                return preds
            else:
                print(f"[PPEDetector] Roboflow API error {resp.status_code}: {resp.text[:200]}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"[PPEDetector] Roboflow request failed: {e}")
            return None

    # ─── Local YOLO Fallback ─────────────────────────────────────────────────

    def _detect_local(self, frame: np.ndarray):
        """Run local YOLO model; returns list of detection dicts."""
        if self._local_model is None:
            return []
        results = self._local_model.predict(
            source=frame,
            conf=config.CONFIDENCE_THRESH,
            iou=config.IOU_THRESH,
            verbose=False,
            stream=False,
        )
        preds = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                cls_id = int(box.cls[0])
                label  = self._local_model.names.get(cls_id, f"cls_{cls_id}")
                conf   = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                w = x2 - x1
                h = y2 - y1
                cx = x1 + w // 2
                cy = y1 + h // 2
                preds.append({
                    "class": label,
                    "confidence": conf,
                    "x": cx, "y": cy, "width": w, "height": h,
                })
        return preds

    # ─── Main detect() ───────────────────────────────────────────────────────

    def detect(self, frame: np.ndarray):
        """
        Run PPE detection using Roboflow API + Local YOLO merge for robustness.
        """
        cloud_preds = self._detect_roboflow(frame) or []
        local_preds = self._detect_local(frame) or []
        
        # Merge logic:
        # 1. Take all cloud predictions (usually more specialized for the project)
        # 2. Add 'person' detections from local YOLO if cloud doesn't have person class
        combined_raw = list(cloud_preds)
        
        # Check if cloud model has 'person' class in its results
        cloud_has_person = any(p.get("class", "").lower() == "person" for p in cloud_preds)
        
        if not cloud_has_person:
            for lp in local_preds:
                if lp.get("class", "").lower() == "person":
                    combined_raw.append(lp)

        detections = []
        annotated  = frame.copy()

        for pred in combined_raw:
            raw_cls = pred.get("class", "").lower()
            cid     = str(pred.get("class_id", ""))
            
            label = _LABEL_MAP.get(cid) or _LABEL_MAP.get(raw_cls) or raw_cls
            conf  = float(pred.get("confidence", 0))

            # Thresholds
            min_conf = 0.25 if label == "person" else config.CONFIDENCE_THRESH
            if conf < min_conf:
                continue

            # Convert format
            cx, cy = pred.get("x", 0), pred.get("y", 0)
            w, h   = pred.get("width", 0), pred.get("height", 0)
            x1, y1 = int(cx - w / 2), int(cy - h / 2)
            x2, y2 = int(cx + w / 2), int(cy + h / 2)

            is_violation = label in config.VIOLATION_CLASSES
            is_safe      = label in config.REQUIRED_PPE

            color = COLOR_DANGER if is_violation else (
                COLOR_SAFE if is_safe else COLOR_PERSON
            )

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            label_text = f"{label} {conf:.2f}"
            (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            cv2.rectangle(annotated, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
            cv2.putText(annotated, label_text, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

            detections.append({
                "box"          : [x1, y1, x2, y2],
                "center"       : [cx, cy],
                "label"        : label,
                "conf"         : conf,
                "is_safe"      : is_safe,
                "is_violation" : is_violation,
            })

        return annotated, detections

    def get_missing_ppe(self, detections: list) -> dict:
        if not detections:
            return {"missing": [], "found": [], "no_detection": True}

        found_set = set()

        for d in detections:
            # 🔥 Handle all possible keys safely
            label = (
            d.get("label") or 
            d.get("class") or 
            d.get("name") or 
            ""
            ).lower()

            print("👉 Parsed Label:", label)

            if "helmet" in label:
                found_set.add("helmet")
            elif "vest" in label:
                found_set.add("vest")
            elif "glove" in label:
                found_set.add("gloves")
            elif "mask" in label:
                found_set.add("mask")
            elif "boot" in label:
                found_set.add("boots")
            elif "suit" in label:
                found_set.add("body-suit")

        print("✅ FOUND SET:", found_set)

        required = config.REQUIRED_PPE

        missing_set = [r for r in required if r not in found_set]

        def _human(name):
            return name.replace("-", " ").title()

        return {
        "missing": [_human(m) for m in missing_set],
        "found": [_human(f) for f in found_set],
        "no_detection": False
        }

    def get_gear_status(self, detections: list) -> dict:
        """
        Returns a dict mapping each required gear key to its status (True/False).
        """
        res = self.get_missing_ppe(detections)
        missing_titles = [m.lower().replace(" ", "-") for m in res.get("missing", [])]
        
        status = {}
        for req in config.REQUIRED_PPE:
            status[req] = req not in missing_titles
        return status

    def detect_video(self, video_path: str, sample_every: int = 15):
        """
        Analyse a video file frame by frame.
        Compliant frame = at least one gear was positively detected & nothing missing.
        Violation frame = explicit missing gear OR no-PPE violations found.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0: fps = 30

        # Track counts for statistical analysis (Exactness)
        found_counts   = {g: 0 for g in config.REQUIRED_PPE}
        missing_counts = {g: 0 for g in config.REQUIRED_PPE}

        frame_idx   = 0
        analysed    = 0
        details     = []
        total_people_detected = 0
        frames_with_detections = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % sample_every == 0:
                annotated, dets = self.detect(frame)
                
                # Check for person context
                if dets:
                    total_people_detected += 1
                
                res = self.get_missing_ppe(dets)
                missing_this_raw = res["missing"] # Titles (e.g. "Helmet")
                found_this_raw   = res["found"]

                analysed += 1
                if not res.get("no_detection"):
                    frames_with_detections += 1
                
                # Update stats using slugified names to match config.REQUIRED_PPE
                for m in missing_this_raw:
                    slug = m.lower().replace(" ", "-")
                    if slug in missing_counts: missing_counts[slug] += 1
                for f in found_this_raw:
                    slug = f.lower().replace(" ", "-")
                    if slug in found_counts: found_counts[slug] += 1

                if not res.get("no_detection") and (missing_this_raw or found_this_raw):
                    seconds   = int(frame_idx / fps)
                    timestamp = f"{seconds // 60:02d}:{seconds % 60:02d}"

                    thumbnail = None
                    if len(details) < 15:
                        try:
                            small = cv2.resize(annotated, (320, 180))
                            _, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 70])
                            thumbnail = base64.b64encode(buf).decode("utf-8")
                        except Exception: pass

                    details.append({
                        "frame"      : frame_idx,
                        "timestamp"  : timestamp,
                        "missing_ppe": missing_this_raw,
                        "found_ppe"  : found_this_raw,
                        "thumbnail"  : thumbnail,
                    })

            frame_idx += 1

        cap.release()

        # Final consolidation (Safety-First / Exactness):
        # A gear is "Missing" if it was absent in more than 15% of frames where a person was seen.
        # This filters out flickering/occlusion while staying strict on actual non-compliance.
        final_missing = []
        final_found   = []
        
        threshold = 0.15 # 15% threshold for "Exact" reporting
        
        for ppe in config.REQUIRED_PPE:
            miss_freq  = missing_counts[ppe] / total_people_detected if total_people_detected > 0 else 0
            found_freq = found_counts[ppe] / total_people_detected if total_people_detected > 0 else 0
            
            title = ppe.replace("-", " ").title()
            if found_freq == 0:
                final_missing.append(title)

            # If detected enough → it's found
            elif found_freq > 0.10:
                final_found.append(title)

            # If frequently missing → missing
            elif miss_freq > threshold:
                final_missing.append(title)

        return {
            "frames_analysed"       : analysed,
            "frames_with_detections": frames_with_detections,
            "missing_ppe"           : final_missing,
            "found_ppe"             : final_found,
            "person_found"          : total_people_detected > 0,
            "details"               : details,
        }

def get_detector():
    """Singleton-like getter for the PPE detector."""
    global _detector
    if _detector is None:
        _detector = PPEDetector()
    return _detector

_detector = None

# ─── Quick test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    detector = PPEDetector()
    cap = cv2.VideoCapture(0)
    print("Press 'q' to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        annotated, dets = detector.detect(frame)
        missing = detector.get_missing_ppe(dets)
        if missing:
            text = "MISSING: " + ", ".join(missing)
            cv2.putText(annotated, text, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        cv2.imshow("SafeGuard AI — PPE Detection", annotated)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
