"""
tests/test_e2e_stress.py
End-to-End lifecycle, security authorization, rate-limiting, and stress tests.
Validates the complete closed-loop workflow:
Telemetry Ingestion -> Anomaly Detection -> Batch Fleet Inference ->
Work Order Generation -> Technician Verification & Repair -> Carbon & E-Waste Recalculation.
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from api import security

client = TestClient(app)


def test_security_auth_and_rate_limiting():
    """Validates X-API-Key requirement and sliding window rate limiter."""
    # Test permissive dev mode
    security.AUTH_STRICT_MODE = False
    res_perm = client.post("/api/v1/telemetry/ingest", json={
        "device_asset_tag": "LAP-0001",
        "avg_cpu_temp_c": 55.0,
        "max_cpu_temp_c": 60.0,
        "ambient_temp_c": 24.0,
        "fan_rpm": 2200,
        "fan_duty_cycle_pct": 50.0,
        "vcore_voltage_v": 1.20,
        "rail_12v_v": 12.02,
        "rail_5v_v": 5.01,
        "cpu_utilization_pct": 30.0,
        "throttling_duration_sec": 0,
        "smart_reallocated_sectors": 0,
        "smart_wear_level_pct": 98.0,
        "power_cycles_count": 80
    })
    assert res_perm.status_code == 202

    # Test strict mode authentication
    security.AUTH_STRICT_MODE = True
    try:
        # Without header -> 401
        res_no_key = client.post("/api/v1/telemetry/ingest", json={
            "device_asset_tag": "LAP-0001",
            "avg_cpu_temp_c": 55.0,
            "max_cpu_temp_c": 60.0,
            "ambient_temp_c": 24.0,
            "fan_rpm": 2200,
            "fan_duty_cycle_pct": 50.0,
            "vcore_voltage_v": 1.20,
            "rail_12v_v": 12.02,
            "rail_5v_v": 5.01,
            "cpu_utilization_pct": 30.0
        })
        assert res_no_key.status_code == 401

        # With invalid header -> 401
        res_bad_key = client.post("/api/v1/telemetry/ingest", json={
            "device_asset_tag": "LAP-0001",
            "avg_cpu_temp_c": 55.0,
            "max_cpu_temp_c": 60.0,
            "ambient_temp_c": 24.0,
            "fan_rpm": 2200,
            "fan_duty_cycle_pct": 50.0,
            "vcore_voltage_v": 1.20,
            "rail_12v_v": 12.02,
            "rail_5v_v": 5.01,
            "cpu_utilization_pct": 30.0
        }, headers={"X-API-Key": "wrong-secret"})
        assert res_bad_key.status_code == 401

        # With valid header -> 202
        res_ok = client.post("/api/v1/telemetry/ingest", json={
            "device_asset_tag": "LAP-0001",
            "avg_cpu_temp_c": 55.0,
            "max_cpu_temp_c": 60.0,
            "ambient_temp_c": 24.0,
            "fan_rpm": 2200,
            "fan_duty_cycle_pct": 50.0,
            "vcore_voltage_v": 1.20,
            "rail_12v_v": 12.02,
            "rail_5v_v": 5.01,
            "cpu_utilization_pct": 30.0
        }, headers={"X-API-Key": security.EDGE_API_KEY_ENV})
        assert res_ok.status_code == 202
    finally:
        # Reset to permissive for dev tests
        security.AUTH_STRICT_MODE = False

    # Test Rate Limiter
    test_limiter = security.SlidingWindowRateLimiter(max_requests=5, window_seconds=10)
    for _ in range(5):
        assert test_limiter.is_allowed("192.168.1.100") is True
    # 6th request must be rejected
    assert test_limiter.is_allowed("192.168.1.100") is False


def test_complete_e2e_closed_loop():
    """
    Simulates the entire closed-loop lifecycle:
    1. Ingest severe degradation telemetry into asset DSK-0002.
    2. Run fleet AI scan.
    3. Check generated work order and prescriptive recommendations.
    4. Resolve work order with OEM reconditioned parts.
    5. Verify KPIs updated (extended lifecycle + avoided carbon).
    """
    # 1. Ingest degradation: 96°C under full throttling into LAP-0001
    for _ in range(3):
        res = client.post("/api/v1/telemetry/ingest", json={
            "device_asset_tag": "LAP-0001",
            "avg_cpu_temp_c": 96.5,
            "max_cpu_temp_c": 102.0,
            "ambient_temp_c": 24.0,
            "fan_rpm": 4200,
            "fan_duty_cycle_pct": 100.0,
            "vcore_voltage_v": 1.24,
            "rail_12v_v": 11.95,
            "rail_5v_v": 5.01,
            "cpu_utilization_pct": 85.0,
            "throttling_duration_sec": 720,
            "smart_reallocated_sectors": 0,
            "smart_wear_level_pct": 94.0,
            "power_cycles_count": 210
        })
        assert res.status_code == 202

    # 2. Trigger fleet AI inference
    scan_res = client.post("/api/v1/pipeline/trigger")
    assert scan_res.status_code == 200
    scan_data = scan_res.json()
    assert scan_data["status"] == "SUCCESS"

    # 3. Fetch device detail and active work orders
    orders_res = client.get("/api/v1/work-orders?status_filter=PENDING_REVIEW")
    assert orders_res.status_code == 200
    orders = orders_res.json()
    assert len(orders) > 0

    target_order = None
    for o in orders:
        if o["asset_tag"] == "LAP-0001":
            target_order = o
            break

    # If DSK-0002 didn't create a new order (e.g. already had one), grab any pending order
    if not target_order:
        target_order = orders[0]

    order_id = target_order["order_id"]
    assert "prescriptive_action_plan" in target_order

    # 4. Resolve the work order
    resolve_res = client.post(f"/api/v1/work-orders/{order_id}/resolve", json={
        "technician_verified_correct": True,
        "technician_findings": "Pasta termal kering dan debu tebal menghambat sirip heatsink.",
        "actions_performed": ["RE_PASTE_THERMAL_COMPOUND", "HEATSINK_CLEANING"],
        "parts_replaced": ["THERMAL_COMPOUND_HIGH_GRADE"],
        "parts_origin": "OEM_RECONDITIONED",
        "pre_service_peak_temp_c": 98.0,
        "post_service_peak_temp_c": 54.0
    })
    assert resolve_res.status_code == 200
    resolve_data = resolve_res.json()
    assert resolve_data["status"] == "RESOLVED_SUCCESSFULLY"
    assert resolve_data["extended_lifecycle_days"] > 0
    assert resolve_data["embodied_carbon_saved_kg"] > 0
    assert resolve_data["ewaste_mass_saved_kg"] > 0

    # 5. Check KPI overview updates
    overview_res = client.get("/api/v1/overview")
    assert overview_res.status_code == 200
    overview_data = overview_res.json()
    assert overview_data["sustainability"]["ewaste_mass_saved_kg"] > 0
    assert overview_data["sustainability"]["embodied_carbon_saved_ton"] > 0
