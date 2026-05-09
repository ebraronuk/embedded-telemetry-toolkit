"""Ucus saglik karnesi ve harita ihrac CLI'i."""
import argparse
import sys
from pathlib import Path

# Windows konsolunda Turkce karakterler bozulmasin diye stdout'u UTF-8'e cek
try:
    sys.stdout.reconfigure(encoding="utf-8")  # Python 3.7+
except Exception:
    pass

from ..telemetry.analyzer import TelemetryAnalyzer
from ..telemetry.flight_score import compute_flight_health
from ..telemetry.geo import collect_anomaly_points, to_geojson_string, to_kml
from ..telemetry.parser import UAVTelemetryParser
from ..telemetry.report import build_report_payload, to_html, to_json, to_markdown


def parse_args() -> argparse.Namespace:
    """CLI argumanlari."""
    p = argparse.ArgumentParser(description="UAV telemetri log'undan ucus saglik karnesi uret.")
    p.add_argument("logfile", type=Path, help="Telemetri CSV log dosyasi.")
    p.add_argument(
        "--format",
        choices=("md", "html", "json"),
        default="md",
        help="Rapor cikti formati (varsayilan: md).",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Cikti dosyasi yolu. Belirtilmezse stdout'a yazar.",
    )
    p.add_argument(
        "--kml",
        type=Path,
        default=None,
        help="Opsiyonel: ucus izini ve anomali pinlerini KML olarak buraya yaz (Google Earth).",
    )
    p.add_argument(
        "--geojson",
        type=Path,
        default=None,
        help="Opsiyonel: ucus izini GeoJSON olarak buraya yaz.",
    )
    return p.parse_args()


def _write(out_path, content: str) -> None:
    """Dosyaya UTF-8 yaz."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")


def main() -> None:
    """Giris noktasi."""
    args = parse_args()

    if not args.logfile.exists():
        # Standart Unix tarzi: stderr'a yaz, exit kodu 2
        print(f"Hata: log bulunamadi: {args.logfile}", file=sys.stderr)
        sys.exit(2)

    parser = UAVTelemetryParser()
    samples = parser.parse_file(args.logfile)
    if not samples:
        print("Hata: log gecerli ornek icermiyor.", file=sys.stderr)
        sys.exit(3)

    analyzer = TelemetryAnalyzer()
    anomaly_report = analyzer.analyze(samples)
    health = compute_flight_health(samples, anomaly_report)
    payload = build_report_payload(samples, anomaly_report, health, source_path=str(args.logfile))

    # Format dispatch
    if args.format == "md":
        rendered = to_markdown(payload)
    elif args.format == "html":
        rendered = to_html(payload)
    else:
        rendered = to_json(payload)

    if args.output:
        _write(args.output, rendered)
        print(f"Rapor yazildi: {args.output}")
    else:
        # stdout'a dogrudan; pipe edilebilir
        sys.stdout.write(rendered)
        if not rendered.endswith("\n"):
            sys.stdout.write("\n")

    # Harita ihraci (opsiyonel)
    if args.kml or args.geojson:
        # Anomali konum pinleri rapordaki bulgu metinlerinden cikarilir
        points = collect_anomaly_points(samples, anomaly_report)
        if args.kml:
            _write(args.kml, to_kml(samples, anomaly_points=points, name=args.logfile.stem))
            print(f"KML yazildi: {args.kml}")
        if args.geojson:
            _write(args.geojson, to_geojson_string(samples, anomaly_points=points))
            print(f"GeoJSON yazildi: {args.geojson}")


if __name__ == "__main__":
    main()
