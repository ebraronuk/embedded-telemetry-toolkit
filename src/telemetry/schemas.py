"""Data schemas for UAV telemetry."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class FlightMode(str, Enum):
    """Autopilot modes."""

    MANUAL = "MANUAL"
    AUTO = "AUTO"
    RTL = "RTL"  # return-to-launch; safety-critical fail-safe
    LOITER = "LOITER"
    STABILIZE = "STABILIZE"


@dataclass
class TelemetrySample:
    """UAV telemetry sample."""

    timestamp_utc: datetime  # UTC timestamp for synchronization
    lat: float  # latitude (deg)
    lon: float  # longitude (deg)
    altitude_m: float  # altitude MSL (m)
    ground_speed_mps: float  # ground speed (m/s)
    vertical_speed_mps: float  # climb/sink (m/s)
    roll_deg: float  # roll angle (deg)
    pitch_deg: float  # pitch angle (deg)
    yaw_deg: float  # yaw/heading (deg)
    flight_mode: FlightMode  # autopilot mode
    battery_voltage: float  # pack voltage (V)
    battery_remaining_pct: float  # remaining energy (%)
    gps_fix: bool  # GPS solution valid
    satellites: int  # satellites used
    armed: bool  # motors armed
    link_rssi: float  # RF link strength (dBm)
