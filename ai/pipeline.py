"""
ai/pipeline.py
Batch Fleet AI Inference Pipeline.
Reads telemetry from SQLite, executes predictive models, records predictions,
and generates prescriptive work orders with Responsible AI guardrails.
"""

import os
import sys
import json
import uuid
from typing import Dict, Any, List, Optional

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.database import get_db_session, get_db_path
from ai.model import FleetPredictor


def run_fleet_inference(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes inference across all active devices in the SQLite database.
    Stores results in failure_predictions and creates work_orders for high-risk assets.
    """
    target_path = db_path or get_db_path()
    predictor = FleetPredictor()

    summary = {
        "processed_devices": 0,
        "critical_count": 0,
        "high_count": 0,
        "moderate_count": 0,
        "low_count": 0,
        "operator_review_flagged": 0,
        "work_orders_created": 0
    }

    with get_db_session(target_path) as conn:
        # Fetch all devices
        devices = conn.execute("""
            SELECT device_id, asset_tag, device_type, operating_age_months, current_status
            FROM asset_devices;
        """).fetchall()

        for dev in devices:
            dev_id = dev["device_id"]
            age_months = dev["operating_age_months"]

            # Fetch recent telemetry window (last 60 records = 15 days)
            telemetry_rows = conn.execute("""
                SELECT 
                    avg_cpu_temp_c, max_cpu_temp_c, ambient_temp_c,
                    fan_rpm, fan_duty_cycle_pct, vcore_voltage_v,
                    rail_12v_v, rail_5v_v, cpu_utilization_pct,
                    throttling_duration_sec, smart_reallocated_sectors,
                    smart_wear_level_pct, power_cycles_count, recorded_at
                FROM sensor_telemetry
                WHERE device_id = ?
                ORDER BY recorded_at DESC
                LIMIT 60;
            """, (dev_id,)).fetchall()

            if len(telemetry_rows) < 4:
                continue

            # Convert rows to dicts in chronological order
            records = [dict(r) for r in reversed(telemetry_rows)]

            # Run AI prediction
            res = predictor.predict_device(records, age_months)
            summary["processed_devices"] += 1

            tier = res["risk_tier"]
            if tier == "CRITICAL":
                summary["critical_count"] += 1
            elif tier == "HIGH":
                summary["high_count"] += 1
            elif tier == "MODERATE":
                summary["moderate_count"] += 1
            else:
                summary["low_count"] += 1

            if res["operator_review_required"]:
                summary["operator_review_flagged"] += 1

            # Save prediction
            pred_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO failure_predictions (
                    prediction_id, device_id, failure_probability_14d, failure_probability_30d,
                    estimated_rul_days, conformal_lower_rul_days, conformal_upper_rul_days,
                    confidence_score, primary_failure_mode, risk_tier, shap_attributions,
                    operator_review_required
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                pred_id,
                dev_id,
                res["failure_probability_14d"],
                res["failure_probability_30d"],
                res["estimated_rul_days"],
                res["conformal_lower_rul_days"],
                res["conformal_upper_rul_days"],
                res["confidence_score"],
                res["primary_failure_mode"],
                res["risk_tier"],
                json.dumps(res["top_shap_factors"]),
                res["operator_review_required"]
            ))

            # Update device status in asset_devices
            conn.execute("""
                UPDATE asset_devices
                SET current_status = ?
                WHERE device_id = ?;
            """, (tier, dev_id))

            # If risk is HIGH or CRITICAL, check if open work order exists
            if tier in ["HIGH", "CRITICAL"]:
                open_wo = conn.execute("""
                    SELECT order_id FROM work_orders
                    WHERE device_id = ? AND order_status IN ('PENDING_REVIEW', 'CONFIRMED', 'IN_PROGRESS');
                """, (dev_id,)).fetchone()

                if not open_wo:
                    order_id = str(uuid.uuid4())
                    action_plan = res["prescriptive_action"]["action"]
                    priority = "URGENT" if tier == "CRITICAL" else "HIGH"
                    conn.execute("""
                        INSERT INTO work_orders (
                            order_id, prediction_id, device_id, assigned_technician_id,
                            priority, prescriptive_action_plan, order_status
                        ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING_REVIEW');
                    """, (
                        order_id,
                        pred_id,
                        dev_id,
                        "usr-tech-01",  # Senior Hardware Tech
                        priority,
                        action_plan
                    ))
                    summary["work_orders_created"] += 1

    return summary


if __name__ == "__main__":
    out = run_fleet_inference()
    print("Inference Pipeline Execution Completed:")
    print(json.dumps(out, indent=2))
