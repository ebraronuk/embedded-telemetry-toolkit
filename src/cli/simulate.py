"""CLI for running UAV telemetry simulations."""
import argparse
from pathlib import Path

from ..telemetry.simulator import UAVTelemetrySimulator


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Simulate UAV telemetry and write CSV log.")
    parser.add_argument(
        "--duration",
        type=int,
        required=True,
        help="Simulation duration in seconds.",
    )
    parser.add_argument(
        "--frequency",
        type=float,
        default=5.0,
        help="Telemetry frequency (Hz).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("logs/simulated_flight.log"),
        help="Output CSV path.",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point for simulation CLI."""
    # Argümanları al
    args = parse_args()

    simulator = UAVTelemetrySimulator()
    simulator.simulate(duration_s=args.duration, frequency_hz=args.frequency, output_path=args.output)

    # Kullanıcıya özet ver
    print(f"Simülasyon tamamlandı: {args.output}")


if __name__ == "__main__":
    main()
