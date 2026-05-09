"""Ucus saglik skoru ve gorev istatistikleri."""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Union

from .schemas import FlightMode, TelemetrySample


# Genel skoru olcerken alt skorlarin agirligi
# Saha tecrubesi: enerji ve GPS, gorev sonucunu en cok belirleyen iki kalemdir
_WEIGHTS = {
    "power": 0.30,
    "gps": 0.25,
    "attitude": 0.20,
    "link": 0.15,
    "mode": 0.10,
}


@dataclass
class MissionStats:
    """Ucus boyunca toplanan ozet metrikler."""

    sample_count: int = 0
    duration_s: float = 0.0
    max_altitude_m: float = 0.0
    min_battery_pct: float = 0.0
    max_ground_speed_mps: float = 0.0
    gps_loss_ratio: float = 0.0  # GPS fix kaybi orani (0-1)
    min_rssi_dbm: float = 0.0
    flight_modes_seen: List[str] = field(default_factory=list)


@dataclass
class SubScore:
    """Tek bir kategoriye ait skor + kisa aciklama."""

    name: str
    score: int  # 0-100
    note: str


@dataclass
class FlightHealthReport:
    """Ucus saglik karnesi: alt skorlar + genel skor + mission stats."""

    overall_score: int  # 0-100
    grade: str  # A/B/C/D/F (hizli okuma icin)
    sub_scores: List[SubScore] = field(default_factory=list)
    stats: MissionStats = field(default_factory=MissionStats)

    def to_dict(self) -> Dict[str, Union[int, str, list, dict]]:
        """JSON'a dokulebilir sade bir dict uret."""
        return {
            "overall_score": self.overall_score,
            "grade": self.grade,
            "sub_scores": [asdict(s) for s in self.sub_scores],
            "stats": asdict(self.stats),
        }


def _grade_for(score: int) -> str:
    """Skor -> harf notu. Egitim notlamasi gibi, hizli okuma icin."""
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def _clip(x: float) -> int:
    """0-100 araligina kirp ve tamsayiya yuvarla."""
    if x < 0:
        return 0
    if x > 100:
        return 100
    return int(round(x))


def _power_score(samples: List[TelemetrySample], anomaly_count: int) -> SubScore:
    # Her batarya bulgusu 6 puan dusurur; %20 alti ekstra ceza
    min_batt = min(s.battery_remaining_pct for s in samples)
    score = 100.0 - anomaly_count * 6.0
    if min_batt < 20.0:
        score -= 20.0
    elif min_batt < 30.0:
        score -= 10.0
    note = f"Min batarya %{min_batt:.0f}, {anomaly_count} bulgu"
    return SubScore(name="power", score=_clip(score), note=note)


def _gps_score(samples: List[TelemetrySample], anomaly_count: int) -> SubScore:
    # GPS fix kaybi yuzdesi dogrudan skoru asindirir
    n = len(samples)
    loss_ratio = sum(1 for s in samples if not s.gps_fix) / n
    score = 100.0 - anomaly_count * 5.0 - loss_ratio * 100.0
    avg_sats = sum(s.satellites for s in samples) / n
    if avg_sats < 6.0:
        score -= 10.0  # ortalama uydu sayisi dusukse navigasyon riskli
    note = f"Ort. uydu {avg_sats:.1f}, fix kaybi %{loss_ratio*100:.1f}, {anomaly_count} bulgu"
    return SubScore(name="gps", score=_clip(score), note=note)


def _attitude_score(samples: List[TelemetrySample], anomaly_count: int) -> SubScore:
    # Tek bir agresif manevra rapora cikabilir; suregen sertlik daha cok puan kirar
    max_tilt = max(max(abs(s.roll_deg), abs(s.pitch_deg)) for s in samples)
    score = 100.0 - anomaly_count * 4.0
    if max_tilt > 45.0:
        score -= 15.0
    elif max_tilt > 35.0:
        score -= 8.0
    note = f"Max tilt {max_tilt:.0f} deg, {anomaly_count} bulgu"
    return SubScore(name="attitude", score=_clip(score), note=note)


