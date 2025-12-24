from pathlib import Path

from src.telemetry.parser import UAVTelemetryParser


def test_parser_parses_real_log():
    parser = UAVTelemetryParser()

    path = Path("examples/sample_logs/example_flight.log")
    assert path.exists(), "Ornek log bulunamadi"

    samples = parser.parse_file(path)

    assert samples, "Parser bos dondu"
    assert samples[0].timestamp_utc is not None, "Timestamp parse edilemedi"
    assert samples[0].timestamp_utc.tzinfo is not None, "Timestamp UTC bilgisi yok"


def test_parse_file_accepts_str_and_path():
    parser = UAVTelemetryParser()

    path = Path("examples/sample_logs/example_flight.log")
    samples_path = parser.parse_file(path)
    samples_str = parser.parse_file(str(path))

    assert samples_path, "Path ile okuma bos dondu"
    assert samples_path == samples_str, "Path ve str okumalari uyumlu degil"


def test_parser_skips_missing_rows(tmp_path):
    parser = UAVTelemetryParser()
    log_path = tmp_path / "lossy.log"
    log_path.write_text(
        "\n".join(
            [
                "timestamp_utc,lat,lon,altitude_m,ground_speed_mps,vertical_speed_mps,roll_deg,pitch_deg,yaw_deg,flight_mode,armed,battery_voltage,battery_remaining_pct,gps_fix,satellites,link_rssi",
                "2025-12-06T17:31:35,37.618805,-122.375416,30.0,5.0,0.1,0.5,0.2,90.0,MANUAL,1,16.5,95.0,1,14,-45.0",
                "",  # kasti bos satir
                "2025-12-06T17:31:36,37.618810,-122.375410,32.0,6.0,0.3,0.7,0.3,90.1,AUTO,1,16.4,94.8,1,14,-45.2",
                "2025-12-06T17:31:37,37.618815",  # eksik kolonlar, atlanmali
                "2025-12-06T17:31:38,37.618820,-122.375400,34.0,6.5,0.2,0.6,0.2,90.3,AUTO,1,16.3,94.6,1,14,-45.5",
            ]
        )
    )

    # Paket kaybŽñ (eksik satir) durumunda parser devam etmeli
    samples = parser.parse_file(log_path)

    assert samples, "Paket kaybi olsa da gecerli satirlar parse edilmedi"
    assert all(s.timestamp_utc.tzinfo is not None for s in samples), "Timestamp UTC bilgisi eksik"
