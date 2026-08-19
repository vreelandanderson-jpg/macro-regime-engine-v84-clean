# Macro Regime Engine v8.9

Universal Instruments + Order Flow Engine.

## Core focus

- Universal instrument map for every searched asset
- Cash / spot / ETF / futures / options proxy / sector / related stocks / credit / volatility / currency / commodity layers
- Order-flow proxy card
- Score, change %, score quality, reason, active cause, target pressure, confirm / contradict / avoid
- Global session engine: Asia, London, US pre-market, NY cash, after-hours, Globex/futures, crypto 24/7
- Gauges, selectable live tiles, action console

## Deploy files

Upload these root files to GitHub:

- `app.py`
- `requirements.txt`
- `README.md`
- `.gitignore`

Then redeploy/reboot Streamlit Cloud.

## Data note

Free public feeds provide price/volume and delayed/limited options chain information. True Level II order flow, live options flow, and professional depth require a broker/data feed such as IBKR, Tradier, Polygon, dxFeed, Rithmic, CQG, or similar.
