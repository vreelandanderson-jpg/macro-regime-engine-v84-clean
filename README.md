# Macro Regime Engine v8.4 Clean Repository

Clean Streamlit-native repository build. No raw HTML rendering, no FRED, no demo logic.

## What this build focuses on

- Action Console first: NOW, active cause, target pressure, confirmation, contradiction, avoid.
- Active Cause Engine across macro, AI, semis, real estate, sectors, credit, commodities, currencies, crypto, volatility, global markets.
- Extended-hours NAS/QQQ/NQ tracking where yfinance intraday feed allows it.
- 1H and 4H close tracking for QQQ/NQ/NDX where feed allows it.
- Full universe: real estate, all 11 sectors, sub-sectors, currencies, global markets, commodities, crypto equities, credit, volatility.
- Clean selectable live tiles.
- Streamlit-native UI only. No raw HTML/CSS card markup.

## Deploy on Streamlit Cloud

Main file path:

```text
app.py
```

Upload all repo files to GitHub, commit, then reboot/rerun the app in Streamlit Cloud.

## Local test

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
streamlit run app.py
```
