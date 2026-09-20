"""Fetch and clean lab and harian data from public Google Sheets."""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from urllib.request import Request, urlopen

import pandas as pd


@dataclass(frozen=True)
class UnitConfig:
    key: str
    sheet_id: str
    lab_gid: str
    harian_gid: str
    pond_order: tuple[str, ...]
    lab_title: str
    harian_title: str
    lab_caption: str
    harian_caption: str


UNITS: dict[str, UnitConfig] = {
    "D": UnitConfig(
        key="D",
        sheet_id="1Ge2ghdKDu6Q6AcbCIB71tIzdYvpvAE0eDUrvTtxWWfM",
        lab_gid="2083899917",
        harian_gid="1480880170",
        pond_order=("D2", "D3", "D5", "D7", "D8", "D9", "Tandon"),
        lab_title="Lab Data Lengkap Unit D",
        harian_title="Lab Harian Unit D",
        lab_caption="Data live dari sheet **lengkap [D]** · Lab Lengkap Unit D Periode Tebar Juni 2026",
        harian_caption="Data live dari sheet **harian [D]** · Pakan, pH, dan kecerahan per kolam",
    ),
    "C": UnitConfig(
        key="C",
        sheet_id="13UU3WfwOiLPtG2ZgP4nNLpQT0xL0JdkcWS80YEDY85k",
        lab_gid="780883902",
        harian_gid="0",
        pond_order=("C1", "C2", "C3", "C5", "C6", "C7", "C9", "C10", "C12", "Tandon"),
        lab_title="Lab Data Lengkap Unit C",
        harian_title="Lab Harian Unit C",
        lab_caption="Data live dari sheet **Lengkap C** · Lab Lengkap Unit C Periode Tebar September 2026",
        harian_caption="Data live dari sheet **Harian C** · Pakan, pH, dan kecerahan per kolam",
    ),
}

SHEET_ID = UNITS["D"].sheet_id
LAB_SHEET_GID = UNITS["D"].lab_gid
HARIAN_SHEET_GID = UNITS["D"].harian_gid
SHEET_GID = LAB_SHEET_GID
CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export"
    f"?format=csv&gid={SHEET_GID}"
)

POND_ORDER = list(UNITS["D"].pond_order)

JAKARTA = ZoneInfo("Asia/Jakarta")
PUBLISH_TODAY_AFTER = time(18, 0)

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

HARIAN_NUMERIC_COLUMNS = [
    "DOC",
    "Pakan Harian",
    "pH Pagi",
    "pH Sore",
    "Kecerahan Pagi",
    "Kecerahan Sore",
]

HARIAN_FOCUS_COLUMNS = [
    "Pakan Harian",
    "pH Pagi",
    "pH Sore",
    "Kecerahan Pagi",
    "Kecerahan Sore",
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
    "Kecerahan Pagi": {"low": 25, "high": 40, "warn_low": 15, "warn_high": 50},
    "Kecerahan Sore": {"low": 25, "high": 40, "warn_low": 15, "warn_high": 50},
    "Diff pH": {"low": 0.0, "high": 0.5, "warn_low": -0.2, "warn_high": 1.0},
    "Diff Kecerahan": {"low": -10, "high": 10, "warn_low": -15, "warn_high": 15},
}

UNIT_THRESHOLDS: dict[str, dict[str, dict[str, float]]] = {
    "C": {
        "Vibrio Total": {"high": 1000},
        "Vibrio Hijau": {"high": 100, "warn_high": 1000},
        "Vibrio Kuning": {"high": 1000},
    }
}


def sheet_csv_url(gid: str = SHEET_GID, sheet_id: str = SHEET_ID) -> str:
    return (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export"
        f"?format=csv&gid={gid}"
    )


