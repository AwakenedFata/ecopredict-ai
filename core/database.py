"""
core/database.py
Database layer for AI-Based Electronic Failure Prediction.
Implements high-performance SQLite storage with Write-Ahead Logging (WAL),
serverless /tmp auto-provisioning, foreign keys enforcement, and thread-safe connections.
"""

import os
import shutil
import sqlite3
from typing import Generator, Optional
from contextlib import contextmanager

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(ROOT_DIR, "electronic_fleet.db")
API_DB_PATH = os.path.join(ROOT_DIR, "api", "electronic_fleet.db")

_IS_SEEDING = False


def is_serverless_env() -> bool:
    """Detects Vercel, AWS Lambda, or read-only container filesystems."""
    if (
        os.environ.get("VERCEL")
        or os.environ.get("VERCEL_ENV")
        or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
        or os.environ.get("AWS_EXECUTION_ENV")
    ):
        return True
    try:
        return not os.access(ROOT_DIR, os.W_OK)
    except Exception:
        return True


def get_db_path() -> str:
    if is_serverless_env():
        tmp_db = "/tmp/electronic_fleet.db"
        if not os.path.exists(tmp_db) or os.path.getsize(tmp_db) < 32768:
            for src in (API_DB_PATH, DEFAULT_DB_PATH):
                if os.path.exists(src) and os.path.getsize(src) >= 32768:
                    try:
                        shutil.copy2(src, tmp_db)
                        break
                    except Exception:
                        pass
        return tmp_db
    return os.environ.get("FLEET_DB_PATH", DEFAULT_DB_PATH)


