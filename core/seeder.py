"""
core/seeder.py
Initializes SQLite database and seeds simulated organization, accounts, devices, and telemetry.
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

# Ensure project root is in sys.path regardless of execution directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.database import initialize_database, get_db_session, get_db_path
from ai.data_generator import HybridFleetSimulator


def seed_fleet_database(
    db_path: Optional[str] = None,
    num_devices: int = 120,
    days_history: int = 30
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Executes schema creation and seeds realistic fleet data."""
    target_path = db_path or get_db_path()
    initialize_database(target_path)

    sim = HybridFleetSimulator(seed=2026)
    devices, telemetry = sim.generate_fleet(num_devices=num_devices, days_history=days_history)

    with get_db_session(target_path) as conn:
        # 1. Organization
        conn.execute("""
            INSERT OR REPLACE INTO organizations (org_id, name, industry_type, sustainability_target_pct)
            VALUES (?, ?, ?, ?);
        """, ("org-green-corp-001", "EcoTech Sustainable Enterprise", "Technology & IT Infrastructure", 35.0))

        # 2. User Accounts
        users = [
            ("usr-tech-01", "org-green-corp-001", "Budi Pratama (Senior Hardware Tech)", "budi.tech@ecotech.local", "TECHNICIAN"),
            ("usr-mgr-01", "org-green-corp-001", "Dewi Sartika (IT Asset & Operations Lead)", "dewi.asset@ecotech.local", "ASSET_MANAGER"),
            ("usr-ops-01", "org-green-corp-001", "Fajar Nugraha (MLOps & Systems Admin)", "fajar.ops@ecotech.local", "MLOPS_ADMIN"),
            ("usr-esg-01", "org-green-corp-001", "Maya Kusuma (Sustainability & ESG Officer)", "maya.esg@ecotech.local", "ESG_OFFICER"),
        ]
        conn.executemany("""
            INSERT OR REPLACE INTO user_accounts (user_id, org_id, full_name, email, role)
            VALUES (?, ?, ?, ?, ?);
        """, users)

        # 3. Devices
        device_rows = [
            (
                d["device_id"],
                d["org_id"],
                d["asset_tag"],
                d["device_type"],
                d["brand_model"],
                d["cpu_spec"],
                d["ram_gb"],
                d["storage_capacity_gb"],
                d["commission_date"],
                d["expected_lifecycle_months"],
                d["operating_age_months"],
                d["current_status"],
                telemetry[-1]["recorded_at"]
            )
            for d in devices
        ]
        conn.executemany("""
            INSERT OR REPLACE INTO asset_devices (
                device_id, org_id, asset_tag, device_type, brand_model,
                cpu_spec, ram_gb, storage_capacity_gb, commission_date,
                expected_lifecycle_months, operating_age_months, current_status, last_telemetry_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, device_rows)

        # 4. Telemetry Records
        telemetry_rows = [
            (
                t["device_id"],
                t["recorded_at"],
                t["avg_cpu_temp_c"],
                t["max_cpu_temp_c"],
                t["ambient_temp_c"],
                t["fan_rpm"],
                t["fan_duty_cycle_pct"],
                t["vcore_voltage_v"],
                t["rail_12v_v"],
                t["rail_5v_v"],
                t["cpu_utilization_pct"],
                t["throttling_duration_sec"],
                t["smart_reallocated_sectors"],
                t["smart_wear_level_pct"],
                t["power_cycles_count"]
            )
            for t in telemetry
        ]
        conn.executemany("""
            INSERT INTO sensor_telemetry (
                device_id, recorded_at, avg_cpu_temp_c, max_cpu_temp_c, ambient_temp_c,
                fan_rpm, fan_duty_cycle_pct, vcore_voltage_v, rail_12v_v, rail_5v_v,
                cpu_utilization_pct, throttling_duration_sec, smart_reallocated_sectors,
                smart_wear_level_pct, power_cycles_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, telemetry_rows)

    return devices, telemetry


if __name__ == "__main__":
    devs, tels = seed_fleet_database(num_devices=120, days_history=30)
    print(f"Seeded {len(devs)} devices and {len(tels)} telemetry records successfully.")
