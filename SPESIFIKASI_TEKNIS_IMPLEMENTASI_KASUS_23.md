# SPESIFIKASI TEKNIS & KONTRAK IMPLEMENTASI SISTEM
## Arsitektur Data, Skema Basis Data DDL, Kontrak API, dan Algoritma Inferensi
**Studi Kasus No. 23: AI-Based Electronic Failure Prediction**  
**Mata Kuliah: Green Computing & Sustainable AI (Pertemuan 10)**

---

## 1. Analisis Kritis & Keputusan Metodologis

### 1.1 Evaluasi Keterbatasan Dataset Publik vs Pendekatan Physics-of-Failure
Dalam riset *Predictive Maintenance*, terdapat godaan umum untuk langsung menggunakan dataset publik seperti:
* **NASA C-MAPSS / Turbofan:** Sering digunakan untuk estimasi RUL, namun karakteristik termodinamika mesin jet turbofan berbeda secara fundamental dari karakteristik degradasi elektronika solid-state (ketiadaan parameter PWM fan, profil daya DC, dan tegangan rel).
* **Backblaze Hard Drive / SSD Data:** Sangat akurat untuk atribut S.M.A.R.T penyimpanan, namun tidak mencakup telemetri termal prosesor, degradasi pasta pendingin (*thermal paste drying*), keausan kapasitor sirkuit daya (VRM), atau beban kerja komputasi harian.

**Keputusan Metodologis yang Akurat & Valid:**
Sistem baseline ini dirancang menggunakan **Hybrid Empirical & Physics-of-Failure Simulation Engine** yang mengkalibrasi parameter fisik dengan hukum-hukum degradasi material yang terbukti:
1. **Model Arrhenius:** Untuk memodelkan percepatan pengeringan pasta termal silikon dan degradasi elektrolit kapasitor sebagai fungsi eksponensial dari temperatur operasional rata-rata:
   $$k = A \exp\left( -\frac{E_a}{k_B T} \right)$$
2. **Hukum Pendinginan Newton & Resistansi Termal Dinamis:**
   $$\frac{dT_{\text{die}}}{dt} = \frac{P_{\text{load}}}{C_{\text{thermal}}} - \frac{T_{\text{die}} - T_{\text{ambient}}}{R_{\text{thermal}}(t) \cdot C_{\text{thermal}}}$$
   di mana $R_{\text{thermal}}(t)$ meningkat seiring penuaan pasta termal dan akumulasi debu pada sirip heatsink.
3. **Distribusi Weibull untuk Keausan Mekanik Kipas Pendingin:**
   $$f(t; \lambda, k) = \frac{k}{\lambda} \left(\frac{t}{\lambda}\right)^{k-1} e^{-(t/\lambda)^k}$$
   di mana parameter bentuk $k > 1$ merefleksikan laju keausan aus (*wear-out phase*) pada bearing kipas.

---

## 2. Skema Basis Data DDL (PostgreSQL & TimescaleDB)

Berikut adalah definisi struktur data relasional dan deret waktu (*time-series*) yang siap dieksekusi pada PostgreSQL 16 dengan ekstensi TimescaleDB aktif:

