/**
 * EcoPredict AI - Frontend Application Controller
 * UI/UX Pro Max Edition: Hardware Telemetry & Circular Operations Deck
 */

function getApiBase() {
  // If accessed from VS Code Live Server (port 5500), dev ports, or file: protocol,
  // automatically target the backend at port 8000.
  if (window.location.port === "5500" || window.location.port === "3000" || window.location.port === "5173" || window.location.protocol === "file:") {
    return "http://127.0.0.1:8000";
  }
  return ""; // Same-origin when running on port 8000, Vercel, or Render
}

const API_BASE = getApiBase();

async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url, options);
    const contentType = res.headers.get("content-type") || "";
    const text = await res.text();

    if (!res.ok) {
      let detailMsg = `HTTP ${res.status}`;
      if (contentType.includes("application/json") && text) {
        try {
          const errJson = JSON.parse(text);
          detailMsg = errJson.detail || detailMsg;
        } catch (_) {}
      } else if (text) {
        detailMsg = text.slice(0, 140);
      }
      throw new Error(detailMsg);
    }

    if (!text || text.trim() === "") {
      throw new Error("Respons kosong diterima dari server. Jika menggunakan Live Server (port 5500), pastikan backend FastAPI aktif di port 8000, atau buka langsung via http://127.0.0.1:8000/");
    }

    if (!contentType.includes("application/json")) {
      throw new Error("Respons bukan JSON. Permintaan kemungkinan terlayani oleh server statis Live Server bukannya backend FastAPI. Buka http://127.0.0.1:8000/");
    }

    return JSON.parse(text);
  } catch (err) {
    if (err.name === "TypeError" && (err.message.includes("fetch") || err.message.includes("NetworkError") || err.message.includes("Failed to fetch"))) {
      throw new Error("Backend FastAPI belum aktif di port 8000. Jalankan: py -3 -m uvicorn main:app --port 8000");
    }
    throw err;
  }
}

const state = {
  activeTab: "panel-fleet",
  overview: null,
  devices: [],
  workOrders: [],
  selectedDevice: null,
  selectedWorkOrder: null,
  filters: {
    risk: "",
    type: "",
    search: ""
  }
};

document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  setupEventListeners();
  loadAllData();
});

function setupTabs() {
  document.querySelectorAll(".segment-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.target;
      document.querySelectorAll(".segment-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-view").forEach(v => v.classList.remove("active"));

      btn.classList.add("active");
      const targetEl = document.getElementById(target);
      if (targetEl) targetEl.classList.add("active");
      state.activeTab = target;

      if (target === "panel-orders") loadWorkOrders();
      if (target === "panel-fleet") loadDevices();
    });
  });
}

