# Macro Regime Engine v9.4 — Persistent Strip Controls

This build keeps the synchronized ≤25-second data architecture, universal instrument universe, strip-card presentation, pharma / healthcare, defense / aero, Geo / Global, order-flow proxy, options pressure, raw-data diagnostics, and Events calendar introduced in the prior build.

## v9.4 changes

- Strip cards now keep their open/closed state in Streamlit session state.
- Automatic refresh and manual UPDATE no longer close an open strip.
- A strip closes only when the user toggles that strip closed.
- Every strip-card module now has three views: Strip Cards, Editable Table, and Raw Table.
- Expanded strips include a one-instrument editable table with every available field.
- Global Score display can switch between Percentage, Decimal, and Whole formats.
- Global Change display can switch between Percentage and Decimal formats.
- Display formatting applies across Instruments, Flow Tracker, Options / Pressure, Sectors, Defense / Aero, Real Estate, Healthcare / Science, Geo / Global, dashboard diagnostics, Data Health, and Raw Data.
- Editable tables are a UI working surface; they do not overwrite the synchronized feed or scoring engine.
- Existing synchronized refresh architecture remains capped at 25 seconds.
