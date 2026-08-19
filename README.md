# Macro Regime Engine v9.2 — Synchronized Clean Command Center

This build replaces the staggered tier clocks and dense vertical-card layout from v9.1.

## v9.2 changes

- **One synchronized universe snapshot** drives every dashboard module.
- **Every tier is capped at ≤25 seconds**; default auto-refresh is 20 seconds.
- Manual **UPDATE** clears the global snapshot and refreshes all modules together.
- Data Health now reports actual snapshot age and `LIVE / CURRENT / STALE` state.
- Universal instrument tiles are compact and no longer print long role text inside narrow cards.
- Dashboard is split into interactive **Command / Market Pulse / Regime / Diagnostics** views to remove long-page clutter.
- Detail information moves into popovers instead of permanently consuming screen space.
- Raw Data is now a diagnostic console with domain filtering, age, status and feed state.
- Added a dedicated **Defense / Aero** tracking view and expanded the defense universe.
- Added **Geo / Global** view while preserving indexes, sectors, commodities, FX, credit, crypto, real estate and healthcare/science tracking.
- Public-feed latency is distinguished from dashboard refresh age; proxy data is not represented as exchange-direct Level II or options-chain data.

## Streamlit Cloud

Upload these root files to GitHub:

- `app.py`
- `requirements.txt`
- `README.md`
- `.gitignore`

Main file path: `app.py`
