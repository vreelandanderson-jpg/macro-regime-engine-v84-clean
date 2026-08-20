# Macro Regime Engine v10.3 — Immediate Intelligence + Interactive Tables

## Immediate decision read
- The selected instrument no longer opens with a passive provider-text dump.
- A visible **Immediate read** now shows the active level, current usability state, best routed symbol, check age, provider-event age, driver, current issue, and last observed price move.
- Full provider/reference timestamps remain available under **Provider audit** so the command surface stays concise.

## Problems-first dashboard
- Added **Immediate Market Attention** directly to the Command tab.
- Instruments are ranked by collection/provider severity before normal rows.
- Health focus buttons filter the attention surface to `LIVE`, `CURRENT`, `WATCH`, `DEGRADED`, `STALE`, or `UNAVAILABLE` without forcing the user into the Data Health page.
- Clicking a table row focuses that instrument across the dashboard.

## Fully interactive tables
- Added an **Interactive Table** mode to every strip-card module.
- Native table console adds search, quick health filters, category/source/feed filters, column visibility controls, sorting controls, CSV export, and row selection.
- Table row selection updates the selected instrument.
- Existing **Editable Table** remains available and display edits still persist through refresh.
- Score edits continue to recompute display State/Quality unless those fields are explicitly edited too.
- Raw tables stay auditable while still gaining search/filter/sort/row-focus behavior.

## Change awareness
- Added session-persistent observation tracking for price, route, source, and market-state changes.
- The UI can now say how long ago the dashboard itself observed the last price/route/source/state change without overwriting provider timestamps.
- Provider event age and collection/check age remain separate.

## No market-data semantics were weakened
- 25-second collection SLA remains intact.
- No fabricated prices are introduced.
- Direct LIVE still requires a valid direct/broker/provider route; current polling checks remain explicitly distinguishable from true live streams.
