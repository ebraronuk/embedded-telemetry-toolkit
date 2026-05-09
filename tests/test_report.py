import json
from datetime import datetime, timedelta, timezone

from src.telemetry.flight_score import compute_flight_health
from src.telemetry.report import build_report_payload, to_html, to_json, to_markdown
from src.telemetry.schemas import FlightMode, TelemetrySample


def _sample(t, batt=90.0):
    return TelemetrySample(
        timestamp_utc=t,
        lat=37.6188, lon=-122.3754, altitude_m=120.0,
        ground_speed_mps=10.0, vertical_speed_mps=0.0,
        roll_deg=0.0, pitch_deg=0.0, yaw_deg=90.0,
        flight_mode=FlightMode.AUTO,
        battery_voltage=16.0, battery_remaining_pct=batt,
        gps_fix=True, satellites=14, armed=True,
        link_rssi=-45.0,
    )


def _build_inputs(n=20):
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    samples = [_sample(t0 + timedelta(seconds=i)) for i in range(n)]
    anomaly = {
        "battery": [],
        "gps": ["GPS fix yok: 2026-01-01T12:00:05+00:00"],
        "attitude": [],
        "rssi": [],
        "flight_mode": [],
        "severity": "medium",
    }
    health = compute_flight_health(samples, anomaly)
    return samples, anomaly, health


def test_payload_temel_alanlar():
    samples, anomaly, health = _build_inputs()
    payload = build_report_payload(samples, anomaly, health, source_path="logs/x.log")

    assert payload["overall_score"] == health.overall_score
    assert payload["grade"] == health.grade
    assert payload["severity"] == "medium"
    assert payload["severity_tr"] == "Orta"
    assert payload["source"] == "logs/x.log"
    # Yol uzunlugu hesabi anahtar alan olarak gelmeli
    assert "path_length_m" in payload["stats"]


def test_to_json_parse_edilebilir():
    samples, anomaly, health = _build_inputs()
    payload = build_report_payload(samples, anomaly, health)
    text = to_json(payload)
    data = json.loads(text)
    assert data["overall_score"] == payload["overall_score"]


def test_to_markdown_kategorileri_icerir():
    samples, anomaly, health = _build_inputs()
    payload = build_report_payload(samples, anomaly, health)
    md = to_markdown(payload)
    # Beklenen baslıklar
    for h in ("Ucus Saglik Karnesi", "Gorev Ozeti", "Alt Skorlar", "Anomaliler", "GPS"):
        assert h in md
    # Anomali metni gecmeli
    assert "GPS fix yok" in md


def test_to_html_minimal_kontrol():
    samples, anomaly, health = _build_inputs()
    payload = build_report_payload(samples, anomaly, health)
    html = to_html(payload)
    assert "<html" in html and "</html>" in html
    assert "Ucus Saglik Karnesi" in html
    # Severity rozeti renkli olarak basilmali
    assert "badge" in html


def test_html_xss_escape():
    # Anomali metnine zararli HTML konsa bile escape edilmeli
    samples, anomaly, health = _build_inputs()
    anomaly["gps"].append("<script>alert(1)</script>")
    payload = build_report_payload(samples, anomaly, health)
    html = to_html(payload)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
