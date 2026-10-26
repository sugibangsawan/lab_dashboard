# Lab Dashboard

Pulls live data for **Unit B** (`Lengkap B` / `Harian B` / `Plankton B`), **Unit C** (`Lengkap C` / `Harian C` / `Plankton C`), and **Unit D** (`lengkap [D]` / `harian [D]`), then shows a dashboard per pond.

```bash
uv sync
uv run lab-dashboard
```

The app opens in the browser. Use the top navigation to switch between **Lab Lengkap**, **Lab Harian**, and **Lab Plankton**, and the sidebar to pick **Unit B**, **Unit C** (default), or **Unit D**. Lab Plankton is available for Unit B and Unit C. In harian, each pond profile focuses on pakan harian, pH pagi/sore, and kecerahan pagi/sore.

On Streamlit Community Cloud, set the main file to `main.py` (not a nested `streamlit run`).
