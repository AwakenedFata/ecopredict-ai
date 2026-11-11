"""
tests/test_ai_pipeline.py
Unit tests verifying AI feature engineering, LightGBM models, TreeSHAP,
and Responsible AI conformal prediction intervals.
"""

import pytest
import numpy as np
from ai.feature_engineering import FEATURE_NAMES, extract_features_from_telemetry
from ai.model import FleetPredictor, FAILURE_MODE_LABELS


@pytest.fixture(scope="module")
def predictor():
    return FleetPredictor()


def create_mock_telemetry(mode: str = "HEALTHY"):
    records = []
    for step in range(16):
        if mode == "THERMAL":
            cpu_temp = 88.0 + (step * 0.5)
            max_temp = cpu_temp + 6.0
            fan_rpm = 3400
            rail_12v = 11.95
            throttling = 300
            bad_sec = 0
            wear = 95.0
        elif mode == "VRM":
            cpu_temp = 55.0
            max_temp = 62.0
            fan_rpm = 2100
            rail_12v = 10.40 - (step * 0.05)  # severe voltage sag
            throttling = 0
            bad_sec = 0
            wear = 92.0
        else:
            cpu_temp = 52.0
            max_temp = 58.0
            fan_rpm = 1800
            rail_12v = 12.01
            throttling = 0
            bad_sec = 0
            wear = 98.0

        records.append({
            "avg_cpu_temp_c": cpu_temp,
            "max_cpu_temp_c": max_temp,
            "ambient_temp_c": 24.0,
            "fan_rpm": fan_rpm,
            "fan_duty_cycle_pct": 75.0,
            "vcore_voltage_v": 1.25,
            "rail_12v_v": rail_12v,
            "rail_5v_v": 5.01,
            "cpu_utilization_pct": 60.0,
            "throttling_duration_sec": throttling,
            "smart_reallocated_sectors": bad_sec,
            "smart_wear_level_pct": wear,
            "power_cycles_count": 100
        })
    return records


def test_feature_engineering_extraction():
    records = create_mock_telemetry("THERMAL")
    feats = extract_features_from_telemetry(records, age_months=24)

    for col in FEATURE_NAMES:
        assert col in feats, f"Missing feature '{col}'"
        assert not np.isnan(feats[col]), f"NaN found in feature '{col}'"

    # In thermal mode, Thermal Stress Index should be elevated
    assert feats["thermal_stress_index"] > 0.8
    assert feats["throttling_hours"] > 0


def test_prediction_output_structure(predictor):
    records = create_mock_telemetry("HEALTHY")
    res = predictor.predict_device(records, operating_age_months=12)

    required_keys = [
        "estimated_rul_days",
        "conformal_lower_rul_days",
        "conformal_upper_rul_days",
        "failure_probability_14d",
        "failure_probability_30d",
        "confidence_score",
        "primary_failure_mode",
        "risk_tier",
        "operator_review_required",
        "top_shap_factors",
        "prescriptive_action"
    ]
    for key in required_keys:
        assert key in res, f"Expected key '{key}' missing from prediction dictionary."

    # Validate conformal interval ordering
    assert res["conformal_lower_rul_days"] <= res["estimated_rul_days"] <= res["conformal_upper_rul_days"]
    assert 0.0 <= res["confidence_score"] <= 1.0
    assert res["primary_failure_mode"] in FAILURE_MODE_LABELS


def test_thermal_anomaly_diagnosis(predictor):
    records = create_mock_telemetry("THERMAL")
    res = predictor.predict_device(records, operating_age_months=36)

    assert res["risk_tier"] in ["CRITICAL", "HIGH"]
    assert res["estimated_rul_days"] <= 35
    assert res["failure_probability_14d"] > 0.50

    # Verify SHAP factor attributions exist
    assert len(res["top_shap_factors"]) > 0
    top_feature = res["top_shap_factors"][0]["feature"]
    assert top_feature in ["thermal_stress_index", "avg_cpu_temp_c", "max_cpu_temp_c", "fan_dissipation_efficiency"]