```sql
-- Ekstensi yang Dibutuhkan
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "timescaledb";

-- 1. TABEL ORGANISASI
CREATE TABLE organizations (
    org_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(150) NOT NULL,
    industry_type VARCHAR(100) NOT NULL,
    sustainability_target_pct FLOAT DEFAULT 20.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. TABEL ASET PERANGKAT ELEKTRONIK
CREATE TABLE asset_devices (
    device_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    asset_tag VARCHAR(50) UNIQUE NOT NULL,
    device_type VARCHAR(50) NOT NULL, -- 'LAPTOP', 'DESKTOP', 'SERVER_NODE', 'EDGE_GATEWAY'
    brand_model VARCHAR(100) NOT NULL,
    cpu_spec VARCHAR(100) NOT NULL,
    ram_gb INT NOT NULL,
    storage_capacity_gb INT NOT NULL,
    commission_date DATE NOT NULL,
    expected_lifecycle_months INT NOT NULL DEFAULT 48,
    current_status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE', -- 'ACTIVE', 'WATCHLIST', 'CRITICAL', 'MAINTENANCE', 'RETIRED'
    last_telemetry_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. TABEL TELEMETRI SENSOR (TIME-SERIES HYPERTABLE)
CREATE TABLE sensor_telemetry (
    recorded_at TIMESTAMPTZ NOT NULL,
    device_id UUID NOT NULL REFERENCES asset_devices(device_id) ON DELETE CASCADE,
    avg_cpu_temp_c REAL NOT NULL,
    max_cpu_temp_c REAL NOT NULL,
    ambient_temp_c REAL DEFAULT 25.0,
    fan_rpm INT NOT NULL,
    fan_duty_cycle_pct REAL NOT NULL,
    vcore_voltage_v REAL NOT NULL,
    rail_12v_v REAL NOT NULL,
    rail_5v_v REAL NOT NULL,
    cpu_utilization_pct REAL NOT NULL,
    throttling_duration_sec INT DEFAULT 0,
    smart_reallocated_sectors INT DEFAULT 0,
    smart_wear_level_pct REAL DEFAULT 100.0,
    power_cycles_count INT DEFAULT 1
);

-- Konversi ke TimescaleDB Hypertable dengan partisi 1 hari
SELECT create_hypertable('sensor_telemetry', 'recorded_at', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_telemetry_device_time ON sensor_telemetry (device_id, recorded_at DESC);

-- 4. TABEL AKUN PENGGUNA SISTEM
CREATE TABLE user_accounts (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(30) NOT NULL, -- 'TECHNICIAN', 'ASSET_MANAGER', 'MLOPS_ADMIN', 'ESG_OFFICER'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. TABEL PREDIKSI KEGAGALAN AI
CREATE TABLE failure_predictions (
    prediction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID NOT NULL REFERENCES asset_devices(device_id) ON DELETE CASCADE,
    predicted_at TIMESTAMPTZ DEFAULT NOW(),
    failure_probability_14d REAL NOT NULL,
    failure_probability_30d REAL NOT NULL,
    estimated_rul_days INT NOT NULL,
    conformal_lower_rul_days INT NOT NULL,
    conformal_upper_rul_days INT NOT NULL,
    confidence_score REAL NOT NULL,
    primary_failure_mode VARCHAR(60) NOT NULL, -- 'THERMAL_TIM_DEGRADATION', 'FAN_BEARING_FAILURE', 'VRM_VOLTAGE_SAG', 'STORAGE_EXHAUSTION'
    risk_tier VARCHAR(20) NOT NULL, -- 'LOW', 'MODERATE', 'HIGH', 'CRITICAL'
    shap_attributions JSONB NOT NULL,
    operator_review_required BOOLEAN DEFAULT FALSE
);
CREATE INDEX idx_predictions_device_date ON failure_predictions (device_id, predicted_at DESC);

-- 6. TABEL TIKET KERJA PRESKRIPTIF (WORK ORDERS)
CREATE TABLE work_orders (
    order_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prediction_id UUID NOT NULL REFERENCES failure_predictions(prediction_id) ON DELETE CASCADE,
    device_id UUID NOT NULL REFERENCES asset_devices(device_id) ON DELETE CASCADE,
    assigned_technician_id UUID REFERENCES user_accounts(user_id),
    priority VARCHAR(20) NOT NULL DEFAULT 'HIGH', -- 'LOW', 'MEDIUM', 'HIGH', 'URGENT'
    prescriptive_action_plan TEXT NOT NULL,
    order_status VARCHAR(30) NOT NULL DEFAULT 'PENDING_REVIEW', -- 'PENDING_REVIEW', 'CONFIRMED', 'IN_PROGRESS', 'RESOLVED', 'REJECTED_FALSE_ALARM'
    technician_findings TEXT,
    technician_verified_correct BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

-- 7. TABEL LOG PEMELIHARAAN & SIKLUS HIDUP SIRKULAR
CREATE TABLE maintenance_records (
    maintenance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    work_order_id UUID REFERENCES work_orders(order_id),
    device_id UUID NOT NULL REFERENCES asset_devices(device_id) ON DELETE CASCADE,
    technician_id UUID NOT NULL REFERENCES user_accounts(user_id),
    service_date TIMESTAMPTZ DEFAULT NOW(),
    maintenance_category VARCHAR(50) NOT NULL, -- 'REPAIR', 'REFURBISH', 'PREVENTIVE_CLEANING', 'REPURPOSE'
    actions_performed TEXT[] NOT NULL,
    parts_replaced TEXT[] DEFAULT ARRAY[]::TEXT[],
    parts_origin VARCHAR(50) DEFAULT 'OEM_RECONDITIONED', -- 'NEW', 'HARVESTED_REUSED', 'OEM_RECONDITIONED'
    service_cost_idr NUMERIC(12, 2) NOT NULL,
    new_device_replacement_cost_idr NUMERIC(12, 2) NOT NULL,
    pre_service_peak_temp_c REAL,
    post_service_peak_temp_c REAL,
    extended_lifecycle_days INT NOT NULL,
    embodied_carbon_saved_kg REAL NOT NULL,
    ewaste_mass_saved_kg REAL NOT NULL
);
```

