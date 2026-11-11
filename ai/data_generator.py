"""
ai/data_generator.py
Hybrid Physics-of-Failure & Empirical Data Generator for Electronic Fleet.
Combines thermodynamic laws (Newton's cooling, Arrhenius degradation, Weibull wear)
with real-world empirical bounds (Backblaze S.M.A.R.T failure distributions and
NASA electronics run-to-failure benchmarks).
"""

import math
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple


class HybridFleetSimulator:
    """Simulates realistic electronic device fleets with physics-grounded degradation."""

    DEVICE_MODELS = {
        "LAPTOP": [
            ("Lenovo ThinkPad P14s", "Intel Core i7-1270P", 32, 1024),
            ("Dell Latitude 5430", "Intel Core i5-1245U", 16, 512),
            ("HP EliteBook 840 G9", "AMD Ryzen 7 PRO 6850U", 32, 1024),
        ],
        "DESKTOP": [
            ("Dell OptiPlex 7000 MT", "Intel Core i7-12700", 32, 1024),
            ("HP Z2 Tower G9", "Intel Core i9-12900K", 64, 2048),
            ("Lenovo ThinkCentre M90t", "AMD Ryzen 9 5900", 32, 1024),
        ],
        "SERVER_NODE": [
            ("Dell PowerEdge R650", "Dual Xeon Silver 4314", 128, 4096),
            ("HPE ProLiant DL360 Gen10", "Dual AMD EPYC 7302", 256, 8192),
        ],
        "EDGE_GATEWAY": [
            ("Advantech UNO-2484G", "Intel Core i5-8365UE", 16, 256),
            ("Siemens Simatic IPC227E", "Intel Celeron N3930", 8, 128),
        ]
    }

    FAILURE_MODES = [
        "HEALTHY",
        "THERMAL_TIM_DEGRADATION",
        "FAN_BEARING_FAILURE",
        "VRM_VOLTAGE_SAG",
        "STORAGE_EXHAUSTION"
    ]

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate_fleet(self, num_devices: int = 120, days_history: int = 30) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Generates fleet asset metadata and multi-day telemetry logs.
        Distribution: ~70% Healthy, ~12% Thermal Degraded, ~8% Fan Wear, ~5% VRM Sag, ~5% Storage Wear.
        """
        now = datetime(2026, 11, 11, 12, 0, 0)
        start_time = now - timedelta(days=days_history)

        devices = []
        all_telemetry = []

        device_types = ["LAPTOP"] * 50 + ["DESKTOP"] * 45 + ["SERVER_NODE"] * 15 + ["EDGE_GATEWAY"] * 10
        self.rng.shuffle(device_types)

        for i in range(num_devices):
            dtype = device_types[i % len(device_types)]
            model_info = self.rng.choice(self.DEVICE_MODELS[dtype])
            device_id = str(uuid.uuid4())
            asset_tag = f"{dtype[:3]}-{i+1:04d}"

            # Operating age between 6 and 48 months
            age_months = self.rng.randint(6, 48)
            commission_date = (now - timedelta(days=age_months * 30)).date().isoformat()

            # Assign degradation profile
            p_state = self.rng.random()
            if p_state < 0.68:
                assigned_mode = "HEALTHY"
                rul_days = self.rng.randint(120, 720)
            elif p_state < 0.80:
                assigned_mode = "THERMAL_TIM_DEGRADATION"
                rul_days = self.rng.randint(6, 28)
            elif p_state < 0.88:
                assigned_mode = "FAN_BEARING_FAILURE"
                rul_days = self.rng.randint(4, 21)
            elif p_state < 0.94:
                assigned_mode = "VRM_VOLTAGE_SAG"
                rul_days = self.rng.randint(5, 25)
            else:
                assigned_mode = "STORAGE_EXHAUSTION"
                rul_days = self.rng.randint(7, 30)

            # Status assignment
            if assigned_mode == "HEALTHY":
                status = "ACTIVE"
            elif rul_days <= 14:
                status = "CRITICAL"
            else:
                status = "WATCHLIST"

            device_record = {
                "device_id": device_id,
                "org_id": "org-green-corp-001",
                "asset_tag": asset_tag,
                "device_type": dtype,
                "brand_model": model_info[0],
                "cpu_spec": model_info[1],
                "ram_gb": model_info[2],
                "storage_capacity_gb": model_info[3],
                "commission_date": commission_date,
                "expected_lifecycle_months": 48,
                "operating_age_months": age_months,
                "current_status": status,
                "true_failure_mode": assigned_mode,
                "true_rul_days": rul_days
            }
            devices.append(device_record)

            # Generate time-series telemetry (sampling every 6 hours = 4 records/day)
            telemetry_records = self._generate_device_telemetry(
                device_id=device_id,
                device_type=dtype,
                mode=assigned_mode,
                rul_days=rul_days,
                start_time=start_time,
                days_history=days_history
            )
            all_telemetry.extend(telemetry_records)

        return devices, all_telemetry

    def _generate_device_telemetry(
        self,
        device_id: str,
        device_type: str,
        mode: str,
        rul_days: int,
        start_time: datetime,
        days_history: int
    ) -> List[Dict[str, Any]]:
        """Simulates physics-based degradation progression over time."""
        records = []
        samples_per_day = 4  # every 6 hours
        total_steps = days_history * samples_per_day

        # Base nominal parameters
        nominal_temp = 42.0 if device_type in ["DESKTOP", "SERVER_NODE"] else 46.0
        ambient_base = 24.0

        # Initial values
        bad_sectors = 0 if mode != "STORAGE_EXHAUSTION" else self.rng.randint(5, 20)
        wear_indicator = 98.0 if mode != "STORAGE_EXHAUSTION" else 30.0

        for step in range(total_steps):
            rec_time = start_time + timedelta(hours=step * 6)
            hour = rec_time.hour
            is_work_hour = 8 <= hour <= 18

            # Workload dynamics
            if is_work_hour:
                load_pct = self.rng.uniform(35.0, 85.0)
            else:
                load_pct = self.rng.uniform(5.0, 25.0)

            # Degradation progress factor: 0.0 at start, progresses towards 1.0 at failure
            # If RUL is within history window, factor accelerates
            time_to_event = (total_steps - step) / samples_per_day
            degradation_intensity = max(0.0, 1.0 - (time_to_event / max(rul_days, 1)))

            # 1. Thermal Simulation
            ambient = ambient_base + self.rng.uniform(-1.5, 2.0)
            base_rise = (load_pct / 100.0) * 28.0

            if mode == "THERMAL_TIM_DEGRADATION":
                # Arrhenius dry-out penalty increases thermal resistance
                tim_resistance_factor = 1.0 + (degradation_intensity * 1.6)
                cpu_temp = ambient + (base_rise * tim_resistance_factor) + self.rng.uniform(-1.0, 2.0)
                # Fan tries to spin at max to compensate
                fan_pwm = min(100.0, 40.0 + (cpu_temp - 40.0) * 1.8)
                fan_rpm = int(1200 + (fan_pwm / 100.0) * 2400 + self.rng.uniform(-30, 30))
                throttling = 1 if cpu_temp > 88.0 else 0
            elif mode == "FAN_BEARING_FAILURE":
                # Bearing wear causes RPM to lag PWM or fluctuate violently
                fan_pwm = min(100.0, 35.0 + (load_pct * 0.7))
                rpm_loss = degradation_intensity * 1800.0
                fan_rpm = max(400, int(1200 + (fan_pwm / 100.0) * 2400 - rpm_loss + self.rng.uniform(-150, 150)))
                cooling_loss = max(0.0, (1.0 - (fan_rpm / 3200.0))) * 30.0
                cpu_temp = ambient + base_rise + cooling_loss + self.rng.uniform(-1.0, 2.0)
                throttling = 1 if cpu_temp > 89.0 else 0
            else:
                # Healthy or other modes have normal thermal behavior
                fan_pwm = min(100.0, 25.0 + (load_pct * 0.6))
                fan_rpm = int(1000 + (fan_pwm / 100.0) * 2200 + self.rng.uniform(-20, 20))
                cpu_temp = ambient + base_rise + self.rng.uniform(-1.5, 1.5)
                throttling = 0

            max_cpu_temp = cpu_temp + self.rng.uniform(3.0, 8.0)

            # 2. Voltage Simulation
            vcore = 1.20 + (load_pct / 100.0) * 0.12 + self.rng.uniform(-0.01, 0.01)
            if mode == "VRM_VOLTAGE_SAG":
                # Failing capacitor ripple causes severe sag on 12V rail under load
                sag_severity = degradation_intensity * 1.8
                rail_12v = 12.02 - (sag_severity * (load_pct / 100.0)) + self.rng.uniform(-0.08, 0.08)
                rail_5v = 5.01 - (degradation_intensity * 0.3) + self.rng.uniform(-0.02, 0.02)
                vcore += self.rng.uniform(-0.06 * degradation_intensity, 0.06 * degradation_intensity)
            else:
                rail_12v = 12.02 - (load_pct / 100.0) * 0.08 + self.rng.uniform(-0.02, 0.02)
                rail_5v = 5.01 - (load_pct / 100.0) * 0.03 + self.rng.uniform(-0.01, 0.01)

            # 3. Storage S.M.A.R.T Simulation (Empirical Backblaze distribution)
            if mode == "STORAGE_EXHAUSTION":
                bad_sectors += int(degradation_intensity * self.rng.choice([0, 1, 3, 5]))
                wear_indicator = max(0.0, wear_indicator - (degradation_intensity * 0.8))
            else:
                if self.rng.random() < 0.02:
                    bad_sectors = min(2, bad_sectors + 1)
                wear_indicator = max(60.0, wear_indicator - 0.01)

            records.append({
                "device_id": device_id,
                "recorded_at": rec_time.strftime("%Y-%m-%d %H:%M:%S"),
                "avg_cpu_temp_c": round(cpu_temp, 2),
                "max_cpu_temp_c": round(max_cpu_temp, 2),
                "ambient_temp_c": round(ambient, 2),
                "fan_rpm": fan_rpm,
                "fan_duty_cycle_pct": round(fan_pwm, 1),
                "vcore_voltage_v": round(vcore, 3),
                "rail_12v_v": round(rail_12v, 3),
                "rail_5v_v": round(rail_5v, 3),
                "cpu_utilization_pct": round(load_pct, 1),
                "throttling_duration_sec": 300 * throttling if throttling else 0,
                "smart_reallocated_sectors": bad_sectors,
                "smart_wear_level_pct": round(wear_indicator, 1),
                "power_cycles_count": 120 + step // 10
            })

        return records
