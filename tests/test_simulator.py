from src.telemetry.analyzer import TelemetryAnalyzer
from src.telemetry.parser import UAVTelemetryParser
from src.telemetry.simulator import UAVTelemetrySimulator


def test_simulator_generates_csv(tmp_path):
    out = tmp_path / "sim.csv"

    sim = UAVTelemetrySimulator()
    sim.simulate(duration_s=2, frequency_hz=1, output_path=out)

    assert out.exists(), "Simulasyon CSV dosyasi olusmadi"

    content = out.read_text()
    first_line = content.splitlines()[0]

    assert "timestamp_utc" in first_line.lower(), "Baslikta timestamp_utc yok"


def test_simulated_log_parse_and_analyze(tmp_path):
    out = tmp_path / "sim_pipeline.csv"

    sim = UAVTelemetrySimulator()
    sim.simulate(duration_s=3, frequency_hz=2, output_path=out)

    parser = UAVTelemetryParser()
    samples = parser.parse_file(out)

    assert samples, "Simulasyon logu parse edilemedi"
    assert all(s.timestamp_utc.tzinfo is not None for s in samples), "Timestamp UTC bilgisi eksik"

    analyzer = TelemetryAnalyzer()
    report = analyzer.analyze(samples)

    expected_keys = {"battery", "gps", "attitude", "rssi", "flight_mode", "severity"}
    assert expected_keys.issubset(report.keys()), "Rapor anahtarlari eksik"
    assert report["severity"] in {"low", "medium", "high"}, "Severity beklenenden farkli"


def test_simulator_packet_loss(tmp_path):
    out = tmp_path / "lossy.csv"
    duration = 5
    freq = 10

    sim = UAVTelemetrySimulator(packet_loss_pct=20.0)
    sim.simulate(duration_s=duration, frequency_hz=freq, output_path=out)

    lines = out.read_text().splitlines()
    total_expected = duration * freq
    produced = max(len(lines) - 1, 0)

    # Paket kaybi ile satir sayisi belirgin az olmali
    assert produced > 0, "Tum paketler kaybolamaz"
    assert produced < total_expected * 0.95, "Paket kaybi etkisi gorulmedi"
