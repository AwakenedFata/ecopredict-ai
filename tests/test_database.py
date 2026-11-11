"""
tests/test_database.py
Unit tests verifying SQLite database integrity and seed data.
"""

import sqlite3
import pytest
from core.database import get_db_session, get_db_path


def test_database_tables_exist():
    with get_db_session() as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]

    expected = [
        "organizations",
        "asset_devices",
        "sensor_telemetry",
        "user_accounts",
        "failure_predictions",
        "work_orders",
        "maintenance_records"
    ]
    for table in expected:
        assert table in tables, f"Expected table '{table}' not found in SQLite schema."


def test_fleet_seeded_counts():
    with get_db_session() as conn:
        org_count = conn.execute("SELECT COUNT(*) FROM organizations;").fetchone()[0]
        device_count = conn.execute("SELECT COUNT(*) FROM asset_devices;").fetchone()[0]
        telemetry_count = conn.execute("SELECT COUNT(*) FROM sensor_telemetry;").fetchone()[0]
        user_count = conn.execute("SELECT COUNT(*) FROM user_accounts;").fetchone()[0]

    assert org_count >= 1
    assert device_count == 120
    assert telemetry_count >= 14400
    assert user_count == 4


def test_telemetry_ranges_and_constraints():
    with get_db_session() as conn:
        row = conn.execute("""
            SELECT 
                MIN(avg_cpu_temp_c) as min_temp,
                MAX(avg_cpu_temp_c) as max_temp,
                MIN(fan_rpm) as min_rpm,
                MAX(fan_rpm) as max_rpm,
                MIN(rail_12v_v) as min_12v,
                MAX(rail_12v_v) as max_12v
            FROM sensor_telemetry;
        """).fetchone()

    assert 20.0 <= row["min_temp"] <= 55.0
    assert row["max_temp"] <= 120.0
    assert row["min_rpm"] >= 400
    assert 9.0 <= row["min_12v"] <= 12.5
