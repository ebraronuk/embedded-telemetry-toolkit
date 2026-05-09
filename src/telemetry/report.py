"""Ucus sonrasi rapor uretici (Markdown / HTML / JSON)."""
import json
from html import escape as _html_escape
from typing import Dict, List, Union

from .flight_score import FlightHealthReport
from .geo import path_length_m
from .schemas import TelemetrySample


# Genel ciddiyet etiketinden okunakli metne donusum
_SEVERITY_TR = {"low": "Dusuk", "medium": "Orta", "high": "Yuksek"}

# Anomali kategorisinden Turkce baslik
_CATEGORY_TR = {
    "battery": "Batarya",
    "gps": "GPS",
    "attitude": "Tutum (Attitude)",
    "rssi": "RSSI",
    "flight_mode": "Flight Mode",
}


def build_report_payload(
    samples: List[TelemetrySample],
    anomaly_report: Dict[str, Union[List[str], str]],
    health: FlightHealthReport,
    source_path: str = "",
) -> Dict:
    """Tum cikti formatlarinin paylastigi yapi. JSON cikti dogrudan budur."""
    severity_raw = str(anomaly_report.get("severity", "low")).lower()
    return {
        "source": source_path,
        "severity": severity_raw,
        "severity_tr": _SEVERITY_TR.get(severity_raw, severity_raw),
        "overall_score": health.overall_score,
        "grade": health.grade,
        "sub_scores": [{"name": s.name, "score": s.score, "note": s.note} for s in health.sub_scores],
        "stats": {
            **health.stats.__dict__,
            "path_length_m": round(path_length_m(samples), 1),
        },
        "anomalies": {
            cat: anomaly_report.get(cat, []) if isinstance(anomaly_report.get(cat, []), list) else []
            for cat in _CATEGORY_TR
        },
    }


def to_json(payload: Dict, indent: int = 2) -> str:
    """JSON metni uret. Pretty print varsayilan."""
    return json.dumps(payload, indent=indent, default=str, ensure_ascii=False)


def to_markdown(payload: Dict) -> str:
    """Tek sayfa, gozden gecirilebilir bir Markdown rapor uret."""
    # Baslik ve ozet kart
    lines: List[str] = []
    lines.append("# Ucus Saglik Karnesi")
    if payload.get("source"):
        lines.append(f"_Kaynak: `{payload['source']}`_")
    lines.append("")
    lines.append(f"**Genel Skor:** {payload['overall_score']}/100 - Not: **{payload['grade']}**  ")
    lines.append(f"**Genel Ciddiyet:** {payload['severity_tr']} (`{payload['severity']}`)")
    lines.append("")

    # Mission stats tablosu
    s = payload["stats"]
    lines.append("## Gorev Ozeti")
    lines.append("")
    lines.append("| Metrik | Deger |")
    lines.append("|---|---|")
    lines.append(f"| Ornek sayisi | {s.get('sample_count', 0)} |")
    lines.append(f"| Sure (s) | {s.get('duration_s', 0)} |")
    lines.append(f"| Maks irtifa (m) | {s.get('max_altitude_m', 0)} |")
    lines.append(f"| Min batarya (%) | {s.get('min_battery_pct', 0)} |")
    lines.append(f"| Maks yer hizi (m/s) | {s.get('max_ground_speed_mps', 0)} |")
    lines.append(f"| Min RSSI (dBm) | {s.get('min_rssi_dbm', 0)} |")
    lines.append(f"| GPS kaybi orani | {s.get('gps_loss_ratio', 0)} |")
    lines.append(f"| Yol uzunlugu (m) | {s.get('path_length_m', 0)} |")
    lines.append(f"| Goruluen modlar | {', '.join(s.get('flight_modes_seen', [])) or '-'} |")
    lines.append("")

    # Alt skorlar
    lines.append("## Alt Skorlar")
    lines.append("")
    lines.append("| Kategori | Skor | Not |")
    lines.append("|---|---:|---|")
    for sub in payload["sub_scores"]:
        lines.append(f"| {sub['name']} | {sub['score']} | {sub['note']} |")
    lines.append("")

    # Anomali listesi (kategori basligi altinda)
    lines.append("## Anomaliler")
    lines.append("")
    any_anomaly = False
    for key, title in _CATEGORY_TR.items():
        items = payload["anomalies"].get(key, [])
        lines.append(f"### {title}")
        if not items:
            lines.append("- Yok")
        else:
            any_anomaly = True
            for it in items:
                lines.append(f"- {it}")
        lines.append("")
    if not any_anomaly:
        lines.append("> Hicbir kategoride bulgu yok. Ucus temiz gorunuyor.")
        lines.append("")

    return "\n".join(lines)