---

## 3. Spesifikasi Kontrak Ingesti Telemetri (JSON Schema)

Setiap agen perangkat edge mengirimkan payload telemetri tervalidasi ke gateway server melalui enkripsi HTTPS POST:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "DeviceTelemetryPayload",
  "type": "object",
  "required": [
    "device_asset_tag",
    "timestamp_utc",
    "thermal_metrics",
    "power_metrics",
    "system_workload",
    "storage_smart"
  ],
  "properties": {
    "device_asset_tag": {
      "type": "string",
      "pattern": "^[A-Z0-9_-]{4,30}$"
    },
    "timestamp_utc": {
      "type": "string",
      "format": "date-time"
    },
    "thermal_metrics": {
      "type": "object",
      "required": ["cpu_temp_avg_c", "cpu_temp_max_c", "fan_rpm", "fan_pwm_pct"],
      "properties": {
        "cpu_temp_avg_c": { "type": "number", "minimum": 0, "maximum": 125 },
        "cpu_temp_max_c": { "type": "number", "minimum": 0, "maximum": 130 },
        "ambient_temp_c": { "type": "number", "minimum": -10, "maximum": 60, "default": 25.0 },
        "fan_rpm": { "type": "integer", "minimum": 0, "maximum": 12000 },
        "fan_pwm_pct": { "type": "number", "minimum": 0, "maximum": 100 },
        "thermal_throttling_count": { "type": "integer", "minimum": 0 }
      }
    },
    "power_metrics": {
      "type": "object",
      "required": ["vcore_v", "rail_12v_v", "rail_5v_v"],
      "properties": {
        "vcore_v": { "type": "number", "minimum": 0.5, "maximum": 2.2 },
        "rail_12v_v": { "type": "number", "minimum": 9.0, "maximum": 15.0 },
        "rail_5v_v": { "type": "number", "minimum": 4.0, "maximum": 6.0 },
        "power_cycles_total": { "type": "integer", "minimum": 1 }
      }
    },
    "system_workload": {
      "type": "object",
      "required": ["cpu_load_pct", "memory_usage_pct"],
      "properties": {
        "cpu_load_pct": { "type": "number", "minimum": 0, "maximum": 100 },
        "memory_usage_pct": { "type": "number", "minimum": 0, "maximum": 100 }
      }
    },
    "storage_smart": {
      "type": "object",
      "required": ["reallocated_sectors", "wear_indicator_pct"],
      "properties": {
        "reallocated_sectors": { "type": "integer", "minimum": 0 },
        "wear_indicator_pct": { "type": "number", "minimum": 0, "maximum": 100 }
      }
    }
  }
}
```

---

## 4. Spesifikasi Kontrak REST API (Core Endpoints)

### 4.1 Ingestion Gateway: `POST /api/v1/telemetry/ingest`
* **Deskripsi:** Menerima paket data telemetri berkala dari agen perangkat.
* **Autentikasi:** Token Perangkat Berbasis Header (`X-Device-Token: Bearer <HMAC-SHA256>`).
* **Respon Sukses (202 Accepted):**
  ```json
  {
    "status": "ACCEPTED",
    "received_records": 1,
    "device_status": "MONITORED",
    "local_action_directive": "NORMAL_POLLING"
  }
  ```

### 4.2 Analisis Kesehatan Aset: `GET /api/v1/devices/{device_id}/health-summary`
* **Deskripsi:** Mengembalikan metrik telemetri 7 hari terakhir, skor risiko kegagalan, dan penjelasan fitur teratas.
* **Respon Sukses (200 OK):**
  ```json
  {
    "device_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "asset_tag": "WS-CAD-042",
    "current_status": "CRITICAL",
    "operating_age_months": 36,
    "latest_prediction": {
      "predicted_at": "2026-11-11T08:00:00Z",
      "estimated_rul_days": 14,
      "conformal_interval_days": [10, 18],
      "failure_probability_14d": 0.84,
      "confidence_score": 0.92,
      "primary_mode": "THERMAL_TIM_DEGRADATION",
      "top_shap_factors": [
        {"feature": "thermal_stress_index", "impact": "+0.41", "description": "Suhu CPU 89C pada beban 45%"},
        {"feature": "fan_rpm_saturation", "impact": "+0.27", "description": "Kipas berputar 100% tanpa penurunan suhu"},
        {"feature": "months_since_last_repaste", "impact": "+0.18", "description": "Sudah 36 bulan tanpa servis pasta termal"}
      ]
    },
    "prescriptive_recommendation": {
      "action_type": "URGENT_HEATSINK_SERVICE",
      "instructions": "Bongkar heatsink, bersihkan residu pasta kering dengan alkohol isopropil 99%, aplikasikan pasta baru konduktivitas tinggi, bersihkan debu sirip radiator.",
      "estimated_savings_idr": 15000000,
      "embodied_carbon_avoided_kg": 280.0
    }
  }
  ```

### 4.3 Verifikasi & Penutupan Tiket: `POST /api/v1/work-orders/{order_id}/resolve`
* **Deskripsi:** Modul *Human-in-the-Loop* bagi teknisi untuk mencatat verifikasi fisik dan pengukuran sensor pasca-perbaikan.
* **Payload Request:**
  ```json
  {
    "technician_verified_correct": true,
    "actual_fault_found": "Pasta termal mengering total dan debu menutup 70% sirip pendingin",
    "actions_taken": [
      "CLEANED_DUST_HEATSINK",
      "REPLACED_THERMAL_PASTE",
      "LUBRICATED_BEARING_FAN"
    ],
    "parts_used": ["THERMAL_PASTE_ARCTIC_MX4"],
    "pre_temp_peak_c": 94.5,
    "post_temp_peak_c": 62.0,
    "calculated_extension_days": 365
  }
  ```

---

## 5. Algoritma Feature Extraction & Inference Pipeline

### 5.1 Algoritma Ekstraksi Fitur Fisika Degradasi (Pseudo-Code)

```python
def extract_failure_features(telemetry_window_df, device_metadata):
    """
    Mengekstrak fitur berbasis hukum fisika degradasi dari jendela telemetri 14 hari terakhir.
    """
    # 1. Thermal Stress Index (TSI)
    # Rasio kenaikan suhu di atas ambient terhadap beban komputasi
    delta_temp = telemetry_window_df['avg_cpu_temp_c'] - telemetry_window_df['ambient_temp_c']
    tsi_series = delta_temp / telemetry_window_df['cpu_utilization_pct'].clip(lower=10.0)
    
    # 2. Fan Dispassion Efficiency (FDE)
    # Mengukur efektivitas pelepasan panas per 1.000 RPM kipas
    fde_series = delta_temp / (telemetry_window_df['fan_rpm'] / 1000.0).clip(lower=0.5)
    
    # 3. Voltage Stability & Sag Under Load
    vcore_std = telemetry_window_df['vcore_voltage_v'].std()
    rail_12v_min = telemetry_window_df['rail_12v_v'].min()
    voltage_sag_12v = 12.0 - rail_12v_min
    
    # 4. Storage Wear & Reallocated Sector Velocity
    sector_delta = (telemetry_window_df['smart_reallocated_sectors'].iloc[-1] - 
                    telemetry_window_df['smart_reallocated_sectors'].iloc[0])
    
    # 5. Fitur Agregat Usia & Pemeliharaan
    operating_age_months = device_metadata['operating_age_months']
    months_since_last_service = device_metadata['months_since_last_service']
    
    feature_vector = {
        'tsi_rolling_mean_7d': tsi_series.rolling('7D').mean().iloc[-1],
        'tsi_trend_slope': calculate_linear_slope(tsi_series),
        'fde_rolling_mean_7d': fde_series.rolling('7D').mean().iloc[-1],
        'throttling_event_hours': telemetry_window_df['throttling_duration_sec'].sum() / 3600.0,
        'vcore_volatility': vcore_std,
        'rail_12v_sag_max': voltage_sag_12v,
        'smart_bad_sector_velocity': sector_delta,
        'operating_age_months': operating_age_months,
        'months_since_last_service': months_since_last_service
    }
    
    return feature_vector
