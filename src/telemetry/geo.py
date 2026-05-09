"""Cografi yardimcilar: KML/GeoJSON ihrac, haversine mesafe."""
import json
import math
from typing import Dict, Iterable, List, Optional, Tuple, Union

from .schemas import TelemetrySample


# Dunya yaricap (m). Haversine icin standart deger
_R_EARTH_M = 6_371_000.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Iki nokta arasi yuzey mesafesi (metre). Kisa mesafede yeterince hassas."""
    # Aci farklarini radyana cevir
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return _R_EARTH_M * c


def path_length_m(samples: List[TelemetrySample]) -> float:
    """Ardisik noktalari toplayarak ucus izi uzunlugunu metre olarak ver."""
    if len(samples) < 2:
        return 0.0
    total = 0.0
    for prev, curr in zip(samples, samples[1:]):
        # GPS fix yoksa konum guvenilmez; mesafeye katma
        if not prev.gps_fix or not curr.gps_fix:
            continue
        total += haversine_m(prev.lat, prev.lon, curr.lat, curr.lon)
    return total


def bounding_box(samples: List[TelemetrySample]) -> Optional[Tuple[float, float, float, float]]:
    """Ucus izinin sinir kutusu (min_lat, min_lon, max_lat, max_lon)."""
    fix_pts = [(s.lat, s.lon) for s in samples if s.gps_fix]
    if not fix_pts:
        return None
    lats = [p[0] for p in fix_pts]
    lons = [p[1] for p in fix_pts]
    return (min(lats), min(lons), max(lats), max(lons))


def to_geojson(samples: List[TelemetrySample], anomaly_points: Optional[Iterable[Dict[str, Union[str, float]]]] = None) -> Dict:
    """Ucus izi LineString + opsiyonel anomali pinleri olarak FeatureCollection dondur."""
    features: List[Dict] = []
    coords: List[List[float]] = []
    for s in samples:
        if s.gps_fix:
            # GeoJSON sirasi: [lon, lat, alt]
            coords.append([s.lon, s.lat, s.altitude_m])
    if coords:
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {"name": "flight_track", "point_count": len(coords)},
        })
    if anomaly_points:
        for p in anomaly_points:
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(p["lon"]), float(p["lat"])]},
                "properties": {
                    "category": p.get("category", "anomaly"),
                    "label": p.get("label", ""),
                    "severity": p.get("severity", "low"),
                },
            })
    return {"type": "FeatureCollection", "features": features}


def to_geojson_string(samples: List[TelemetrySample], anomaly_points=None, indent: int = 2) -> str:
    """to_geojson sonucunu JSON string olarak ver."""
    return json.dumps(to_geojson(samples, anomaly_points), indent=indent)


def _kml_escape(text: str) -> str:
    """KML/XML icindeki ozel karakterleri escape et."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )


