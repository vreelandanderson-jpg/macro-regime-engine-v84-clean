# Macro Regime Engine v9.3 — Strip Cards + Calendar

This is the clean v9.3 command-center build.

## v9.3 changes

- Replaces primary instrument column tables with **interactive horizontal strip cards**.
- **No instrument data is removed**: click any strip to expand every available field from that module.
- Adds a **Strip Cards / Raw Table** toggle for full audit visibility.
- Applies strip-card presentation to Instruments, Flow Tracker, Options / Pressure, Sectors, Defense / Aero, Real Estate, Healthcare / Science, and Geo / Global.
- Raw Data and Data Health remain audit-focused table views.
- Adds an **Events mini-calendar popover** with selected-day, selected-week, and full-month filtering.
- Event watch dates are never silently fabricated. Items that require a verified external calendar feed are labeled `DATE TBA / provider date required`.
- Keeps the single synchronized snapshot architecture and maximum dashboard data age of 25 seconds.
- Global manual UPDATE still rebuilds the shared snapshot for every module.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```
