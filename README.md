# EcoPredict AI: AI-Based Electronic Failure Prediction & Circular Fleet Lifecycle Platform
**Studi Kasus No. 23: AI-Based Electronic Failure Prediction**  
**Mata Kuliah: Green Computing & Sustainable AI (Pertemuan 10)**  
**Fokus: Circular Economy • Pengelolaan Limbah Elektronik • Machine Learning & Telemetri**

---

## 1. Ringkasan Eksekutif & Nilai Kebaruan

Dalam paradigma industri konvensional (*take-make-dispose*), perangkat elektronik organisasi (desktop, laptop, server, edge node) kerap mengalami penggantian prematur berbasis usia buku akuntansi kaku (3-4 tahun) atau sebaliknya, dioperasikan hingga rusak total (*catastrophic breakdown*) yang membakar sirkuit utama dan langsung menghasilkan *e-waste*.

**EcoPredict AI** adalah platform prediktif keandalan perangkat keras yang mentransformasi tata kelola aset menjadi *proactive, condition-based, circular maintenance*. Dengan mengombinasikan hukum fisika degradasi (*physics-of-failure*) dan algoritma *Green Machine Learning*, sistem ini:
1. Mendeteksi anomali degradasi komponen (pasta termal mengering, keausan bearing kipas, keausan sel SSD NAND, dan fluktuasi rel tegangan VRM/kapasitor) sebelum terjadi kerusakan fatal.
2. Memproyeksikan sisa masa pakai (*Remaining Useful Life* - RUL) dalam hari dengan interval toleransi keyakinan (*Conformal Prediction*).
3. Memberikan transparansi keputusan AI melalui nilai atribusi fitur lokal (*TreeSHAP*), memastikan teknisi memahami akar masalah fisik.
4. Menerapkan pengaman *Responsible AI* & *Human-in-the-Loop*: Prediksi dengan ketidakpastian tinggi wajib ditinjau operator, dan perbaikan diverifikasi oleh teknisi sebelum tiket kerja ditutup.
5. Menghitung secara otomatis dampak ekonomi sirkular riil (kilogram *e-waste* dicegah, ton emisi *Scope 3 embodied carbon* dihindari, dan penghematan biaya total kepemilikan aset / TCO).

---

## 2. Arsitektur Solusi 5-Tier

```
[ Tier 1: Klien / Edge ]
  └── Edge Telemetry Daemon (edge_agent/client_daemon.py)
      ├── Sampling Hardware Counters (CPU load, Temp, S.M.A.R.T, Voltage)
      └── Offline Store-and-Forward Buffer (SQLite Lokal)
           │
           ▼ (HTTPS POST /api/v1/telemetry/ingest)
[ Tier 2: Ingestion & Gateway ]
  └── FastAPI Ingestion Gateway (api/routes.py)
           │
           ▼
[ Tier 3: Penyimpanan Data ]
  └── High-Performance SQLite WAL Engine (core/database.py)
      ├── asset_devices & organizations
      ├── sensor_telemetry (Time-Series)
      ├── failure_predictions & work_orders
      └── maintenance_records (Circular Accounting)
           │
           ▼
[ Tier 4: Mesin AI & Guardrail ]
  └── Predictive Engine (ai/model.py & ai/pipeline.py)
      ├── Feature Engineering: Thermal Stress Index (TSI), FDE, Sag
      ├── LightGBM RUL Regressor & Risk Classifier
      ├── TreeSHAP Local Feature Attribution
      └── Conformal Prediction Uncertainty Filter (Responsible AI)
           │
           ▼
[ Tier 5: Antarmuka & Eksekusi ]
  └── Web Operations Dashboard (static/index.html & static/js/app.js)
      ├── Executive Fleet & Sustainability KPI
      ├── Interactive Device Health & Telemetry Sparklines
      └── Prescriptive Maintenance Modal (Human-in-the-Loop)
```

---

## 3. Struktur Direktori Proyek