def _link_score(samples: List[TelemetrySample], anomaly_count: int) -> SubScore:
    # RSSI alt sinirina yakinlik link kalitesinin en sade gostergesi
    min_rssi = min(s.link_rssi for s in samples)
    score = 100.0 - anomaly_count * 5.0
    if min_rssi < -90.0:
        score -= 20.0
    elif min_rssi < -80.0:
        score -= 10.0
    note = f"Min RSSI {min_rssi:.0f} dBm, {anomaly_count} bulgu"
    return SubScore(name="link", score=_clip(score), note=note)


def _mode_score(samples: List[TelemetrySample], anomaly_count: int) -> SubScore:
    # Mod disiplini tek bir guclu ceza ile cezalandirilir, fazla mikro ayar gereksiz
    seen = []
    for s in samples:
        if not seen or seen[-1] != s.flight_mode:
            seen.append(s.flight_mode)
    score = 100.0 - anomaly_count * 25.0
    note = f"Mod sirasi: {' -> '.join(m.value for m in seen) or '-'}"
    return SubScore(name="mode", score=_clip(score), note=note)


def _build_stats(samples: List[TelemetrySample]) -> MissionStats:
    """Ucus genelinden ozet metrikleri cikar."""
    # Bos veriyi cagiran taraf yakalamali; burada savunmacı kontrol yine de var
    if not samples:
        return MissionStats()
    duration = (samples[-1].timestamp_utc - samples[0].timestamp_utc).total_seconds()
    seen_modes: List[str] = []
    for s in samples:
        m = s.flight_mode.value
        if m not in seen_modes:
            seen_modes.append(m)
    return MissionStats(
        sample_count=len(samples),
        duration_s=round(max(duration, 0.0), 2),
        max_altitude_m=round(max(s.altitude_m for s in samples), 2),
        min_battery_pct=round(min(s.battery_remaining_pct for s in samples), 2),
        max_ground_speed_mps=round(max(s.ground_speed_mps for s in samples), 2),
        gps_loss_ratio=round(sum(1 for s in samples if not s.gps_fix) / len(samples), 4),
        min_rssi_dbm=round(min(s.link_rssi for s in samples), 1),
        flight_modes_seen=seen_modes,
    )


def compute_flight_health(
    samples: List[TelemetrySample],
    anomaly_report: Dict[str, Union[List[str], str]],
) -> FlightHealthReport:
    """Telemetri ornekleri ve analyzer raporundan ucus saglik karnesini olustur."""
    if not samples:
        # Bos ucus = degerlendirilemez. F notu yerine 0 ve aciklama dondur
        return FlightHealthReport(
            overall_score=0,
            grade="F",
            sub_scores=[SubScore(name=k, score=0, note="Veri yok") for k in _WEIGHTS],
            stats=MissionStats(),
        )

    # Anomali sayilari (rapor liste tutar; severity metni atlanmali)
    def _count(key: str) -> int:
        v = anomaly_report.get(key, [])
        return len(v) if isinstance(v, list) else 0

    subs = [
        _power_score(samples, _count("battery")),
        _gps_score(samples, _count("gps")),
        _attitude_score(samples, _count("attitude")),
        _link_score(samples, _count("rssi")),
        _mode_score(samples, _count("flight_mode")),
    ]

    # Agirlikli toplam; isim eslemesi alt skorla bire bir
    weight_map = {s.name: s for s in subs}
    overall = sum(weight_map[name].score * w for name, w in _WEIGHTS.items())
    overall_int = _clip(overall)

    return FlightHealthReport(
        overall_score=overall_int,
        grade=_grade_for(overall_int),
        sub_scores=subs,
        stats=_build_stats(samples),
    )
