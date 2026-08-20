# Macro Regime Engine v10.3 — Immediate Intelligence + Quote-Detected Router

This build replaces the closed/reference-first behavior with a universal real-level router across the entire tracked instrument universe.

## What changed

- Every instrument is routed independently to the best real quote available now.
- MT5 broker feed auto-detection was added for local Windows deployments. This lets continuously quoted broker markets such as NAS100/USTEC remain real and moving after the official cash index calculation stops.
- Massive now covers stocks, ETFs, indices, FX, crypto **and futures** in the same engine.
- Databento remains the highest-priority CME futures/order-book path when configured.
- Quote midpoints can keep an instrument current when the bid/ask is moving but no new trade/aggregate printed.
- The official/reference value is retained separately whenever a broker-active level takes over.
- No fabricated market levels are used.
- Existing strip-card persistence, editable Score formatting, volume diagnostics, Events calendar, Pharma, Defense/Aero, Geo/Global and Raw Data views remain.

## Live-source setup

### Simplest broad remote source

Add a Massive API key in **LIVE DATA CONNECTIONS** or Streamlit secrets. Your plan/market-data entitlements determine whether each asset class is real-time or delayed. Delayed provider timestamps are detected as stale rather than mislabeled LIVE.

### CME futures / order flow

Add a Databento key for the higher-priority CME Globex futures stream and MBP-1 quotes.

### Same broker levels as your MT5 terminal

Windows/local only:

```bash
pip install -r requirements-mt5-windows.txt
streamlit run app.py
```

Keep MetaTrader 5 running. The engine automatically scans the broker symbol catalog and maps the tracked universe where the broker provides a matching instrument.

Optional environment controls:

```text
MT5_LIVE_ENABLE=1
MT5_TERMINAL_PATH=C:\\Program Files\\Your Broker MT5\\terminal64.exe
MT5_POLL_MS=250
```

`MT5_TERMINAL_PATH` is optional; the MetaTrader integration can auto-discover the local terminal.

## Provider keys

Streamlit secrets:

```toml
MASSIVE_API_KEY = "..."
DATABENTO_API_KEY = "..."
```

See `SOURCE_ROUTER.md` for exact source priority and active/reference behavior.

## Options / Pressure

With a Massive Options entitlement, the selected instrument loads a 20-second-cached chain snapshot with actual bid/ask, last trade, volume, open interest, IV and Greeks. Futures/cash references use a clearly labeled liquid listed-options proxy (for example NQ/NDX -> QQQ); the instrument price itself still comes from the universal live router.


## v10.1 collection integrity
See `RELEASE_NOTES_v10.1.md`. The engine now separates source check age from market-event age and holds the last verified real value through transient collection failures.


## v10.2 health semantics
The command-center health card now measures collection/check health directly. A fresh polling/reference check is CURRENT rather than REFERENCE/IDLE; provider event age remains a separate diagnostic clock. See `RELEASE_NOTES_v10.2.md`.


## v10.3 immediate intelligence
The Command tab now surfaces an immediate decision read, problems-first attention table, clickable health focus, persistent observed-change ages, and fully interactive table consoles with search/filter/sort/column controls/row focus. Editable table overrides remain synchronized with strip cards. See `RELEASE_NOTES_v10.3.md`.
