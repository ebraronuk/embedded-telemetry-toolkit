from src.telemetry.simulator import UAVTelemetrySimulator


def test_simulator_generates_csv(tmp_path):
    out = tmp_path / "sim.csv"

    sim = UAVTelemetrySimulator()
    sim.simulate(duration_s=2, frequency_hz=1, output_path=out)

    # Dosya üretildi mi?
    assert out.exists(), "Simülatör CSV dosyası oluşturamadı!"

    content = out.read_text()
    first_line = content.splitlines()[0]

    # Başlık satırında timestamp olmalı
    assert "timestamp" in first_line.lower()
