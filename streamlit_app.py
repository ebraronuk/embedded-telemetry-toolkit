"""Streamlit dashboard for UAV telemetry."""
import sys
from datetime import datetime
from pathlib import Path
from typing import List

import altair as alt
import pandas as pd
import streamlit as st

# Modul yolu ayari
ROOT = Path(__file__).resolve().parent
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

from telemetry.analyzer import TelemetryAnalyzer  # type: ignore
from telemetry.parser import UAVTelemetryParser  # type: ignore
from telemetry.simulator import UAVTelemetrySimulator  # type: ignore
from telemetry.schemas import TelemetrySample  # type: ignore


def _init_state() -> None:
    """Ensure shared state exists."""
    # Basit durum saklama
    st.session_state.setdefault("selected_path", None)
    st.session_state.setdefault("samples", None)
    st.session_state.setdefault("df", None)
    st.session_state.setdefault("report", None)


def _samples_to_frame(samples: List[TelemetrySample]) -> pd.DataFrame:
    """Convert samples to DataFrame."""
    # Veri cercevesi kur
    return pd.DataFrame(
        [
            {
                "timestamp_utc": s.timestamp_utc,
                "altitude_m": s.altitude_m,
                "battery_remaining_pct": s.battery_remaining_pct,
                "link_rssi": s.link_rssi,
                "ground_speed_mps": s.ground_speed_mps,
                "vertical_speed_mps": s.vertical_speed_mps,
                "roll_deg": s.roll_deg,
                "pitch_deg": s.pitch_deg,
                "yaw_deg": s.yaw_deg,
                "flight_mode": s.flight_mode.value,
            }
            for s in samples
        ]
    )


def _plot_charts(df: pd.DataFrame) -> None:
    """Render charts."""
    # Zaman indeksle
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
    st.caption("İrtifa değişimi uçuş stabilitesini ve görev profilini yorumlamak için kullanılır.")
    st.divider()

    st.subheader("Battery Remaining vs Time")
    st.altair_chart(_line("battery_remaining_pct", "Battery Remaining (%)", "#2ca02c"), use_container_width=True)
    st.caption("Batarya yüzdesi görev sonunda iniş için yeterli enerji olup olmadığını gösterir.")
    st.divider()

    st.subheader("RSSI vs Time")
    st.altair_chart(_line("link_rssi", "Link RSSI (dBm)", "#d62728"), use_container_width=True)
    st.caption("Link RSSI, yer istasyonu ile haberleşme sağlığı için kritik bir metriktir.")


def _print_anomalies(report: dict) -> None:
    """Show anomaly tables."""
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


def _run_pipeline(path: Path) -> None:
    """Parse and analyze selected log."""
    parser = UAVTelemetryParser()
    samples = parser.parse_file(path)
    if not samples:
        st.session_state["samples"] = None
        st.session_state["df"] = None
        st.session_state["report"] = None
        st.session_state["selected_path"] = None
        return

    df = _samples_to_frame(samples)
    analyzer = TelemetryAnalyzer()
    report = analyzer.analyze(samples)

    st.session_state["samples"] = samples
    st.session_state["df"] = df
    st.session_state["report"] = report
    st.session_state["selected_path"] = path


def main() -> None:
    """Main Streamlit app."""
    st.set_page_config(page_title="UAV Telemetry Toolkit", layout="wide")
    st.title("UAV Telemetry Toolkit")
    _init_state()

    log_dir = ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    tab_sim, tab_analysis, tab_charts, tab_anomalies = st.tabs(
        ["Simülasyon", "Analiz", "Grafikler", "Anomali Karnesi"]
    )

    with tab_sim:
        st.subheader("Simülasyon")
        duration = st.slider("Simülasyon Süresi (s)", min_value=10, max_value=900, value=120, step=10)
        frequency = st.slider("Frekans (Hz)", min_value=1.0, max_value=20.0, value=5.0, step=0.5)
        start_sim = st.button("Simülasyonu Başlat")
        uploaded = st.file_uploader("Log Dosyası Yükle", type=["log", "csv"])

        if start_sim:
            # Simulasyon üret
            output_path = log_dir / f"sim_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.log"
            simulator = UAVTelemetrySimulator()
            simulator.simulate(duration_s=duration, frequency_hz=frequency, output_path=output_path)
            _run_pipeline(output_path)
            st.success(f"Simülasyon tamamlandı: {output_path}")

        if uploaded is not None:
            # Yüklenen dosyayı sakla
            tmp_path = log_dir / f"upload_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.log"
            tmp_path.write_bytes(uploaded.read())
            _run_pipeline(tmp_path)
            st.info(f"Yüklenen dosya işlendi: {tmp_path}")

    with tab_analysis:
        st.subheader("Analiz Özeti")
        if st.session_state["df"] is None:
            st.warning("Önce simülasyon başlatın veya bir log dosyası yükleyin.")
        else:
            df = st.session_state["df"]
            report = st.session_state["report"]
            path = st.session_state["selected_path"]
            st.write(f"Kaynak dosya: `{path}`")
            st.write(f"Kayıt sayısı: {len(df)}")
            st.divider()
            st.json(report)

    with tab_charts:
        st.subheader("Grafikler")
        if st.session_state["df"] is None:
            st.warning("Grafik için veri yok. Simülasyon çalıştırın veya log yükleyin.")
        else:
            _plot_charts(st.session_state["df"])

    with tab_anomalies:
        st.subheader("Anomali Karnesi")
        if st.session_state["report"] is None:
            st.warning("Anomali raporu için veri yok.")
        else:
            _print_anomalies(st.session_state["report"])


if __name__ == "__main__":
    main()
