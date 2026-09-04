"""Simple Streamlit dashboard for Lab Lengkap Unit D ponds."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lab_dashboard.data import (
    load_lab_data,
    latest_row,
    metric_status,
    ponds_in_data,
)

st.set_page_config(
    page_title="Lab Data Lengkap Unit D",
    page_icon="🦐",
    layout="wide",
    initial_sidebar_state="expanded",
)

POND_COLORS = {
    "D2": "#0ea5e9",
    "D3": "#22c55e",
    "D5": "#f59e0b",
    "D7": "#a855f7",
    "D8": "#ef4444",
    "D9": "#14b8a6",
    "Tandon": "#64748b",
}

STATUS_STYLE = {
    "ok": ("#166534", "#dcfce7"),
    "warn": ("#854d0e", "#fef9c3"),
    "alert": ("#991b1b", "#fee2e2"),
    "na": ("#475569", "#f1f5f9"),
}

KPI_GROUPS = [
    ("Air", [("pH Pagi", "pH pagi"), ("pH Sore", "pH sore"), ("Salinitas", "ppt"), ("Alkalinitas", "ppm")]),
    ("TOM", [("TOM", "ppm")]),
    ("Nutrien", [("NH4", "ppm"), ("NH3", "ppm"), ("NO2", "ppm"), ("PO4", "ppm")]),
    ("Bakteri", [("Vibrio Hijau", "CFU"), ("Vibrio Kuning", "CFU"), ("Swanella", "CFU"), ("Vibrio Total", "CFU")]),
]


def _fmt(value: object, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "—"
    number = float(value)
    if abs(number) >= 100:
        return f"{number:,.0f}"
    if abs(number) >= 10:
        return f"{number:,.1f}"
    return f"{number:.{digits}f}"


def _apply_style() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.4rem; padding-bottom: 2rem; }
        div[data-testid="stMetric"] {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 0.6rem 0.85rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=120, show_spinner="Mengambil data dari Google Sheet...")
def _cached_data() -> pd.DataFrame:
    return load_lab_data()


def _line_chart(frame: pd.DataFrame, columns: list[str], title: str, y_title: str) -> go.Figure:
    fig = go.Figure()
    for column in columns:
        series = frame[["Tanggal", column]].dropna()
        if series.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=series["Tanggal"],
                y=series[column],
                mode="lines+markers",
                name=column,
                hovertemplate="%{x|%d %b %Y}<br>" + column + ": %{y}<extra></extra>",
            )
        )
    fig.update_layout(
        title=title,
        height=320,
        margin=dict(l=40, r=16, t=48, b=32),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        xaxis_title=None,
        yaxis_title=y_title,
        hovermode="x unified",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#eef2f7")
    fig.update_yaxes(showgrid=True, gridcolor="#eef2f7")
    return fig


def _comparison_chart(frame: pd.DataFrame, column: str, ponds: list[str]) -> go.Figure:
    fig = go.Figure()
    for pond in ponds:
        subset = frame.loc[frame["Kolam"] == pond, ["Tanggal", column]].dropna()
        if subset.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=subset["Tanggal"],
                y=subset[column],
                mode="lines+markers",
                name=pond,
                line=dict(color=POND_COLORS.get(pond, "#334155")),
                hovertemplate=f"{pond}<br>%{{x|%d %b %Y}}<br>{column}: %{{y}}<extra></extra>",
            )
        )
    fig.update_layout(
        title=column,
        height=300,
        margin=dict(l=40, r=16, t=48, b=32),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        hovermode="x unified",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#eef2f7")
    fig.update_yaxes(showgrid=True, gridcolor="#eef2f7")
    return fig


def _status_badge(column: str, value: object) -> str:
    number = None if value is None or pd.isna(value) else float(value)
    status = metric_status(column, number)
    fg, bg = STATUS_STYLE[status]
    label = {"ok": "OK", "warn": "Perhatian", "alert": "Tinggi", "na": "Kosong"}[status]
    return f'<span style="background:{bg};color:{fg};padding:2px 8px;border-radius:999px;font-size:0.78rem;">{label}</span>'


def _kpi_card(label: str, value: object, unit: str, column: str) -> None:
    number = None if value is None or pd.isna(value) else float(value)
    status = metric_status(column, number)
    fg, bg = STATUS_STYLE[status]
    st.markdown(
        f"""
        <div style="background:{bg};border:1px solid {fg}22;border-radius:12px;padding:12px 14px;min-height:92px;">
            <div style="font-size:0.78rem;color:{fg};opacity:0.85;">{label}</div>
            <div style="font-size:1.45rem;font-weight:700;color:{fg};line-height:1.2;">{_fmt(value)}</div>
            <div style="font-size:0.75rem;color:{fg};opacity:0.75;">{unit}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
            st.markdown(f"**{pond}**")
            st.caption(f"{date} · DOC {_fmt(row.get('DOC'), 0)}")
            st.markdown(
                f"pH {_fmt(row.get('pH Pagi'))} / {_fmt(row.get('pH Sore'))}<br>"
                f"Alk {_fmt(row.get('Alkalinitas'))} · NH₃ {_fmt(row.get('NH3'), 3)}<br>"
                f"Vibrio {_fmt(row.get('Vibrio Total'), 0)} {_status_badge('Vibrio Total', row.get('Vibrio Total'))}",
                unsafe_allow_html=True,
            )

    st.subheader("Perbandingan antar kolam")
    left, right = st.columns(2)
    with left:
        st.plotly_chart(_comparison_chart(frame, "NH4", ponds), width="stretch")
        st.plotly_chart(_comparison_chart(frame, "Vibrio Hijau", ponds), width="stretch")
    with right:
        st.plotly_chart(_comparison_chart(frame, "NO2", ponds), width="stretch")
        st.plotly_chart(_comparison_chart(frame, "Vibrio Kuning", ponds), width="stretch")


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
    info[1].metric("DOC", _fmt(latest.get("DOC"), 0))
    info[2].metric("Sampel", str(len(subset)))
    info[3].metric(
        "Periode",
        f"{first['Tanggal'].strftime('%d %b')} – {latest['Tanggal'].strftime('%d %b')}",
    )

    for title, metrics in KPI_GROUPS:
        st.markdown(f"**{title}**")
        cols = st.columns(len(metrics))
        for col, (name, unit) in zip(cols, metrics, strict=True):
            with col:
                _kpi_card(name, latest.get(name), unit, name)

    st.markdown("")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(
            _line_chart(subset, ["pH Pagi", "pH Sore"], "pH pagi & sore", "pH"),
            use_container_width=True,
        )
        st.plotly_chart(
            _line_chart(subset, ["Salinitas"], "Salinitas", "ppt"),
            use_container_width=True,
        )
        st.plotly_chart(
            _line_chart(subset, ["TOM"], "TOM", "ppm"),
            use_container_width=True,
        )
    with c2:
        st.plotly_chart(
            _line_chart(subset, ["NH4", "NH3", "NO2", "PO4"], "NH4, NH3, NO2, PO4", "ppm"),
            use_container_width=True,
        )
        st.plotly_chart(
            _line_chart(
                subset,
                ["Vibrio Hijau", "Vibrio Kuning", "Swanella", "Vibrio Total"],
                "Vibrio",
                "CFU",
            ),
            use_container_width=True,
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
    st.dataframe(table[display_cols], use_container_width=True, hide_index=True)


def main() -> None:
    _apply_style()
    st.title("Lab Data Lengkap Unit D")
    st.caption("Data live dari sheet **lengkap [D]** · Lab Lengkap Unit D Periode Tebar Juni 2026")

    sidebar = st.sidebar
    sidebar.header("Kolam")
    if sidebar.button("Muat ulang data", use_container_width=True):
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
    page = sidebar.radio("Lihat", pages, index=0)

    if page == "Ringkasan":
        render_overview(frame, ponds)
    else:
        render_pond(frame, page)


main()
