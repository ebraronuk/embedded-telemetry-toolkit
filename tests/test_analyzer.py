from datetime import datetime, timezone

from src.telemetry.analyzer import TelemetryAnalyzer
from src.telemetry.schemas import FlightMode, TelemetrySample


def test_analyzer_detects_low_battery():
    analyzer = TelemetryAnalyzer()

    samples = [
        TelemetrySample(
            timestamp_utc=datetime.now(timezone.utc),
            lat=0.0,
            lon=0.0,
            altitude_m=10.0,
            ground_speed_mps=0.0,
            vertical_speed_mps=0.0,
            roll_deg=0.0,
            pitch_deg=0.0,
            yaw_deg=0.0,
            flight_mode=FlightMode.AUTO,
            battery_voltage=14.8,
            battery_remaining_pct=15.0,  # kritik deger
            gps_fix=True,
            satellites=10,
            armed=True,
            link_rssi=-40.0,
        )
    ]

    report = analyzer.analyze(samples)

    assert "battery" in report
    assert len(report["battery"]) > 0
    assert report["severity"] in ["medium", "high"]