function setupEventListeners() {
  // Search & Filter Listeners
  const searchInput = document.getElementById("search-input");
  if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener("input", (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        state.filters.search = e.target.value.trim();
        loadDevices();
      }, 250);
    });
  }

  const riskFilter = document.getElementById("risk-filter");
  if (riskFilter) {
    riskFilter.addEventListener("change", (e) => {
      state.filters.risk = e.target.value;
      loadDevices();
    });
  }

  const typeFilter = document.getElementById("type-filter");
  if (typeFilter) {
    typeFilter.addEventListener("change", (e) => {
      state.filters.type = e.target.value;
      loadDevices();
    });
  }

  // Trigger Batch AI Inference
  const triggerBtn = document.getElementById("btn-trigger-ai");
  if (triggerBtn) {
    triggerBtn.addEventListener("click", async () => {
      triggerBtn.disabled = true;
      triggerBtn.innerHTML = `<span>Memindai...</span>`;
      try {
        const data = await apiFetch("/api/v1/pipeline/trigger", { method: "POST" });
        showToast(`Pemindaian AI Selesai: ${data.summary.processed_devices} perangkat diproses (${data.summary.critical_count} Kritis).`, "success");
        loadAllData();
      } catch (err) {
        showToast("Gagal memindai: " + err.message, "error");
      } finally {
        triggerBtn.disabled = false;
        triggerBtn.innerHTML = `
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <polyline points="23 4 23 10 17 10"></polyline>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
          </svg>
          Pindai Armada AI
        `;
      }
    });
  }

  // Ingestion Simulator
  const ingestForm = document.getElementById("ingest-form");
  if (ingestForm) {
    ingestForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        device_asset_tag: document.getElementById("ingest-tag").value,
        avg_cpu_temp_c: parseFloat(document.getElementById("ingest-temp").value),
        max_cpu_temp_c: parseFloat(document.getElementById("ingest-temp").value) + 6.0,
        ambient_temp_c: 24.0,
        fan_rpm: parseInt(document.getElementById("ingest-fan").value),
        fan_duty_cycle_pct: parseFloat(document.getElementById("ingest-pwm").value),
        vcore_voltage_v: 1.22,
        rail_12v_v: parseFloat(document.getElementById("ingest-rail12").value),
        rail_5v_v: 5.01,
        cpu_utilization_pct: parseFloat(document.getElementById("ingest-load").value),
        throttling_duration_sec: document.getElementById("ingest-temp").value > 90 ? 300 : 0,
        smart_reallocated_sectors: 0,
        smart_wear_level_pct: 95.0,
        power_cycles_count: 140
      };

      try {
        await apiFetch("/api/v1/telemetry/ingest", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        showToast(`Telemetri ${payload.device_asset_tag} berhasil diterima Gateway.`, "success");
        loadAllData();
      } catch (err) {
        showToast("Ingest gagal: " + err.message, "error");
      }
    });
  }

  // Modal Closers
  document.querySelectorAll(".modal-close, .modal-cancel").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".drawer-backdrop").forEach(d => d.classList.remove("active"));
    });
  });

  // Resolve Work Order Submission
  const resolveForm = document.getElementById("resolve-form");
  if (resolveForm) {
    resolveForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!state.selectedWorkOrder) return;

      const isVerified = document.querySelector('input[name="wo-verify"]:checked').value === "true";
      const findings = document.getElementById("wo-findings").value;
      const actions = Array.from(document.querySelectorAll('input[name="wo-action"]:checked')).map(cb => cb.value);

      const payload = {
        technician_verified_correct: isVerified,
        technician_findings: findings,
        actions_performed: actions.length > 0 ? actions : ["INSPEKSI_DAN_PEMBERSIHAN"],
        parts_replaced: isVerified ? ["THERMAL_COMPOUND_GRADE_A"] : [],
        parts_origin: "OEM_RECONDITIONED",
        pre_service_peak_temp_c: parseFloat(document.getElementById("wo-pre-temp").value) || 94.0,
        post_service_peak_temp_c: parseFloat(document.getElementById("wo-post-temp").value) || 58.0
      };

      try {
        const data = await apiFetch(`/api/v1/work-orders/${state.selectedWorkOrder.order_id}/resolve`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (data.status === "RESOLVED_SUCCESSFULLY") {
          showToast(`Tiket Selesai! Masa pakai +${data.extended_lifecycle_days} hari, E-waste dicegah: ${data.ewaste_mass_saved_kg} kg.`, "success");
        } else {
          showToast("Tiket ditutup dengan catatan False Alarm.", "info");
        }
        document.getElementById("modal-resolve").classList.remove("active");
        loadAllData();
      } catch (err) {
        showToast("Gagal menyelesaikan tiket: " + err.message, "error");
      }
    });
  }
}

// Data Fetching
async function loadAllData() {
  await loadOverview();
  await loadDevices();
  await loadWorkOrders();
}

async function loadOverview() {
  try {
    const data = await apiFetch("/api/v1/overview");
    state.overview = data;
    renderKPIs(data);
  } catch (err) {
    console.error("Error loading overview KPIs:", err);
    showToast(err.message, "error");
  }
}

