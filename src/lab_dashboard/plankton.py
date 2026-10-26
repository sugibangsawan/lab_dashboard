"""Plankton dashboard for units that publish a plankton sheet."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from lab_dashboard.data import (
    PLANKTON_COUNT_COLUMNS,
    UNITS,
    filter_visible_rows,
    latest_row,
    load_plankton_data,
    ponds_in_data,
)
from lab_dashboard.ui import (
    apply_style,
    comparison_chart,
    fmt,
    kpi_card,
    latest_bar_chart,
    line_chart,
    CARD_GAP,
    SECTION_GAP,
    section_heading,
    selected_unit,
    show_chart,
    stacked_area_chart,
)

GROUP_COLUMNS = [
    "Green Algae",
    "Blue Green Algae",
    "Diatom",
    "Golden Green Algae",
    "Euglenophyta",
    "Dinoflagellata",
    "Protozoa",
    "Zooplankton",
]

KPI_GROUPS = [
    ("Kelimpahan", [(column, "sel") for column in GROUP_COLUMNS]),
    ("Komposisi", [(f"{column} %", "%") for column in GROUP_COLUMNS]),
]


@st.cache_data(ttl=120, max_entries=8, refresh_mode="background", show_spinner="Mengambil data plankton...")
def _cached_data(unit: str) -> pd.DataFrame:
    return load_plankton_data(unit=unit)


def _dominant_group(row: pd.Series) -> tuple[str, object]:
    groups = [column for column in PLANKTON_COUNT_COLUMNS if column != "Total Plankton"]
    best = max(groups, key=lambda column: float(row[column]) if pd.notna(row.get(column)) else -1)
    return best, row.get(best)


def render_overview(frame: pd.DataFrame, ponds: list[str]) -> None:
    st.subheader("Ringkasan kolam")
    cards = st.columns(len(ponds))
    for column, pond in zip(cards, ponds, strict=True):
        row = latest_row(frame, pond)
        with column:
            if row is None:
                st.info(f"{pond}: tidak ada data")
                continue
            date = row["Tanggal"].strftime("%d %b %Y")
            group, amount = _dominant_group(row)
            st.markdown(f"**{pond}**")
            st.caption(date)
            st.markdown(
                f"Total {fmt(row.get('Total Plankton'), 0)} sel<br>"
                f"Dominan {group}<br>"
                f"{fmt(amount, 0)} sel",
                unsafe_allow_html=True,
            )

    st.subheader("Perbandingan antar kolam")
    show_chart(latest_bar_chart(frame, "Total Plankton", ponds, "Total Plankton terakhir"))
    show_chart(comparison_chart(frame, "Total Plankton", ponds))
    for column in GROUP_COLUMNS:
        show_chart(comparison_chart(frame, column, ponds))


def render_pond(frame: pd.DataFrame, pond: str) -> None:
    subset = frame.loc[frame["Kolam"] == pond].copy()
    if subset.empty:
        st.warning(f"Belum ada data untuk kolam {pond}.")
        return

    latest = subset.iloc[-1]
    first = subset.iloc[0]
    st.subheader(f"Kolam {pond}")
    info = st.columns(4)
    info[0].metric("Tanggal terakhir", latest["Tanggal"].strftime("%d %b %Y"))
    group, _ = _dominant_group(latest)
    info[1].metric("Dominan", group)
    info[2].metric("Sampel", str(len(subset)))
    info[3].metric(
        "Periode",
        f"{first['Tanggal'].strftime('%d %b')} – {latest['Tanggal'].strftime('%d %b')}",
    )

    with st.container(gap=SECTION_GAP):
        for index, (title, metrics) in enumerate(KPI_GROUPS):
            section_heading(title, spaced=index > 0)
            if title == "Kelimpahan":
                total = latest.get("Total Plankton")
                previous = subset.iloc[-2].get("Total Plankton") if len(subset) >= 2 else None
                delta = None
                if total is not None and pd.notna(total) and previous is not None and pd.notna(previous):
                    delta = float(total) - float(previous)
                st.metric(
                    "Total Plankton",
                    fmt(total, 0),
                    delta=None if delta is None else f"{delta:,.0f} sel",
                    border=True,
                    icon=":material/biotech:",
                )
                st.space(CARD_GAP)
            starts = list(range(0, len(metrics), 4))
            for index, start in enumerate(starts):
                if index:
                    st.space(CARD_GAP)
                chunk = metrics[start : start + 4]
                cols = st.columns(4, gap=CARD_GAP)
                for col, (name, unit) in zip(cols, chunk):
                    with col:
                        kpi_card(name, latest.get(name), unit, name)
    st.space(40)
    show_chart(
        stacked_area_chart(
            subset,
            GROUP_COLUMNS,
            "Total Plankton",
            "sel",
        )
    )
    show_chart(
        line_chart(
            subset,
            [f"{column} %" for column in GROUP_COLUMNS],
            "Komposisi Plankton",
            "%",
        )
    )

    table = subset.copy()
    table["Tanggal"] = table["Tanggal"].dt.strftime("%d %b %Y")
    display_cols = ["Tanggal", *PLANKTON_COUNT_COLUMNS, *[f"{c} %" for c in PLANKTON_COUNT_COLUMNS[:-1]]]
    st.subheader("Riwayat plankton")
    st.dataframe(table[display_cols], hide_index=True, width="stretch")


def plankton_page() -> None:
    unit = selected_unit()
    apply_style()

    config = UNITS[unit]
    if not config.plankton_gid:
        st.title("Lab Plankton")
        st.info(f"Lab Plankton belum tersedia untuk Unit {unit}.")
        return
    st.title(config.plankton_title)
    st.caption(config.plankton_caption)

    sidebar = st.sidebar
    sidebar.header("Kolam")
    if sidebar.button("Muat ulang data", width="stretch", key="reload_plankton"):
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
    page_name = sidebar.radio("Lihat", pages, key=f"plankton_page_{unit}")

    if page_name == "Ringkasan":
        render_overview(frame, ponds)
    else:
        render_pond(frame, page_name)
