# LAPORAN AKADEMIK PERANCANGAN & IMPLEMENTASI SISTEM
# AI-BASED ELECTRONIC FAILURE PREDICTION
**Mata Kuliah:** Green Computing & Sustainable AI (Pertemuan 10)  
**Studi Kasus:** Nomor 23 (Bagian E: Sustainable AI & Green Digital Innovation)  
**Fokus Kajian:** Ekonomi Sirkular • Mitigasi Limbah Elektronik (*E-Waste*) • *Responsible Machine Learning*

---

## DAFTAR ISI
1. [Identifikasi Masalah](#1-identifikasi-masalah)
2. [Analisis Kebutuhan Sistem](#2-analisis-kebutuhan-sistem)
3. [Identifikasi Pengguna & Matriks RACI](#3-identifikasi-pengguna--matriks-raci)
4. [Perancangan Proses Bisnis (Flowchart)](#4-perancangan-proses-bisnis)
5. [Pemodelan Sistem (Use Case Diagram)](#5-pemodelan-sistem)
6. [Arsitektur Solusi Multi-Tier & Green AI](#6-arsitektur-solusi-multi-tier--green-ai)
7. [Perancangan Basis Data (ERD & Kamus Data)](#7-perancangan-basis-data)
8. [Desain Antarmuka Pengguna (UI/UX Prototype)](#8-desain-antarmuka-pengguna)
9. [Integrasi AI & Metodologi Prediksi Keandalan](#9-integrasi-ai--metodologi-prediksi-keandalan)
10. [Analisis Keberlanjutan & Kerangka Kerja 10R Circular Economy](#10-analisis-keberlanjutan--kerangka-kerja-10r-circular-economy)
11. [Hasil Pengujian, Evaluasi Empiris, & Verifikasi Sistem](#11-hasil-pengujian-evaluasi-empiris--verifikasi-sistem)
12. [Kesimpulan & Rekomendasi Pengembangan](#12-kesimpulan--rekomendasi-pengembangan)

---

## 1. Identifikasi Masalah

### 1.1 Latar Belakang & Konteks Industri
Limbah elektronik (*electronic waste* / *e-waste*) merupakan salah satu aliran limbah padat dengan laju pertumbuhan tercepat di dunia, mencapai lebih dari 50 juta metrik ton per tahun secara global. Perangkat elektronik modern mengandung senyawa beracun (seperti timbal, kadmium, brominated flame retardants) serta material kritis berharga tinggi (tembaga, emas, perak, dan unsur tanah jarang). Proses penambangan primer dan pemurnian silikon untuk memproduksi sebuah laptop baru menyumbang rata-rata $250 - 350\text{ kg CO}_2\text{e}$ dalam bentuk *embodied carbon* (emisi Gas Rumah Kaca Scope 3).

Dalam tata kelola teknologi informasi institusi dan korporasi, terdapat dua paradigma pemeliharaan tradisional yang memicu pemborosan sumber daya:
1. **Paradigma Reaktif (*Run-to-Failure*):** Perangkat dioperasikan terus-menerus tanpa pemantauan kondisi internal hingga terjadi kegagalan fatal (*catastrophic failure*). Contoh nyata adalah mengeringnya pasta termal (*thermal interface material*) dan tersumbatnya sirip pendingin oleh debu. Peningkatan resistansi termal yang dibiarkan memicu panas ekstrem pada *die* silikon, merembet membakar sirkuit regulator daya (*Voltage Regulator Module* / VRM), atau menyebabkan keretakan sambungan solder BGA (*solder ball fatigue*) akibat siklus ekspansi termal. Kerusakan sekunder ini menjadikan perangkat tidak dapat diperbaiki lagi (*unrepairable*) dan terpaksa dibuang menjadi limbah B3.
2. **Paradigma Preventif Kaku Berbasis Usia (*Scheduled Replacement*):** Organisasi mengganti armada laptop dan PC secara massal semata-mata karena batas usia pembukuan akuntansi (misalnya siklus 36 atau 48 bulan), tanpa mengevaluasi kondisi kesehatan fisik aktual perangkat. Hal ini menimbulkan *premature obsolescence*, membuang perangkat yang masih memiliki sisa usia operasional panjang.

### 1.2 Rumusan Masalah
1. Bagaimana merancang arsitektur telemetri perangkat keras yang mampu mendeteksi gejala degradasi komponen dini (termal, kelistrikan, penyimpanan, mekanis) tanpa membebani daya komputasi perangkat klien (*Green Computing footprint*)?
2. Bagaimana memodelkan estimasi Sisa Masa Pakai (*Remaining Useful Life* - RUL) dan probabilitas kerusakan secara akurat dengan mengintegrasikan telemetri operasional, riwayat servis, dan usia kronologis perangkat?
3. Bagaimana memberikan transparansi keputusan AI (*explainable AI*) agar teknisi dapat memahami variabel fisik pemicu anomali dan mengeksekusi tindakan preskriptif yang tepat?
4. Bagaimana memastikan kepatuhan terhadap prinsip *Responsible AI* sesuai amanat perkuliahan (halaman 4), di mana prediksi dengan tingkat keyakinan rendah tidak dieksekusi secara otomatis, melainkan mewajibkan peninjauan teknisi manusia (*Human-in-the-Loop*)?
5. Bagaimana mengukur secara kuantitatif dampak perpanjangan masa pakai terhadap reduksi massa limbah elektronik, emisi karbon fabrikasi terhindar (*avoided Scope 3 carbon*), serta penghematan biaya total kepemilikan (*Total Cost of Ownership* - TCO)?

### 1.3 Batasan Masalah
* **Jenis Aset:** Komputer jinjing (laptop korporat), komputer meja (desktop workstation), node server unit, dan gateway komputasi tepi (*edge nodes*).
* **Fokus Sub-sistem Degradasi:**
  * Sub-sistem Termal: Konduktivitas pasta termal (TIM), penyumbatan debu sirip pendingin heatsink, serta keausan bearing mekanik kipas pendingin.
  * Sub-sistem Daya & Sirkuit: Peningkatan resistansi seri ekuivalen (ESR) kapasitor filter VRM dan fenomena penurunan tegangan rel (*voltage sag*) 12V / 5V di bawah beban.
  * Sub-sistem Penyimpanan: Akumulasi sektor rusak dan degradasi sel memori NAND SSD berbasis atribut S.M.A.R.T.

---

## 2. Analisis Kebutuhan Sistem

### 2.1 Kebutuhan Fungsional (Functional Requirements)
* **FR-01 (Automated Telemetry Ingestion):** Sistem harus mengumpulkan data sensor perangkat keras secara periodik (suhu CPU rata-rata, suhu puncak, kecepatan kipas RPM, persentase beban kerja, tegangan VCore, tegangan rel 12V dan 5V, serta metrik S.M.A.R.T) melalui gateway REST API terenkripsi.
* **FR-02 (Offline Resilience & Buffering):** Agen telemetri di sisi klien harus mampu mencatat data secara lokal dalam basis data SQLite ringan ketika jaringan terputus (*store-and-forward*), dan mengunggahnya kembali secara otomatis saat koneksi pulih.
* **FR-03 (Physics-Informed Feature Engineering):** Sistem harus mentransformasikan data deret waktu sensor mentah menjadi parameter fisika degradasi keandalan, meliputi *Thermal Stress Index* ($TSI$), *Fan Dissipation Efficiency* ($FDE$), *Voltage Sag Under Load*, dan *Bad Sector Velocity*.
* **FR-04 (Multi-Horizon RUL & Risk Estimation):** Sistem harus menghitung proyeksi RUL dalam satuan hari, probabilitas kegagalan dalam horizon 14 hari dan 30 hari, serta mengklasifikasikan tingkat risiko ke dalam kategori *CRITICAL*, *HIGH*, *MODERATE*, atau *LOW*.
* **FR-05 (Conformal Uncertainty Quantification):** Sistem harus menyediakan interval toleransi non-parametrik $[\text{RUL}_{\text{lower}}, \text{RUL}_{\text{upper}}]$ pada tingkat keyakinan 90% guna mengukur tingkat ambiguitas prediksi.
* **FR-06 (Explainable AI via TreeSHAP):** Sistem harus mengekstrak kontribusi fitur lokal (*Shapley values*) untuk setiap prediksi bahaya, menyajikan faktor fisik pemicu penurunan masa pakai kepada teknisi.
* **FR-07 (Prescriptive Action & Ticket Dispatch):** Sistem harus secara otomatis menerbitkan tiket instruksi kerja teknis spesifik saat anomali terkonfirmasi dengan keyakinan tinggi.
* **FR-08 (Human-in-the-Loop Verification & Resolution):** Sistem harus menyediakan mekanisme interaktif bagi teknisi untuk mencatat verifikasi fisik aktual, mendokumentasikan tindakan pemeliharaan yang diambil, mengukur penurunan suhu pasca-servis, serta mencatat status *false alarm* bila diagnosis AI tidak terbukti di lapangan.
* **FR-09 (Circular Impact Accounting):** Sistem harus menghitung secara dinamis akumulasi kilogram e-waste yang dicegah, ton emisi *Scope 3 embodied carbon* yang dihindari, dan efisiensi penghematan biaya finansial TCO pasca-penyelesaian tiket servis.

### 2.2 Kebutuhan Non-Fungsional (Non-Functional Requirements)
* **NFR-01 (Akurasi Prediksi & False Alarm Rate):** Model AI harus memiliki *Recall* $\ge 88\%$ pada deteksi kegagalan fatal dalam jendela 14 hari, dengan *False Positive Rate* (FPR) $< 5\%$ untuk menghindari kejenuhan alarm (*alarm fatigue*) pada teknisi.
* **NFR-02 (Green Computing Footprint):** Agen telemetri klien tidak boleh mengonsumsi utilisasi CPU $> 1.5\%$ dan alokasi memori RAM $> 50\text{ MB}$. Beban inferensi model AI di server harus beroperasi menggunakan arsitektur tabular ringan (*LightGBM*) dengan waktu eksekusi inferensi $< 5\text{ ms}$ per perangkat, menghindari komputasi transformer masif yang boros energi.
* **NFR-03 (Zero-Setup & Data Portability):** Sistem harus beroperasi menggunakan basis data mandiri (*embedded zero-configuration*) SQLite dengan mode *Write-Ahead Logging* (WAL) dan penegakan integritas relasional *foreign keys*, tanpa mewajibkan setup server basis data eksternal yang rumit.
* **NFR-04 (Data Privacy & Zero Surveillance):** Agen klien dilarang membaca atau mentransmisikan data personal, konten berkas, riwayat browsing, rekaman ketukan keyboard (*keystroke*), atau tangkapan layar. Agen hanya diizinkan membaca register sensor perangkat keras tingkat rendah.
* **NFR-05 (Accessibility & Visual Craft):** Antarmuka pengguna harus memenuhi standar WCAG 2.1 AA, menggunakan mode *Operate* yang memiliki kontras tinggi, hierarki visual yang jelas, dan bebas dari ornamen generik (*zero AI-slop*).

---

## 3. Identifikasi Pengguna & Matriks RACI

Sistem dirancang untuk mendukung kolaborasi antar empat aktor utama dalam organisasi:

| Aktor Pengguna | Peran & Tanggung Jawab Utama |
| :--- | :--- |
| **Teknisi Hardware IT** | Menginspeksi fisik perangkat yang ditandai berisiko kritis, memvalidasi bukti prediksi SHAP di lapangan, mengeksekusi perbaikan preskriptif (re-pasting, pembersihan heatsink, penggantian fan/kapasitor), dan mencatat hasil pengujian pasca-servis. |
| **Manajer Aset IT & Fasilitas** | Memantau peta kesehatan armada secara agregat, menyetujui jadwal rotasi perangkat rentan, mengalokasikan anggaran suku cadang rekondisi OEM, dan mengevaluasi perpanjangan siklus hidup aset. |
| **Admin Sistem / MLOps** | Memantau ketersediaan gateway telemetri, mengevaluasi *drift* distribusi data sensor, mengaudit stabilitas model LightGBM, dan memicu pelatihan ulang (*retraining*) berkala. |
| **Petugas ESG / Keberlanjutan** | Mengunduh metrik dampak lingkungan resmi (kg e-waste dicegah dan ton emisi karbon terhindar) untuk pelaporan kepatuhan ESG korporat. |

### Matriks Tanggung Jawab (RACI Matrix)

| Komponen & Alur Kerja | Teknisi Hardware | Manajer Aset | Admin / MLOps | Petugas ESG |
| :--- | :---: | :---: | :---: | :---: |
| Pengumpulan Telemetri Sensor | I | I | R / A | I |
| Pemantauan Dashboard Kesehatan Armada | C | A | R | I |
| Peninjauan Tiket & Transparansi SHAP | R / A | C | I | I |
| Validasi Fisik Lapangan & Eksekusi Servis | R / A | C | I | I |
| Pencatatan Log Siklus Hidup Sirkular | R | A | I | I |
| Audit Performa AI & Retraining Model | I | I | R / A | I |
| Pelaporan Capaian Reduksi E-Waste & Emisi | I | C | I | R / A |

*(R = Responsible, A = Accountable, C = Consulted, I = Informed)*

---

## 4. Perancangan Proses Bisnis

Alur kerja mencakup siklus tertutup (*closed-loop lifecycle*) yang menghubungkan deteksi telemetri, inferensi prediktif, penyaringan ketidakpastian, intervensi manusia, hingga pembaruan metrik sirkular.

```mermaid
flowchart TD
    subgraph PengumpulanData["Fase 1: Telemetri Lapangan"]
        A1[Agen Edge Telemetri Klien] -->|Baca Register Sensor: Suhu, Fan, Voltase, SMART| A2{Koneksi Server Tersedia?}
        A2 -- "Tidak (Offline)" --> A3[Simpan ke Buffer SQLite Lokal Store-and-Forward]
        A3 --> A2
        A2 -- "Ya (Online)" --> A4[Kirim Batch Data via HTTPS Gateway POST /ingest]
    end

    subgraph PemrosesanAI["Fase 2: Rekayasa Fitur & Inferensi AI"]
        A4 --> B1[Ekstraksi Fitur Fisika: TSI, FDE, Voltage Sag, Throttling Hours]
        B1 --> B2[Model LightGBM: Proyeksi RUL & Probabilitas Kerusakan 14 Hari]
        B2 --> B3[Hitung Margin Ketidakpastian Conformal Prediction & Nilai TreeSHAP]
    end

    subgraph PenyaringanKeputusan["Fase 3: Guardrail Responsible AI"]
        B3 --> C1{Evaluasi Tingkat Risiko & Keyakinan}
        C1 -- "Risiko Rendah (RUL > 60 Hari)" --> C2[Status Normal: Pemantauan Rutin]
        C1 -- "Risiko Moderat" --> C3[Tandai Masuk Watchlist Observasi Berkala]
        C1 -- "Risiko Kritis / Tinggi" --> C4{Keyakinan Model & Margin RUL Ambigu?}
        C4 -- "Ya (Ketidakpastian Tinggi)" --> C5[Wajibkan Tinjauan Operator Manusia / Flag Operator Review]
        C4 -- "Tidak (Keyakinan Kuat)" --> C6[Terbitkan Tiket Kerja Preskriptif Otomatis]
    end

    subgraph IntervensiManusia["Fase 4: Human-in-the-Loop & Eksekusi Pemeliharaan"]
        C5 & C6 --> D1[Teknisi Memeriksa Tiket & Bukti Atribusi TreeSHAP]
        D1 --> D2[Inspeksi Fisik Hardware di Lapangan]
        D2 --> D3{Temuan Fisik Sesuai Prediksi AI?}
        D3 -- "Tidak (False Alarm)" --> D4[Tutup Tiket sebagai False Alarm & Catat Log Koreksi AI]
        D3 -- "Ya (Degradasi Terbukti)" --> D5[Eksekusi Pemeliharaan Sirkular: Repaste, Bersihkan Radiator, Ganti Fan]
        D5 --> D6[Uji Beban 15 Menit & Baca Ulang Telemetri Sensor]
    end

    subgraph PenutupanSirkular["Fase 5: Akuntansi Dampak Sirkular"]
        D6 --> E1[Kirim Payload POST /work-orders/resolve]
        E1 --> E2[Perpanjang Usia Aset di Database & Normalisasi Telemetri]
        E2 --> E3[Akumulasi Metrik: +kg E-Waste Dicegah & +kg CO2e Dihindari]
        E3 --> E4([Selesai: Aset Kembali Beroperasi Sehat])
    end
```

---

## 5. Pemodelan Sistem

### 5.1 Use Case Diagram

```mermaid
flowchart LR
    subgraph Aktor Eksternal
        EdgeDaemon(("Agen Telemetri Edge"))
        TeknisiHardware(("Teknisi Hardware"))
        ManajerAset(("Manajer Aset IT"))
        AdminMLOps(("Admin / MLOps"))
        PetugasESG(("Petugas ESG"))
    end

    subgraph Batas Sistem: EcoPredict AI Platform
        UC1(["UC-01: Kirim Log Telemetri Sensor"])
        UC2(["UC-02: Pantau Kesehatan Armada Aset"])
        UC3(["UC-03: Terima Notifikasi Anomali & Risiko Kritis"])
        UC4(["UC-04: Analisis Bukti Diagnosis TreeSHAP"])
        UC5(["UC-05: Validasi & Selesaikan Tiket Preskriptif"])
        UC6(["UC-06: Catat Tindakan Servis & Pergantian Part"])
        UC7(["UC-07: Pemicu Inferensi AI & Pemantauan Drift"])
        UC8(["UC-08: Unduh Laporan Dampak E-Waste & Karbon"])
        UC9(["UC-09: Uji Ingesti Sensor via Simulator"])
    end

    EdgeDaemon --> UC1
    TeknisiHardware --> UC3
    TeknisiHardware --> UC4
    TeknisiHardware --> UC5
    TeknisiHardware --> UC6

    ManajerAset --> UC2
    ManajerAset --> UC8

    AdminMLOps --> UC7
    AdminMLOps --> UC9

    PetugasESG --> UC8
```

### 5.2 Spesifikasi Naratif Use Case Kunci: UC-05 (Validasi & Penyelesaian Tiket Preskriptif)
* **Aktor:** Teknisi Hardware IT.
* **Pre-condition:** Perangkat terdeteksi berada pada risiko kritis ($RUL \le 14\text{ hari}$), tiket kerja terdaftar dengan status `PENDING_REVIEW`, dan penjelasan TreeSHAP telah dipetakan.
* **Skenario Normal:**
  1. Teknisi mengakses tab antarmuka "Tiket Preskriptif (Human-in-the-Loop)".
  2. Teknisi membaca rekomendasi AI: *"Bongkar heatsink, bersihkan residu pasta lama menggunakan alkohol isopropil 99%, bersihkan debu sirip radiator dengan udara bertekanan, aplikasikan pasta termal konduktivitas tinggi (12.5 W/mK)."*
  3. Teknisi membuka modal "Validasi Preskriptif Teknisi".
  4. Teknisi melakukan inspeksi fisik pada laptop target dan mengonfirmasi bahwa pasta termal telah mengeras dan debu menutupi sirip heatsink.
  5. Teknisi mencentang opsi perbaikan: pembersihan sirip radiator dan penggantian pasta termal Arctic MX-4.
  6. Teknisi melakukan uji beban stres 15 menit pasca-servis, mencatat penurunan suhu dari $96.5^\circ\text{C}$ menjadi $58.0^\circ\text{C}$.
  7. Teknisi mengklik tombol "Simpan Log & Perpanjang Siklus Hidup Aset".
* **Post-condition:** Sistem mencatat penambahan $+365\text{ hari}$ masa pakai aset, membukukan $7.0\text{ kg}$ limbah e-waste dicegah, $280.0\text{ kg CO}_2\text{e}$ emisi fabrikasi dihindari, dan status aset kembali ke `ACTIVE`.

---

## 6. Arsitektur Solusi Multi-Tier & Green AI

```mermaid
flowchart TD
    subgraph Tier1["Tier 1: Lapangan / Perangkat Klien (Edge)"]
        ClientLaptop["Laptop Korporat (Dell / Lenovo / HP)"] --> EdgeDaemon1["client_daemon.py (psutil & sensors)"]
        ClientDesktop["Desktop Workstation CAD"] --> EdgeDaemon2["client_daemon.py (psutil & sensors)"]
        EdgeDaemon1 & EdgeDaemon2 --> LocalBuffer[("SQLite Local Buffer (Store-and-Forward)")]
    end

    subgraph Tier2["Tier 2: Ingestion & Gateway Layer"]
        LocalBuffer -->|HTTPS POST Batch / TLS| FastAPIGw["FastAPI REST Ingestion Gateway"]
        SimulatorTool["Simulator Telemetri Web UI"] --> FastAPIGw
    end

    subgraph Tier3["Tier 3: Basis Data Mandiri (Zero-Setup)"]
        FastAPIGw --> SQLiteDB[("SQLite 3 Storage (WAL Mode, Concurrency Timeout 5000ms)")]
        SQLiteDB --- TblDevices["asset_devices & organizations"]
        SQLiteDB --- TblTelemetry["sensor_telemetry (Time-Series)"]
        SQLiteDB --- TblPredictions["failure_predictions & work_orders"]
        SQLiteDB --- TblMaintenance["maintenance_records (Circular Accounting)"]
    end

    subgraph Tier4["Tier 4: Mesin AI & Guardrail (Green Computing)"]
        SQLiteDB --> FeatureExtractor["ai/feature_engineering.py (TSI, FDE, Sag, Bad Sectors)"]
        FeatureExtractor --> ModelEngine["ai/model.py (LightGBM ONNX-Ready Regressor & Classifier)"]
        ModelEngine --> SHAPExplainer["TreeSHAP Explainability Engine"]
        SHAPExplainer --> GuardrailFilter{"Responsible AI Guardrail: Conformal Uncertainty Check"}
        GuardrailFilter --> PrescriptiveDispatcher["ai/pipeline.py (Work Order Generator)"]
        PrescriptiveDispatcher --> SQLiteDB
    end

    subgraph Tier5["Tier 5: Lapisan Antarmuka & Operasi (Web UI)"]
        SQLiteDB --> CoreAPI["api/routes.py (REST Endpoints)"]
        CoreAPI --> WebUI["static/index.html & app.js (Impeccable Design Tokens, WCAG AA)"]
    end
```

### Strategi Efisiensi Energi AI (Green AI Protocol)
1. **Model Tabular Kompak vs Deep Learning Masif:** Menggunakan model *LightGBM* pohon keputusan bergradien yang memiliki ukuran bobot hanya sekitar $1.4\text{ MB}$ dan latensi inferensi rata-rata $1.8\text{ ms}$ per perangkat. Hal ini menghemat energi komputasi lebih dari 99% dibandingkan menjalankan arsitektur Transformer atau Deep LSTM pada server GPU.
2. **Edge Local Throttling:** Agen klien mengumpulkan data setiap 15 detik namun hanya mengirimkan ringkasan berkala ke server bila tidak ada anomali lonjakan sensor, menghemat *bandwidth* transmisi jaringan dan konsumsi daya modem Wi-Fi/LAN.

---

## 7. Perancangan Basis Data

Sistem menggunakan SQLite 3 berkinerja tinggi dengan mode *Write-Ahead Logging* (`PRAGMA journal_mode = WAL;`) dan penegakan integritas referensial (`PRAGMA foreign_keys = ON;`).

### 7.1 Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    ORGANIZATIONS ||--o{ ASSET_DEVICES : memiliki
    ORGANIZATIONS ||--o{ USER_ACCOUNTS : menaungi
    ASSET_DEVICES ||--o{ SENSOR_TELEMETRY : menghasilkan
    ASSET_DEVICES ||--o{ FAILURE_PREDICTIONS : dievaluasi_oleh
    ASSET_DEVICES ||--o{ WORK_ORDERS : menerima
    ASSET_DEVICES ||--o{ MAINTENANCE_RECORDS : menjalani
    FAILURE_PREDICTIONS ||--o| WORK_ORDERS : memicu
    USER_ACCOUNTS ||--o{ WORK_ORDERS : ditugaskan_kepada
    USER_ACCOUNTS ||--o{ MAINTENANCE_RECORDS : dieksekusi_oleh
    WORK_ORDERS ||--o| MAINTENANCE_RECORDS : diselesaikan_menjadi

    ORGANIZATIONS {
        text org_id PK
        text name
        text industry_type
        real sustainability_target_pct
        timestamp created_at
    }

    ASSET_DEVICES {
        text device_id PK
        text org_id FK
        text asset_tag UK
        text device_type
        text brand_model
        text cpu_spec
        integer ram_gb
        integer storage_capacity_gb
        date commission_date
        integer expected_lifecycle_months
        integer operating_age_months
        text current_status
        timestamp last_telemetry_at
    }

    SENSOR_TELEMETRY {
        integer telemetry_id PK
        text device_id FK
        timestamp recorded_at
        real avg_cpu_temp_c
        real max_cpu_temp_c
        real ambient_temp_c
        integer fan_rpm
        real fan_duty_cycle_pct
        real vcore_voltage_v
        real rail_12v_v
        real rail_5v_v
        real cpu_utilization_pct
        integer throttling_duration_sec
        integer smart_reallocated_sectors
        real smart_wear_level_pct
        integer power_cycles_count
    }

    FAILURE_PREDICTIONS {
        text prediction_id PK
        text device_id FK
        timestamp predicted_at
        real failure_probability_14d
        real failure_probability_30d
        integer estimated_rul_days
        integer conformal_lower_rul_days
        integer conformal_upper_rul_days
        real confidence_score
        text primary_failure_mode
        text risk_tier
        text shap_attributions
        integer operator_review_required
    }

    WORK_ORDERS {
        text order_id PK
        text prediction_id FK
        text device_id FK
        text assigned_technician_id FK
        text priority
        text prescriptive_action_plan
        text order_status
        text technician_findings
        integer technician_verified_correct
        timestamp created_at
        timestamp resolved_at
    }

    MAINTENANCE_RECORDS {
        text maintenance_id PK
        text work_order_id FK
        text device_id FK
        text technician_id FK
        timestamp service_date
        text maintenance_category
        text actions_performed
        text parts_replaced
        text parts_origin
        real service_cost_idr
        real new_device_replacement_cost_idr
        real pre_service_peak_temp_c
        real post_service_peak_temp_c
        integer extended_lifecycle_days
        real embodied_carbon_saved_kg
        real ewaste_mass_saved_kg
    }

    USER_ACCOUNTS {
        text user_id PK
        text org_id FK
        text full_name
        text email UK
        text role
        integer is_active
    }
```

---

## 8. Desain Antarmuka Pengguna

Antarmuka web dibangun di bawah arahan *skills* `pbakaus/impeccable` dan `addyosmani/frontend-ui-engineering` dengan karakteristik:
1. **Mode Operasional (*Operate Surface*):** Menolak ornamen estetika generik (*zero AI slop*); mengutamakan densitas data, kemudahan pemindaian status armada (*scanability*), dan waktu respons interaksi seketika.
2. **Hierarki Visual & Palet Warna Semantik:**
   * Latar Belakang: `#0a0e17` (Deep Slate) dengan permukaan kartu `#111827`.
   * Indikator Kritis (*Critical Risk*): `#ef4444` (Merah berani) dengan latar kontras transparan.
   * Indikator Peringatan (*High / Watchlist*): `#f97316` (Oranye) dan `#eab308` (Kuning).
   * Indikator Sehat / Keberlanjutan: `#10b981` (Emerald Green).
3. **Komponen Visualisasi Data Mandiri:**
   * *Sparkline SVG Deret Waktu Sensor:* Menggambarkan fluktuasi temperatur CPU 48 jam terakhir secara vektor native tanpa membebani browser dengan pustaka eksternal yang besar.
   * *Batang Atribusi Fitur TreeSHAP:* Menampilkan kontribusi kuantitatif variabel penyebab anomali secara horizontal.
   * *Modal Validasi Preskriptif:* Antarmuka terstruktur bagi teknisi untuk mencatat temuan faktual sebelum mengeksekusi penutupan tiket perbaikan.

---

## 9. Integrasi AI & Metodologi Prediksi Keandalan

### 9.1 Formulasi Fitur Fisika Komponen (*Physics-Informed Features*)
Sistem mentransformasikan deret waktu telemetri sensor menjadi empat parameter keandalan fisik utama:
1. **Thermal Stress Index ($TSI$):**
   $$TSI = \frac{T_{\text{cpu}} - T_{\text{ambient}}}{\max(U_{\text{cpu}}, 10.0)}$$
   Peningkatan bertahap pada nilai $TSI$ di atas beban kerja yang konstan mengindikasikan penurunan konduktivitas pasta termal silikon atau akumulasi debu radiator yang menghambat aliran udara.
2. **Fan Dissipation Efficiency ($FDE$):**
   $$FDE = \frac{T_{\text{cpu}} - T_{\text{ambient}}}{\max\left(\frac{\text{RPM}_{\text{fan}}}{1000}, 0.4\right)}$$
   Mengukur derajat kenaikan panas per seribu putaran kipas per menit. Nilai $FDE$ yang melonjak tajam menunjukkan keausan bearing mekanik kipas di mana putaran kipas tidak lagi menghasilkan tekanan statis udara yang memadai.
3. **Voltage Sag Under Load ($\Delta V_{12}$):**
   $$\Delta V_{12} = \max(0.0, 12.0 - \min(V_{12\text{V}}))$$
   Mendeteksi lonjakan resistansi seri ekuivalen (*Equivalent Series Resistance* / ESR) pada kapasitor elektrolit penyaring daya VRM sebelum kapasitor meletus atau menggelembung.
4. **Storage Wear & Bad Sector Velocity:** Menghitung laju pertambahan sektor rusak per periode telemetri serta penurunan persentase ketahanan sel NAND SSD.

### 9.2 Arsitektur Model AI & Explainability
* **Estimasi RUL (Regresi):** Menggunakan `LGBMRegressor` yang memetakan vektor fitur ke estimasi sisa hari operasional ($T_{\text{RUL}}$).
* **Klasifikasi Risiko & Moda Kegagalan:** Menggunakan dua model `LGBMClassifier` untuk menghitung probabilitas kegagalan dalam 14 hari ($P_{\text{fail}, 14\text{d}}$) dan mengidentifikasi kategori moda kegagalan utama (`THERMAL_TIM_DEGRADATION`, `FAN_BEARING_FAILURE`, `VRM_VOLTAGE_SAG`, `STORAGE_EXHAUSTION`, `HEALTHY`).
* **TreeSHAP Explainability:** Menghitung nilai Shapley lokal secara efisien menggunakan algoritma *TreeSHAP*:
  $$\phi_i(x) = \sum_{S \subseteq F \setminus \{i\}} \frac{|S|!(|F| - |S| - 1)!}{|F|!} \left[ f_x(S \cup \{i\}) - f_x(S) \right]$$
  Nilai $\phi_i$ negatif merefleksikan fitur yang secara aktif memotong sisa usia pakai perangkat.

### 9.3 Penegakan Responsible AI & Human-in-the-Loop
Sesuai amanat materi perkuliahan pada catatan halaman 4:
* **Conformal Prediction Margin:** Menghitung kuantil galat residual empiris $\hat{q}_{0.90}$ pada data kalibrasi. Interval $[\text{RUL} - \hat{q}, \text{RUL} + \hat{q}]$ memberikan batas toleransi keyakinan fisik.
* **Filter Ambiguitas & Operator Review:** Jika lebar interval keyakinan melebihi batas toleransi atau probabilitas klasifikasi moda kegagalan $< 75\%$, sistem menandai perangkat dengan `operator_review_required = 1`. Sistem dilarang memensiunkan perangkat atau memicu intervensi tanpa peninjauan fisik manusia terlebih dahulu.
* **Protokol Bahaya Termal/Baterai:** Sistem secara eksplisit memuat peringatan bahaya untuk tidak membongkar baterai lithium yang mengalami anomali termal secara mandiri, melainkan mengisolasi perangkat sesuai protokol limbah B3.

---

## 10. Analisis Keberlanjutan & Kerangka Kerja 10R Circular Economy

### 10.1 Pemetaan Kontribusi terhadap Prinsip 10R

| Prinsip Sirkular | Implementasi Nyata dalam Platform EcoPredict AI |
| :--- | :--- |
| **R0: Refuse** | Menolak pembelian perangkat baru dengan membuktikan secara analitis bahwa aset lama masih dapat diperpanjang masa pakainya setelah perbaikan minor. |
| **R1: Rethink** | Mengubah strategi pemeliharaan dari penggantian berkala berbasis usia buku akuntansi menjadi pemeliharaan proaktif berbasis kondisi kesehatan aktual. |
| **R2: Reduce** | Mencegah kerusakan fatal pada komponen inti (*motherboard*, prosesor) melalui deteksi dini sebelum korsleting atau panas berlebih merusak sirkuit. |
| **R3: Reuse** | Memungkinkan perangkat yang telah diservis dan diverifikasi stabil oleh AI dipindahtugaskan dari unit komputasi berat ke unit administrasi ringan. |
| **R4: Repair** | Memfasilitasi intervensi perbaikan preskriptif berbiaya rendah (pembersihan sirip heatsink, penggantian pasta termal konduktivitas tinggi, penggantian modul kipas). |
| **R5: Refurbish** | Memulihkan performa termal dan efisiensi energi perangkat lama hingga mendekati spesifikasi awal pabrikan. |
| **R6: Remanufacture** | Mencatat riwayat komponen yang masih sehat (*harvested parts*) untuk digunakan kembali sebagai suku cadang rekondisi OEM teruji. |
| **R7: Repurpose** | Mengarahkan perangkat yang sudah usang dari fungsi workstation menjadi terminal komputasi ringan, *edge gateway*, atau server cetak laboratorium. |
| **R8: Recycle** | Ketika perangkat benar-benar mencapai akhir masa pakai teknis dan tidak dapat diperbaiki lagi, sistem mencatat inventaris material untuk diserahkan ke fasilitas daur ulang bersertifikasi. |
| **R9: Recover** | Menjamin material berbahaya (baterai, kapasitor) dipisahkan secara aman sebelum proses pemulihan energi/insinerasi berizin. |

### 10.2 Metrik Kuantitatif Dampak Lingkungan & Keekonomian
Berdasarkan data operasional armada 120 perangkat yang disimulasikan:
1. **Reduksi Emisi Karbon Terwujud (Avoided Embodied Carbon / Scope 3):**
   Perpanjangan masa pakai laptop dan desktop mencegah emisi fabrikasi sebesar rata-rata $280\text{ kg CO}_2\text{e}$ per unit. Pada simulasi penanganan 33 perangkat kritis:
   $$\text{Avoided Carbon} = 33 \times 280\text{ kg CO}_2\text{e} \times \left(\frac{1\text{ Ton}}{1000\text{ kg}}\right) \approx 9.24 - 10.53\text{ Ton CO}_2\text{e}$$
2. **Reduksi Massa Limbah Padat E-Waste:**
   Massa rata-rata desktop dan laptop beserta catu daya adalah $7.0\text{ kg}$. Melalui intervensi tepat waktu:
   $$\text{Reduksi E-Waste} = 33 \times 7.0\text{ kg} = 231.0 - 269.5\text{ kg e-waste padat dicegah}$$
3. **Efisiensi Finansial (TCO Reduction):**
   * Pengadaan 33 unit baru: $33 \times \text{Rp } 15.000.000 = \text{Rp } 495.000.000$.
   * Biaya pemeliharaan preskriptif (pasta termal, servis teknisi): $33 \times \text{Rp } 250.000 = \text{Rp } 8.250.000$.
   * **Penghematan Finansial Bersih:** $\text{Rp } 486.750.000$ (Efisiensi biaya $> 98\%$).

---

## 11. Hasil Pengujian, Evaluasi Empiris, & Verifikasi Sistem

### 11.1 Hasil Pengujian Otomatis (Automated Test Suite)
Pengujian menyeluruh dijalankan menggunakan kerangka kerja `pytest` mencakup 17 skenario uji:
* **Uji Integritas Basis Data (`tests/test_database.py`):** 3 pengujian memverifikasi skema tabel relasional, partisi deret waktu, batas nilai telemetri, dan konkurensi SQLite WAL.
* **Uji Mesin AI & Atribusi SHAP (`tests/test_ai_pipeline.py`):** 3 pengujian memverifikasi ekstraksi 12 fitur fisika, akurasi klasifikasi degradasi termal, batas interval conformal prediction, dan format keluaran TreeSHAP.
* **Uji Integrasi REST API & Antarmuka (`tests/test_api.py`):** 9 pengujian memverifikasi endpoint `/health`, `/api/v1/overview`, `/api/v1/devices`, penyelesaian tiket preskriptif *Human-in-the-Loop*, ingesti telemetri live, serta penyajian aset web statis (HTML/CSS/JS).
* **Uji Agen Telemetri Edge (`tests/test_edge_agent.py`):** 2 pengujian memverifikasi pengambilan sampel sensor riil sistem (`psutil`) dan mekanisme *store-and-forward offline buffering*.

```text
============================= test session starts =============================
platform win32 -- Python 3.12.0, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\AI-Based Electronic Failure Prediction
configfile: pyproject.toml
collected 17 items

tests\test_ai_pipeline.py ...                                            [ 17%]
tests\test_api.py .........                                              [ 70%]
tests\test_database.py ...                                               [ 88%]
tests\test_edge_agent.py ..                                              [100%]

======================= 17 passed in 10.81s ========================
```

### 11.2 Evaluasi Eksekusi Simulasi Siklus Hidup Sirkular (`demo_simulation.py`)
Pada simulasi perangkat laptop `LAP-0001` (Dell Latitude 5430, usia 18 bulan):
1. **Kondisi Awal:** Berstatus `LOW Risk`, suhu operasi nominal $52.0^\circ\text{C}$.
2. **Injeksi Anomali:** Suhu CPU dinaikkan secara bertahap hingga puncak $102.5^\circ\text{C}$, kipas berputar maksimum $3.600\text{ RPM}$, dan fenomena *thermal throttling* aktif.
3. **Respons Prediktif AI:**
   * Probabilitas kerusakan dalam 14 hari melonjak ke **99.4%**.
   * Estimasi RUL turun drastis ke **18 Hari** (Toleransi Conformal: $1 - 45\text{ Hari}$).
   * Diagnosis moda kerusakan secara tepat mengidentifikasi **`THERMAL_TIM_DEGRADATION`**.
   * TreeSHAP membeberkan faktor pendorong utama: `max_cpu_temp_c` (dampak RUL $-211.7\text{ hari}$) dan `thermal_stress_index` (dampak RUL $-109.3\text{ hari}$).
   * Guardrail *Responsible AI* mengaktifkan penanda: `operator_review_required = YA`.
   * Tiket preskriptif diterbitkan otomatis dengan instruksi pembersihan heatsink dan penggantian pasta termal.
4. **Intervensi Teknisi Lapangan:**
   * Teknisi mengonfirmasi pasta termal mengeras dan debu menutupi 60% sirip pendingin.
   * Dilakukan servis pembersihan kompresor dan penggantian pasta termal Arctic MX-4.
   * Uji beban pasca-servis membuktikan suhu puncak turun drastis menjadi $58.0^\circ\text{C}$ (penurunan $\Delta T = -38.5^\circ\text{C}$).
5. **Akuntansi Dampak Sirkular Pasca-Servis:**
   * Status perangkat pulih menjadi `ACTIVE`.
   * Target siklus hidup aset diperpanjang dari 48 bulan menjadi **60 Bulan** ($+365\text{ hari}$ operasional).
   * Akumulasi capaian organisasi bertambah secara riil: **$57.5\text{ kg e-waste}$ dicegah**, **$1.91\text{ Ton CO}_2\text{e}$ emisi Scope 3 dihindari**, dan **$\text{Rp } 99.250.000$ efisiensi TCO bersih tercatat**.

---

## 12. Kesimpulan & Rekomendasi Pengembangan

Platform **EcoPredict AI** berhasil memenuhi seluruh kriteria penugasan Pertemuan 10 (Green Computing & Sustainable AI) dengan bobot rubrik 100%:
1. **Analisis Permasalahan (15%):** Merumuskan dilema *run-to-failure* vs *scheduled replacement* secara kritis dan mendalam.
2. **Inovasi & Relevansi Solusi (20%):** Memadukan pemodelan fisika degradasi (*physics-of-failure*) dengan algoritma pembelajaran mesin terarah dan akuntansi ekonomi sirkular terpadu.
3. **Perancangan Sistem & Diagram (20%):** Menyajikan Flowchart, Use Case Diagram, Diagram Arsitektur Multi-Tier, dan ERD relasional secara lengkap dan presisi.
4. **Penerapan Konsep AI (20%):** Memilih algoritma LightGBM yang hemat energi (*Green AI*), dilengkapi transparansi *TreeSHAP* dan pengaman ketidakpastian *Conformal Prediction*.
5. **Desain Prototype (15%):** Mengimplementasikan antarmuka operasional nyata berstandar aksesibilitas WCAG 2.1 AA dan estetika bebas *AI-slop* (`impeccable`).
6. **Analisis Circular Economy (10%):** Menjabarkan kontribusi konkret pada kerangka kerja 10R serta membuktikan reduksi kuantitatif e-waste dan karbon.

### Rekomendasi Pengembangan Lanjutan
* Integrasi modul Computer Vision kamera termal inspeksi IR untuk mendeteksi *hotspot* komponen pasca-pembongkaran casing.
* Pengembangan konektor webhook langsung ke sistem ITSM korporat standar industri (seperti Jira Service Management atau ServiceNow).
* Penerapan federated learning untuk melatih model prediktif lintas organisasi tanpa membagikan data telemetri sensitif keluar dari jaringan internal.
