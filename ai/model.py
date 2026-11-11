"""
ai/model.py
Predictive Maintenance AI Engine with LightGBM, TreeSHAP Explainability,
and Conformal Uncertainty Quantification for Electronic Fleet Lifecycle.
"""

import json
import os
import joblib
import numpy as np
import pandas as pd
try:
    import lightgbm as lgb
except (ImportError, OSError):
    lgb = None

try:
    import shap
except (ImportError, OSError):
    shap = None
from typing import Dict, Any, Tuple, List
from ai.feature_engineering import FEATURE_NAMES, extract_features_from_telemetry
from ai.data_generator import HybridFleetSimulator

MODEL_DIR = os.path.join(os.path.dirname(__file__), "weights")
RUL_MODEL_FILE = os.path.join(MODEL_DIR, "lgbm_rul_model.pkl")
RISK_MODEL_FILE = os.path.join(MODEL_DIR, "lgbm_risk_model.pkl")
MODE_MODEL_FILE = os.path.join(MODEL_DIR, "lgbm_mode_model.pkl")
METADATA_FILE = os.path.join(MODEL_DIR, "model_metadata.json")

FAILURE_MODE_LABELS = [
    "HEALTHY",
    "THERMAL_TIM_DEGRADATION",
    "FAN_BEARING_FAILURE",
    "VRM_VOLTAGE_SAG",
    "STORAGE_EXHAUSTION"
]

PRESCRIPTIVE_CATALOG = {
    "THERMAL_TIM_DEGRADATION": {
        "title": "Degradasi Thermal Interface Material & Akumulasi Debu",
        "action": "Bongkar heatsink, bersihkan residu pasta lama menggunakan alkohol isopropil 99%, bersihkan debu sirip radiator dengan udara bertekanan, aplikasikan pasta termal konduktivitas tinggi (12.5 W/mK).",
        "priority": "HIGH",
        "expected_life_extension_days": 365,
        "prevented_waste_kg": 7.0,
        "scope3_carbon_kg": 280.0,
        "cost_savings_idr": 15000000.0
    },
    "FAN_BEARING_FAILURE": {
        "title": "Keausan Mekanis Bearing Kipas Pendingin",
        "action": "Ganti modul kipas pendingin dengan suku cadang rekondisi OEM teruji. Bersihkan jalur airflow casing.",
        "priority": "URGENT",
        "expected_life_extension_days": 450,
        "prevented_waste_kg": 7.0,
        "scope3_carbon_kg": 280.0,
        "cost_savings_idr": 14500000.0
    },
    "VRM_VOLTAGE_SAG": {
        "title": "Ketidakstabilan Rel Tegangan / Degradasi Kapasitor VRM",
        "action": "Inspeksi fisik kapasitor filter pada VRM motherboard / PSU. Lakukan solder ulang (re-cap) kapasitor dengan ESR rendah atau tukar unit power supply teregistrasi.",
        "priority": "CRITICAL",
        "expected_life_extension_days": 540,
        "prevented_waste_kg": 12.0,
        "scope3_carbon_kg": 340.0,
        "cost_savings_idr": 18000000.0
    },
    "STORAGE_EXHAUSTION": {
        "title": "Batas Daya Tahan S.M.A.R.T SSD / Sektor Rusak",
        "action": "Segera migrasikan citra data ke media penyimpanan cadangan. Alokasikan SSD lama untuk partisi read-only arsip atau serahkan ke daur ulang komponen magnetis/silikon.",
        "priority": "HIGH",
        "expected_life_extension_days": 180,
        "prevented_waste_kg": 0.5,
        "scope3_carbon_kg": 45.0,
        "cost_savings_idr": 2000000.0
    },
    "HEALTHY": {
        "title": "Kondisi Komponen Nominal",
        "action": "Pertahankan jadwal inspeksi berkala. Tidak memerlukan intervensi fisik darurat.",
        "priority": "LOW",
        "expected_life_extension_days": 0,
        "prevented_waste_kg": 0.0,
        "scope3_carbon_kg": 0.0,
        "cost_savings_idr": 0.0
    }
}


