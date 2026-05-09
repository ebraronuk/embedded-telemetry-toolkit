"""Streamlit dashboard for UAV telemetry."""
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

# Modul yolu ayari
ROOT = Path(__file__).resolve().parent
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

from telemetry.analyzer import TelemetryAnalyzer  # type: ignore
from telemetry.flight_score import FlightHealthReport, compute_flight_health  # type: ignore
from telemetry.geo import (  # type: ignore
    bounding_box,
    collect_anomaly_points,
    to_geojson_string,
    to_kml,
)
from telemetry.parser import UAVTelemetryParser  # type: ignore
from telemetry.report import build_report_payload, to_html, to_json, to_markdown  # type: ignore
from telemetry.simulator import UAVTelemetrySimulator  # type: ignore
from telemetry.schemas import TelemetrySample  # type: ignore

SEVERITY_COLORS = {"low": "#2ca02c", "medium": "#ff7f0e", "high": "#d62728"}
# Pydeck pin renkleri (RGBA, 0-255)
PIN_RGBA = {"low": [80, 180, 80, 200], "medium": [255, 140, 30, 220], "high": [220, 40, 40, 230]}
# Harita acilirken merkezlenecek varsayilan nokta (Istanbul / Kilyos)
DEFAULT_MAP_LAT = 41.2486
DEFAULT_MAP_LON = 29.0420


def _init_state() -> None:
    """Ortak durumu kur."""
    # Birincil log icin alanlar
    st.session_state.setdefault("selected_path", None)
    st.session_state.setdefault("samples", None)
    st.session_state.setdefault("df", None)
    st.session_state.setdefault("report", None)
    st.session_state.setdefault("health", None)
    # Ikincil log (karsilastirma sekmesinde)
    st.session_state.setdefault("compare_path", None)
    st.session_state.setdefault("compare_samples", None)
    st.session_state.setdefault("compare_df", None)
    st.session_state.setdefault("compare_report", None)
    st.session_state.setdefault("compare_health", None)


def _samples_to_frame(samples: List[TelemetrySample]) -> pd.DataFrame:
    """TelemetrySample listesini grafik icin DataFrame'e cevir."""
    return pd.DataFrame(
        [
            {
                "timestamp_utc": s.timestamp_utc,
                "lat": s.lat,
                "lon": s.lon,
                "altitude_m": s.altitude_m,
                "battery_remaining_pct": s.battery_remaining_pct,
                "link_rssi": s.link_rssi,
                "ground_speed_mps": s.ground_speed_mps,
                "vertical_speed_mps": s.vertical_speed_mps,
                "roll_deg": s.roll_deg,
                "pitch_deg": s.pitch_deg,
                "yaw_deg": s.yaw_deg,
                "flight_mode": s.flight_mode.value,
                "gps_fix": s.gps_fix,
            }
            for s in samples
        ]
    )


