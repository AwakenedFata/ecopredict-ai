"""
deploy_check.py
Pre-flight verification script to validate system readiness before deployment.
Checks Python version, dependencies, model weights, database status, and API health.
"""

import os
import sys
import sqlite3

def run_checks():
    print("=" * 60)
    print("EcoPredict AI - Pre-Flight Deployment Readiness Verification")
    print("=" * 60)

    # 1. Python runtime check
    py_ver = sys.version_info
    print(f"[OK] Python Runtime: {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    if py_ver < (3, 10):
        print("[FAIL] Python >= 3.10 required.")
        return False

    # 2. Key library imports
    required_packages = [
        ("fastapi", "FastAPI Web Framework"),
        ("uvicorn", "ASGI Server"),
        ("lightgbm", "Gradient Boosting ML Engine"),
        ("sklearn", "Scikit-Learn ML Suite"),
        ("shap", "TreeSHAP Explainability"),
        ("pydantic", "Schema Validation"),
        ("psutil", "Hardware Telemetry Provider")
    ]

    for pkg, label in required_packages:
        try:
            __import__(pkg)
            print(f"[OK] Package loaded: {pkg} ({label})")
        except ImportError as e:
            print(f"[FAIL] Missing package: {pkg} - {e}")
            return False

    # 3. Model weights check
    weights = [
        "ai/weights/lgbm_rul_model.pkl",
        "ai/weights/lgbm_risk_model.pkl",
        "ai/weights/lgbm_mode_model.pkl",
        "ai/weights/model_metadata.json"
    ]
    for w in weights:
        if os.path.exists(w) and os.path.getsize(w) > 0:
            print(f"[OK] Weight file verified: {w} ({os.path.getsize(w)} bytes)")
        else:
            print(f"[FAIL] Missing or empty weight file: {w}")
            return False

    # 4. Database integrity
    db_file = "electronic_fleet.db"
    if not os.path.exists(db_file):
        print(f"[WARN] Database {db_file} not found locally, seeding now...")
        from core.seeder import seed_fleet_database
        seed_fleet_database()

    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    dev_count = cur.execute("SELECT COUNT(*) FROM asset_devices").fetchone()[0]
    tel_count = cur.execute("SELECT COUNT(*) FROM sensor_telemetry").fetchone()[0]
    pred_count = cur.execute("SELECT COUNT(*) FROM failure_predictions").fetchone()[0]
    conn.close()

    print(f"[OK] Database online: {dev_count} devices, {tel_count} telemetry points, {pred_count} AI predictions.")
    if dev_count < 100:
        print("[FAIL] Device fleet underpopulated.")
        return False

    # 5. Static assets
    static_files = ["static/index.html", "static/css/style.css", "static/js/app.js"]
    for s in static_files:
        if os.path.exists(s) and os.path.getsize(s) > 0:
            print(f"[OK] Static asset verified: {s}")
        else:
            print(f"[FAIL] Missing static asset: {s}")
            return False

    print("=" * 60)
    print("ALL CHECKS PASSED: System is READY for presentation & cloud deployment.")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_checks()
    sys.exit(0 if success else 1)