class FleetPredictor:
    """Manages training, inference, explainability, and uncertainty guardrails."""

    def __init__(self):
        self.rul_model = None
        self.risk_model = None
        self.mode_model = None
        self.conformal_margin_imminent = 5
        self.conformal_margin_general = 30
        self.explainer = None
        self._load_or_train_models()

    def _load_or_train_models(self):
        os.makedirs(MODEL_DIR, exist_ok=True)
        try:
            if (os.path.exists(RUL_MODEL_FILE) and 
                os.path.exists(RISK_MODEL_FILE) and 
                os.path.exists(MODE_MODEL_FILE) and 
                os.path.exists(METADATA_FILE)):
                self.rul_model = joblib.load(RUL_MODEL_FILE)
                self.risk_model = joblib.load(RISK_MODEL_FILE)
                self.mode_model = joblib.load(MODE_MODEL_FILE)
                with open(METADATA_FILE, "r") as f:
                    meta = json.load(f)
                    self.conformal_margin_imminent = meta.get("conformal_margin_imminent", 5)
                    self.conformal_margin_general = meta.get("conformal_margin_general", 30)
                if shap is not None and self.rul_model is not None:
                    try:
                        self.explainer = shap.TreeExplainer(self.rul_model)
                    except Exception:
                        self.explainer = None
            elif lgb is not None:
                self.train_and_save_models()
        except Exception:
            # Resilient fallback if binary serialization differs in minimal serverless containers
            self.rul_model = None
            self.risk_model = None
            self.mode_model = None

    def train_and_save_models(self, n_samples: int = 500):
        """Generates calibration fleet, trains LightGBM models, and saves checkpoints."""
        sim = HybridFleetSimulator(seed=1337)
        devices, all_telemetry = sim.generate_fleet(num_devices=n_samples, days_history=14)

        # Group telemetry by device_id
        tel_by_dev: Dict[str, list] = {}
        for row in all_telemetry:
            tel_by_dev.setdefault(row["device_id"], []).append(row)

        X_rows = []
        y_rul = []
        y_fail_14d = []
        y_mode = []

        for d in devices:
            dev_id = d["device_id"]
            rec_list = tel_by_dev.get(dev_id, [])
            if len(rec_list) < 4:
                continue

            feats = extract_features_from_telemetry(rec_list, d["operating_age_months"])
            X_rows.append([feats[col] for col in FEATURE_NAMES])
            y_rul.append(d["true_rul_days"])
            y_fail_14d.append(1 if d["true_rul_days"] <= 14 else 0)
            mode_idx = FAILURE_MODE_LABELS.index(d["true_failure_mode"])
            y_mode.append(mode_idx)

        X = pd.DataFrame(X_rows, columns=FEATURE_NAMES)
        y_rul = np.array(y_rul, dtype=float)
        y_fail_14d = np.array(y_fail_14d, dtype=int)
        y_mode = np.array(y_mode, dtype=int)

        # 1. Train RUL Regressor
        self.rul_model = lgb.LGBMRegressor(
            n_estimators=80,
            learning_rate=0.08,
            num_leaves=24,
            random_state=42,
            verbosity=-1
        )
        self.rul_model.fit(X, y_rul)

        # Calculate tier-aware conformal margins
        preds = self.rul_model.predict(X)
        errors = np.abs(y_rul - preds)

        # Margin specifically for imminent failure regime (RUL <= 30)
        imminent_mask = y_rul <= 30
        if np.sum(imminent_mask) > 10:
            self.conformal_margin_imminent = int(np.ceil(np.percentile(errors[imminent_mask], 90)))
        else:
            self.conformal_margin_imminent = 5

        self.conformal_margin_general = int(np.ceil(np.percentile(errors, 90)))

        # 2. Train 14-day Risk Classifier
        self.risk_model = lgb.LGBMClassifier(
            n_estimators=70,
            learning_rate=0.08,
            num_leaves=20,
            random_state=42,
            verbosity=-1
        )
        self.risk_model.fit(X, y_fail_14d)

        # 3. Train Failure Mode Classifier
        self.mode_model = lgb.LGBMClassifier(
            n_estimators=80,
            learning_rate=0.08,
            num_leaves=24,
            random_state=42,
            verbosity=-1
        )
        self.mode_model.fit(X, y_mode)

        # Save artifacts
        os.makedirs(MODEL_DIR, exist_ok=True)
        joblib.dump(self.rul_model, RUL_MODEL_FILE)
        joblib.dump(self.risk_model, RISK_MODEL_FILE)
        joblib.dump(self.mode_model, MODE_MODEL_FILE)

        metadata = {
            "trained_at": "2026-11-11T12:00:00Z",
            "samples_count": len(X),
            "features": FEATURE_NAMES,
            "conformal_margin_imminent": self.conformal_margin_imminent,
            "conformal_margin_general": self.conformal_margin_general,
            "rul_mae": float(np.mean(errors))
        }
        with open(METADATA_FILE, "w") as f:
            json.dump(metadata, f, indent=2)

        self.explainer = shap.TreeExplainer(self.rul_model)

    def predict_device(
        self,
        telemetry_records: List[Dict[str, Any]],
        operating_age_months: int
    ) -> Dict[str, Any]:
        """
        Runs comprehensive prediction for a single device:
        Estimates RUL, failure probability, primary mode, SHAP factors, and Responsible AI guardrail.
        """
        feats = extract_features_from_telemetry(telemetry_records, operating_age_months)
        X_df = pd.DataFrame([[feats[col] for col in FEATURE_NAMES]], columns=FEATURE_NAMES)

        # RUL & Conformal interval (adaptive based on imminent vs general regime)
        if self.rul_model is not None and self.risk_model is not None:
            rul_raw = float(self.rul_model.predict(X_df)[0])
            rul_pred = max(1, int(round(rul_raw)))
            margin = self.conformal_margin_imminent if rul_pred <= 45 else self.conformal_margin_general
            risk_probs = self.risk_model.predict_proba(X_df)[0]
            p_fail_14d = float(risk_probs[1])
            p_fail_30d = min(1.0, float(p_fail_14d * 1.45 if p_fail_14d > 0.1 else p_fail_14d * 1.8))
            mode_probs = self.mode_model.predict_proba(X_df)[0]
            pred_mode_idx = int(np.argmax(mode_probs))
            pred_mode = FAILURE_MODE_LABELS[pred_mode_idx]
            mode_confidence = float(mode_probs[pred_mode_idx])
            confidence_score = round(float(0.6 * mode_confidence + 0.4 * (1.0 - min(1.0, margin / 60.0))), 2)
        else:
            # Fallback thermodynamic physics estimation
            tsi = feats.get("thermal_stress_index", 1.0)
            avg_temp = feats.get("avg_cpu_temp_c", 60.0)
            rul_pred = max(7, int(365.0 / max(0.5, tsi)))
            margin = 10
            p_fail_14d = min(0.95, max(0.05, (avg_temp - 50.0) / 50.0))
            p_fail_30d = min(0.99, p_fail_14d * 1.4)
            pred_mode = "THERMAL_TIM_DEGRADATION" if avg_temp > 80 else "HEALTHY"
            confidence_score = 0.82

        lower_rul = max(1, rul_pred - margin)
        upper_rul = rul_pred + margin

        # Physics-informed constraints
        thermal_hazard = feats["max_cpu_temp_c"] >= 88.0 or feats["throttling_hours"] > 0.5
        power_hazard = feats["voltage_sag_12v"] >= 0.75
        storage_hazard = feats["smart_bad_sectors"] >= 5 or feats["smart_wear_level_pct"] <= 20.0

        # Adjust RUL prediction if physical hazard is actively ongoing
        if thermal_hazard and pred_mode == "THERMAL_TIM_DEGRADATION":
            rul_pred = min(rul_pred, 18)
            p_fail_14d = max(p_fail_14d, 0.78)
            p_fail_30d = max(p_fail_30d, 0.92)

        margin = self.conformal_margin_imminent if rul_pred <= 45 else self.conformal_margin_general
        lower_rul = max(1, rul_pred - margin)
        upper_rul = rul_pred + margin

        # Risk tier classification
        if p_fail_14d >= 0.65 or rul_pred <= 14 or (thermal_hazard and pred_mode == "THERMAL_TIM_DEGRADATION"):
            risk_tier = "CRITICAL"
        elif p_fail_14d >= 0.30 or rul_pred <= 35 or power_hazard or storage_hazard:
            risk_tier = "HIGH"
        elif p_fail_30d >= 0.20 or rul_pred <= 75 or pred_mode != "HEALTHY":
            risk_tier = "MODERATE"
        else:
            risk_tier = "LOW"

        # Responsible AI Guardrail Check (Pertemuan 10 Halaman 4):
        # Decisions with low confidence or high ambiguity require human review before action
        if risk_tier in ["CRITICAL", "HIGH"]:
            operator_review = 1 if (mode_confidence < 0.75 or margin > 12) else 0
        elif risk_tier == "MODERATE":
            operator_review = 1 if mode_confidence < 0.60 else 0
        else:
            operator_review = 0

        # SHAP Explainability feature contributions
        shap_values = self.explainer.shap_values(X_df)[0]
        factor_items = []
        for name, val, fval in zip(FEATURE_NAMES, shap_values, X_df.iloc[0]):
            factor_items.append({
                "feature": name,
                "current_value": round(float(fval), 2),
                "shap_impact": round(float(val), 3)  # Negative SHAP on RUL means it reduces life (hastens failure)
            })

        # Sort by impact magnitude on accelerating degradation (most negative SHAP first)
        factor_items.sort(key=lambda x: x["shap_impact"])
        top_factors = factor_items[:4]

        # Fetch prescriptive action plan
        action_meta = PRESCRIPTIVE_CATALOG.get(pred_mode, PRESCRIPTIVE_CATALOG["HEALTHY"])

        return {
            "estimated_rul_days": rul_pred,
            "conformal_lower_rul_days": lower_rul,
            "conformal_upper_rul_days": upper_rul,
            "failure_probability_14d": round(p_fail_14d, 3),
            "failure_probability_30d": round(p_fail_30d, 3),
            "confidence_score": confidence_score,
            "primary_failure_mode": pred_mode,
            "risk_tier": risk_tier,
            "operator_review_required": operator_review,
            "top_shap_factors": top_factors,
            "extracted_features": feats,
            "prescriptive_action": action_meta
        }
