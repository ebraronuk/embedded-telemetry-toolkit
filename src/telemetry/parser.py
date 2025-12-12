"""UAV telemetry log parser."""
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

from .schemas import FlightMode, TelemetrySample


class UAVTelemetryParser:
    """Parse telemetry CSV logs into TelemetrySample objects."""

    def parse_line(self, line: str) -> Optional[TelemetrySample]:
        """Parse a single CSV line; return None on errors."""
        cleaned = line.strip()
        # Bos, sadece virgullu veya yorum satirini atla
        if not cleaned or cleaned.strip(",") == "" or cleaned.lstrip().startswith("#"):
            return None

        try:
            row = next(csv.reader([cleaned]))
        except Exception:
            return None

        if len(row) != 16:
            return None

        try:
            timestamp = datetime.fromisoformat(row[0])
            lat = float(row[1])
            lon = float(row[2])
            altitude_m = float(row[3])
            ground_speed_mps = float(row[4])
            vertical_speed_mps = float(row[5])
            roll_deg = float(row[6])
            pitch_deg = float(row[7])
            yaw_deg = float(row[8])
            mode_raw = row[9].strip().upper()
            flight_mode = FlightMode(mode_raw)
            armed = bool(int(row[10]))
            battery_voltage = float(row[11])
            battery_remaining_pct = float(row[12])
            gps_raw = row[13].strip()
            if gps_raw not in ("0", "1"):
                raise ValueError("gps_fix out of range")
            gps_fix = gps_raw == "1"
            satellites = int(row[14])
            link_rssi = float(row[15])
        except (ValueError, IndexError):
            return None

        return TelemetrySample(
            timestamp_utc=timestamp,
            lat=lat,
            lon=lon,
            altitude_m=altitude_m,
            ground_speed_mps=ground_speed_mps,
            vertical_speed_mps=vertical_speed_mps,
            roll_deg=roll_deg,
            pitch_deg=pitch_deg,
            yaw_deg=yaw_deg,
            flight_mode=flight_mode,
            battery_voltage=battery_voltage,
            battery_remaining_pct=battery_remaining_pct,
            gps_fix=gps_fix,
            satellites=satellites,
            armed=armed,
            link_rssi=link_rssi,
        )

    def parse_file(self, path: Union[str, Path]) -> List[TelemetrySample]:
        """Read a telemetry log file and parse all valid lines."""
        if isinstance(path, str):
            path = Path(path)
        samples: List[TelemetrySample] = []
        with path.open("r", newline="") as f:
            reader = enumerate(f)
            for idx, line in reader:
                # Baslik satirini atla
                if idx == 0 and line.lower().startswith("timestamp_utc"):
                    continue
                sample = self.parse_line(line)
                if sample is not None:
                    samples.append(sample)
        return samples
