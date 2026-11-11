"""
tests/test_edge_agent.py
Unit tests verifying the Edge Client Telemetry Daemon and offline store-and-forward buffering.
"""

import os
import sqlite3
import pytest
from edge_agent.client_daemon import EdgeTelemetryDaemon


@pytest.fixture
def temp_buffer(tmp_path):
    return str(tmp_path / "test_buffer.db")


def test_edge_daemon_sampling(temp_buffer):
    daemon = EdgeTelemetryDaemon(asset_tag="TEST-ASSET-01", buffer_db_path=temp_buffer)
    metrics = daemon.sample_hardware_metrics()

    assert metrics["device_asset_tag"] == "TEST-ASSET-01"
    assert 10.0 <= metrics["avg_cpu_temp_c"] <= 125.0
    assert 0.0 <= metrics["cpu_utilization_pct"] <= 100.0
    assert metrics["fan_rpm"] >= 500
    assert 10.0 <= metrics["rail_12v_v"] <= 13.0


def test_edge_daemon_offline_buffering(temp_buffer):
    # Use invalid server URL to force offline condition
    daemon = EdgeTelemetryDaemon(
        asset_tag="TEST-ASSET-02",
        server_url="http://127.0.0.1:59999/invalid/route",
        buffer_db_path=temp_buffer
    )

    metrics = daemon.sample_hardware_metrics()
    success = daemon.transmit_or_buffer(metrics)

    # Transmission must fail gracefully and buffer locally
    assert success is False

    with sqlite3.connect(temp_buffer) as conn:
        count = conn.execute("SELECT COUNT(*) FROM offline_buffer;").fetchone()[0]
    assert count == 1
