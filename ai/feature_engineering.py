"""
ai/feature_engineering.py
Physics-Informed Feature Engineering for Electronic Component Degradation.
Extracts thermodynamic and electrical indicators from telemetry time-series windows.
"""

import numpy as np
from typing import Dict, Any, List


FEATURE_NAMES = [
    "thermal_stress_index",
    "fan_dissipation_efficiency",
    "avg_cpu_temp_c",
    "max_cpu_temp_c",
    "throttling_hours",
    "voltage_sag_12v",
    "vcore_volatility",
    "rail_5v_deviation",
    "smart_bad_sectors",
    "smart_wear_level_pct",
    "operating_age_months",
    "cpu_utilization_avg"
]


def extract_features_from_telemetry(telemetry_records: List[Dict[str, Any]], age_months: int) -> Dict[str, float]:
    """
    Extracts high-order physics features from a window of telemetry records.
    Uses vectorized NumPy operations for sub-millisecond performance without heavy DataFrame overhead.
    """
    if not telemetry_records:
        raise ValueError("Telemetry records list cannot be empty for feature extraction.")

    avg_temps = np.array([float(r["avg_cpu_temp_c"]) for r in telemetry_records], dtype=np.float64)
    max_temps = np.array([float(r["max_cpu_temp_c"]) for r in telemetry_records], dtype=np.float64)
    amb_temps = np.array([float(r.get("ambient_temp_c", 24.0)) for r in telemetry_records], dtype=np.float64)
    utils = np.array([float(r["cpu_utilization_pct"]) for r in telemetry_records], dtype=np.float64)
    rpms = np.array([float(r["fan_rpm"]) for r in telemetry_records], dtype=np.float64)
    r12v = np.array([float(r["rail_12v_v"]) for r in telemetry_records], dtype=np.float64)
    vcore = np.array([float(r["vcore_voltage_v"]) for r in telemetry_records], dtype=np.float64)
    r5v = np.array([float(r["rail_5v_v"]) for r in telemetry_records], dtype=np.float64)
    throttling = np.array([float(r.get("throttling_duration_sec", 0)) for r in telemetry_records], dtype=np.float64)

    # 1. Thermal Stress Index (TSI)
    delta_t = avg_temps - amb_temps
    clipped_util = np.clip(utils, 10.0, 100.0)
    tsi = float(np.mean(delta_t / clipped_util))

    # 2. Fan Dissipation Efficiency (FDE)
    rpm_k = np.clip(rpms / 1000.0, 0.4, 10.0)
    fde = float(np.mean(delta_t / rpm_k))

    # 3. Voltage sag & volatility
    min_12v = float(np.min(r12v))
    voltage_sag_12v = max(0.0, 12.0 - min_12v)
    vcore_volatility = float(np.std(vcore, ddof=1)) if len(vcore) > 1 else 0.005
    rail_5v_dev = float(np.mean(np.abs(5.0 - r5v)))

    # 4. Thermal throttling hours
    throttling_hours = float(np.sum(throttling) / 3600.0)

    # 5. Storage health parameters
    smart_bad_sectors = float(telemetry_records[-1].get("smart_reallocated_sectors", 0))
    smart_wear_level_pct = float(telemetry_records[-1].get("smart_wear_level_pct", 100.0))

    features = {
        "thermal_stress_index": round(tsi, 4),
        "fan_dissipation_efficiency": round(fde, 4),
        "avg_cpu_temp_c": round(float(np.mean(avg_temps)), 2),
        "max_cpu_temp_c": round(float(np.max(max_temps)), 2),
        "throttling_hours": round(throttling_hours, 3),
        "voltage_sag_12v": round(voltage_sag_12v, 4),
        "vcore_volatility": round(vcore_volatility, 4),
        "rail_5v_deviation": round(rail_5v_dev, 4),
        "smart_bad_sectors": smart_bad_sectors,
        "smart_wear_level_pct": smart_wear_level_pct,
        "operating_age_months": float(age_months),
        "cpu_utilization_avg": round(float(np.mean(utils)), 2)
    }

    return features
