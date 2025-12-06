import os
from src.telemetry.parser import UAVTelemetryParser


def test_parser_parses_real_log():
    parser = UAVTelemetryParser()

    # Örnek log dosyası
    path = "examples/sample_logs/example_flight.log"
    assert os.path.exists(path), "Sample log bulunamadı!"

    samples = parser.parse_file(path)

    # Temel doğrulamalar
    assert len(samples) > 0, "Parser hiç sample döndürmedi!"
    assert samples[0].timestamp is not None, "Timestamp parse edilemedi!"
