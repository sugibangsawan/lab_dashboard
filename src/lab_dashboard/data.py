"""Fetch and clean Lab Lengkap Unit D data from the public Google Sheet."""

from __future__ import annotations

import io
from datetime import datetime
from urllib.request import Request, urlopen

import pandas as pd

SHEET_ID = "1Ge2ghdKDu6Q6AcbCIB71tIzdYvpvAE0eDUrvTtxWWfM"
SHEET_GID = "2083899917"
CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export"
    f"?format=csv&gid={SHEET_GID}"
)

POND_ORDER = ["D2", "D3", "D5", "D7", "D8", "D9", "Tandon"]

NUMERIC_COLUMNS = [
    "DOC",
    "pH Pagi",
    "pH Sore",
    "Salinitas",
    "CO3",
    "HCO3",
    "Alkalinitas",
    "TOM",
    "NH4",
    "NH3",
    "NO3",
    "NO2",
    "Ca",
    "Mg",
    "PO4",
    "Vibrio Hijau",
    "Vibrio Kuning",
    "Swanella",
    "Vibrio Total",
]

# Typical vannamei pond guidance used only for dashboard coloring.
THRESHOLDS: dict[str, dict[str, float]] = {
    "pH Pagi": {"low": 7.5, "high": 8.5, "warn_low": 7.3, "warn_high": 8.7},
    "pH Sore": {"low": 7.5, "high": 8.5, "warn_low": 7.3, "warn_high": 8.7},
    "Salinitas": {"low": 15, "high": 35, "warn_low": 10, "warn_high": 38},
    "Alkalinitas": {"low": 80, "high": 160, "warn_low": 60, "warn_high": 200},
    "TOM": {"high": 80, "warn_high": 100},
    "NH3": {"high": 0.05, "warn_high": 0.10},
    "NH4": {"high": 0.5, "warn_high": 1.0},
    "NO2": {"high": 0.25, "warn_high": 1.0},
    "PO4": {"high": 0.4, "warn_high": 0.6},
    "Vibrio Hijau": {"high": 100, "warn_high": 500},
    "Vibrio Total": {"high": 2000, "warn_high": 5000},
}


def fetch_sheet_csv(timeout: int = 30) -> str:
    request = Request(CSV_URL, headers={"User-Agent": "lab-dashboard/0.1"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8-sig")


def _to_number(value: object) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().replace(",", ".")
    if not text or text in {"-", "—", "n/a", "N/A", "NA"}:
        return None
    text = text.rstrip(".")
    try:
        return float(text)
    except ValueError:
        return None


def _normalize_pond(name: object) -> str | None:
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return None
    pond = str(name).strip()
    if not pond:
        return None
    if pond.upper() in {"TD", "TANDON"}:
        return "Tandon"
    return pond


def _parse_date(value: object) -> datetime | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%d %b %y", "%d %b %Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def load_lab_data(csv_text: str | None = None) -> pd.DataFrame:
    raw = csv_text if csv_text is not None else fetch_sheet_csv()
    frame = pd.read_csv(io.StringIO(raw), header=2)
    frame.columns = [str(column).strip() for column in frame.columns]
    frame = frame.loc[:, ~frame.columns.str.match(r"^Unnamed")]

    if "Tanggal" not in frame.columns or "Kolam" not in frame.columns:
        raise ValueError("Sheet is missing Tanggal or Kolam columns.")

    frame["Kolam"] = frame["Kolam"].map(_normalize_pond)
    frame["Tanggal"] = frame["Tanggal"].map(_parse_date)
    frame = frame.dropna(subset=["Tanggal", "Kolam"])

    for column in NUMERIC_COLUMNS:
        if column in frame.columns:
            frame[column] = frame[column].map(_to_number)
        else:
            frame[column] = pd.NA

    measured = [column for column in NUMERIC_COLUMNS if column != "DOC"]
    has_values = frame[measured].notna().any(axis=1)
    frame = frame.loc[has_values].copy()
    frame = frame.sort_values(["Kolam", "Tanggal"]).reset_index(drop=True)
    return frame


def ponds_in_data(frame: pd.DataFrame) -> list[str]:
    present = set(frame["Kolam"].unique())
    return [pond for pond in POND_ORDER if pond in present] + sorted(
        present.difference(POND_ORDER)
    )


def latest_row(frame: pd.DataFrame, pond: str) -> pd.Series | None:
    subset = frame.loc[frame["Kolam"] == pond]
    if subset.empty:
        return None
    return subset.iloc[-1]


def metric_status(column: str, value: float | None) -> str:
    if value is None or pd.isna(value):
        return "na"
    rules = THRESHOLDS.get(column)
    if not rules:
        return "ok"
    if "low" in rules and value < rules.get("warn_low", rules["low"]):
        return "alert"
    if "high" in rules and value > rules.get("warn_high", rules["high"]):
        return "alert"
    if "low" in rules and value < rules["low"]:
        return "warn"
    if "high" in rules and value > rules["high"]:
        return "warn"
    return "ok"