def _render_severity(report: dict) -> None:
    """Severity rozeti."""
    severity = str(report.get("severity", "")).lower()
    if severity not in SEVERITY_COLORS:
        return

    color = SEVERITY_COLORS[severity]
    # Kisa renkli kutu
    st.markdown(
        f"""
        <div style="
            padding: 0.85rem 1rem;
            border-radius: 10px;
            background: {color};
            color: white;
            font-weight: 700;
            font-size: 1.05rem;">
            Genel ciddiyet: {severity.upper()}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _plot_charts(df: pd.DataFrame) -> None:
    """Zaman serisi grafikleri."""
    df = df.copy()
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])

    def _line(y: str, title: str, color: str) -> alt.Chart:
        return (
            alt.Chart(df)
            .mark_line(color=color)
            .encode(
                x=alt.X("timestamp_utc:T", axis=alt.Axis(title="Time (UTC)", format="%H:%M:%S")),
                y=alt.Y(f"{y}:Q", title=title),
                tooltip=[alt.Tooltip("timestamp_utc:T", title="Time"), alt.Tooltip(f"{y}:Q", title=title)],
            )
        )

    st.subheader("Altitude vs Time")
    st.altair_chart(_line("altitude_m", "Altitude (m)", "#1f77b4"), use_container_width=True)
    st.caption("Irtifa degisimi ucus stabilitesini ve gorev profilini yorumlamak icin kullanilir.")
    st.divider()

    st.subheader("Battery Remaining vs Time")
    st.altair_chart(_line("battery_remaining_pct", "Battery Remaining (%)", "#2ca02c"), use_container_width=True)
    st.caption("Batarya yuzdesi gorev sonunda inis icin yeterli enerji olup olmadigini gosterir.")
    st.divider()

    st.subheader("RSSI vs Time")
    st.altair_chart(_line("link_rssi", "Link RSSI (dBm)", "#d62728"), use_container_width=True)
    st.caption("Link RSSI, yer istasyonu ile haberlesme sagligi icin kritik bir metriktir.")


def _print_anomalies(report: dict) -> None:
    """Anomali tablolari."""
    for key, label in [
        ("battery", "Batarya Anomalileri"),
        ("gps", "GPS Anomalileri"),
        ("attitude", "Tutum Anomalileri"),
        ("rssi", "RSSI Anomalileri"),
        ("flight_mode", "Flight Mode Anomalileri"),
    ]:
        st.subheader(label)
        items = report.get(key, [])
        if not items:
            st.info("Yok")
        else:
            st.table(pd.DataFrame(items, columns=["Detay"]))
        st.divider()


def _run_pipeline(path: Path, slot: str = "primary") -> bool:
    """Log'u parse + analiz + skorla. slot='primary' veya 'compare'."""
    parser = UAVTelemetryParser()
    samples = parser.parse_file(path)
    keys = _slot_keys(slot)

    if not samples:
        for k in keys.values():
            st.session_state[k] = None
        return False

    df = _samples_to_frame(samples)
    analyzer = TelemetryAnalyzer()
    report = analyzer.analyze(samples)
    health = compute_flight_health(samples, report)

    st.session_state[keys["samples"]] = samples
    st.session_state[keys["df"]] = df
    st.session_state[keys["report"]] = report
    st.session_state[keys["health"]] = health
    st.session_state[keys["selected_path"]] = path
    return True


def _slot_keys(slot: str) -> Dict[str, str]:
    """Birincil ve ikincil (karsilastirma) durum anahtarlarini ayir."""
    if slot == "compare":
        return {
            "selected_path": "compare_path",
            "samples": "compare_samples",
            "df": "compare_df",
            "report": "compare_report",
            "health": "compare_health",
        }
    return {
        "selected_path": "selected_path",
        "samples": "samples",
        "df": "df",
        "report": "report",
        "health": "health",
    }


def _render_health_card(health: FlightHealthReport, report: dict) -> None:
    """Ucus saglik karnesi: buyuk skor + alt skor barlari."""
    color = SEVERITY_COLORS.get(str(report.get("severity", "low")).lower(), "#666")
    # Buyuk skor kutusu
    st.markdown(
        f"""
        <div style="display:flex; gap:16px; align-items:center; padding: 14px 18px; border-radius: 12px;
                    background: linear-gradient(135deg, {color} 0%, #333 200%); color: white;">
            <div style="font-size: 3rem; font-weight: 800;">{health.overall_score}</div>
            <div style="font-size: 1.3rem; line-height: 1.1;">
                <div style="opacity: 0.9;">Genel Skor / 100</div>
                <div style="font-weight: 700;">Not: {health.grade}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    # Alt skor barlari
    for sub in health.sub_scores:
        col1, col2, col3 = st.columns([1, 4, 3])
        col1.markdown(f"**{sub.name}**")
        col2.progress(sub.score / 100.0)
        col3.caption(f"{sub.score}/100 - {sub.note}")


def _render_download_buttons(samples: List[TelemetrySample], report: dict, health: FlightHealthReport,
                             source_path: Optional[Path]) -> None:
    """Karne sekmesinde rapor + harita ihrac butonlari."""
    payload = build_report_payload(samples, report, health,
                                   source_path=str(source_path) if source_path else "")
    points = collect_anomaly_points(samples, report)

    md_text = to_markdown(payload)
    html_text = to_html(payload)
    json_text = to_json(payload)
    kml_text = to_kml(samples, anomaly_points=points,
                     name=source_path.stem if source_path else "flight")
    geojson_text = to_geojson_string(samples, anomaly_points=points)

    base = source_path.stem if source_path else "report"

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.download_button("Rapor (.md)", md_text, file_name=f"{base}.md", mime="text/markdown")
    c2.download_button("Rapor (.html)", html_text, file_name=f"{base}.html", mime="text/html")
    c3.download_button("Rapor (.json)", json_text, file_name=f"{base}.json", mime="application/json")
    c4.download_button("Harita (.kml)", kml_text, file_name=f"{base}.kml",
                       mime="application/vnd.google-earth.kml+xml")
    c5.download_button("Harita (.geojson)", geojson_text, file_name=f"{base}.geojson",
                       mime="application/geo+json")


def _build_pin_dataframe(points: List[dict]) -> pd.DataFrame:
    """Anomali pinlerini pydeck icin RGBA renkli DF'e cevir."""
    rows = []
    for p in points:
        sev = str(p.get("severity", "low")).lower()
        rgba = PIN_RGBA.get(sev, PIN_RGBA["low"])
        rows.append({
            "lat": float(p["lat"]),
            "lon": float(p["lon"]),
            "category": p.get("category", "anomaly"),
            "label": p.get("label", ""),
            "severity": sev,
            "color_r": rgba[0],
            "color_g": rgba[1],
            "color_b": rgba[2],
            "color_a": rgba[3],
        })
    return pd.DataFrame(rows)


def _render_map(samples: List[TelemetrySample], report: dict) -> None:
    """Pydeck haritasi: ucus izi + anomali pinleri."""
    fix_pts = [(s.lat, s.lon, s.altitude_m) for s in samples if s.gps_fix]
    if not fix_pts:
        st.warning("GPS fix'li ornek yok, harita cizilemiyor.")
        return

    track_df = pd.DataFrame(fix_pts, columns=["lat", "lon", "alt"])
    # Tek bir LineString icin path layer; kaynak DF tek satir
    path_df = pd.DataFrame([{"path": [[lon, lat] for lat, lon, _ in fix_pts]}])

    points = collect_anomaly_points(samples, report)
    pin_df = _build_pin_dataframe(points)

    bb = bounding_box(samples)
    if bb:
        center_lat = (bb[0] + bb[2]) / 2.0
        center_lon = (bb[1] + bb[3]) / 2.0
    else:
        center_lat, center_lon = float(track_df["lat"].mean()), float(track_df["lon"].mean())

    layers = [
        pdk.Layer(
            "PathLayer",
            data=path_df,
            get_path="path",
            get_color=[30, 144, 255, 220],
            width_min_pixels=3,
        ),
        pdk.Layer(
            "ScatterplotLayer",
            data=track_df,
            get_position=["lon", "lat"],
            get_radius=6,
            get_fill_color=[30, 144, 255, 80],
        ),
    ]
    if not pin_df.empty:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=pin_df,
                get_position=["lon", "lat"],
                get_radius=18,
                get_fill_color=["color_r", "color_g", "color_b", "color_a"],
                pickable=True,
                stroked=True,
            )
        )

    view = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=15, pitch=35)
    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view,
        tooltip={"text": "{category}\n{severity}\n{label}"},
        map_style=None,  # acik harita karosu yerine sade arkaplan
    )
    st.pydeck_chart(deck)

    # Pin sayilari ozet
    if not pin_df.empty:
        counts = pin_df["severity"].value_counts().to_dict()
        st.caption(
            f"Anomali pinleri: yuksek={counts.get('high', 0)}, "
            f"orta={counts.get('medium', 0)}, dusuk={counts.get('low', 0)}"
        )
    else:
        st.caption("Eslesen anomali pini yok (timestamp eslemesi yapilamadi veya bulgu yok).")