def fetch_sheet_csv(
    timeout: int = 30,
    gid: str = SHEET_GID,
    sheet_id: str = SHEET_ID,
) -> str:
    request = Request(
        sheet_csv_url(gid, sheet_id),
        headers={"User-Agent": "lab-dashboard/0.1"},
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8-sig")


def _unit(unit: str) -> UnitConfig:
    try:
        return UNITS[unit]
    except KeyError as exc:
        raise ValueError(f"Unknown unit {unit!r}. Expected one of {sorted(UNITS)}.") from exc


def _to_number(value: object) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().replace(",", ".")
    if not text or text.upper() in {"-", "—", "N/A", "NA", "TD"}:
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


_MONTHS = {
    "jan": 1,
    "january": 1,
    "januari": 1,
    "feb": 2,
    "february": 2,
    "februari": 2,
    "mar": 3,
    "march": 3,
    "maret": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "mei": 5,
    "jun": 6,
    "june": 6,
    "juni": 6,
    "jul": 7,
    "july": 7,
    "juli": 7,
    "aug": 8,
    "august": 8,
    "agt": 8,
    "agustus": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "okt": 10,
    "oktober": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
    "des": 12,
    "desember": 12,
}


def _parse_date(value: object) -> datetime | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%d %b %y", "%d %b %Y", "%d %B %Y", "%d %B %y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    parts = text.replace(",", " ").split()
    if len(parts) == 3 and parts[0].isdigit() and parts[2].isdigit():
        month = _MONTHS.get(parts[1].lower().rstrip("."))
        if month:
            year = int(parts[2])
            if year < 100:
                year += 2000
            try:
                return datetime(year, month, int(parts[0]))
            except ValueError:
                return None
    return None


def _parse_csv_with_header(csv_text: str) -> pd.DataFrame:
    for header in (0, 1, 2):
        frame = pd.read_csv(io.StringIO(csv_text), header=header)
        frame.columns = [str(column).strip() for column in frame.columns]
        if "Tanggal" in frame.columns and "Kolam" in frame.columns:
            return frame
    raise ValueError("Sheet is missing Tanggal or Kolam columns.")


def _read_unit_sheet(
    csv_text: str,
    numeric_columns: list[str],
    measured_columns: list[str],
) -> pd.DataFrame:
    frame = _parse_csv_with_header(csv_text)
    frame = frame.loc[:, ~frame.columns.str.match(r"^Unnamed")]

    frame["Kolam"] = frame["Kolam"].map(_normalize_pond)
    frame["Tanggal"] = frame["Tanggal"].map(_parse_date)
    frame = frame.dropna(subset=["Tanggal", "Kolam"])

    for column in numeric_columns:
        if column in frame.columns:
            frame[column] = frame[column].map(_to_number)
        else:
            frame[column] = pd.NA

    present_measured = [column for column in measured_columns if column in frame.columns]
    has_values = frame[present_measured].notna().any(axis=1)
    frame = frame.loc[has_values].copy()
    keep = ["Tanggal", "Kolam", *numeric_columns]
    frame = frame.loc[:, [column for column in keep if column in frame.columns]]
    return frame.sort_values(["Kolam", "Tanggal"]).reset_index(drop=True)


def last_visible_date(now: datetime | None = None) -> datetime:
    """Latest calendar day that may be shown in Jakarta time.

    Today's rows stay hidden until 18:00 WIB. Future dates are never shown.
    """
    if now is None:
        current = datetime.now(JAKARTA)
    elif now.tzinfo is None:
        current = now.replace(tzinfo=JAKARTA)
    else:
        current = now.astimezone(JAKARTA)
    today = current.date()
    visible = today if current.time() >= PUBLISH_TODAY_AFTER else today - timedelta(days=1)
    return datetime(visible.year, visible.month, visible.day)


def filter_visible_rows(frame: pd.DataFrame, now: datetime | None = None) -> pd.DataFrame:
    if frame.empty or "Tanggal" not in frame.columns:
        return frame
    cutoff = pd.Timestamp(last_visible_date(now))
    dates = pd.to_datetime(frame["Tanggal"], errors="coerce")
    return frame.loc[dates.dt.normalize() <= cutoff].copy()


def load_lab_data(csv_text: str | None = None, unit: str = "D") -> pd.DataFrame:
    config = _unit(unit)
    raw = (
        csv_text
        if csv_text is not None
        else fetch_sheet_csv(gid=config.lab_gid, sheet_id=config.sheet_id)
    )
    measured = [column for column in NUMERIC_COLUMNS if column != "DOC"]
    return _read_unit_sheet(raw, NUMERIC_COLUMNS, measured)


def load_harian_data(csv_text: str | None = None, unit: str = "D") -> pd.DataFrame:
    config = _unit(unit)
    raw = (
        csv_text
        if csv_text is not None
        else fetch_sheet_csv(gid=config.harian_gid, sheet_id=config.sheet_id)
    )
    frame = _read_unit_sheet(raw, HARIAN_NUMERIC_COLUMNS, HARIAN_FOCUS_COLUMNS)
    frame["Diff pH"] = frame["pH Sore"] - frame["pH Pagi"]
    frame["Diff Kecerahan"] = frame["Kecerahan Sore"] - frame["Kecerahan Pagi"]
    return frame


def ponds_in_data(frame: pd.DataFrame, unit: str = "D") -> list[str]:
    order = list(_unit(unit).pond_order)
    present = set(frame["Kolam"].unique())
    return [pond for pond in order if pond in present] + sorted(present.difference(order))


def latest_row(frame: pd.DataFrame, pond: str) -> pd.Series | None:
    subset = frame.loc[frame["Kolam"] == pond]
    if subset.empty:
        return None
    return subset.iloc[-1]


def metric_status(column: str, value: float | None, farm: str = "D") -> str:
    if value is None or pd.isna(value):
        return "na"
    rules = UNIT_THRESHOLDS.get(farm, {}).get(column) or THRESHOLDS.get(column)
    if not rules:
        return "ok"
    if "low" in rules and value < rules.get("warn_low", rules["low"]):
        return "alert"
    if "high" in rules and "warn_high" in rules and value > rules["warn_high"]:
        return "alert"
    if "low" in rules and value < rules["low"]:
        return "warn"
    if "high" in rules and value > rules["high"]:
        return "warn"
    return "ok"