SCHEMA_SQL = """
-- 1. ORGANIZATIONS
CREATE TABLE IF NOT EXISTS organizations (
    org_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    industry_type TEXT NOT NULL,
    sustainability_target_pct REAL DEFAULT 20.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. ASSET DEVICES
CREATE TABLE IF NOT EXISTS asset_devices (
    device_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(org_id),
    asset_tag TEXT NOT NULL UNIQUE,
    device_type TEXT NOT NULL, -- 'LAPTOP', 'DESKTOP', 'SERVER_NODE', 'EDGE_GATEWAY'
    brand_model TEXT NOT NULL,
    cpu_spec TEXT NOT NULL,
    ram_gb INTEGER NOT NULL,
    storage_capacity_gb INTEGER NOT NULL,
    commission_date DATE NOT NULL,
    expected_lifecycle_months INTEGER NOT NULL DEFAULT 48,
    operating_age_months INTEGER NOT NULL,
    current_status TEXT NOT NULL DEFAULT 'ACTIVE', -- 'ACTIVE', 'MAINTENANCE', 'RETIRED'
    last_telemetry_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_devices_type ON asset_devices(device_type);
CREATE INDEX IF NOT EXISTS idx_devices_status ON asset_devices(current_status);

-- 3. SENSOR TELEMETRY (Time-Series Logs)
CREATE TABLE IF NOT EXISTS sensor_telemetry (
    telemetry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL REFERENCES asset_devices(device_id) ON DELETE CASCADE,
    recorded_at TIMESTAMP NOT NULL,
    avg_cpu_temp_c REAL NOT NULL,
    max_cpu_temp_c REAL NOT NULL,
    ambient_temp_c REAL NOT NULL DEFAULT 24.0,
    fan_rpm INTEGER NOT NULL,
    fan_duty_cycle_pct REAL NOT NULL,
    vcore_voltage_v REAL NOT NULL,
    rail_12v_v REAL NOT NULL,
    rail_5v_v REAL NOT NULL,
    cpu_utilization_pct REAL NOT NULL,
    throttling_duration_sec INTEGER NOT NULL DEFAULT 0,
    smart_reallocated_sectors INTEGER NOT NULL DEFAULT 0,
    smart_wear_level_pct REAL NOT NULL DEFAULT 100.0,
    power_cycles_count INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_telemetry_device_time ON sensor_telemetry(device_id, recorded_at DESC);

-- 4. USER ACCOUNTS (RBAC)
CREATE TABLE IF NOT EXISTS user_accounts (
    user_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(org_id),
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL, -- 'TECHNICIAN', 'ASSET_MANAGER', 'MLOPS_ADMIN', 'ESG_OFFICER'
    is_active INTEGER NOT NULL DEFAULT 1
);

-- 5. FAILURE PREDICTIONS (AI Inference Outputs)
CREATE TABLE IF NOT EXISTS failure_predictions (
    prediction_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL REFERENCES asset_devices(device_id) ON DELETE CASCADE,
    predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    failure_probability_14d REAL NOT NULL,
    failure_probability_30d REAL NOT NULL,
    estimated_rul_days INTEGER NOT NULL,
    conformal_lower_rul_days INTEGER NOT NULL,
    conformal_upper_rul_days INTEGER NOT NULL,
    confidence_score REAL NOT NULL,
    primary_failure_mode TEXT NOT NULL,
    risk_tier TEXT NOT NULL, -- 'LOW', 'MODERATE', 'HIGH', 'CRITICAL'
    shap_attributions TEXT NOT NULL, -- JSON string
    operator_review_required INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_predictions_device_latest ON failure_predictions(device_id, predicted_at DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_risk ON failure_predictions(risk_tier);

-- 6. PRESCRIPTIVE WORK ORDERS
CREATE TABLE IF NOT EXISTS work_orders (
    order_id TEXT PRIMARY KEY,
    prediction_id TEXT NOT NULL REFERENCES failure_predictions(prediction_id),
    device_id TEXT NOT NULL REFERENCES asset_devices(device_id) ON DELETE CASCADE,
    assigned_technician_id TEXT REFERENCES user_accounts(user_id),
    priority TEXT NOT NULL, -- 'URGENT', 'HIGH', 'STANDARD'
    prescriptive_action_plan TEXT NOT NULL,
    order_status TEXT NOT NULL DEFAULT 'PENDING_REVIEW', -- 'PENDING_REVIEW', 'CONFIRMED', 'IN_PROGRESS', 'RESOLVED', 'REJECTED_FALSE_ALARM'
    technician_findings TEXT,
    technician_verified_correct INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

-- 7. MAINTENANCE & CIRCULAR ECONOMY RECORDS
CREATE TABLE IF NOT EXISTS maintenance_records (
    maintenance_id TEXT PRIMARY KEY,
    work_order_id TEXT REFERENCES work_orders(order_id),
    device_id TEXT NOT NULL REFERENCES asset_devices(device_id) ON DELETE CASCADE,
    technician_id TEXT REFERENCES user_accounts(user_id),
    service_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    maintenance_category TEXT NOT NULL, -- 'REPAIR', 'REFURBISH', 'PREVENTIVE_CLEANING', 'REPURPOSE'
    actions_performed TEXT NOT NULL, -- JSON list of strings
    parts_replaced TEXT, -- JSON list of strings
    parts_origin TEXT DEFAULT 'OEM_RECONDITIONED',
    service_cost_idr REAL NOT NULL,
    new_device_replacement_cost_idr REAL NOT NULL,
    pre_service_peak_temp_c REAL,
    post_service_peak_temp_c REAL,
    extended_lifecycle_days INTEGER NOT NULL,
    embodied_carbon_saved_kg REAL NOT NULL,
    ewaste_mass_saved_kg REAL NOT NULL
);
"""


def init_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Initialize a configured SQLite connection with schema & auto-bootstrap."""
    global _IS_SEEDING
    target_path = db_path or get_db_path()
    conn = sqlite3.connect(target_path, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    with conn:
        if is_serverless_env():
            conn.execute("PRAGMA journal_mode = DELETE;")
        else:
            conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA synchronous = NORMAL;")

        tbl = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='asset_devices';"
        ).fetchone()
        if not tbl:
            conn.executescript(SCHEMA_SQL)

        if not _IS_SEEDING and db_path is None:
            cnt = conn.execute("SELECT COUNT(*) FROM asset_devices;").fetchone()[0]
            if cnt == 0:
                _IS_SEEDING = True
                try:
                    from core.seeder import seed_fleet_database
                    from ai.pipeline import run_fleet_inference
                    days = 6 if is_serverless_env() else 30
                    seed_fleet_database(target_path, num_devices=120, days_history=days)
                    run_fleet_inference(target_path)
                finally:
                    _IS_SEEDING = False
    return conn


@contextmanager
def get_db_session(db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager yielding a transactional SQLite connection."""
    conn = init_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database(db_path: Optional[str] = None) -> None:
    """Executes schema DDL to create tables and indexes."""
    target_path = db_path or get_db_path()
    with get_db_session(target_path) as conn:
        conn.executescript(SCHEMA_SQL)
