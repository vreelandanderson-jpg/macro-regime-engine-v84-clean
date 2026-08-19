# Macro Regime Engine v9.7 — Live Provider Hub

v9.7 replaces the old "refresh means live" model with two separate clocks:

- **Provider event clock** — timestamp carried by the actual market event/bar/quote.
- **UI refresh clock** — how often Streamlit redraws the current in-memory state.

A UI rerun can no longer make an old market value look `00s LIVE`.

## Primary live architecture

### Databento
Used for CME-group futures in the universe through `GLBX.MDP3`:

- continuous front contract subscriptions such as `NQ.c.0`, `ES.c.0`, `YM.c.0`, `RTY.c.0`
- 1-second OHLCV for continuously updating futures prices
- MBP-1 for futures top-of-book / L1 order-flow fields
- automatic background reconnect loop

### Massive
Used as the broad real-time WebSocket layer:

- U.S. equities / ETFs: per-second aggregates + NBBO quotes
- U.S. cash indices: direct index value stream where covered
- Forex: per-second quote-derived aggregates
- Crypto: per-second aggregates
- one connection per supported asset class, with all needed symbols multiplexed through that connection

### yfinance
Retained only as a timestamp-correct fallback/baseline source.

It is **not** allowed to fabricate missing prices. Failed symbols remain unavailable until a real source provides a value.

## NDX / cash-index behavior

`^NDX` remains the real Nasdaq 100 cash-index value. It is never overwritten with NQ futures.

When cash is closed, the strip keeps the official cash value and separately exposes:

- `market_state = CLOSED`
- `live_proxy_symbol = NQ=F`
- `live_proxy_price`
- `live_proxy_age_sec`
- `live_proxy_source`

This gives the engine an always-active Nasdaq check without mislabeling futures as the cash index.

The same separation is used for other cash/reference instruments where a valid live proxy exists.

## Freshness rules

For active/extended instruments:

- `LIVE` = direct stream and provider event age <= 5 seconds
- `CURRENT` = provider event age <= 25 seconds
- `STALE` = provider event age > 25 seconds
- `OFFLINE` = no verified price

For closed instruments:

- `CLOSED` = official/reference market is closed
- `CLOSED · PROXY LIVE` = official market is closed but its configured live proxy is fresh

`fetch_age_sec` and `market_age_sec` are both preserved so the app can distinguish a recent fetch from a recent market event.

## Order flow

Where plan entitlement exists:

- CME futures use Databento `MBP-1`
- equities / ETFs use Massive NBBO quotes

Fields include:

- `bid`
- `ask`
- `bid_size`
- `ask_size`
- `mid`
- `spread`
- `book_imbalance`
- `orderflow_source`
- `orderflow_ts`

Other instruments retain the existing proxy-flow logic rather than pretending L1 data exists.

## Volume

Volume fields are no longer built from a zero-valued latest minute cell.

The engine preserves:

- `volume_1s` when supplied by the stream
- `stream_volume` accumulated since connection
- `volume_1m`
- `session_volume`
- `relative_volume`
- `volume_delta_pct`
- `volume_source`
- `volume_proxy_symbol`

For stock WebSocket aggregates, provider accumulated session volume is used when supplied. A live stream never silently replaces a fuller baseline session-volume value with an incomplete since-connect total.

## UI behavior retained

- strip cards remain open through automatic and manual refreshes
- they close only when the user closes them
- edit/format changes propagate immediately to the matching strip
- Score display: Percentage / Decimal / Whole
- Change display: Percentage / Decimal
- Editable Table and Raw Table remain available
- display overrides never mutate the underlying live/raw feed
- Events calendar remains included
- Pharma / Healthcare & Science and Defense / Aero remain included

## Streamlit Cloud secrets

Set the following in **Streamlit Cloud -> App -> Settings -> Secrets**:

```toml
MASSIVE_API_KEY = "your_key_here"
DATABENTO_API_KEY = "your_key_here"
```

A template is included at `.streamlit/secrets.toml.example`.

Do not commit real API keys to GitHub.

## Important provider-entitlement behavior

The app detects configuration, connection state and last provider message. If a plan does not entitle a specific channel/symbol, that instrument remains on its real fallback source and is not promoted to `LIVE` simply because the UI refreshed.

## Files

- `app.py` — Streamlit application / UI / scoring / fallback baseline
- `live_feeds.py` — persistent WebSocket + Databento live hub
- `requirements.txt` — dependencies
- `.streamlit/secrets.toml.example` — provider-key template
