"""
tests/test_api.py
Integration tests for FastAPI REST Endpoints using TestClient.
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from core.database import get_db_session

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"


def test_get_fleet_overview():
    response = client.get("/api/v1/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["total_devices"] == 120
    assert "CRITICAL" in data["risk_distribution"]
    assert "ewaste_mass_saved_kg" in data["sustainability"]
    assert data["sustainability"]["ewaste_mass_saved_kg"] > 0


def test_get_devices_list():
    response = client.get("/api/v1/devices?limit=10")
    assert response.status_code == 200
    devices = response.json()
    assert len(devices) == 10
    first = devices[0]
    assert "asset_tag" in first
    assert "risk_tier" in first
    assert "estimated_rul_days" in first


def test_get_device_detail():
    # Pick a device ID from list
    dev_res = client.get("/api/v1/devices?limit=1")
    dev_id = dev_res.json()[0]["device_id"]

    response = client.get(f"/api/v1/devices/{dev_id}")
    assert response.status_code == 200
    detail = response.json()
    assert "device" in detail
    assert "latest_prediction" in detail
    assert "telemetry_history" in detail
    assert len(detail["telemetry_history"]) > 0

    if detail["latest_prediction"]:
        assert "shap_attributions" in detail["latest_prediction"]
        assert len(detail["latest_prediction"]["shap_attributions"]) > 0


def test_work_order_resolve_human_in_the_loop():
    # Fetch an open work order
    wo_res = client.get("/api/v1/work-orders?status_filter=PENDING_REVIEW")
    assert wo_res.status_code == 200
    orders = wo_res.json()
    assert len(orders) > 0, "Expected at least one pending work order to test resolution."
    order_id = orders[0]["order_id"]

    resolve_payload = {
        "technician_verified_correct": True,
        "technician_findings": "Inspeksi fisik mengonfirmasi pasta termal kering dan sirip heatsink berdebu tebal.",
        "actions_performed": [
            "PEMBERSIHAN_DEBU_HEATSINK",
            "PENGGANTIAN_PASTA_TERMAL_ARCTIC_MX4"
        ],
        "parts_replaced": ["THERMAL_PASTE_ARCTIC_MX4"],
        "parts_origin": "OEM_RECONDITIONED",
        "pre_service_peak_temp_c": 92.5,
        "post_service_peak_temp_c": 57.0
    }

    res = client.post(f"/api/v1/work-orders/{order_id}/resolve", json=resolve_payload)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] == "RESOLVED_SUCCESSFULLY"
    assert res_data["extended_lifecycle_days"] >= 180
    assert res_data["ewaste_mass_saved_kg"] > 0


def test_telemetry_ingest():
    # Fetch first device asset tag
    dev_res = client.get("/api/v1/devices?limit=1")
    tag = dev_res.json()[0]["asset_tag"]

    payload = {
        "device_asset_tag": tag,
        "avg_cpu_temp_c": 48.5,
        "max_cpu_temp_c": 55.0,
        "ambient_temp_c": 24.0,
        "fan_rpm": 1850,
        "fan_duty_cycle_pct": 40.0,
        "vcore_voltage_v": 1.21,
        "rail_12v_v": 12.02,
        "rail_5v_v": 5.01,
        "cpu_utilization_pct": 32.0,
        "throttling_duration_sec": 0,
        "smart_reallocated_sectors": 0,
        "smart_wear_level_pct": 98.0,
        "power_cycles_count": 140
    }

    response = client.post("/api/v1/telemetry/ingest", json=payload)
    assert response.status_code == 202
    assert response.json()["status"] == "ACCEPTED"


def test_serve_frontend_dashboard():
    response = client.get("/")
    assert response.status_code == 200
    assert "EcoPredict AI" in response.text
    assert "<!DOCTYPE html>" in response.text


def test_static_assets():
    css_res = client.get("/static/css/style.css")
    assert css_res.status_code == 200
    assert "--bg-primary" in css_res.text

    js_res = client.get("/static/js/app.js")
    assert js_res.status_code == 200
    assert "loadAllData" in js_res.text


def test_trigger_batch_pipeline():
    response = client.post("/api/v1/pipeline/trigger")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "summary" in data
    assert data["summary"]["processed_devices"] >= 100
