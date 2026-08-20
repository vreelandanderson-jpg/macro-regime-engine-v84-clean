# Macro Regime Engine v10.2 — Health Semantics Repair

## Fixed
- Active Market Data Health no longer interprets non-stream/reference instruments as `REFERENCE/IDLE`.
- The dashboard health card is now driven by **collection/check age**, which is the same clock used by the `89/89 ≤25s` collector coverage counter.
- Provider market-event age remains separate and visible in Diagnostics/Data Health; an unchanged market event can no longer make a successfully checked feed look idle.
- Health rows now report coverage and feed mode explicitly, e.g. `CURRENT · 89/89 · 03s · POLL`.
- Fresh but degraded checks report `DEGRADED`; partial coverage reports `PARTIAL`; failed collection reports `STALE`.
- Sidebar/version label now uses the actual application version and no longer displays the stale v10.0 label.

## Health semantics
- **CURRENT**: every instrument in the group has been checked within 25 seconds.
- **DEGRADED**: every instrument was checked within 25 seconds, but at least one check reported a degraded source.
- **PARTIAL**: only part of the group was checked within 25 seconds.
- **STALE**: none of the group is within the 25-second collection SLA.
- Feed mode (`STREAM`, `POLL`, `MIXED`, `HOLD`) is shown separately and does not decide collection health by itself.

Market-event timestamps remain independent so the engine does not claim that a polled/reference quote is a real-time stream.
