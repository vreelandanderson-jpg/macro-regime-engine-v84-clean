# Macro Regime Engine v10.1 — Collection Integrity

- Separates **collection/check age** from **market-event age**. A source checked 2 seconds ago is no longer labelled as if the engine itself stopped checking just because the last trade was older.
- Public fallback is now a **continuous public check**, not a fake live stream. Fresh public values are `CURRENT`; delayed/quiet events remain visibly distinguished.
- Adds a **last verified value hold** so a transient batch/API miss does not erase a valid instrument level on the next Streamlit rerun.
- Source-router priority now compares **provider event timestamps**. A delayed high-priority feed can no longer block a fresher secondary feed just because its HTTP response arrived recently.
- Diagnostics include `collection_state`, `collection_age_sec`, and `event_age_sec` alongside the original provider timestamp.
- `Live Checks` header is renamed **Collection** and measures actual engine collection cadence.
- `FALLBACK` is renamed **PUBLIC CHECK** when no direct provider is configured. It is not represented as exchange-real-time.
- Public snapshot cache reduced to 10 seconds while the global hard collection SLA remains 25 seconds.
- No synthetic prices are introduced.
- Direct stream events older than 25 seconds are rejected at ingestion and stale hub rows are not allowed to overwrite a newer public/reference value.