function renderKPIs(data) {
  document.getElementById("kpi-total-devices").innerHTML = `${data.total_devices} <span class="unit">Unit</span>`;
  document.getElementById("kpi-critical-risk").innerHTML = `${data.risk_distribution.CRITICAL} <span class="unit" style="color:#fca5a5;">Unit</span>`;
  document.getElementById("kpi-ewaste-saved").innerHTML = `${data.sustainability.ewaste_mass_saved_kg} <span class="unit">kg</span>`;
  document.getElementById("kpi-carbon-saved").innerHTML = `${data.sustainability.embodied_carbon_saved_ton} <span class="unit">Ton CO2e</span>`;

  const openTicketsBadge = document.getElementById("open-tickets-count");
  if (openTicketsBadge) openTicketsBadge.innerText = data.open_work_orders_count;
}

async function loadDevices() {
  try {
    let endpoint = `/api/v1/devices?limit=100`;
    if (state.filters.risk) endpoint += `&risk_tier=${state.filters.risk}`;
    if (state.filters.type) endpoint += `&device_type=${state.filters.type}`;
    if (state.filters.search) endpoint += `&search=${encodeURIComponent(state.filters.search)}`;

    const devices = await apiFetch(endpoint);
    state.devices = devices;
    renderDevicesTable(devices);
  } catch (err) {
    console.error("Error loading devices list:", err);
  }
}

