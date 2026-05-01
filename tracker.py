"""
tracker.py — DeepSort multi-object tracker for SafeGuard AI
Links YOLOv11 PPE detections to consistent person IDs across frames.
"""

import numpy as np
from deep_sort_realtime.deepsort_tracker import DeepSort
import config


class PPETracker:
    def __init__(self):
        self.tracker = DeepSort(
            max_age=config.MAX_AGE,
            n_init=config.N_INIT,
            max_iou_distance=config.MAX_IOU_DISTANCE,
            embedder="mobilenet",          # lightweight re-ID embedder
            half=False,
            embedder_gpu=False,
        )
        # track_id → latest missing PPE list
        self.track_violations: dict[int, list] = {}

    def update(self, detections: list, frame: np.ndarray) -> list:
        """
        Update DeepSort with new detections.

        Args:
            detections: list of dicts from PPEDetector.detect()
            frame     : original BGR frame (needed for appearance embedding)

        Returns:
            tracks: list of dicts with keys:
                'track_id', 'box' [x1,y1,x2,y2], 'label', 'is_violation'
        """
        # Separate person boxes from PPE boxes
        person_detections = [
            d for d in detections
            if d["label"] == "person"
        ]

        # Build input format for DeepSort: ([left, top, w, h], conf, class)
        ds_input = []
        for det in person_detections:
            x1, y1, x2, y2 = det["box"]
            w = x2 - x1
            h = y2 - y1
            ds_input.append(
                ([x1, y1, w, h], det["conf"], "person")
            )

        tracks = []
        if ds_input:
            raw_tracks = self.tracker.update_tracks(ds_input, frame=frame)
            for t in raw_tracks:
                if not t.is_confirmed():
                    continue
                ltrb = t.to_ltrb()
                tx1, ty1, tx2, ty2 = map(int, ltrb)
                track_id = t.track_id

                # Find PPE violations near this person's bounding box
                missing = self._get_nearby_violations(
                    [tx1, ty1, tx2, ty2], detections
                )
                self.track_violations[track_id] = missing

                tracks.append({
                    "track_id"    : track_id,
                    "box"         : [tx1, ty1, tx2, ty2],
                    "missing_ppe" : missing,
                })

        return tracks

    def _get_nearby_violations(self, person_box: list, detections: list) -> list:
        """
        Find PPE violations overlapping with a person bounding box.
        Gear center must be within the person's bounding box.
        """
        px1, py1, px2, py2 = person_box
        missing = []
        person_gear = []

        for det in detections:
            # Note: detections now have a 'center' key from detect()
            dcx, dcy = det.get("center", [0, 0])
            
            # Center-in-box check
            if px1 <= dcx <= px2 and py1 <= dcy <= py2:
                if det["is_violation"]:
                    if det["label"] == "no-helmet": missing.append("Helmet")
                    elif det["label"] == "no-gloves": missing.append("Gloves")
                    elif det["label"] == "no-vest": missing.append("Safety Vest")
                elif det["label"] in config.REQUIRED_PPE:
                    person_gear.append(det["label"])

        # Absence check
        if "helmet" not in person_gear and "Helmet" not in missing:
            missing.append("Helmet")
        if "gloves" not in person_gear and "Gloves" not in missing:
            missing.append("Gloves")
        if "vest" not in person_gear and "Safety Vest" not in missing:
            missing.append("Safety Vest")

        return list(set(missing))

    def get_violations(self) -> dict:
        """Return current track_id → missing PPE mapping."""
        return self.track_violations
