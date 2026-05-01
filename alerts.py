"""
alerts.py — Consolidated Alert System for SafeGuard AI
Handles both email notifications and sound/siren triggers.
"""
import os
import time

# ─── Sound / Siren Tracking ──────────────────────────────────────────────────
_siren_active = False

def trigger_siren():
    """
    Mock trigger_siren: updates the local state and prints to console.
    """
    global _siren_active
    if not _siren_active:
        print("[ALARM] >>> SIREN TRIGGERED (MOCKED) <<<")
        _siren_active = True
    return True

def stop_siren():
    """
    Mock stop_siren: resets the state.
    """
    global _siren_active
    if _siren_active:
        print("[ALARM] >>> SIREN STOPPED (MOCKED) <<<")
        _siren_active = False
    return True

def is_siren_active():
    """
    Returns the current mocked siren status.
    """
    return _siren_active


# ─── Email / Notification Logic ──────────────────────────────────────────────

def send_alert(worker_name, missing_ppe, snapshot_path, gear_status=None):
    """
    Mock send_alert: logs the violation to the console.
    """
    print(f"\n[ALERT] Worker '{worker_name}' is missing PPE: {missing_ppe}")
    print(f"[ALERT] Snapshot saved at: {snapshot_path}")
    if gear_status:
        print(f"[ALERT] Gear Status: {gear_status}")
    print("[ALERT] Email notification (MOCKED) sent successfully.\n")
    return True