function renderDevicesTable(devices) {
  const tbody = document.getElementById("devices-tbody");
  tbody.innerHTML = "";

  if (!devices || devices.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 32px; color: var(--text-muted);">Tidak ada perangkat yang sesuai dengan kriteria filter.</td></tr>`;
    return;
  }

  devices.forEach(d => {
    const tr = document.createElement("tr");

    const pillClass = {
      CRITICAL: "pill-critical",
      HIGH: "pill-high",
      MODERATE: "pill-mod",
      LOW: "pill-low"
    }[d.risk_tier] || "pill-low";

    const operatorIndicator = d.operator_review_required ? `<span style="font-size:11px; color:#d8b4fe; font-family:var(--font-mono); display:block; margin-top:2px;">• Review Wajib</span>` : "";

    // Device Icon SVG
    const iconSvg = d.device_type === "LAPTOP" 
      ? `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="12" rx="2" ry="2"></rect><line x1="2" y1="20" x2="22" y2="20"></line></svg>`
      : d.device_type === "SERVER_NODE"
      ? `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>`
      : `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>`;

    // Gauge calculation (RUL / 365)
    const rulDays = d.estimated_rul_days || 0;
    const rulPct = Math.min(100, Math.max(5, Math.round((rulDays / 365.0) * 100)));
    const gaugeColor = rulDays <= 14 ? "#ef4444" : rulDays <= 30 ? "#f97316" : rulDays <= 60 ? "#eab308" : "#10b981";

    tr.innerHTML = `
      <td>
        <div class="asset-cell">
          <div class="asset-icon-box" aria-hidden="true">${iconSvg}</div>
          <div class="asset-name-group">
            <span class="asset-tag-text">${d.asset_tag}</span>
            <span class="asset-model-sub">${d.brand_model}</span>
          </div>
        </div>
      </td>
      <td><span style="font-size:12px; font-weight:600; color:var(--text-secondary);">${d.device_type}</span></td>
      <td>
        <span class="pill-status ${pillClass}">
          <span class="dot"></span>
          <span>${d.risk_tier}</span>
        </span>
        ${operatorIndicator}
      </td>
      <td>
        <div class="rul-gauge-wrapper">
          <div class="rul-gauge-header">
            <span>${rulDays} Hari</span>
            <span style="color:var(--text-muted);">${rulPct}%</span>
          </div>
          <div class="rul-gauge-track">
            <div class="rul-gauge-fill" style="width: ${rulPct}%; background-color: ${gaugeColor};"></div>
          </div>
        </div>
      </td>
      <td>
        <span style="font-size: 12.5px; color: ${d.primary_failure_mode === 'HEALTHY' ? 'var(--text-muted)' : '#f8fafc'};">
          ${d.primary_failure_mode ? d.primary_failure_mode.replace(/_/g, " ") : "Nominal"}
        </span>
      </td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick="openDeviceDetail('${d.device_id}')">
          Analisis SHAP
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

async function loadWorkOrders() {
  try {
    const orders = await apiFetch("/api/v1/work-orders");
    state.workOrders = orders;
    renderWorkOrdersTable(orders);
  } catch (err) {
    console.error("Error loading work orders:", err);
  }
}

function renderWorkOrdersTable(orders) {
  const tbody = document.getElementById("orders-tbody");
  tbody.innerHTML = "";

  if (!orders || orders.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 32px; color: var(--text-muted);">Tidak ada tiket terbuka. Seluruh armada dalam kondisi stabil.</td></tr>`;
    return;
  }

  orders.forEach(wo => {
    const tr = document.createElement("tr");
    const isResolved = wo.order_status === "RESOLVED";

    tr.innerHTML = `
      <td>
        <strong style="color:#ffffff; font-family:var(--font-mono);">${wo.asset_tag}</strong>
        <div style="font-size:11.5px; color:var(--text-muted);">${wo.device_type} - ${wo.brand_model}</div>
      </td>
      <td>
        <span class="pill-status ${wo.priority === 'URGENT' ? 'pill-critical' : 'pill-high'}">
          <span class="dot"></span>
          <span>${wo.priority}</span>
        </span>
      </td>
      <td><span style="font-family: var(--font-mono); font-weight: 700;">${wo.estimated_rul_days} Hari</span></td>
      <td style="font-size: 12.5px; max-width: 320px; line-height: 1.4;">${wo.prescriptive_action_plan}</td>
      <td style="font-size: 12.5px; color: var(--text-secondary);">${wo.technician_name || "Teknisi Hardware"}</td>
      <td>
        <span class="pill-status ${isResolved ? 'pill-low' : 'pill-high'}">
          <span>${wo.order_status}</span>
        </span>
      </td>
      <td>
        ${!isResolved 
          ? `<button class="btn btn-primary btn-sm" onclick="openResolveModal('${wo.order_id}')">Verifikasi</button>` 
          : `<span style="color:var(--color-brand); font-size:12px; font-weight:600;">Selesai</span>`
        }
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// Modal Handlers
window.openDeviceDetail = async function(deviceId) {
  try {
    const detail = await apiFetch(`/api/v1/devices/${deviceId}`);
    state.selectedDevice = detail;

    const d = detail.device;
    const p = detail.latest_prediction;

    document.getElementById("modal-device-title").innerText = `${d.asset_tag} • ${d.brand_model}`;
    document.getElementById("spec-cpu").innerText = d.cpu_spec;
    document.getElementById("spec-ram").innerText = `${d.ram_gb} GB RAM / ${d.storage_capacity_gb} GB Storage`;
    document.getElementById("spec-age").innerText = `${d.operating_age_months} Bulan Operasional`;
    document.getElementById("spec-rul").innerText = p 
      ? `${p.estimated_rul_days} Hari (Toleransi: ${p.conformal_lower_rul_days} - ${p.conformal_upper_rul_days} Hari)` 
      : "Nominal";

    if (p && p.prescriptive_catalog) {
      document.getElementById("pred-mode-title").innerText = p.prescriptive_catalog.title;
      document.getElementById("pred-action-text").innerText = p.prescriptive_catalog.action;
      document.getElementById("pred-impact-text").innerText = `Potensi Perpanjangan: +${p.prescriptive_catalog.expected_life_extension_days} hari | Scope 3 Dihindari: ${p.prescriptive_catalog.scope3_carbon_kg} kg CO2e`;
    }

    // Render SHAP Waterfall Bars
    const shapContainer = document.getElementById("shap-bars-container");
    shapContainer.innerHTML = "";
    if (p && p.shap_attributions) {
      p.shap_attributions.forEach(item => {
        const absImpact = Math.abs(item.shap_impact);
        const pct = Math.min(100, Math.max(10, Math.round((absImpact / 200.0) * 100)));
        const isHazard = item.shap_impact < 0;

        const row = document.createElement("div");
        row.className = "shap-item-row";
        row.innerHTML = `
          <div class="shap-name">${item.feature}</div>
          <div class="shap-bar-track-outer">
            <div class="shap-bar-fill-inner" style="width: ${pct}%; background: ${isHazard ? 'linear-gradient(90deg, #ef4444, #f97316)' : '#10b981'};"></div>
          </div>
          <div class="shap-score-val" style="color: ${isHazard ? '#fca5a5' : '#6ee7b7'};">
            ${item.shap_impact > 0 ? '+' : ''}${item.shap_impact}
          </div>
        `;
        shapContainer.appendChild(row);
      });
    }

    renderTelemetrySVG(detail.telemetry_history);
    document.getElementById("modal-device").classList.add("active");
  } catch (err) {
    showToast("Gagal memuat detail: " + err.message, "error");
  }
};

window.openResolveModal = function(orderId) {
  const order = state.workOrders.find(o => o.order_id === orderId);
  if (!order) return;
  state.selectedWorkOrder = order;

  document.getElementById("modal-wo-title").innerText = `Validasi Preskriptif: ${order.asset_tag}`;
  document.getElementById("wo-modal-action-summary").innerText = order.prescriptive_action_plan;
  document.getElementById("modal-resolve").classList.add("active");
};

function renderTelemetrySVG(history) {
  const chartEl = document.getElementById("telemetry-svg-chart");
  if (!history || history.length === 0) {
    chartEl.innerHTML = `<text x="50" y="50" fill="#64748b">Tidak ada data sensor.</text>`;
    return;
  }

  const width = 800;
  const height = 180;
  const padding = 32;

  const temps = history.map(h => h.avg_cpu_temp_c);
  const minTemp = 30;
  const maxTemp = 110;

  const points = temps.map((t, i) => {
    const x = padding + (i / (temps.length - 1)) * (width - 2 * padding);
    const y = height - padding - ((t - minTemp) / (maxTemp - minTemp)) * (height - 2 * padding);
    return `${x},${y}`;
  }).join(" ");

  const criticalY = height - padding - ((88 - minTemp)/(maxTemp - minTemp)) * (height - 2*padding);

  chartEl.innerHTML = `
    <defs>
      <linearGradient id="curveGradient" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#ef4444" stop-opacity="0.3"/>
        <stop offset="100%" stop-color="#ef4444" stop-opacity="0.0"/>
      </linearGradient>
    </defs>

    <!-- Grid Lines -->
    <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" stroke="rgba(255,255,255,0.08)"/>
    <line x1="${padding}" y1="${padding}" x2="${width - padding}" y2="${padding}" stroke="rgba(255,255,255,0.08)"/>

    <!-- Critical 88 C Threshold -->
    <line x1="${padding}" y1="${criticalY}" x2="${width - padding}" y2="${criticalY}" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="4"/>
    <text x="${width - padding - 110}" y="${criticalY - 6}" fill="#fca5a5" font-size="10.5" font-family="JetBrains Mono">Batas Throttling (88°C)</text>

    <!-- Curve & Data Line -->
    <polyline fill="none" stroke="#f97316" stroke-width="2.5" points="${points}" />
    <text x="${padding}" y="18" fill="#ffffff" font-size="11.5" font-family="JetBrains Mono" font-weight="600">Suhu CPU (°C) 48 Jam Terakhir — Puncak: ${temps[temps.length-1]}°C</text>
  `;
}

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = "toast";
  toast.style.borderLeftColor = type === "error" ? "var(--color-critical)" : type === "success" ? "var(--color-brand)" : "var(--color-blue)";
  toast.innerText = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(40px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4500);
}