def to_kml(
    samples: List[TelemetrySample],
    anomaly_points: Optional[Iterable[Dict[str, Union[str, float]]]] = None,
    name: str = "UAV Flight",
) -> str:
    """Google Earth'te acilabilen KML metni uret."""
    # KML basligi ve dokuman kapsayici
    lines: List[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '<Document>',
        f'<name>{_kml_escape(name)}</name>',
        # Severity bazli yer imi stilleri (renk dizilimi: aabbggrr)
        '<Style id="sev_low"><IconStyle><color>ff00aa00</color><scale>0.9</scale></IconStyle></Style>',
        '<Style id="sev_medium"><IconStyle><color>ff00aaff</color><scale>1.0</scale></IconStyle></Style>',
        '<Style id="sev_high"><IconStyle><color>ff0000ff</color><scale>1.2</scale></IconStyle></Style>',
        '<Style id="track_style"><LineStyle><color>ffff7f00</color><width>3</width></LineStyle></Style>',
    ]

    # Ucus izi: tek bir LineString. altitudeMode=absolute, MSL irtifa kullanildigi varsayimiyla
    coord_chunks = [
        f"{s.lon:.7f},{s.lat:.7f},{s.altitude_m:.2f}"
        for s in samples if s.gps_fix
    ]
    if coord_chunks:
        lines.extend([
            '<Placemark>',
            '<name>Flight Track</name>',
            '<styleUrl>#track_style</styleUrl>',
            '<LineString>',
            '<extrude>1</extrude>',
            '<altitudeMode>absolute</altitudeMode>',
            '<coordinates>',
            ' '.join(coord_chunks),
            '</coordinates>',
            '</LineString>',
            '</Placemark>',
        ])

    # Anomali yer imleri
    if anomaly_points:
        for p in anomaly_points:
            sev = str(p.get("severity", "low")).lower()
            style_id = "sev_" + (sev if sev in {"low", "medium", "high"} else "low")
            label = _kml_escape(str(p.get("label", "")))
            category = _kml_escape(str(p.get("category", "anomaly")))
            lines.extend([
                '<Placemark>',
                f'<name>{category}</name>',
                f'<description>{label}</description>',
                f'<styleUrl>#{style_id}</styleUrl>',
                '<Point>',
                f'<coordinates>{float(p["lon"]):.7f},{float(p["lat"]):.7f},0</coordinates>',
                '</Point>',
                '</Placemark>',
            ])

    lines.extend(['</Document>', '</kml>'])
    return "\n".join(lines)


def collect_anomaly_points(
    samples: List[TelemetrySample],
    anomaly_report: Dict,
) -> List[Dict[str, Union[str, float]]]:
    """Anomali metinlerinden timestamp cikar, ornekte eslesen konuma pinle.

    Yaklasim: analyzer'in urettigi mesajlardaki ISO timestamp'i regex ile yakala,
    saniyeye yuvarlayip ornek listesindeki ayni saniyeli ornekle eslestir.
    Eslesen yoksa o anomaliyi atla.
    """
    import re
    from datetime import datetime as _dt, timezone as _tz

    # ISO benzeri timestamp yakalama. saniye duzeyine kadar yeterli
    ts_pattern = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:[+-]\d{2}:?\d{2})?")
    # Ornekleri saniyeye dair sozluk olarak indeksle (tekrari sona yazar; sorun degil)
    by_second: Dict[_dt, TelemetrySample] = {}
    for s in samples:
        key = s.timestamp_utc.replace(microsecond=0)
        # Naive timestamp gelirse UTC say (parser zaten ekliyor; yine de defansif)
        if key.tzinfo is None:
            key = key.replace(tzinfo=_tz.utc)
        by_second[key] = s

    # Bulgudaki anahtar kelimelerden severity tahmini (analyzer metinleriyle uyumlu)
    def _severity_guess(category: str, msg: str) -> str:
        msg_low = msg.lower()
        if any(t in msg_low for t in ("kritik", "fix yok", "hizli", "limit disi", "ani")):
            return "high"
        if category in ("battery", "gps", "attitude"):
            return "medium"
        return "low"

    points: List[Dict[str, Union[str, float]]] = []
    for category in ("battery", "gps", "attitude", "rssi", "flight_mode"):
        msgs = anomaly_report.get(category, [])
        if not isinstance(msgs, list):
            continue
        for msg in msgs:
            m = ts_pattern.search(msg)
            if not m:
                continue
            ts_text = m.group(0).replace(",", ".")
            try:
                parsed = _dt.fromisoformat(ts_text)
            except ValueError:
                # Ornegin tz icindeki ":" yoksa Python <3.11 hata verebilir; kisa fallback
                continue
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=_tz.utc)
            key = parsed.replace(microsecond=0)
            sample = by_second.get(key)
            if sample is None or not sample.gps_fix:
                continue
            points.append({
                "lat": sample.lat,
                "lon": sample.lon,
                "category": category,
                "label": msg,
                "severity": _severity_guess(category, msg),
            })
    return points
