"""CLI for analyzing UAV telemetry logs."""
import argparse
from pathlib import Path

from ..telemetry.analyzer import TelemetryAnalyzer
from ..telemetry.parser import UAVTelemetryParser


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Analyze UAV telemetry log for anomalies.")
    parser.add_argument("logfile", type=Path, help="Path to telemetry CSV log.")
    return parser.parse_args()


def _print_report(report: dict) -> None:
    """Pretty-print anomalies in Turkish."""
    # Boş ve temiz rapor
    if all(len(v) == 0 for v in report.values()):
        print("Anomali bulunamadı.")
        return

    def _print_section(title: str, items: list[str]) -> None:
        # Bölüm çıktısı
        print(f"{title}:")
        if not items:
            print("  - Yok")
        else:
            for item in items:
                print(f"  - {item}")

    _print_section("Batarya", report.get("battery", []))
    _print_section("GPS", report.get("gps", []))
    _print_section("Tutum", report.get("attitude", []))
    _print_section("RSSI", report.get("rssi", []))
    _print_section("Flight Mode", report.get("flight_mode", []))


def main() -> None:
    """Entry point for analysis CLI."""
    # Argümanları al
    args = parse_args()

    parser = UAVTelemetryParser()
    samples = parser.parse_file(args.logfile)

    analyzer = TelemetryAnalyzer()
    report = analyzer.analyze(samples)

    # Raporu yazdır
    _print_report(report)


if __name__ == "__main__":
    main()
