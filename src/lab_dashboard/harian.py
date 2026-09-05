"""Harian dashboard for Unit D ponds from sheet harian [D]."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from lab_dashboard.data import latest_row, load_harian_data, ponds_in_data
from lab_dashboard.ui import apply_style, comparison_chart, fmt, kpi_card, line_chart, status_badge

KPI_GROUPS = [
    ("Pakan", [("Pakan Harian", "kg")]),
    ("pH", [("pH Pagi", "pH"), ("pH Sore", "pH"), ("Diff pH", "Δ")]),
    ("Kecerahan", [("Kecerahan Pagi", "cm"), ("Kecerahan Sore", "cm"), ("Diff Kecerahan", "cm")]),
]


@st.cache_data(ttl=120, max_entries=4, refresh_mode="background", show_spinner="Mengambil data harian (pH & kecerahan)...")
def _cached_data() -> pd.DataFrame:
    return load_harian_data()


def render_overview(frame: pd.DataFrame, ponds: list[str]) -> None:
    st.subheader("Profil kolam")
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
                f"Pakan {fmt(row.get('Pakan Harian'), 0)} kg<br>"
                f"pH {fmt(row.get('pH Pagi'))} / {fmt(row.get('pH Sore'))} "
                f"(Δ {fmt(row.get('Diff pH'))})<br>"
                f"Kecerahan {fmt(row.get('Kecerahan Pagi'), 0)} / "
                f"{fmt(row.get('Kecerahan Sore'), 0)} cm "
                f"(Δ {fmt(row.get('Diff Kecerahan'), 0)}) "
                f"{status_badge('Kecerahan Pagi', row.get('Kecerahan Pagi'))}",
                unsafe_allow_html=True,
            )

    st.subheader("Perbandingan antar kolam")
    left, right = st.columns(2)
    with left:
        st.plotly_chart(comparison_chart(frame, "Pakan Harian", ponds), width="stretch")
        st.plotly_chart(comparison_chart(frame, "pH Pagi", ponds), width="stretch")
        st.plotly_chart(comparison_chart(frame, "Kecerahan Pagi", ponds), width="stretch")
        st.plotly_chart(comparison_chart(frame, "Diff pH", ponds), width="stretch")
    with right:
        st.plotly_chart(comparison_chart(frame, "pH Sore", ponds), width="stretch")
        st.plotly_chart(comparison_chart(frame, "Kecerahan Sore", ponds), width="stretch")
        st.plotly_chart(comparison_chart(frame, "Diff Kecerahan", ponds), width="stretch")


def render_pond(frame: pd.DataFrame, pond: str) -> None:
    subset = frame.loc[frame["Kolam"] == pond].copy()
    if subset.empty:
        st.warning(f"Belum ada data untuk kolam {pond}.")
        return

    latest = subset.iloc[-1]
    first = subset.iloc[0]
    st.subheader(f"Profil kolam {pond}")
    info = st.columns(4)
    info[0].metric("Tanggal terakhir", latest["Tanggal"].strftime("%d %b %Y"))
    info[1].metric("DOC", fmt(latest.get("DOC"), 0))
    info[2].metric("Hari tercatat", str(len(subset)))
    info[3].metric(
        "Periode",
        f"{first['Tanggal'].strftime('%d %b')} – {latest['Tanggal'].strftime('%d %b')}",
    )

    for title, metrics in KPI_GROUPS:
        st.markdown(f"**{title}**")
        cols = st.columns(len(metrics))
        for col, (name, unit) in zip(cols, metrics, strict=True):
            with col:
                kpi_card(name, latest.get(name), unit, name)

    st.markdown("")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(
            line_chart(subset, ["Pakan Harian"], "Pakan harian", "kg"),
            width="stretch",
        )
        st.plotly_chart(
            line_chart(subset, ["pH Pagi", "pH Sore"], "pH pagi & sore", "pH"),
            width="stretch",
        )
        st.plotly_chart(
            line_chart(subset, ["Diff pH"], "Diff pH (sore − pagi)", "Δ pH"),
            width="stretch",
        )
    with c2:
        st.plotly_chart(
            line_chart(
                subset,
                ["Kecerahan Pagi", "Kecerahan Sore"],
                "Kecerahan pagi & sore",
                "cm",
            ),
            width="stretch",
        )
        st.plotly_chart(
            line_chart(
                subset,
                ["Diff Kecerahan"],
                "Diff kecerahan (sore − pagi)",
                "cm",
            ),
            width="stretch",
        )

    table = subset.copy()
    table["Tanggal"] = table["Tanggal"].dt.strftime("%d %b %Y")
    display_cols = ["Tanggal", "DOC"] + [
        col for _, metrics in KPI_GROUPS for col, _ in metrics if col in table.columns
    ]
    st.subheader("Riwayat harian")
    st.dataframe(table[display_cols], hide_index=True, width="stretch")


def page() -> None:
    apply_style()
    st.title("Lab Harian Unit D")
    st.caption("Data live dari sheet **harian [D]** · Pakan, pH, dan kecerahan per kolam")

    sidebar = st.sidebar
    sidebar.header("Kolam")
    if sidebar.button("Muat ulang data", width="stretch", key="reload_harian"):
        _cached_data.clear()

    try:
        frame = _cached_data()
    except Exception as exc:
        st.error(f"Gagal mengambil Google Sheet: {exc}")
        st.stop()

    ponds = ponds_in_data(frame)
    growout = [pond for pond in ponds if pond != "Tandon"]
    latest_date = frame["Tanggal"].max().strftime("%d %b %Y")
    sidebar.caption(f"Update terakhir di sheet: **{latest_date}**")
    sidebar.caption(f"{len(frame)} baris · {len(growout)} kolam budidaya")

    pages = ["Ringkasan"] + ponds
    page_name = sidebar.radio("Lihat", pages, key="harian_page")

    if page_name == "Ringkasan":
        render_overview(frame, ponds)
    else:
        render_pond(frame, page_name)