def _overlay_chart(df_a: pd.DataFrame, df_b: pd.DataFrame, y: str, title: str) -> alt.Chart:
    """Iki uçusun ayni metrikte ust uste karsilastirma grafigi."""
    # Zamani ucus baslangicina goreli saniyeye cevir, boylece farkli zamanlardaki ucuslar yan yana karsilastirilabilir
    def _rel(df: pd.DataFrame, label: str) -> pd.DataFrame:
        d = df.copy()
        d["timestamp_utc"] = pd.to_datetime(d["timestamp_utc"])
        if len(d):
            t0 = d["timestamp_utc"].iloc[0]
            d["t_s"] = (d["timestamp_utc"] - t0).dt.total_seconds()
        else:
            d["t_s"] = []
        d["flight"] = label
        return d

    a = _rel(df_a, "A")
    b = _rel(df_b, "B")
    merged = pd.concat([a, b], ignore_index=True)
    return (
        alt.Chart(merged)
        .mark_line()
        .encode(
            x=alt.X("t_s:Q", title="Gorev zamani (s)"),
            y=alt.Y(f"{y}:Q", title=title),
            color=alt.Color("flight:N", title="Ucus"),
            tooltip=["flight:N", "t_s:Q", f"{y}:Q"],
        )
        .properties(height=240)
    )


