# Macro Regime Engine v8.8 — All-Session NAS Engine

Clean Streamlit repo package.

## v8.8 fix

NDX/NAS live tracking is no longer treated as NY-cash-only.

Instrument rules:

- `NQ=F` = primary NAS live driver for Asia, London, Globex, overnight, and non-cash sessions.
- `QQQ` = tradable US pre-market and after-hours NAS proxy.
- `^NDX` = official NY cash index reference only.

## Included

- Action Console
- Active Cause Engine
- Full universe coverage
- Real estate / housing
- Healthcare / science / biotech / pharma
- Global session map
- NAS all-session driver panel
- NAS / QQQ / NQ session range panel
- Selectable live tiles
- Gauges
- Toronto / Eastern 12-hour time
- No FRED
- No demo logic

## GitHub upload files

Upload only these files to Streamlit/GitHub:

- `app.py`
- `requirements.txt`
- `README.md`
- `.gitignore`

## Deploy

Main file path: `app.py`