def to_html(payload: Dict) -> str:
    """Markdown'a paralel sade bir HTML rapor uret. Stil minimal."""
    # Markdown'i bir defa daha render etmek yerine dogrudan HTML kuruyoruz; bagimliliksiz kalsin
    e = _html_escape
    s = payload["stats"]

    rows_subs = "".join(
        f"<tr><td>{e(sub['name'])}</td><td style='text-align:right'>{sub['score']}</td><td>{e(sub['note'])}</td></tr>"
        for sub in payload["sub_scores"]
    )

    rows_anom_blocks = []
    for key, title in _CATEGORY_TR.items():
        items = payload["anomalies"].get(key, [])
        if items:
            li = "".join(f"<li>{e(str(x))}</li>" for x in items)
            rows_anom_blocks.append(f"<h3>{e(title)}</h3><ul>{li}</ul>")
        else:
            rows_anom_blocks.append(f"<h3>{e(title)}</h3><p><em>Yok</em></p>")

    severity_color = {"low": "#2ca02c", "medium": "#ff7f0e", "high": "#d62728"}.get(payload["severity"], "#666")

    return f"""<!DOCTYPE html>
<html lang="tr"><head><meta charset="utf-8"><title>Ucus Saglik Karnesi</title>
<style>
body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 880px; margin: 24px auto; padding: 0 16px; color: #222; }}
h1 {{ margin-bottom: 4px; }}
.badge {{ display: inline-block; padding: 6px 12px; border-radius: 10px; color: white; font-weight: 700; background: {severity_color}; }}
.score {{ font-size: 2.2rem; font-weight: 700; }}
table {{ border-collapse: collapse; width: 100%; margin: 8px 0 16px; }}
th, td {{ border-bottom: 1px solid #eee; padding: 6px 8px; text-align: left; }}
th {{ background: #fafafa; }}
section {{ margin-bottom: 18px; }}
small {{ color: #888; }}
</style></head><body>
<h1>Ucus Saglik Karnesi</h1>
<small>{e(payload.get('source', ''))}</small>
<section>
  <div class="score">{payload['overall_score']}/100 - Not: <strong>{e(payload['grade'])}</strong></div>
  <div>Genel ciddiyet: <span class="badge">{e(payload['severity_tr'])}</span></div>
</section>

<section>
  <h2>Gorev Ozeti</h2>
  <table>
    <tr><th>Metrik</th><th>Deger</th></tr>
    <tr><td>Ornek sayisi</td><td>{s.get('sample_count', 0)}</td></tr>
    <tr><td>Sure (s)</td><td>{s.get('duration_s', 0)}</td></tr>
    <tr><td>Maks irtifa (m)</td><td>{s.get('max_altitude_m', 0)}</td></tr>
    <tr><td>Min batarya (%)</td><td>{s.get('min_battery_pct', 0)}</td></tr>
    <tr><td>Maks yer hizi (m/s)</td><td>{s.get('max_ground_speed_mps', 0)}</td></tr>
    <tr><td>Min RSSI (dBm)</td><td>{s.get('min_rssi_dbm', 0)}</td></tr>
    <tr><td>GPS kaybi orani</td><td>{s.get('gps_loss_ratio', 0)}</td></tr>
    <tr><td>Yol uzunlugu (m)</td><td>{s.get('path_length_m', 0)}</td></tr>
    <tr><td>Goruluen modlar</td><td>{e(', '.join(s.get('flight_modes_seen', [])) or '-')}</td></tr>
  </table>
</section>

<section>
  <h2>Alt Skorlar</h2>
  <table>
    <tr><th>Kategori</th><th style='text-align:right'>Skor</th><th>Not</th></tr>
    {rows_subs}
  </table>
</section>

<section>
  <h2>Anomaliler</h2>
  {''.join(rows_anom_blocks)}
</section>
</body></html>
"""
