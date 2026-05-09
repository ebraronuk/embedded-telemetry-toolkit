from datetime import datetime, timedelta, timezone

from src.telemetry.flight_score import compute_flight_health
from src.telemetry.schemas import FlightMode, TelemetrySample


def _sample(t, batt=95.0, rssi=-45.0, alt=120.0, fix=True, sats=14, mode=FlightMode.AUTO,
            roll=0.0, pitch=0.0, yaw=90.0, gs=10.0):
    # Test yardimcisi: alanlarin cogu makul varsayilanlarla doldurulur
    return TelemetrySample(
        timestamp_utc=t,
        lat=37.6188, lon=-122.3754,
        altitude_m=alt,
        ground_speed_mps=gs,
        vertical_speed_mps=0.0,
        roll_deg=roll, pitch_deg=pitch, yaw_deg=yaw,
        flight_mode=mode,
        battery_voltage=16.0,
        battery_remaining_pct=batt,
        gps_fix=fix, satellites=sats, armed=True,
        link_rssi=rssi,
    )


def test_health_temiz_ucus_yuksek_skor():
    # Hicbir bulgu yoksa A notu gelmeli
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    samples = [_sample(t0 + timedelta(seconds=i)) for i in range(60)]
    report = {"battery": [], "gps": [], "attitude": [], "rssi": [], "flight_mode": [], "severity": "low"}

    health = compute_flight_health(samples, report)

    assert health.overall_score >= 90
    assert health.grade == "A"
    assert health.stats.sample_count == 60
    assert health.stats.duration_s > 0


def test_health_bos_ornek_F_dondurur():
    health = compute_flight_health([], {"battery": [], "gps": [], "attitude": [], "rssi": [], "flight_mode": []})
    assert health.overall_score == 0
    assert health.grade == "F"
    assert health.stats.sample_count == 0


def test_health_dusuk_batarya_skoru_dusurur():
    # %15 batarya ile bitince power skoru ciddi dusmeli
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    samples = [_sample(t0 + timedelta(seconds=i), batt=max(15.0, 95.0 - 1.5 * i)) for i in range(60)]
    report = {
        "battery": [f"Batarya kritik seviye <20%: t{i}" for i in range(5)],
        "gps": [], "attitude": [], "rssi": [], "flight_mode": [],
    }

    health = compute_flight_health(samples, report)
    power = next(s for s in health.sub_scores if s.name == "power")

    assert power.score < 60  # %15 + 5 bulgu kombinasyonu
    assert health.overall_score < 90


def test_health_gps_kaybinda_gps_skoru_dusuk():
    # Yarisinda GPS yoksa gps skoru ciddi dusmeli
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    samples = [_sample(t0 + timedelta(seconds=i), fix=(i % 2 == 0)) for i in range(40)]
    report = {
        "battery": [], "gps": ["GPS fix yok: t1"] * 3,
        "attitude": [], "rssi": [], "flight_mode": [],
    }

    health = compute_flight_health(samples, report)
    gps = next(s for s in health.sub_scores if s.name == "gps")

    assert gps.score < 50


def test_health_grade_mantikli():
    # Skor sinirlarinda harf notu beklenen kovaya dusuyor mu
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    samples = [_sample(t0 + timedelta(seconds=i)) for i in range(30)]

    perfect = compute_flight_health(samples, {"battery": [], "gps": [], "attitude": [], "rssi": [], "flight_mode": []})
    assert perfect.grade in ("A", "B")

    # Cok bulgulu durumda F'e iniyor mu
    bad_report = {
        "battery": ["x"] * 10,
        "gps": ["x"] * 10,
        "attitude": ["x"] * 10,
        "rssi": ["x"] * 10,
        "flight_mode": ["x"] * 4,
    }
    bad = compute_flight_health(samples, bad_report)
    assert bad.grade in ("D", "F")


def test_health_to_dict_serileri_dondurur():
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    samples = [_sample(t0 + timedelta(seconds=i)) for i in range(10)]
    health = compute_flight_health(samples, {"battery": [], "gps": [], "attitude": [], "rssi": [], "flight_mode": []})

    d = health.to_dict()
    assert d["overall_score"] == health.overall_score
    assert d["grade"] == health.grade
    assert isinstance(d["sub_scores"], list) and len(d["sub_scores"]) == 5
    assert d["stats"]["sample_count"] == 10
