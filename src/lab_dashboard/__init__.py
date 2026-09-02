from __future__ import annotations

from pathlib import Path
import sys


def main() -> None:
    from streamlit.web import cli as stcli

    dashboard = Path(__file__).with_name("dashboard.py")
    sys.argv = [
        "streamlit",
        "run",
        str(dashboard),
        "--browser.gatherUsageStats=false",
    ]
    sys.exit(stcli.main())
