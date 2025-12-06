"""UAV telemetry simulator."""
import csv
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

from .schemas import FlightMode, TelemetrySample


class UAVTelemetrySimulator:
    """Generate synthetic UAV telemetry."""

    def __init__(
        self,
        start_lat: float = 37.618805,
        start_lon: float = -122.375416,
        start_altitude_m: float = 5.0,
        start_battery_voltage: float = 16.8,
        start_battery_remaining_pct: float = 100.0,
        start_link_rssi: float = -45.0,
    ) -> None:
        # Başlangıç durumu
        self.lat = start_lat
        self.lon = start_lon
        self.altitude_m = start_altitude_m
        self.ground_speed_mps = 0.5
        self.vertical_speed_mps = 0.0
        self.roll_deg = 0.0
        self.pitch_deg = 0.0
        self.yaw_deg = 90.0
        self.flight_mode = FlightMode.MANUAL
        self.armed = True
        self.battery_voltage = start_battery_voltage
        self.battery_remaining_pct = start_battery_remaining_pct
        self.gps_fix = True
        self.satellites = 14
        self.link_rssi = start_link_rssi
        self._start_time = datetime.utcnow()

    def simulate(self, duration_s: int, frequency_hz: float, output_path: Path) -> None:
        """Run simulation and write CSV log."""
        # Zaman adımı ve toplam örnek
        step_s = 1.0 / max(frequency_hz, 1e-6)
        total_steps = max(int(duration_s * frequency_hz), 1)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "timestamp_utc",
                    "lat",
                    "lon",
                    "altitude_m",
                    "ground_speed_mps",
                    "vertical_speed_mps",
                    "roll_deg",
                    "pitch_deg",
                    "yaw_deg",
                    "flight_mode",
                    "armed",
                    "battery_voltage",
                    "battery_remaining_pct",
                    "gps_fix",
                    "satellites",
                    "link_rssi",
                ]
            )

            for idx in range(total_steps):
                progress = idx / max(total_steps - 1, 1)
                timestamp = self._start_time + timedelta(seconds=idx * step_s)
                self.flight_mode = self._mode_for_progress(progress)
                self._update_state(step_s, progress)
                sample = TelemetrySample(
                    timestamp_utc=timestamp,
                    lat=self.lat,
                    lon=self.lon,
                    altitude_m=self.altitude_m,
                    ground_speed_mps=self.ground_speed_mps,
                    vertical_speed_mps=self.vertical_speed_mps,
                    roll_deg=self.roll_deg,
                    pitch_deg=self.pitch_deg,
                    yaw_deg=self.yaw_deg,
                    flight_mode=self.flight_mode,
                    battery_voltage=self.battery_voltage,
                    battery_remaining_pct=self.battery_remaining_pct,
                    gps_fix=self.gps_fix,
                    satellites=self.satellites,
                    armed=self.armed,
                    link_rssi=self.link_rssi,
                )
                writer.writerow(
                    [
                        sample.timestamp_utc.isoformat(),
                        f"{sample.lat:.7f}",
                        f"{sample.lon:.7f}",
                        f"{sample.altitude_m:.2f}",
                        f"{sample.ground_speed_mps:.2f}",
                        f"{sample.vertical_speed_mps:.2f}",
                        f"{sample.roll_deg:.2f}",
                        f"{sample.pitch_deg:.2f}",
                        f"{sample.yaw_deg:.2f}",
                        sample.flight_mode.value,
                        int(sample.armed),
                        f"{sample.battery_voltage:.2f}",
                        f"{sample.battery_remaining_pct:.2f}",
                        int(sample.gps_fix),
                        self.satellites,
                        f"{sample.link_rssi:.1f}",
                    ]
                )

    def _mode_for_progress(self, progress: float) -> FlightMode:
        """Select flight mode over mission timeline."""
        # Mod geçişi: MANUAL -> AUTO -> RTL
        if progress < 0.25:
            return FlightMode.MANUAL
        if progress < 0.85:
            return FlightMode.AUTO
        return FlightMode.RTL

    def _update_state(self, step_s: float, progress: float) -> None:
        """Update kinematics and health."""
        # Hız hedefi mod bağlı
        target_speed = {
            FlightMode.MANUAL: 8.0,
            FlightMode.AUTO: 15.0,
            FlightMode.RTL: 12.0,
        }[self.flight_mode]
        accel = (target_speed - self.ground_speed_mps) * 0.6
        self.ground_speed_mps = max(0.0, self.ground_speed_mps + accel * step_s + random.gauss(0, 0.05))

        # Başlık ve konum
        heading_rate = 1.5 * math.sin(progress * math.pi * 2)
        self.yaw_deg = (self.yaw_deg + heading_rate * step_s + random.gauss(0, 0.05)) % 360.0
        yaw_rad = math.radians(self.yaw_deg)
        dx = self.ground_speed_mps * math.cos(yaw_rad) * step_s
        dy = self.ground_speed_mps * math.sin(yaw_rad) * step_s
        meters_per_deg_lat = 111_320.0
        meters_per_deg_lon = 111_320.0 * math.cos(math.radians(self.lat) or 1e-6)
        self.lat += dy / meters_per_deg_lat
        self.lon += dx / meters_per_deg_lon

        # İrtifa profili
        if progress < 0.15:
            target_alt = 120.0
        elif progress < 0.85:
            target_alt = 120.0
        else:
            target_alt = 8.0
        climb_cmd = max(min((target_alt - self.altitude_m) * 0.25, 3.0), -3.0)
        self.vertical_speed_mps = climb_cmd + random.gauss(0, 0.05)
        self.altitude_m = max(0.0, self.altitude_m + self.vertical_speed_mps * step_s + random.gauss(0, 0.02))

        # Tutum yumuşatma
        self.roll_deg = 5.0 * math.sin(progress * math.pi * 3) + random.gauss(0, 0.3)
        self.pitch_deg = 2.0 * math.sin(progress * math.pi * 2) + 0.1 * self.vertical_speed_mps + random.gauss(0, 0.2)

        # Batarya tüketimi
        discharge_pct_s = 0.02
        self.battery_remaining_pct = max(0.0, self.battery_remaining_pct - discharge_pct_s * step_s)
        self.battery_voltage = max(13.0, 16.8 * (self.battery_remaining_pct / 100.0) + random.gauss(0, 0.01))

        # Link RSSI düşüşü
        self.link_rssi = max(-110.0, self.link_rssi - 0.02 * step_s + random.gauss(0, 0.1))

        # GPS doğruluğu
        self.gps_fix = random.random() > 0.01
        if self.gps_fix:
            self.satellites = max(8, min(18, int(random.gauss(14, 1.2))))
        else:
            self.satellites = max(4, min(10, int(random.gauss(6, 1.0))))
