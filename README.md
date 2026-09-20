# Lab Dashboard

Pulls live data for **Unit D** (`lengkap [D]` / `harian [D]`) and **Unit C** (`Lengkap C` / `Harian C`), then shows a dashboard per pond.

```bash
uv sync
uv run lab-dashboard
```

The app opens in the browser. Use the top navigation to switch between **Lab Lengkap** and **Lab Harian**, then Unit C or Unit D. The default view is Unit C lab lengkap. In harian, each pond profile focuses on pakan harian, pH pagi/sore, and kecerahan pagi/sore.

On Streamlit Community Cloud, set the main file to `main.py` (not a nested `streamlit run`).
