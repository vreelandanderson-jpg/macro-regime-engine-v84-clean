# Macro Regime Engine v10.0 — Quote-Detected Extended Markets

- Primary market state is now quote-detected: LIVE / EXTENDED / STALE / UNAVAILABLE.
- LIVE/EXTENDED require an actual provider quote/trade event no older than 25 seconds.
- Added dxFeed production REST quote detector for overnight U.S. stocks/ETFs and other entitled asset classes.
- Supports Basic auth, Bearer token, and custom IPF symbol-map JSON.
- Cash index references NDX/SPX/Dow/Russell can promote a fresh traded futures level while preserving official reference price separately.
- No synthetic/implied values and no clock-only EXTENDED tags.
- Existing strip cards, edits, volume, Events calendar, Defense/Aero, Pharma, Flow, Options and Geo modules retained.
