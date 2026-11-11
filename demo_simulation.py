"""
demo_simulation.py
End-to-End Circular Economy Lifecycle Simulation for Case 23:
AI-Based Electronic Failure Prediction & Prescriptive Maintenance.

Demonstrates:
1. Nominal baseline operation
2. Thermal degradation progression (paste drying & dust clogging)
3. AI Predictive Detection & TreeSHAP Root-Cause Attribution
4. Responsible AI Guardrail & Human-in-the-Loop Work Order Triage
5. Physical Intervention & Telemetry Normalization
6. Real-time Circular Economy Impact Accounting (CO2e, E-waste, TCO)
"""

import sys
import json
import time
from datetime import datetime, timedelta
from core.database import get_db_session, get_db_path
from ai.pipeline import run_fleet_inference
from api.routes import resolve_work_order
from api.schemas import ResolveWorkOrderPayload


def print_step(title: str):
    print("\n" + "=" * 80)
    print(f">> {title.upper()}")
    print("=" * 80)


def run_demo():
    print_step("Inisialisasi Demonstrasi Siklus Hidup Sirkular (Studi Kasus 23)")
    
    target_tag = "LAP-0005"
    with get_db_session() as conn:
        device = conn.execute("""
            SELECT device_id, asset_tag, brand_model, current_status, operating_age_months
            FROM asset_devices
            WHERE asset_tag = ?;
        """, (target_tag,)).fetchone()
        
        if not device:
            # Fallback to first available laptop
            device = conn.execute("SELECT device_id, asset_tag, brand_model, current_status, operating_age_months FROM asset_devices WHERE device_type = 'LAPTOP' LIMIT 1;").fetchone()
            target_tag = device["asset_tag"]

    dev_id = device["device_id"]
    print(f"Target Perangkat Terpilih : {device['asset_tag']} ({device['brand_model']})")
    print(f"Usia Operasional          : {device['operating_age_months']} Bulan")
    print(f"Status Awal               : {device['current_status']}")

    # 1. Simulasikan Degradasi Termal Akut (Pasta Termal Mengering & Debu Menumpuk)
    print_step(f"Tahap 1: Injeksi Degradasi Termal Progresif pada {target_tag}")
    print("Mensimulasikan pengeringan pasta termal (Arrhenius) & penyumbatan sirip heatsink...")
    
    now = datetime.now()
    degraded_records = []
    for step in range(8):
        rec_time = (now - timedelta(hours=(8 - step) * 6)).strftime("%Y-%m-%d %H:%M:%S")
        temp = 72.0 + (step * 3.5)  # Meningkat hingga 96.5 C
        fan_rpm = int(2200 + (step * 200)) # Kipas dipaksa berputar kencang tapi suhu tetap panas
        throttling = 300 if temp > 88.0 else 0
        
        degraded_records.append((
            dev_id, rec_time, temp, temp + 6.0, 24.0, fan_rpm, 100.0,
            1.25, 11.96, 5.01, 75.0, throttling, 0, 95.0, 150 + step
        ))

    with get_db_session() as conn:
        conn.executemany("""
            INSERT INTO sensor_telemetry (
                device_id, recorded_at, avg_cpu_temp_c, max_cpu_temp_c, ambient_temp_c,
                fan_rpm, fan_duty_cycle_pct, vcore_voltage_v, rail_12v_v, rail_5v_v,
                cpu_utilization_pct, throttling_duration_sec, smart_reallocated_sectors,
                smart_wear_level_pct, power_cycles_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, degraded_records)
    print(f"-> Berhasil menginjeksi 8 jendela telemetri anomali (Suhu Puncak: 102.5 C, Throttling Aktif).")

    # 2. Jalankan Inferensi Batch AI
    print_step("Tahap 2: Eksekusi Mesin Inferensi AI & Guardrail Responsible AI")
    summary = run_fleet_inference()
    print("Hasil Pemindaian Armada AI:")
    print(f"- Total Perangkat Diproses   : {summary['processed_devices']}")
    print(f"- Terdeteksi Risiko Kritis   : {summary['critical_count']}")
    print(f"- Tiket Preskriptif Dibuat   : {summary['work_orders_created']}")

    # 3. Analisis Hasil Prediksi & Bukti TreeSHAP
    print_step(f"Tahap 3: Tinjauan Diagnosis Prediktif & Atribusi TreeSHAP ({target_tag})")
    with get_db_session() as conn:
        pred = conn.execute("""
            SELECT * FROM failure_predictions
            WHERE device_id = ?
            ORDER BY predicted_at DESC LIMIT 1;
        """, (dev_id,)).fetchone()
        
        wo = conn.execute("""
            SELECT * FROM work_orders
            WHERE device_id = ? AND order_status IN ('PENDING_REVIEW', 'CONFIRMED')
            ORDER BY created_at DESC LIMIT 1;
        """, (dev_id,)).fetchone()

    print(f"Tingkat Risiko Terkini       : {pred['risk_tier']}")
    print(f"Probabilitas Rusak (14 Hari) : {pred['failure_probability_14d'] * 100:.1f}%")
    print(f"Estimasi Sisa Umur (RUL)     : {pred['estimated_rul_days']} Hari (Toleransi: {pred['conformal_lower_rul_days']} - {pred['conformal_upper_rul_days']} Hari)")
    print(f"Diagnosis Moda Kerusakan     : {pred['primary_failure_mode']}")
    print(f"Skor Keyakinan Model         : {pred['confidence_score'] * 100:.1f}%")
    print(f"Tinjauan Operator Wajib      : {'YA (Human-in-the-Loop Diaktifkan)' if pred['operator_review_required'] else 'TIDAK'}")
    
    print("\nFaktor Pendorong Kerusakan Menurut TreeSHAP (Explainability):")
    shap_items = json.loads(pred["shap_attributions"])
    for item in shap_items:
        print(f"  * {item['feature']:<28} Nilai: {item['current_value']:<8} Dampak RUL: {item['shap_impact']} hari")

    # 4. Validasi Teknisi Lapangan (Human-in-the-Loop) & Eksekusi Servis Preskriptif
    print_step("Tahap 4: Intervensi Teknisi Hardware & Penyelesaian Tiket Preskriptif")
    print("Instruksi Preskriptif AI:")
    print(f"\"{wo['prescriptive_action_plan']}\"")
    print("\nTeknisi lapangan melakukan verifikasi fisik:")
    print("  [x] Mengonfirmasi pasta termal mengeras (degradasi TIM)")
    print("  [x] Mengonfirmasi akumulasi debu tebal pada sirip pendingin")
    print("  [x] Melakukan pembersihan sirip heatsink dan aplikasi pasta termal konduktivitas tinggi")
    print("  [x] Uji beban pasca-servis: Suhu turun dari 96.5 C menjadi 58.0 C")

    resolve_payload = ResolveWorkOrderPayload(
        technician_verified_correct=True,
        technician_findings="Inspeksi fisik mengonfirmasi pasta termal mengeras total dan sirip pendingin tersumbat 60% debu. Dilakukan pembersihan kompresor dan penggantian pasta termal baru.",
        actions_performed=[
            "PEMBERSIHAN_DEBU_HEATSINK",
            "PENGGANTIAN_PASTA_TERMAL_ARCTIC_MX4",
            "PENGUJIAN_BEBAN_TERMAL_15_MENIT"
        ],
        parts_replaced=["THERMAL_PASTE_ARCTIC_MX4"],
        parts_origin="OEM_RECONDITIONED",
        pre_service_peak_temp_c=96.5,
        post_service_peak_temp_c=58.0
    )

    resolve_res = resolve_work_order(wo["order_id"], resolve_payload)
    print("\nStatus Penyelesaian Tiket:")
    print(json.dumps(resolve_res, indent=2))

    # 5. Tinjauan Dampak Keberlanjutan & Circular Economy Pasca-Intervensi
    print_step("Tahap 5: Akuntansi Dampak Keberlanjutan & Circular Economy")
    with get_db_session() as conn:
        updated_dev = conn.execute("SELECT current_status, expected_lifecycle_months FROM asset_devices WHERE device_id = ?;", (dev_id,)).fetchone()
        stats = conn.execute("""
            SELECT 
                SUM(ewaste_mass_saved_kg) as ewaste_kg,
                SUM(embodied_carbon_saved_kg) as carbon_kg,
                SUM(new_device_replacement_cost_idr - service_cost_idr) as savings_idr,
                SUM(extended_lifecycle_days) as extended_days
            FROM maintenance_records;
        """).fetchone()

    print(f"Status Perangkat Pasca-Servis: {updated_dev['current_status']} (Sehat & Aktif Normal)")
    print(f"Target Siklus Hidup Aset     : {updated_dev['expected_lifecycle_months']} Bulan (Diperpanjang secara resmi)")
    print("\nAkumulasi Dampak Lingkungan & Finansial Organisasi (YTD):")
    print(f"  1. Total Limbah Padat E-Waste Dicegah      : {stats['ewaste_kg']:.1f} kg")
    print(f"  2. Total Emisi Fabrikasi Dicegah (Scope 3) : {stats['carbon_kg'] / 1000.0:.2f} Ton CO2e")
    print(f"  3. Efisiensi Penghematan Finansial (TCO)   : Rp {stats['savings_idr']:,.0f}")
    print(f"  4. Total Hari Operasional Tambahan Aset    : {stats['extended_days']} Hari")
    
    print("\nDemonstrasi Siklus Hidup Sirkular Selesai dengan Sukses.")
    print("=" * 80)


if __name__ == "__main__":
    run_demo()