```

### 5.2 Algoritma Filter Keyakinan & Guardrail Responsible AI (Pseudo-Code)

```python
def evaluate_responsible_guardrail(prediction_output, uncertainty_interval):
    """
    Mengevaluasi keputusan model sesuai amanat Responsible AI (Pertemuan 10 Halaman 4):
    Keputusan penting dilarang sepenuhnya otomatis jika tingkat keyakinan rendah.
    """
    p_fail_14d = prediction_output['p_fail_14d']
    confidence = prediction_output['confidence_score']
    interval_width = uncertainty_interval[1] - uncertainty_interval[0]
    
    # Ambang batas ketidakpastian (Uncertainty threshold)
    if confidence < 0.75 or interval_width > 20: # Rentang RUL terlalu lebar (>20 hari)
        return {
            'action_code': 'HUMAN_OPERATOR_REVIEW_REQUIRED',
            'auto_generate_work_order': False,
            'alert_level': 'CAUTION_AMBIGUOUS_DATA',
            'message': 'Prediksi memiliki ketidakpastian tinggi. Operator manusia wajib melakukan review manual sebelum penjadwalan intervensi.'
        }
    
    if p_fail_14d >= 0.75:
        return {
            'action_code': 'EMIT_PRESCRIPTIVE_WORK_ORDER',
            'auto_generate_work_order': True,
            'alert_level': 'HIGH_RISK_FAILURE_IMMINENT',
            'message': 'Anomali degradasi terkonfirmasi dengan keyakinan tinggi. Perintah kerja diterbitkan untuk teknisi.'
        }
    
    elif 0.40 <= p_fail_14d < 0.75:
        return {
            'action_code': 'ADD_TO_TELEMETRY_WATCHLIST',
            'auto_generate_work_order': False,
            'alert_level': 'MODERATE_MONITORING',
            'message': 'Indikasi degradasi awal terdeteksi. Pindahkan interval pengambilan sampel sensor ke frekuensi lebih rapat.'
        }
    
    else:
        return {
            'action_code': 'NORMAL_OPERATION',
            'auto_generate_work_order': False,
            'alert_level': 'HEALTHY',
            'message': 'Kondisi perangkat dalam batas normal operasional.'
        }
