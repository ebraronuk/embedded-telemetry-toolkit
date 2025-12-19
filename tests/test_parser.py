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
