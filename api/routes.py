"""
api/routes.py
FastAPI router implementing REST endpoints for Fleet AI Failure Prediction,
Prescriptive Work Orders, Telemetry Ingestion, and Circular Impact Analytics.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from core.database import get_db_session
from api.schemas import TelemetryIngestPayload, ResolveWorkOrderPayload, OverviewKPIResponse
from ai.pipeline import run_fleet_inference
from ai.model import PRESCRIPTIVE_CATALOG
from api.security import verify_edge_api_key, verify_operator_role

router = APIRouter(prefix="/api/v1", tags=["Fleet AI"])


@router.get("/overview", response_model=OverviewKPIResponse)
def get_fleet_overview():
    """Returns high-level KPI metrics, risk distributions, and sustainability statistics."""
    with get_db_session() as conn:
        # Total devices
        total_devices = conn.execute("SELECT COUNT(*) FROM asset_devices;").fetchone()[0]

        # Risk distribution from latest prediction per device
        risk_rows = conn.execute("""
            SELECT fp.risk_tier, COUNT(*) as cnt
            FROM failure_predictions fp
            INNER JOIN (
                SELECT device_id, MAX(predicted_at) as max_date
                FROM failure_predictions
                GROUP BY device_id
            ) latest ON fp.device_id = latest.device_id AND fp.predicted_at = latest.max_date
            GROUP BY fp.risk_tier;
        """).fetchall()
        risk_dist = {"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0}
        for r in risk_rows:
            risk_dist[r["risk_tier"]] = r["cnt"]

        # Failure mode distribution
        mode_rows = conn.execute("""
            SELECT fp.primary_failure_mode, COUNT(*) as cnt
            FROM failure_predictions fp
            INNER JOIN (
                SELECT device_id, MAX(predicted_at) as max_date
                FROM failure_predictions
                GROUP BY device_id
            ) latest ON fp.device_id = latest.device_id AND fp.predicted_at = latest.max_date
            GROUP BY fp.primary_failure_mode;
        """).fetchall()
        mode_dist = {r["primary_failure_mode"]: r["cnt"] for r in mode_rows}

        # Open work orders
        open_wo = conn.execute("""
            SELECT COUNT(*) FROM work_orders 
            WHERE order_status IN ('PENDING_REVIEW', 'CONFIRMED', 'IN_PROGRESS');
        """).fetchone()[0]

        # Flagged for operator review (Responsible AI)
        flagged_review = conn.execute("""
            SELECT COUNT(*) FROM failure_predictions fp
            INNER JOIN (
                SELECT device_id, MAX(predicted_at) as max_date
                FROM failure_predictions
                GROUP BY device_id
            ) latest ON fp.device_id = latest.device_id AND fp.predicted_at = latest.max_date
            WHERE fp.operator_review_required = 1;
        """).fetchone()[0]

        # Sustainability metrics from maintenance_records
        maint_stats = conn.execute("""
            SELECT 
                COALESCE(SUM(ewaste_mass_saved_kg), 0.0) as ewaste_saved_kg,
                COALESCE(SUM(embodied_carbon_saved_kg), 0.0) as carbon_saved_kg,
                COALESCE(SUM(new_device_replacement_cost_idr - service_cost_idr), 0.0) as net_savings_idr,
                COALESCE(SUM(extended_lifecycle_days), 0) as total_extended_days
            FROM maintenance_records;
        """).fetchone()

        # Potential sustainability from pending work orders
        potential_ewaste = (risk_dist["CRITICAL"] + risk_dist["HIGH"]) * 7.0  # 7kg avg per PC/laptop
        potential_carbon = (risk_dist["CRITICAL"] + risk_dist["HIGH"]) * 280.0  # 280kg CO2e Scope 3 avg
        potential_savings = (risk_dist["CRITICAL"] + risk_dist["HIGH"]) * 14500000.0  # IDR 14.5M avg

        sustainability = {
            "ewaste_mass_saved_kg": round(float(maint_stats["ewaste_saved_kg"]) + potential_ewaste, 1),
            "embodied_carbon_saved_ton": round((float(maint_stats["carbon_saved_kg"]) + potential_carbon) / 1000.0, 2),
            "net_cost_savings_idr": float(maint_stats["net_savings_idr"]) + potential_savings,
            "total_extended_days": int(maint_stats["total_extended_days"])
        }

    return OverviewKPIResponse(
        total_devices=total_devices,
        risk_distribution=risk_dist,
        failure_mode_distribution=mode_dist,
        open_work_orders_count=open_wo,
        operator_review_flagged_count=flagged_review,
        sustainability=sustainability
    )


@router.get("/devices")
def get_devices_list(
    device_type: Optional[str] = None,
    risk_tier: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0)
):
    """Retrieves paginated list of devices with latest prediction indicators."""
    with get_db_session() as conn:
        query = """
            SELECT 
                d.device_id, d.asset_tag, d.device_type, d.brand_model,
                d.operating_age_months, d.current_status, d.last_telemetry_at,
                fp.risk_tier, fp.estimated_rul_days, fp.conformal_lower_rul_days,
                fp.conformal_upper_rul_days, fp.failure_probability_14d,
                fp.confidence_score, fp.primary_failure_mode, fp.operator_review_required
            FROM asset_devices d
            LEFT JOIN (
                SELECT fp1.*
                FROM failure_predictions fp1
                INNER JOIN (
                    SELECT device_id, MAX(predicted_at) as max_date
                    FROM failure_predictions
                    GROUP BY device_id
                ) latest ON fp1.device_id = latest.device_id AND fp1.predicted_at = latest.max_date
            ) fp ON d.device_id = fp.device_id
            WHERE 1=1
        """
        params: List[Any] = []
        if device_type:
            query += " AND d.device_type = ?"
            params.append(device_type)
        if risk_tier:
            query += " AND fp.risk_tier = ?"
            params.append(risk_tier)
        if search:
            query += " AND (d.asset_tag LIKE ? OR d.brand_model LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        # Order by severity: CRITICAL first, then HIGH, MODERATE, LOW
        query += """
            ORDER BY 
                CASE fp.risk_tier
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'MODERATE' THEN 3
                    ELSE 4
                END,
                fp.estimated_rul_days ASC
            LIMIT ? OFFSET ?;
        """
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


@router.get("/devices/{device_id}")
def get_device_detail(device_id: str):
    """Returns detailed device information, recent telemetry time-series, and SHAP explainability."""
    with get_db_session() as conn:
        device = conn.execute("""
            SELECT * FROM asset_devices WHERE device_id = ?;
        """, (device_id,)).fetchone()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found.")

        # Latest prediction
        prediction = conn.execute("""
            SELECT * FROM failure_predictions 
            WHERE device_id = ? 
            ORDER BY predicted_at DESC 
            LIMIT 1;
        """, (device_id,)).fetchone()

        pred_data = None
        if prediction:
            pred_dict = dict(prediction)
            pred_dict["shap_attributions"] = json.loads(pred_dict["shap_attributions"])
            pred_dict["prescriptive_catalog"] = PRESCRIPTIVE_CATALOG.get(
                pred_dict["primary_failure_mode"],
                PRESCRIPTIVE_CATALOG["HEALTHY"]
            )
            pred_data = pred_dict

        # Recent telemetry (last 48 records)
        telemetry_rows = conn.execute("""
            SELECT 
                recorded_at, avg_cpu_temp_c, max_cpu_temp_c, ambient_temp_c,
                fan_rpm, fan_duty_cycle_pct, vcore_voltage_v, rail_12v_v, rail_5v_v,
                cpu_utilization_pct, throttling_duration_sec, smart_reallocated_sectors,
                smart_wear_level_pct
            FROM sensor_telemetry
            WHERE device_id = ?
            ORDER BY recorded_at ASC
            LIMIT 60;
        """, (device_id,)).fetchall()

        # Open work order if any
        work_order = conn.execute("""
            SELECT * FROM work_orders 
            WHERE device_id = ? AND order_status IN ('PENDING_REVIEW', 'CONFIRMED', 'IN_PROGRESS')
            ORDER BY created_at DESC LIMIT 1;
        """, (device_id,)).fetchone()

        # Maintenance history
        maintenance_logs = conn.execute("""
            SELECT * FROM maintenance_records
            WHERE device_id = ?
            ORDER BY service_date DESC;
        """, (device_id,)).fetchall()

        return {
            "device": dict(device),
            "latest_prediction": pred_data,
            "telemetry_history": [dict(r) for r in telemetry_rows],
            "active_work_order": dict(work_order) if work_order else None,
            "maintenance_history": [dict(m) for m in maintenance_logs]
        }


@router.get("/work-orders")
def get_work_orders(status_filter: Optional[str] = "ALL"):
    """Lists work orders joined with device asset tag, risk level, and technician."""
    with get_db_session() as conn:
        query = """
            SELECT 
                wo.order_id, wo.prediction_id, wo.device_id, wo.assigned_technician_id,
                wo.priority, wo.prescriptive_action_plan, wo.order_status, wo.created_at,
                d.asset_tag, d.device_type, d.brand_model,
                fp.risk_tier, fp.estimated_rul_days, fp.primary_failure_mode,
                fp.confidence_score, fp.operator_review_required,
                u.full_name as technician_name
            FROM work_orders wo
            JOIN asset_devices d ON wo.device_id = d.device_id
            JOIN failure_predictions fp ON wo.prediction_id = fp.prediction_id
            LEFT JOIN user_accounts u ON wo.assigned_technician_id = u.user_id
        """
        params: List[Any] = []
        if status_filter and status_filter != "ALL":
            query += " WHERE wo.order_status = ?"
            params.append(status_filter)

        query += " ORDER BY wo.created_at DESC;"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


@router.post("/work-orders/{order_id}/resolve")
def resolve_work_order(
    order_id: str,
    payload: ResolveWorkOrderPayload,
    operator: str = Depends(verify_operator_role)
):
    """
    Human-in-the-Loop completion endpoint:
    Technician logs verification, records repair actions, and system updates device health & circular impact.
    """
    with get_db_session() as conn:
        wo = conn.execute("""
            SELECT wo.*, fp.primary_failure_mode, d.asset_tag, d.device_type
            FROM work_orders wo
            JOIN failure_predictions fp ON wo.prediction_id = fp.prediction_id
            JOIN asset_devices d ON wo.device_id = d.device_id
            WHERE wo.order_id = ?;
        """, (order_id,)).fetchone()

        if not wo:
            raise HTTPException(status_code=404, detail="Work order not found.")

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not payload.technician_verified_correct:
            # False alarm recorded
            conn.execute("""
                UPDATE work_orders
                SET order_status = 'REJECTED_FALSE_ALARM',
                    technician_findings = ?,
                    technician_verified_correct = 0,
                    resolved_at = ?
                WHERE order_id = ?;
            """, (payload.technician_findings, now_str, order_id))

            conn.execute("""
                UPDATE asset_devices
                SET current_status = 'ACTIVE'
                WHERE device_id = ?;
            """, (wo["device_id"],))

            return {
                "status": "FALSE_ALARM_LOGGED",
                "message": "Temuan teknisi mencatat false alarm. Status aset dikembalikan ke Normal."
            }

        # Verified repair executed
        catalog_info = PRESCRIPTIVE_CATALOG.get(wo["primary_failure_mode"], PRESCRIPTIVE_CATALOG["HEALTHY"])
        ext_days = catalog_info["expected_life_extension_days"]
        carbon_saved = catalog_info["scope3_carbon_kg"]
        ewaste_saved = catalog_info["prevented_waste_kg"]
        new_cost = catalog_info["cost_savings_idr"]
        service_cost = 250000.0  # nominal maintenance service cost

        maint_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO maintenance_records (
                maintenance_id, work_order_id, device_id, technician_id,
                service_date, maintenance_category, actions_performed,
                parts_replaced, parts_origin, service_cost_idr,
                new_device_replacement_cost_idr, pre_service_peak_temp_c,
                post_service_peak_temp_c, extended_lifecycle_days,
                embodied_carbon_saved_kg, ewaste_mass_saved_kg
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            maint_id,
            order_id,
            wo["device_id"],
            wo["assigned_technician_id"],
            now_str,
            "REPAIR",
            json.dumps(payload.actions_performed),
            json.dumps(payload.parts_replaced or []),
            payload.parts_origin,
            service_cost,
            new_cost,
            payload.pre_service_peak_temp_c or 92.0,
            payload.post_service_peak_temp_c or 58.0,
            ext_days,
            carbon_saved,
            ewaste_saved
        ))

        # Close work order
        conn.execute("""
            UPDATE work_orders
            SET order_status = 'RESOLVED',
                technician_findings = ?,
                technician_verified_correct = 1,
                resolved_at = ?
            WHERE order_id = ?;
        """, (payload.technician_findings, now_str, order_id))

        # Update device status and extend lifecycle
        conn.execute("""
            UPDATE asset_devices
            SET current_status = 'ACTIVE',
                expected_lifecycle_months = expected_lifecycle_months + ?
            WHERE device_id = ?;
        """, (ext_days // 30, wo["device_id"]))

        # Inject normalized post-service telemetry records so subsequent AI runs see healthy device
        post_temp = payload.post_service_peak_temp_c or 58.0
        conn.execute("""
            INSERT INTO sensor_telemetry (
                device_id, recorded_at, avg_cpu_temp_c, max_cpu_temp_c, ambient_temp_c,
                fan_rpm, fan_duty_cycle_pct, vcore_voltage_v, rail_12v_v, rail_5v_v,
                cpu_utilization_pct, throttling_duration_sec, smart_reallocated_sectors,
                smart_wear_level_pct, power_cycles_count
            ) VALUES (?, ?, ?, ?, 24.0, 1800, 45.0, 1.20, 12.01, 5.01, 35.0, 0, 0, 95.0, 150);
        """, (wo["device_id"], now_str, post_temp - 5.0, post_temp))

        return {
            "status": "RESOLVED_SUCCESSFULLY",
            "extended_lifecycle_days": ext_days,
            "embodied_carbon_saved_kg": carbon_saved,
            "ewaste_mass_saved_kg": ewaste_saved,
            "net_cost_savings_idr": new_cost - service_cost
        }


@router.post("/telemetry/ingest", status_code=status.HTTP_202_ACCEPTED)
def ingest_telemetry(
    payload: TelemetryIngestPayload,
    auth_key: str = Depends(verify_edge_api_key)
):
    """Ingests live telemetry from edge agents with validation and rate limiting."""
    with get_db_session() as conn:
        device = conn.execute("""
            SELECT device_id FROM asset_devices WHERE asset_tag = ?;
        """, (payload.device_asset_tag,)).fetchone()

        if not device:
            raise HTTPException(status_code=404, detail=f"Asset tag '{payload.device_asset_tag}' not registered.")

        device_id = device["device_id"]
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn.execute("""
            INSERT INTO sensor_telemetry (
                device_id, recorded_at, avg_cpu_temp_c, max_cpu_temp_c, ambient_temp_c,
                fan_rpm, fan_duty_cycle_pct, vcore_voltage_v, rail_12v_v, rail_5v_v,
                cpu_utilization_pct, throttling_duration_sec, smart_reallocated_sectors,
                smart_wear_level_pct, power_cycles_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            device_id,
            now_str,
            payload.avg_cpu_temp_c,
            payload.max_cpu_temp_c,
            payload.ambient_temp_c,
            payload.fan_rpm,
            payload.fan_duty_cycle_pct,
            payload.vcore_voltage_v,
            payload.rail_12v_v,
            payload.rail_5v_v,
            payload.cpu_utilization_pct,
            payload.throttling_duration_sec,
            payload.smart_reallocated_sectors,
            payload.smart_wear_level_pct,
            payload.power_cycles_count
        ))

        conn.execute("""
            UPDATE asset_devices
            SET last_telemetry_at = ?
            WHERE device_id = ?;
        """, (now_str, device_id))

        return {"status": "ACCEPTED", "device_id": device_id, "timestamp": now_str}


@router.post("/pipeline/trigger")
def trigger_ai_pipeline(operator: str = Depends(verify_operator_role)):
    """Manually triggers batch inference across the entire electronic fleet (Protected)."""
    result = run_fleet_inference()
    return {"status": "SUCCESS", "summary": result}
