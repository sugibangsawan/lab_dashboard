"""Shared Streamlit helpers for Unit D dashboards."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from lab_dashboard.data import UNITS, metric_status


def selected_unit() -> str:
    unit = st.session_state.get("unit", "C")
    return unit if unit in UNITS else "C"

PLANKTON_GROUP_COLORS = {
    "Green Algae": "#22c55e",
    "Blue Green Algae": "#0ea5e9",
    "Diatom": "#a16207",
    "Golden Green Algae": "#eab308",
    "Euglenophyta": "#84cc16",
    "Dinoflagellata": "#ef4444",
    "Protozoa": "#a855f7",
    "Zooplankton": "#6366f1",
}

POND_COLORS = {
    "D2": "#0ea5e9",
    "D3": "#22c55e",
    "D5": "#f59e0b",
    "D7": "#a855f7",
    "D8": "#ef4444",
    "D9": "#14b8a6",
    "C1": "#0ea5e9",
    "C2": "#22c55e",
    "C3": "#f59e0b",
    "C5": "#a855f7",
    "C6": "#ef4444",
    "C7": "#14b8a6",
    "C9": "#6366f1",
    "C10": "#ec4899",
    "C12": "#84cc16",
    "Tandon": "#64748b",
}

STATUS_STYLE = {
    "ok": ("#166534", "#dcfce7"),
    "warn": ("#854d0e", "#fef9c3"),
    "alert": ("#991b1b", "#fee2e2"),
    "na": ("#475569", "#f1f5f9"),
}


def fmt(value: object, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "—"
    number = float(value)
    if abs(number) >= 100:
        return f"{number:,.0f}"
    if abs(number) >= 10:
        return f"{number:,.1f}"
    return f"{number:.{digits}f}"


def apply_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2rem;
            max-width: 100%;
            padding-left: 2rem;
            padding-right: 2rem;
        }
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


def _daily_frame(frame: pd.DataFrame, value_columns: list[str], *, extra: str | None = None) -> pd.DataFrame:
    keep = ["Tanggal", *value_columns]
    if extra:
        keep.insert(1, extra)
    subset = frame.loc[:, [column for column in keep if column in frame.columns]].copy()
    subset["Tanggal"] = pd.to_datetime(subset["Tanggal"], errors="coerce").dt.normalize()
    subset = subset.dropna(subset=["Tanggal"])
    long = subset.melt(
        id_vars=["Tanggal"] + ([extra] if extra else []),
        value_vars=[column for column in value_columns if column in subset.columns],
        var_name="Metric",
        value_name="Value",
    ).dropna(subset=["Value"])
    long["Hari"] = long["Tanggal"].dt.strftime("%d %b")
    long["Urutan"] = long["Tanggal"].dt.strftime("%Y-%m-%d")
    return long


PH_METRICS = frozenset({"pH Pagi", "pH Sore"})
PH_Y_SCALE = alt.Scale(domain=[7, 9], nice=False, zero=False)


def _date_ticks(data: pd.DataFrame, max_labels: int = 12) -> list[str]:
    ordered = sorted(data["Urutan"].dropna().unique())
    if len(ordered) <= max_labels:
        return list(ordered)
    indexes = [
        round(index * (len(ordered) - 1) / (max_labels - 1))
        for index in range(max_labels)
    ]
    return list(dict.fromkeys(ordered[index] for index in indexes))


def _date_x_encoding(data: pd.DataFrame) -> alt.X:
    return alt.X(
        "Urutan:O",
        title=None,
        sort="ascending",
        axis=alt.Axis(
            labelAngle=0,
            labelOverlap=True,
            values=_date_ticks(data),
            labelExpr="timeFormat(toDate(datum.value), '%d %b')",
        ),
    )


PERCENT_Y_SCALE = alt.Scale(domain=[0, 100], nice=False, zero=True)


def _count_y_encoding(title: str | None, *, stack: str | None = None) -> alt.Y:
    return alt.Y(
        "Value:Q",
        title=title,
        stack=stack,
        scale=alt.Scale(zero=True, nice=True),
        axis=alt.Axis(format=",.0f"),
    )


def _value_y_encoding(title: str | None, metrics: list[str], *, stack: str | None = None) -> alt.Y:
    if metrics and set(metrics) <= PH_METRICS:
        return alt.Y("Value:Q", title=title, scale=PH_Y_SCALE)
    if metrics and all(metric.endswith(" %") for metric in metrics):
        return alt.Y("Value:Q", title=title, scale=PERCENT_Y_SCALE)
    if metrics and (
        metrics == ["Total Plankton"]
        or (stack is not None and not any(metric.endswith(" %") for metric in metrics))
    ):
        return _count_y_encoding(title, stack=stack)
    return alt.Y("Value:Q", title=title)


def show_chart(chart: alt.Chart) -> None:
    st.altair_chart(chart, width="stretch")


def line_chart(frame: pd.DataFrame, columns: list[str], title: str, y_title: str) -> alt.Chart:
    data = _daily_frame(frame, columns)
    if data.empty:
        return (
            alt.Chart(pd.DataFrame({"Hari": [], "Value": []}))
            .mark_line()
            .encode(x="Hari:N", y=_value_y_encoding(y_title, columns))
            .properties(title=title, height=360)
        )
    return (
        alt.Chart(data)
        .mark_line(point=True)
        .encode(
            x=_date_x_encoding(data),
            y=_value_y_encoding(y_title, columns),
            color=alt.Color("Metric:N", title=None, legend=alt.Legend(orient="top")),
            tooltip=[
                alt.Tooltip("Tanggal:T", title="Tanggal", format="%d %b %Y"),
                alt.Tooltip("Metric:N", title=""),
                alt.Tooltip("Value:Q", title=y_title, format=",.0f"),
            ],
        )
        .properties(title=title, height=360)
    )


def comparison_chart(frame: pd.DataFrame, column: str, ponds: list[str]) -> alt.Chart:
    data = _daily_frame(frame, [column], extra="Kolam")
    data = data.loc[data["Kolam"].isin(ponds)]
    if data.empty:
        return (
            alt.Chart(pd.DataFrame({"Hari": [], "Value": []}))
            .mark_line()
            .encode(x="Hari:N", y=_value_y_encoding(None, [column]))
            .properties(title=column, height=340)
        )
    present = [pond for pond in ponds if pond in set(data["Kolam"])]
    return (
        alt.Chart(data)
        .mark_line(point=True)
        .encode(
            x=_date_x_encoding(data),
            y=_value_y_encoding(None, [column]),
            color=alt.Color(
                "Kolam:N",
                title=None,
                scale=alt.Scale(
                    domain=present,
                    range=[POND_COLORS.get(pond, "#334155") for pond in present],
                ),
                legend=alt.Legend(orient="top"),
            ),
            tooltip=[
                alt.Tooltip("Kolam:N"),
                alt.Tooltip("Tanggal:T", title="Tanggal", format="%d %b %Y"),
                alt.Tooltip("Value:Q", title=column, format=",.0f"),
            ],
        )
        .properties(title=column, height=340)
    )


def stacked_area_chart(frame: pd.DataFrame, columns: list[str], title: str, y_title: str) -> alt.Chart:
    data = _daily_frame(frame, columns)
    if data.empty:
        return (
            alt.Chart(pd.DataFrame({"Hari": [], "Value": []}))
            .mark_area()
            .encode(x="Hari:N", y=_count_y_encoding(y_title, stack="zero"))
            .properties(title=title, height=380)
        )
    present = [column for column in columns if column in set(data["Metric"])]
    rank = {name: index for index, name in enumerate(columns)}
    data["UrutanKelompok"] = data["Metric"].map(rank)
    return (
        alt.Chart(data)
        .mark_area(opacity=0.9, line=True)
        .encode(
            x=_date_x_encoding(data),
            y=_count_y_encoding(y_title, stack="zero"),
            color=alt.Color(
                "Metric:N",
                title=None,
                scale=alt.Scale(
                    domain=present,
                    range=[PLANKTON_GROUP_COLORS.get(column, "#334155") for column in present],
                ),
                legend=alt.Legend(orient="top", columns=4),
            ),
            order=alt.Order("UrutanKelompok:Q", sort="ascending"),
            tooltip=[
                alt.Tooltip("Tanggal:T", title="Tanggal", format="%d %b %Y"),
                alt.Tooltip("Metric:N", title="Kelompok"),
                alt.Tooltip("Value:Q", title=y_title, format=",.0f"),
            ],
        )
        .properties(title=title, height=380)
    )


def latest_bar_chart(frame: pd.DataFrame, column: str, ponds: list[str], title: str) -> alt.Chart:
    subset = frame.loc[frame["Kolam"].isin(ponds), ["Kolam", "Tanggal", column]].dropna(subset=[column])
    if subset.empty:
        return (
            alt.Chart(pd.DataFrame({"Kolam": [], "Value": []}))
            .mark_bar()
            .encode(x="Kolam:N", y=_count_y_encoding("sel"))
            .properties(title=title, height=320)
        )
    latest_index = subset.groupby("Kolam")["Tanggal"].idxmax()
    data = subset.loc[latest_index].rename(columns={column: "Value"})
    present = [pond for pond in ponds if pond in set(data["Kolam"])]
    bars = (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x=alt.X("Kolam:N", title=None, sort=present),
            y=_count_y_encoding("sel"),
            color=alt.Color(
                "Kolam:N",
                title=None,
                scale=alt.Scale(
                    domain=present,
                    range=[POND_COLORS.get(pond, "#334155") for pond in present],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Kolam:N"),
                alt.Tooltip("Tanggal:T", title="Tanggal", format="%d %b %Y"),
                alt.Tooltip("Value:Q", title=column, format=",.0f"),
            ],
        )
    )
    labels = (
        alt.Chart(data)
        .mark_text(dy=-8, fontSize=11)
        .encode(
            x=alt.X("Kolam:N", sort=present),
            y=alt.Y("Value:Q"),
            text=alt.Text("Value:Q", format=",.0f"),
        )
    )
    return (bars + labels).properties(title=title, height=320)


def status_badge(column: str, value: object, farm: str = "D") -> str:
    number = None if value is None or pd.isna(value) else float(value)
    status = metric_status(column, number, farm=farm)
    fg, bg = STATUS_STYLE[status]
    label = {"ok": "OK", "warn": "Perhatian", "alert": "Tinggi", "na": "Kosong"}[status]
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 8px;'
        f'border-radius:999px;font-size:0.78rem;">{label}</span>'
    )


def kpi_card(label: str, value: object, unit: str, column: str, farm: str = "D") -> None:
    number = None if value is None or pd.isna(value) else float(value)
    status = metric_status(column, number, farm=farm)
    fg, bg = STATUS_STYLE[status]
    st.markdown(
        f"""
        <div style="background:{bg};border:1px solid {fg}22;border-radius:12px;padding:12px 14px;min-height:92px;">
            <div style="font-size:0.78rem;color:{fg};opacity:0.85;">{label}</div>
            <div style="font-size:1.45rem;font-weight:700;color:{fg};line-height:1.2;">{fmt(value)}</div>
            <div style="font-size:0.75rem;color:{fg};opacity:0.75;">{unit}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
