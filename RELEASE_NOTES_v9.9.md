# v9.9 Release Notes — Universal Live Source Router

- Universal routing applied to the full current instrument universe, not only Nasdaq.
- Real provider/broker quotes can become the active displayed level even when the canonical cash/reference instrument is outside its official calculation window.
- Official/reference values remain separately auditable.
- Local MT5 broker feed auto-detection added (optional Windows dependency).
- Massive futures streaming added to the existing stocks/ETFs/indices/FX/crypto coverage.
- Massive futures contract discovery now prefers the active contract with the highest session volume when Futures Snapshot entitlement is available; otherwise it uses the nearest active expiry.
- Databento futures remains higher priority when fresh.
- Source priority failover occurs after 5 seconds without a fresh event from the stronger source.
- Bid/ask midpoint can supply the active level when quotes are moving but no new trade aggregate prints.
- 25-second freshness ceiling continues to use provider event time, never UI refresh time.
- `BROKER LIVE`, `OFFICIAL INDEX`, `EXCHANGE FUTURES`, `EXCHANGE QUOTE`, and `REFERENCE` are explicit price types.
- Data Health and Raw Data now expose active provider symbol, price type, reference price/source, and provider timestamps.
- Existing persistent strip cards, editable Score formatting, repaired volume diagnostics, Events calendar, Pharma, Defense/Aero, Geo/Global, and order-flow displays retained.
- Options / Pressure now supports actual Massive option-chain snapshots (bid/ask, last, volume, OI, IV, Greeks) with provider timeframe preserved and ≤20s cache; unavailable entitlements are explicitly shown.
