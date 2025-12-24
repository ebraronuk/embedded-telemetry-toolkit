"""UAV telemetry analyzer."""
from dataclasses import dataclass
from typing import Dict, List, Tuple, Union

from .schemas import FlightMode, TelemetrySample


@dataclass
class _ChangeRate:
    roll_rate: float
    pitch_rate: float
    yaw_rate: float


class TelemetryAnalyzer:
    """Detect anomalies in telemetry samples."""

    def analyze(self, samples: List[TelemetrySample]) -> Dict[str, Union[List[str], str]]:
        """Analyze samples and return anomaly report."""
        # Bos veri icin erken cik
        empty_report: Dict[str, Union[List[str], str]] = {
            "battery": [],
            "gps": [],
            "attitude": [],
            "rssi": [],
            "flight_mode": [],
            "severity": "low",
        }
        if not samples:
            return empty_report

        anomalies: Dict[str, Union[List[str], str]] = {
            "battery": self._detect_battery(samples),
            "gps": self._detect_gps(samples),
            "attitude": self._detect_attitude(samples),
            "rssi": self._detect_rssi(samples),
            "flight_mode": self._detect_flight_mode_sequence(samples),
        }
        anomalies["severity"] = self._compute_severity(anomalies)
        return anomalies

    def _detect_battery(self, samples: List[TelemetrySample]) -> List[str]:
        """Detect battery issues."""
        findings: List[str] = []
        for prev, curr in zip(samples, samples[1:]):
            dt = (curr.timestamp_utc - prev.timestamp_utc).total_seconds() or 1e-6
            # Sahada asiri hassasiyet yalanci alarmlari sisirir, esikleri yumusatildi
            pct_rate = (prev.battery_remaining_pct - curr.battery_remaining_pct) / dt
            volt_rate = (prev.battery_voltage - curr.battery_voltage) / dt
            if pct_rate > 1.2 or volt_rate > 0.25:
                findings.append(f"Batarya hizli tuketim: {curr.timestamp_utc.isoformat()}")
            # Tek adimda ani voltaj dususunu yakala, tek spike'i atla
            volt_drop = prev.battery_voltage - curr.battery_voltage
            if volt_drop > 0.4 and prev.battery_voltage > 12.5:
                findings.append(f"Ani voltaj dususu >0.4V: {curr.timestamp_utc.isoformat()}")
        for s in samples:
            if s.battery_remaining_pct < 20.0:
                findings.append(f"Batarya kritik seviye <20%: {s.timestamp_utc.isoformat()}")
        return findings

    def _detect_gps(self, samples: List[TelemetrySample]) -> List[str]:
        """Flag GPS loss or weak fix."""
        findings: List[str] = []
        loss_streak = 0
        sat_low_streak = 0
        for s in samples:
            if not s.gps_fix:
                loss_streak += 1
            else:
                loss_streak = 0
            if s.gps_fix and s.satellites < 5:
                sat_low_streak += 1
            else:
                sat_low_streak = 0
            # Kisa kesinti ve tek uydu diplerini es gec
            if loss_streak == 2:
                findings.append(f"GPS fix yok: {s.timestamp_utc.isoformat()}")
            if sat_low_streak == 2:
                findings.append(f"Zayif GPS (<5 uydu): {s.timestamp_utc.isoformat()}")
        return findings

    def _detect_rssi(self, samples: List[TelemetrySample]) -> List[str]:
        """Flag link quality issues."""
        findings: List[str] = []
        low_streak = 0
        for s in samples:
            if s.link_rssi < -92.0:
                low_streak += 1
            else:
                low_streak = 0
            # Tek olcumu alarm yapma, iki ardil dususte bildir
            if low_streak == 2:
                findings.append(f"RSSI kritik (<-92 dBm): {s.timestamp_utc.isoformat()} (yer istasyonu link zayif)")
        if len(samples) >= 3:
            delta = samples[-1].link_rssi - samples[0].link_rssi
            if delta < -7.0:
                findings.append(f"RSSI dusus trendi: {delta:.1f} dB")
        return findings

    def _detect_attitude(self, samples: List[TelemetrySample]) -> List[str]:
        """Detect unrealistic attitude limits or rates."""
        findings: List[str] = []
        rates = self._compute_attitude_rates(samples)
        for s, rate in rates:
            # Tek adimlik sertlikleri filtrelemek icin esikler yumusatildi
            if abs(rate.roll_rate) > 35.0 or abs(rate.pitch_rate) > 35.0:
                findings.append(f"Tutum hizi limit disi: {s.timestamp_utc.isoformat()} (agresif manevra)")
            if abs(rate.yaw_rate) > 55.0:
                findings.append(f"Yaw ani degisim >55 deg/s: {s.timestamp_utc.isoformat()}")
        for s in samples:
            if abs(s.roll_deg) > 40.0 or abs(s.pitch_deg) > 40.0:
                findings.append(f"Roll/Pitch >40 deg: {s.timestamp_utc.isoformat()} (tutum limit asildi)")
        return findings

    def _compute_attitude_rates(self, samples: List[TelemetrySample]) -> List[Tuple[TelemetrySample, _ChangeRate]]:
        """Compute attitude rates between consecutive samples."""
        rates: List[Tuple[TelemetrySample, _ChangeRate]] = []
        for prev, curr in zip(samples, samples[1:]):
            dt = (curr.timestamp_utc - prev.timestamp_utc).total_seconds() or 1e-6
            # Tutum degisim hizlari
            roll_rate = (curr.roll_deg - prev.roll_deg) / dt
            pitch_rate = (curr.pitch_deg - prev.pitch_deg) / dt
            yaw_rate = (curr.yaw_deg - prev.yaw_deg) / dt
            rates.append((curr, _ChangeRate(roll_rate, pitch_rate, yaw_rate)))
        return rates

    def _detect_flight_mode_sequence(self, samples: List[TelemetrySample]) -> List[str]:
        """Check for valid flight mode ordering."""
        findings: List[str] = []
        expected_order = [FlightMode.MANUAL, FlightMode.AUTO, FlightMode.RTL]
        # Sira kontrolu: ilk gorulen indekslerin artmasi beklenir
        first_seen = {mode: None for mode in expected_order}
        for idx, s in enumerate(samples):
            if s.flight_mode in first_seen and first_seen[s.flight_mode] is None:
                first_seen[s.flight_mode] = idx
        indices = [first_seen[m] for m in expected_order if first_seen[m] is not None]
        if indices != sorted(indices) or len(indices) != len([m for m in expected_order if first_seen[m] is not None]):
            findings.append("Flight mode sirasi beklenen MANUAL -> AUTO -> RTL degil")
        return findings

    def _compute_severity(self, anomalies: Dict[str, Union[List[str], str]]) -> str:
        """Compute overall severity."""
        # Kritik anahtarlar
        critical_keys = ("kritik", "fix yok", "hizli", "limit disi", "ani", ">35", ">45")
        has_any = False
        for key, msgs in anomalies.items():
            if key == "severity":
                continue
            if not isinstance(msgs, list):
                continue
            if msgs:
                has_any = True
            for msg in msgs:
                if any(token in msg for token in critical_keys):
                    return "high"
        if has_any:
            return "medium"
        return "low"