```

---

## 6. Struktur Direktori Proyek Standar Implementasi

```
D:\AI-Based Electronic Failure Prediction\
├── docs/
│   ├── DOKUMEN_DESAIN_SISTEM_BASELINE_KASUS_23.md
│   └── SPESIFIKASI_TEKNIS_IMPLEMENTASI_KASUS_23.md
├── edge_agent/
│   ├── collector.py           # Ekstraksi sensor lokal (psutil, WMI, openhardwaremonitor)
│   ├── transmitter.py         # Pengiriman batch HTTPS terenkripsi & local buffer
│   └── agent_config.yaml      # Parameter frekuensi sampling & URL gateway
├── backend/
│   ├── app/
│   │   ├── api/               # Router endpoint FastAPI
│   │   ├── core/              # Konfigurasi keamanan, database pool, settings
│   │   ├── models/            # SQLAlchemy / TimescaleDB Models
│   │   ├── schemas/           # Pydantic Schemas (validasi JSON request/response)
│   │   └── services/          # Logika bisnis ingesti & work order management
│   ├── alembic/               # Migrasi database
│   └── main.py                # Entrypoint REST API
├── ai_engine/
│   ├── data_generator/        # Simulator fisika degradasi elektronika (benchmark generator)
│   ├── features/              # Feature engineering (TSI, Thermal Cycling, Voltage Sag)
│   ├── models/                # Survival Trees (LightGBM/XGBoost) & Conformal Predictor
│   ├── explainability/        # Modul Fast TreeSHAP
│   └── inference_pipeline.py  # Pipeline inferensi batch periodik
└── dashboard/                 # Frontend antarmuka monitoring kesehatan armada (Next.js/React)
```
