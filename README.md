# Macro Regime Engine v9.6 — Persistent Edit Sync + Volume Repair

This build keeps the synchronized ≤25-second data architecture, universal instrument universe, persistent strip-card presentation, pharma / healthcare, defense / aero, Geo / Global, order-flow proxy, options pressure, raw-data diagnostics, and Events calendar.

## v9.6 changes

- Open strip cards remain open through automatic refresh and manual UPDATE. They close only when the user closes that strip.
- `EDIT / FORMAT THIS INSTRUMENT` now writes to a persistent UI display-override layer keyed by symbol.
- An edit made inside a strip immediately reruns the UI and updates that strip's summary, Price / Change / Score / State cards, and full detail grid.
- Edits survive data refresh until `RESET DISPLAY OVERRIDES` is used.
- Editable Table view uses the same override layer, so table edits propagate back into Strip Card view.
- Raw Table remains the untouched synchronized feed for audit/reference.
- Score formatting can be switched globally between Percentage, Decimal, and Whole.
- Change formatting can be switched globally between Percentage and Decimal.
- The same format controls are now available from every instrument editor as well as the sidebar.

## Volume repair

The previous build relied on the most recent 1-minute `Volume` cell, which may be zero/unreported. v9.6 replaces that behavior with:

- `volume_1m`: most recent valid non-zero minute volume.
- `session_volume`: cumulative valid volume across the fetched session.
- `relative_volume`: latest valid minute volume versus the median of the prior 20 valid minute bars.
- `volume_delta_pct`: latest valid minute volume versus the previous valid minute bar.
- `volume_source`: explicitly reports `Actual`, `Proxy · SYMBOL`, `N/A`, or fallback state.
- `volume_proxy_symbol`: identifies the proxy where a cash/reference series does not publish reliable native traded volume.
- legacy `volume` now maps to `session_volume` for compatibility.
- Missing/unavailable volume is displayed as N/A instead of silently becoming 0.

Cash/reference series use explicit labeled proxies where practical, including Nasdaq cash → NQ futures, S&P cash → ES futures, Dow cash → YM futures, Russell cash → RTY futures, DXY → UUP, and 10Y yield → TLT. Volatility/FX reference series also use clearly labeled liquid proxy volume when native volume is unavailable.

The Flow Tracker and dashboard Order Flow panel now expose relative-volume activity, volume delta, session volume, and volume source from the synchronized snapshot. This remains a public-feed proxy; true Level II/order-book data requires a broker-grade order-flow provider.


## v9.6 edit safety fix
- Score/change format buttons now use pre-render callbacks, avoiding StreamlitAPIException from modifying selectbox-owned Session State after instantiation.
- Score edits continue to persist as display overrides and rerender the expanded strip card immediately.
- Reset override action is callback-safe as well.
