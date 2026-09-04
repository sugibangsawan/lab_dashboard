"""Shared Streamlit helpers for Unit D dashboards."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lab_dashboard.data import metric_status

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


def _chart_layout(title: str, *, height: int) -> dict[str, object]:
    return dict(
        title=dict(
            text=title,
            x=0,
            xanchor="left",
            y=1,
            yref="container",
            yanchor="top",
            pad=dict(t=2, b=8),
        ),
        height=height,
        margin=dict(l=40, r=16, t=72, b=32),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0,
            xanchor="left",
            bgcolor="rgba(255,255,255,0)",
        ),
        hovermode="x unified",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
    )


def line_chart(frame: pd.DataFrame, columns: list[str], title: str, y_title: str) -> go.Figure:
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
        **_chart_layout(title, height=360),
        xaxis_title=None,
        yaxis_title=y_title,
    )
    fig.update_xaxes(showgrid=True, gridcolor="#eef2f7")
    fig.update_yaxes(showgrid=True, gridcolor="#eef2f7")
    return fig


def comparison_chart(frame: pd.DataFrame, column: str, ponds: list[str]) -> go.Figure:
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
    fig.update_layout(**_chart_layout(column, height=340))
    fig.update_xaxes(showgrid=True, gridcolor="#eef2f7")
    fig.update_yaxes(showgrid=True, gridcolor="#eef2f7")
    return fig


def status_badge(column: str, value: object) -> str:
    number = None if value is None or pd.isna(value) else float(value)
    status = metric_status(column, number)
    fg, bg = STATUS_STYLE[status]
    label = {"ok": "OK", "warn": "Perhatian", "alert": "Tinggi", "na": "Kosong"}[status]
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 8px;'
        f'border-radius:999px;font-size:0.78rem;">{label}</span>'
    )


def kpi_card(label: str, value: object, unit: str, column: str) -> None:
    number = None if value is None or pd.isna(value) else float(value)
    status = metric_status(column, number)
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
