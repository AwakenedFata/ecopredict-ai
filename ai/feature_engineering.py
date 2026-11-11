"""
ai/feature_engineering.py
Physics-Informed Feature Engineering for Electronic Component Degradation.
Extracts thermodynamic and electrical indicators from telemetry time-series windows.
"""

import numpy as np
import pandas as pd
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
    Requires at least 4 records (e.g. 1-2 days).
    """
    if not telemetry_records:
        raise ValueError("Telemetry records list cannot be empty for feature extraction.")

    df = pd.DataFrame(telemetry_records)

    # 1. Thermal Stress Index (TSI)
    # Ratio of temperature delta above ambient over computing workload
    delta_t = df["avg_cpu_temp_c"] - df["ambient_temp_c"]
    clipped_util = np.clip(df["cpu_utilization_pct"], 10.0, 100.0)
    tsi = (delta_t / clipped_util).mean()

    # 2. Fan Dissipation Efficiency (FDE)
    # Heat dissipated per thousand RPM
    rpm_k = np.clip(df["fan_rpm"] / 1000.0, 0.4, 10.0)
    fde = (delta_t / rpm_k).mean()

    # 3. Voltage sag & volatility
    min_12v = df["rail_12v_v"].min()
    voltage_sag_12v = max(0.0, 12.0 - min_12v)
    vcore_volatility = float(df["vcore_voltage_v"].std()) if len(df) > 1 else 0.005
    rail_5v_dev = float(np.abs(5.0 - df["rail_5v_v"]).mean())

    # 4. Thermal throttling hours
    throttling_hours = float(df["throttling_duration_sec"].sum() / 3600.0)

    # 5. Storage health parameters
    smart_bad_sectors = float(df["smart_reallocated_sectors"].iloc[-1])
    smart_wear_level_pct = float(df["smart_wear_level_pct"].iloc[-1])

    features = {
        "thermal_stress_index": round(float(tsi), 4),
        "fan_dissipation_efficiency": round(float(fde), 4),
        "avg_cpu_temp_c": round(float(df["avg_cpu_temp_c"].mean()), 2),
        "max_cpu_temp_c": round(float(df["max_cpu_temp_c"].max()), 2),
        "throttling_hours": round(throttling_hours, 3),
        "voltage_sag_12v": round(float(voltage_sag_12v), 4),
        "vcore_volatility": round(vcore_volatility, 4),
        "rail_5v_deviation": round(rail_5v_dev, 4),
        "smart_bad_sectors": smart_bad_sectors,
        "smart_wear_level_pct": smart_wear_level_pct,
        "operating_age_months": float(age_months),
        "cpu_utilization_avg": round(float(df["cpu_utilization_pct"].mean()), 2)
    }

    return features