def _render_compare_card(label: str, health: FlightHealthReport, report: dict, path: Path) -> None:
    """Karsilastirma sekmesinde tek ucus icin daha kompakt karne."""
    color = SEVERITY_COLORS.get(str(report.get("severity", "low")).lower(), "#666")
    st.markdown(
        f"""
        <div style="padding: 10px 14px; border-radius: 10px; background: {color}; color: white;">
            <div style="opacity: 0.85;">Ucus {label}</div>
            <div style="font-size: 1.8rem; font-weight: 800;">{health.overall_score} / 100 ({health.grade})</div>
            <div style="font-size: 0.85rem; opacity: 0.9;">{path.name}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    rows = [{"Kategori": s.name, "Skor": s.score, "Not": s.note} for s in health.sub_scores]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def main() -> None:
    """Streamlit ana akisi."""
    st.set_page_config(page_title="UAV Telemetry Toolkit", layout="wide")
    st.title("UAV Telemetry Toolkit")
    _init_state()

    log_dir = ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    tab_sim, tab_analysis, tab_charts, tab_anomalies, tab_score, tab_map, tab_compare = st.tabs(
        ["Simulasyon", "Analiz", "Grafikler", "Anomali Karnesi", "Karne", "Harita", "Karsilastirma"]
    )

    with tab_sim:
        st.subheader("Simulasyon")
        duration = st.slider("Simulasyon Suresi (s)", min_value=10, max_value=900, value=120, step=10)
        frequency = st.slider("Frekans (Hz)", min_value=1.0, max_value=20.0, value=5.0, step=0.5)
        start_sim = st.button("Simulasyonu Baslat")
        uploaded = st.file_uploader("Log Dosyasi Yukle", type=["log", "csv"])

        if start_sim:
            # Yeni log dosyasi olustur ve pipeline'i calistir
            output_path = log_dir / f"sim_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.log"
            simulator = UAVTelemetrySimulator()
            simulator.simulate(duration_s=duration, frequency_hz=frequency, output_path=output_path)
            _run_pipeline(output_path)
            st.success(f"Simulasyon tamamlandi: {output_path}")

        if uploaded is not None:
            # Yuklenen dosyayi diske al
            tmp_path = log_dir / f"upload_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.log"
            tmp_path.write_bytes(uploaded.read())
            ok = _run_pipeline(tmp_path)
            if ok:
                st.info(f"Yuklenen dosya islendi: {tmp_path}")
            else:
                st.error("Dosya bozuk veya beklenen CSV semasinda degil.")

    with tab_analysis:
        st.subheader("Analiz Ozeti")
        if st.session_state["df"] is None:
            # Kisa yonlendirme
            st.info("Analiz sonuclarini gormek icin once bir log yukleyin veya simulasyon calistirin.")
            st.warning("Once simulasyon baslatin veya bir log dosyasi yukleyin.")
        else:
            df = st.session_state["df"]
            report = st.session_state["report"]
            path = st.session_state["selected_path"]
            _render_severity(report)
            st.write(f"Kaynak dosya: `{path}`")
            st.write(f"Kayit sayisi: {len(df)}")
            st.divider()
            st.json(report)

    with tab_charts:
        st.subheader("Grafikler")
        if st.session_state["df"] is None:
            st.warning("Grafik icin veri yok. Simulasyon calistirin veya log yukleyin.")
        else:
            _plot_charts(st.session_state["df"])

    with tab_anomalies:
        st.subheader("Anomali Karnesi")
        if st.session_state["report"] is None:
            st.warning("Anomali raporu icin veri yok.")
        else:
            _print_anomalies(st.session_state["report"])

    with tab_score:
        st.subheader("Ucus Saglik Karnesi")
        if st.session_state["health"] is None:
            st.warning("Karne icin veri yok. Simulasyon calistirin veya log yukleyin.")
        else:
            _render_health_card(st.session_state["health"], st.session_state["report"])
            st.divider()
            st.markdown("### Rapor ve Harita Indir")
            _render_download_buttons(
                st.session_state["samples"],
                st.session_state["report"],
                st.session_state["health"],
                st.session_state["selected_path"],
            )

    with tab_map:
        st.subheader("Harita")
        if st.session_state["samples"] is None:
            # Veri yokken bile bos harita gosterelim, kullanici Istanbul'u hemen gorsun
            st.info("Hicbir log yuklenmedi. Simulasyon baslatinca ucus izi burada cizilecek.")
            empty_view = pdk.ViewState(
                latitude=DEFAULT_MAP_LAT,
                longitude=DEFAULT_MAP_LON,
                zoom=11,
                pitch=0,
            )
            st.pydeck_chart(pdk.Deck(layers=[], initial_view_state=empty_view, map_style=None))
        else:
            _render_map(st.session_state["samples"], st.session_state["report"])

    with tab_compare:
        st.subheader("Iki Ucusu Karsilastir")
        st.caption("Ucus A icin ana sekmedeki yuklu/uretilen log kullanilir. Ucus B icin asagidan ikinci log yukleyin.")

        if st.session_state["health"] is None:
            st.warning("Once ana sekmede bir log yukleyin/uretin (Ucus A).")
        else:
            uploaded_b = st.file_uploader("Ucus B icin log yukle", type=["log", "csv"], key="upload_b")
            if uploaded_b is not None:
                tmp_path = log_dir / f"compare_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.log"
                tmp_path.write_bytes(uploaded_b.read())
                if not _run_pipeline(tmp_path, slot="compare"):
                    st.error("Ucus B log dosyasi gecersiz.")
                else:
                    st.success(f"Ucus B yuklendi: {tmp_path}")

            if st.session_state["compare_health"] is not None:
                colA, colB = st.columns(2)
                with colA:
                    _render_compare_card(
                        "A",
                        st.session_state["health"],
                        st.session_state["report"],
                        st.session_state["selected_path"],
                    )
                with colB:
                    _render_compare_card(
                        "B",
                        st.session_state["compare_health"],
                        st.session_state["compare_report"],
                        st.session_state["compare_path"],
                    )

                st.divider()
                st.markdown("#### Metrik karsilastirma (zaman ucus baslangicina gorelidir)")
                df_a = st.session_state["df"]
                df_b = st.session_state["compare_df"]
                st.altair_chart(
                    _overlay_chart(df_a, df_b, "altitude_m", "Irtifa (m)"),
                    use_container_width=True,
                )
                st.altair_chart(
                    _overlay_chart(df_a, df_b, "battery_remaining_pct", "Batarya (%)"),
                    use_container_width=True,
                )
                st.altair_chart(
                    _overlay_chart(df_a, df_b, "link_rssi", "RSSI (dBm)"),
                    use_container_width=True,
                )


if __name__ == "__main__":
    main()
