"""
api/schemas.py
Pydantic schemas for request validation and response serialization.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TelemetryIngestPayload(BaseModel):
    device_asset_tag: str
    avg_cpu_temp_c: float = Field(..., ge=10.0, le=125.0)
    max_cpu_temp_c: float = Field(..., ge=10.0, le=130.0)
    ambient_temp_c: float = Field(default=24.0, ge=-10.0, le=60.0)
    fan_rpm: int = Field(..., ge=0, le=15000)
    fan_duty_cycle_pct: float = Field(..., ge=0.0, le=100.0)
    vcore_voltage_v: float = Field(..., ge=0.5, le=2.2)
    rail_12v_v: float = Field(..., ge=8.0, le=15.0)
    rail_5v_v: float = Field(..., ge=3.5, le=6.5)
    cpu_utilization_pct: float = Field(..., ge=0.0, le=100.0)
    throttling_duration_sec: int = Field(default=0, ge=0)
    smart_reallocated_sectors: int = Field(default=0, ge=0)
    smart_wear_level_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    power_cycles_count: int = Field(default=1, ge=1)


class ResolveWorkOrderPayload(BaseModel):
    technician_verified_correct: bool
    technician_findings: str
    actions_performed: List[str]
    parts_replaced: Optional[List[str]] = []
    parts_origin: Optional[str] = "OEM_RECONDITIONED"
    pre_service_peak_temp_c: Optional[float] = None
    post_service_peak_temp_c: Optional[float] = None


class OverviewKPIResponse(BaseModel):
    total_devices: int
    risk_distribution: Dict[str, int]
    failure_mode_distribution: Dict[str, int]
    open_work_orders_count: int
    operator_review_flagged_count: int
    sustainability: Dict[str, float]


class DeviceListItem(BaseModel):
    device_id: str
    asset_tag: str
    device_type: str
    brand_model: str
    operating_age_months: int
    current_status: str
    risk_tier: Optional[str] = "LOW"
    estimated_rul_days: Optional[int] = None
    primary_failure_mode: Optional[str] = "HEALTHY"
    failure_probability_14d: Optional[float] = 0.0
    confidence_score: Optional[float] = 1.0
    operator_review_required: Optional[int] = 0
    last_telemetry_at: Optional[str] = None
