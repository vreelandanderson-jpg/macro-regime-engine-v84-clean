# Universal Live Source Router (v9.9)

## Routing rule

Every dashboard instrument is routed independently. A real fresh source always wins over a polling/reference source. No synthetic price is created.

Priority while fresh (lower number = stronger):

1. Databento CME futures trade / MBP-1 quote data
2. Massive exchange futures
3. Massive official index / stocks / ETF / FX / crypto streams
4. MT5 broker quote (used automatically for continuous broker markets when an official cash/reference feed stops publishing)
5. yfinance reference fallback (never promoted to STREAM/LIVE)

If the stronger source has not produced a real event for 5 seconds, the next real source may take over. If it resumes, it immediately regains priority.

## Actual level vs reference

`latest_close` is the current active real level selected by the router.

When a broker-active level takes over a cash/reference instrument, the original official/reference value is retained in:

- `reference_price`
- `reference_provider_ts`
- `reference_source`

The active stream identifies itself with:

- `price_type`
- `active_provider_symbol`
- `source`
- `provider_ts`
- `market_age_sec`

## MT5 auto-resolution

On a Windows machine with MetaTrader 5 installed, install `requirements-mt5-windows.txt` and leave the MT5 terminal open. The engine calls `initialize()`, reads the terminal symbol catalog, and maps the complete engine universe to broker symbols when available.

Examples include:

- `^NDX` -> NAS100 / USTEC / US100 family
- `^GSPC` -> US500 / SPX500 family
- `^DJI` -> US30 / DJ30 family
- `^RUT` -> US2000 family
- `GC=F` -> GC / GOLD / XAUUSD family
- `CL=F` -> CL / USOIL / WTI family
- FX and crypto pairs
- US equities/ETFs by exact ticker or common broker suffixes

The broker quote is labeled `BROKER LIVE`; it is not mislabeled as the official cash index.

## Massive universal coverage

The Massive connector now includes the futures channel in addition to stocks, ETFs, indices, FX and crypto. Futures contracts are discovered from the Futures Contracts endpoint; when snapshot access is available, the engine chooses the active contract with the highest current session volume.

## 25-second SLA

The visible age comes from the provider event timestamp. A UI refresh timestamp never makes an old price LIVE. A stream older than 25 seconds is not considered current.

## Options data

The Options / Pressure workspace queries Massive `/v3/snapshot/options/{underlyingAsset}` on demand and caches the result for at most 20 seconds. Provider `timeframe` fields are retained so delayed entitlements are never displayed as real-time. Futures/cash references use a labeled optionable proxy only for the options layer; their own routed price level is not replaced.
