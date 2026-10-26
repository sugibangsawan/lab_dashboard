"""Simple Streamlit dashboard for Lab Lengkap Unit D ponds."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from lab_dashboard.data import UNITS, filter_visible_rows, load_lab_data, latest_row, ponds_in_data
from lab_dashboard.harian import harian_page
from lab_dashboard.plankton import plankton_page
from lab_dashboard.ui import (
    apply_style,
    comparison_chart,
    fmt,
    kpi_card,
    line_chart,
    CARD_GAP,
    SECTION_GAP,
    section_heading,
    selected_unit,
    show_chart,
    status_badge,
)

KPI_GROUPS = [
    ("Air", [("pH Pagi", "pH pagi"), ("pH Sore", "pH sore"), ("Salinitas", "ppt"), ("Alkalinitas", "ppm")]),
    ("TOM", [("TOM", "ppm")]),
    ("Nutrien", [("NH4", "ppm"), ("NH3", "ppm"), ("NO2", "ppm"), ("PO4", "ppm")]),
    ("Bakteri", [("Vibrio Hijau", "CFU"), ("Vibrio Kuning", "CFU"), ("Swanella", "CFU"), ("Vibrio Total", "CFU")]),
]


@st.cache_data(ttl=120, max_entries=8, refresh_mode="background", show_spinner="Mengambil data dari Google Sheet...")
def _cached_data(unit: str) -> pd.DataFrame:
    return load_lab_data(unit=unit)


def render_overview(frame: pd.DataFrame, ponds: list[str], farm: str = "D") -> None:
    st.subheader("Ringkasan kolam")
    cards = st.columns(len(ponds))
    for column, pond in zip(cards, ponds, strict=True):
        row = latest_row(frame, pond)
        with column:
            if row is None:
                st.info(f"{pond}: tidak ada data")
                continue
            date = row["Tanggal"].strftime("%d %b %Y")
            st.markdown(f"**{pond}**")
            st.caption(f"{date} · DOC {fmt(row.get('DOC'), 0)}")
            st.markdown(
                f"pH {fmt(row.get('pH Pagi'))} / {fmt(row.get('pH Sore'))}<br>"
                f"Alk {fmt(row.get('Alkalinitas'))} · NH₃ {fmt(row.get('NH3'), 3)}<br>"
                f"Vibrio {fmt(row.get('Vibrio Total'), 0)} "
                f"{status_badge('Vibrio Total', row.get('Vibrio Total'), farm=farm)}",
                unsafe_allow_html=True,
            )

    st.subheader("Perbandingan antar kolam")
    show_chart(comparison_chart(frame, "NH4", ponds))
    show_chart(comparison_chart(frame, "NO2", ponds))
    show_chart(comparison_chart(frame, "Vibrio Hijau", ponds))
    show_chart(comparison_chart(frame, "Vibrio Kuning", ponds))


def render_pond(frame: pd.DataFrame, pond: str, farm: str = "D") -> None:
    subset = frame.loc[frame["Kolam"] == pond].copy()
    if subset.empty:
        st.warning(f"Belum ada data untuk kolam {pond}.")
        return

    latest = subset.iloc[-1]
    first = subset.iloc[0]
    st.subheader(f"Kolam {pond}")
    info = st.columns(4)
    info[0].metric("Tanggal terakhir", latest["Tanggal"].strftime("%d %b %Y"))
    info[1].metric("DOC", fmt(latest.get("DOC"), 0))
    info[2].metric("Sampel", str(len(subset)))
    info[3].metric(
        "Periode",
        f"{first['Tanggal'].strftime('%d %b')} – {latest['Tanggal'].strftime('%d %b')}",
    )

    with st.container(gap=SECTION_GAP):
        for index, (title, metrics) in enumerate(KPI_GROUPS):
            section_heading(title, spaced=index > 0)
            cols = st.columns(len(metrics), gap=CARD_GAP)
            for col, (name, unit) in zip(cols, metrics, strict=True):
                with col:
                    kpi_card(name, latest.get(name), unit, name, farm=farm)

    st.markdown("")
    if farm not in {"B", "C"}:
        show_chart(line_chart(subset, ["pH Pagi", "pH Sore"], "pH pagi & sore", "pH"))
        show_chart(line_chart(subset, ["Salinitas"], "Salinitas", "ppt"))
    show_chart(line_chart(subset, ["TOM"], "TOM", "ppm"))
    show_chart(line_chart(subset, ["NH4", "NH3", "NO2", "PO4"], "NH4, NH3, NO2, PO4", "ppm"))
    show_chart(
        line_chart(
            subset,
            ["Vibrio Hijau", "Vibrio Kuning", "Swanella", "Vibrio Total"],
            "Vibrio",
            "CFU",
        )
    )

    table = subset.drop(columns=["Kolam"]).copy()
    table["Tanggal"] = table["Tanggal"].dt.strftime("%d %b %Y")
    display_cols = ["Tanggal", "DOC"] + [
        col
        for _, metrics in KPI_GROUPS
        for col, _ in metrics
        if col in table.columns
    ]
    st.subheader("Riwayat lab")
    st.dataframe(table[display_cols], hide_index=True, width="stretch")


def lab_page() -> None:
    unit = selected_unit()
    config = UNITS[unit]
    apply_style()
    st.title(config.lab_title)
    st.caption(config.lab_caption)

    sidebar = st.sidebar
    sidebar.header("Kolam")
    if sidebar.button("Muat ulang data", width="stretch", key="reload_lab"):
        _cached_data.clear()

    try:
        frame = filter_visible_rows(_cached_data(unit))
    except Exception as exc:
        st.error(f"Gagal mengambil Google Sheet: {exc}")
        st.stop()

    if frame.empty:
        st.warning("Belum ada data yang bisa ditampilkan untuk tanggal ini.")
        st.stop()

    ponds = ponds_in_data(frame, unit=unit)
    growout = [pond for pond in ponds if pond != "Tandon"]
    latest_date = frame["Tanggal"].max().strftime("%d %b %Y")
    sidebar.caption(f"Update terakhir di sheet: **{latest_date}**")
    sidebar.caption(f"{len(frame)} baris · {len(growout)} kolam budidaya")

    pages = ["Ringkasan"] + ponds
    page_name = sidebar.radio("Lihat", pages, key=f"lab_page_{unit}")

    if page_name == "Ringkasan":
        render_overview(frame, ponds, farm=unit)
    else:
        render_pond(frame, page_name, farm=unit)


def run() -> None:
    with st.sidebar:
        st.segmented_control(
            "Unit",
            options=["B", "C", "D"],
            default="C",
            required=True,
            format_func=lambda unit: f"Unit {unit}",
            key="unit",
            width="stretch",
        )

    selected_page = st.navigation(
        [
            st.Page(
                lab_page,
                title="Lab Lengkap",
                icon=":material/science:",
                url_path="lab",
                default=True,
            ),
            st.Page(
                harian_page,
                title="Lab Harian",
                icon=":material/calendar_today:",
                url_path="harian",
            ),
            st.Page(
                plankton_page,
                title="Lab Plankton",
                icon=":material/biotech:",
                url_path="plankton",
            ),
        ],
        position="top",
    )
    selected_page.run()


if __name__ == "__main__":
    st.set_page_config(
        page_title="Lab Dashboard",
        page_icon=":material/water_drop:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    run()
