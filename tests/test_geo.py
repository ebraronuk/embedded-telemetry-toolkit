import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from src.telemetry.geo import (
    bounding_box,
    collect_anomaly_points,
    haversine_m,
    path_length_m,
    to_geojson,
    to_kml,
)
from src.telemetry.schemas import FlightMode, TelemetrySample


def _sample(t, lat=37.6188, lon=-122.3754, alt=120.0, fix=True):
    # Test yardimcisi
    return TelemetrySample(
        timestamp_utc=t,
        lat=lat, lon=lon, altitude_m=alt,
        ground_speed_mps=10.0, vertical_speed_mps=0.0,
        roll_deg=0.0, pitch_deg=0.0, yaw_deg=90.0,
        flight_mode=FlightMode.AUTO,
        battery_voltage=16.0, battery_remaining_pct=80.0,
        gps_fix=fix, satellites=14, armed=True,
        link_rssi=-50.0,
    )


def test_haversine_bilinen_mesafe():
    # San Francisco - Los Angeles yaklasik 559 km. Toleransli kontrol
    sf = (37.7749, -122.4194)
    la = (34.0522, -118.2437)
    d = haversine_m(*sf, *la)
    assert 540_000 < d < 580_000


def test_haversine_ayni_nokta_sifir():
    assert haversine_m(40.0, 30.0, 40.0, 30.0) == 0.0


def test_path_length_artar():
    # 1 derece longitude ekvatorda yaklasik 111 km. Bu enlemde bir miktar daralir
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    samples = [
        _sample(t0, lat=37.0, lon=-122.0),
        _sample(t0 + timedelta(seconds=1), lat=37.0, lon=-121.99),
        _sample(t0 + timedelta(seconds=2), lat=37.0, lon=-121.98),
    ]
    d = path_length_m(samples)
    # ~ 2 * 0.01 derece * cos(37) * 111320 ~ 1778 m. Genis bir aralik birak
    assert 1500 < d < 2000


def test_path_length_bos_sifir():
    assert path_length_m([]) == 0.0


def test_path_length_gps_yoksa_atla():
    # GPS fix olmayan adimdan once/sonra mesafe sayilmamali
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    samples = [
        _sample(t0, lat=37.0, lon=-122.0, fix=True),
        _sample(t0 + timedelta(seconds=1), lat=38.0, lon=-122.0, fix=False),
        _sample(t0 + timedelta(seconds=2), lat=38.0, lon=-122.0, fix=True),
    ]
    # Sadece son iki nokta arasi sayilmali, ayni konum oldugu icin sifir
    assert path_length_m(samples) == 0.0


def test_bounding_box():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    samples = [
        _sample(t0, lat=37.0, lon=-122.5),
        _sample(t0 + timedelta(seconds=1), lat=37.5, lon=-122.0),
    ]
    bb = bounding_box(samples)
    assert bb == (37.0, -122.5, 37.5, -122.0)


def test_geojson_yapisi_dogru():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    samples = [_sample(t0 + timedelta(seconds=i)) for i in range(5)]
    fc = to_geojson(samples)
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 1
    line = fc["features"][0]
    assert line["geometry"]["type"] == "LineString"
    assert len(line["geometry"]["coordinates"]) == 5
    # GeoJSON sirasi: [lon, lat, alt]
    assert line["geometry"]["coordinates"][0][0] == -122.3754


def test_geojson_anomali_pinleri_eklenir():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    samples = [_sample(t0)]
    points = [{"lat": 37.0, "lon": -122.0, "category": "battery", "label": "test", "severity": "high"}]
    fc = to_geojson(samples, anomaly_points=points)
    point_features = [f for f in fc["features"] if f["geometry"]["type"] == "Point"]
    assert len(point_features) == 1
    assert point_features[0]["properties"]["severity"] == "high"


def test_kml_gecerli_xml_dondurur():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    samples = [_sample(t0 + timedelta(seconds=i), lat=37.0 + i * 0.0001) for i in range(3)]
    points = [{"lat": 37.0, "lon": -122.0, "category": "gps", "label": "GPS fix yok", "severity": "high"}]

    kml_text = to_kml(samples, anomaly_points=points, name="Test Flight")

    # XML parse edilebilmeli
    root = ET.fromstring(kml_text)
    # Namespace ile sorgu
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    placemarks = root.findall(".//kml:Placemark", ns)
    assert len(placemarks) >= 2  # track + 1 pin


def test_kml_xml_inject_escape_edilir():
    # Anomali mesajinda XML acabilecek karakter varsa escape edilmeli
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    samples = [_sample(t0)]
    points = [{
        "lat": 37.0, "lon": -122.0,
        "category": "battery",
        "label": "<broken>&amp;</broken>",
        "severity": "low",
    }]
    kml_text = to_kml(samples, anomaly_points=points)
    # Hala parse edilebilmeli
    ET.fromstring(kml_text)


def test_collect_anomaly_points_eslestirme():
    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    samples = [_sample(t0 + timedelta(seconds=i), lat=37.0 + i * 0.0001) for i in range(3)]
    # Analyzer benzeri mesaj formati
    msg_ts = (t0 + timedelta(seconds=1)).isoformat()
    report = {
        "battery": [],
        "gps": [f"GPS fix yok: {msg_ts}"],
        "attitude": [],
        "rssi": [],
        "flight_mode": [],
    }
    points = collect_anomaly_points(samples, report)
    assert len(points) == 1
    assert points[0]["category"] == "gps"
    assert abs(points[0]["lat"] - (37.0 + 1 * 0.0001)) < 1e-9
