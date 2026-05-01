"""
database.py — SQLite database setup and helpers for SafeGuard AI
Tables: workers, violations
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import numpy as np
import config


def get_connection():
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist. On Vercel, copy the seed DB to /tmp."""

    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS workers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            email           TEXT,
            role            TEXT DEFAULT 'Worker',
            face_encoding   TEXT,          -- JSON-encoded list of 128 floats
            face_image_path TEXT,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS violations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id   INTEGER,           -- NULL if worker not recognized
            worker_name TEXT,
            missing_ppe TEXT,              -- JSON list e.g. ["Helmet","Gloves"]
            gear_status TEXT,              -- JSON: {"helmet":true,"gloves":false,"vest":true}
            gear_summary TEXT,             -- Human-readable e.g. "Not Proper Gears: Gloves Missing"
            snapshot    TEXT,              -- path to saved frame image
            email_sent  INTEGER DEFAULT 0,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (worker_id) REFERENCES workers(id)
        )
    """)

    # Migrate existing violations table if gear_status / gear_summary columns missing
    existing_cols = [row[1] for row in cur.execute("PRAGMA table_info(violations)").fetchall()]
    if "gear_status" not in existing_cols:
        cur.execute("ALTER TABLE violations ADD COLUMN gear_status TEXT")
    if "gear_summary" not in existing_cols:
        cur.execute("ALTER TABLE violations ADD COLUMN gear_summary TEXT")

    conn.commit()
    conn.close()
    print("[database] Database initialized.")


# ─── Violation helpers ───────────────────────────────────────────────────────

def build_gear_summary(missing_ppe: list) -> str:
    """Build a human-readable gear status summary."""
    if not missing_ppe:
        return "All Gears Proper"
    missing_str = ", ".join(missing_ppe)
    return f"Not Proper Gears: {missing_str} Missing"


def log_violation(worker_id: Optional[int], worker_name: str, missing_ppe: List[str],
                  snapshot: str = "", email_sent: bool = False,
                  gear_status: Optional[Dict[str, bool]] = None) -> int:
    conn = get_connection()
    cur  = conn.cursor()

    gear_status_json = json.dumps(gear_status) if gear_status else None
    gear_summary     = build_gear_summary(missing_ppe)

    cur.execute(
        "INSERT INTO violations (worker_id, worker_name, missing_ppe, gear_status, gear_summary, snapshot, email_sent) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (worker_id, worker_name, json.dumps(missing_ppe),
         gear_status_json, gear_summary, snapshot, int(email_sent))
    )
    conn.commit()
    vid = cur.lastrowid
    conn.close()
    return int(vid or 0)


def get_recent_violations(limit: int = 50) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM violations ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        # Ensure missing_ppe is a list
        ppe_str = d.get("missing_ppe")
        d["missing_ppe"] = json.loads(ppe_str) if ppe_str else []
        
        # Ensure gear_status is a dict
        gs_str = d.get("gear_status")
        if gs_str:
            try:
                d["gear_status"] = json.loads(gs_str)
            except Exception:
                d["gear_status"] = {}
        else:
            d["gear_status"] = {}
        result.append(d)
    return result


def get_stats() -> dict:
    conn = get_connection()
    total_workers = conn.execute("SELECT COUNT(*) FROM workers").fetchone()[0]
    today = datetime.now().strftime("%Y-%m-%d")
    alerts_today = conn.execute(
        "SELECT COUNT(*) FROM violations WHERE created_at LIKE ?", (f"{today}%",)
    ).fetchone()[0]
    total_alerts = conn.execute("SELECT COUNT(*) FROM violations").fetchone()[0]
    conn.close()
    compliance = max(0, round(100 - (alerts_today / max(total_workers, 1)) * 10))
    return {
        "total_workers": total_workers,
        "alerts_today" : alerts_today,
        "total_alerts" : total_alerts,
        "compliance"   : min(100, compliance),
    }


if __name__ == "__main__":
    init_db()
