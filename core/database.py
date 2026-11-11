"""
core/database.py
Database layer for AI-Based Electronic Failure Prediction.
Implements high-performance SQLite storage with Write-Ahead Logging (WAL),
foreign keys enforcement, and thread-safe connections.
"""

import os
import sqlite3
from typing import Generator, Optional
from contextlib import contextmanager

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "electronic_fleet.db")


def get_db_path() -> str:
    if os.environ.get("VERCEL"):
        tmp_db = "/tmp/electronic_fleet.db"
        if not os.path.exists(tmp_db) and os.path.exists(DEFAULT_DB_PATH):
            import shutil
            shutil.copy2(DEFAULT_DB_PATH, tmp_db)
        return tmp_db
    return os.environ.get("FLEET_DB_PATH", DEFAULT_DB_PATH)


def init_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Initialize a configured SQLite connection with WAL mode and foreign keys."""
    target_path = db_path or get_db_path()
    conn = sqlite3.connect(target_path, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    with conn:
        if os.environ.get("VERCEL"):
            conn.execute("PRAGMA journal_mode = DELETE;")
        else:
            conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA synchronous = NORMAL;")
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
    org_id TEXT NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    asset_tag TEXT UNIQUE NOT NULL,
    device_type TEXT NOT NULL, -- 'LAPTOP', 'DESKTOP', 'SERVER_NODE', 'EDGE_GATEWAY'
    brand_model TEXT NOT NULL,
    cpu_spec TEXT NOT NULL,
    ram_gb INTEGER NOT NULL,
    storage_capacity_gb INTEGER NOT NULL,
    commission_date DATE NOT NULL,
    expected_lifecycle_months INTEGER NOT NULL DEFAULT 48,
    operating_age_months INTEGER NOT NULL DEFAULT 12,
    current_status TEXT NOT NULL DEFAULT 'ACTIVE', -- 'ACTIVE', 'WATCHLIST', 'CRITICAL', 'MAINTENANCE', 'RETIRED'
    last_telemetry_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. SENSOR TELEMETRY (Periodic Aggregated Windows)
CREATE TABLE IF NOT EXISTS sensor_telemetry (
    telemetry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL REFERENCES asset_devices(device_id) ON DELETE CASCADE,
    recorded_at TIMESTAMP NOT NULL,
    avg_cpu_temp_c REAL NOT NULL,
    max_cpu_temp_c REAL NOT NULL,
    ambient_temp_c REAL DEFAULT 25.0,
    fan_rpm INTEGER NOT NULL,
    fan_duty_cycle_pct REAL NOT NULL,
    vcore_voltage_v REAL NOT NULL,
    rail_12v_v REAL NOT NULL,
    rail_5v_v REAL NOT NULL,
    cpu_utilization_pct REAL NOT NULL,
    throttling_duration_sec INTEGER DEFAULT 0,
    smart_reallocated_sectors INTEGER DEFAULT 0,
    smart_wear_level_pct REAL DEFAULT 100.0,
    power_cycles_count INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_telemetry_device_time ON sensor_telemetry (device_id, recorded_at DESC);

-- 4. USER ACCOUNTS (Role-Based Access)
CREATE TABLE IF NOT EXISTS user_accounts (
    user_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL, -- 'TECHNICIAN', 'ASSET_MANAGER', 'MLOPS_ADMIN', 'ESG_OFFICER'
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

CREATE INDEX IF NOT EXISTS idx_predictions_device_date ON failure_predictions (device_id, predicted_at DESC);

-- 6. WORK ORDERS (Prescriptive Action Flow)
CREATE TABLE IF NOT EXISTS work_orders (
    order_id TEXT PRIMARY KEY,
    prediction_id TEXT NOT NULL REFERENCES failure_predictions(prediction_id) ON DELETE CASCADE,
    device_id TEXT NOT NULL REFERENCES asset_devices(device_id) ON DELETE CASCADE,
    assigned_technician_id TEXT REFERENCES user_accounts(user_id),
    priority TEXT NOT NULL DEFAULT 'HIGH',
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


def initialize_database(db_path: Optional[str] = None) -> None:
    """Executes schema DDL to create tables and indexes."""
    target_path = db_path or get_db_path()
    with get_db_session(target_path) as conn:
        conn.executescript(SCHEMA_SQL)
        try:
            row = conn.execute("SELECT COUNT(*) FROM asset_devices;").fetchone()
            if row and row[0] == 0:
                from core.seeder import seed_fleet_database
                seed_fleet_database(target_path, num_devices=120, days_history=15)
        except Exception:
            pass