```
D:\AI-Based Electronic Failure Prediction\
├── .agents/skills/                    # Agent Skills (impeccable, addyosmani skills)
├── .gemini/skills/                    # Runtime Skills Mount
├── ai/
│   ├── data_generator.py             # Generator Hibrida Fisika Degradasi & Data Empiris
│   ├── feature_engineering.py        # Ekstraksi Fitur Fisika (TSI, FDE, Voltage Sag)
│   ├── model.py                      # LightGBM Regressor (RUL), Classifier, Conformal & TreeSHAP
│   ├── pipeline.py                   # Mesin Inferensi Batch Armada & Work Order Generator
│   └── weights/                      # Checkpoint Model (.pkl) & model_metadata.json
├── api/
│   ├── routes.py                     # Endpoint REST API (KPI, Devices, Work Orders, Ingest)
│   └── schemas.py                    # Skema Validasi Pydantic
├── core/
│   ├── database.py                   # Engine SQLite dengan mode WAL & Foreign Keys
│   └── seeder.py                     # Inisialisasi 120 Perangkat & 14.400 Log Telemetri
├── edge_agent/
│   └── client_daemon.py              # Agen Background Klien & Offline Buffer
├── static/
│   ├── css/style.css                 # Token Desain Impeccable (Dark Mode, Kontras Tinggi)
│   ├── js/app.js                     # Logika UI, SVG Sparkline Suhu, & Modal Teknisi
│   └── index.html                    # Antarmuka Dashboard Operasional Armada
├── tests/
│   ├── test_ai_pipeline.py           # Unit Test AI, SHAP, & Conformal Intervals
│   ├── test_api.py                   # Integration Test REST API & UI Serving
│   ├── test_database.py              # Unit Test Skema & Integritas Basis Data
│   └── test_edge_agent.py            # Unit Test Agen Edge & Buffering Offline
├── main.py                           # Entrypoint Server Produksi FastAPI
├── demo_simulation.py                # Skrip Simulasi End-to-End Siklus Hidup Sirkular
├── requirements.txt                  # Daftar Dependensi Python
├── pyrefly.toml                      # Konfigurasi Pemeriksa Tipe Pyrefly
├── pyrightconfig.json                # Konfigurasi Pyright
├── DOKUMEN_DESAIN_SISTEM_BASELINE_KASUS_23.md
└── SPESIFIKASI_TEKNIS_IMPLEMENTASI_KASUS_23.md
```

---

## 4. Panduan Menjalankan Sistem

### 4.1 Instalasi Dependensi
Pastikan Python 3.12 telah terpasang, lalu jalankan:
```powershell
py -3 -m pip install -r requirements.txt
```

### 4.2 Inisialisasi & Seeding Basis Data
Jalankan seeder untuk membuat basis data SQLite `electronic_fleet.db` dengan 120 perangkat armada dan 14.400 log telemetri deret waktu:
```powershell
py -3 core/seeder.py
```

### 4.3 Menjalankan Server Produksi
Jalankan server aplikasi (FastAPI + Uvicorn):
```powershell
py -3 -m uvicorn main:app --host 127.0.0.1 --port 8000
```
Layanan dapat diakses pada:
* **Dashboard Operasional Web:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
* **Dokumentasi API Interaktif (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Status Kesehatan Layanan:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 4.4 Menjalankan Agen Telemetri Edge di Klien
Untuk menjalankan pemantauan telemetri mandiri di laptop/PC klien:
```powershell
py -3 edge_agent/client_daemon.py --asset-tag LAP-0001 --interval 15
```

### 4.5 Menjalankan Demonstrasi Siklus Hidup Sirkular Lengkap
Untuk melihat simulasi otomatis perambatan degradasi termal, deteksi AI, atribusi TreeSHAP, intervensi fisik teknisi, hingga kalkulasi penghematan karbon dan limbah:
```powershell
py -3 demo_simulation.py
```

---

## 5. Ringkasan Endpoint REST API

| Metode | Endpoint | Deskripsi |
| :--- | :--- | :--- |
| `GET` | `/health` | Pemeriksaan kesehatan layanan & database |
| `GET` | `/api/v1/overview` | KPI agregat armada, distribusi risiko, dan metrik dampak sirkular |
| `GET` | `/api/v1/devices` | Daftar perangkat dengan pagination, pencarian tag, dan filter risiko |
| `GET` | `/api/v1/devices/{id}` | Detail lengkap perangkat, 60 log telemetri terbaru, dan nilai TreeSHAP |
| `GET` | `/api/v1/work-orders` | Antrean tiket kerja preskriptif yang menunggu tinjauan teknisi |
| `POST` | `/api/v1/work-orders/{id}/resolve` | Endpoint *Human-in-the-Loop* untuk konfirmasi fisik dan penutupan tiket |
| `POST` | `/api/v1/telemetry/ingest` | Gateway ingesti data telemetri berkala dari agen perangkat klien |
| `POST` | `/api/v1/pipeline/trigger` | Pemicu inferensi batch armada dan pembaruan tiket preskriptif |

---

## 6. Verifikasi Pengujian Otomatis

Seluruh modul telah diuji menggunakan `pytest` dengan 17 skenario pengujian komprehensif:
```powershell
py -3 -m pytest tests/
```
Hasil:
```text
tests/test_ai_pipeline.py ...                                            [ 17%]
tests/test_api.py .........                                              [ 70%]
tests/test_database.py ...                                               [ 88%]
tests/test_edge_agent.py ..                                              [100%]

======================== 17 passed in 7.35s ========================
```
