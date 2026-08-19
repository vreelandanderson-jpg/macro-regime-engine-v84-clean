from __future__ import annotations

import json
import math
import os
import re
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

import requests

try:
    import websocket  # websocket-client
except Exception:  # pragma: no cover
    websocket = None

try:
    import databento as db
except Exception:  # pragma: no cover
    db = None

try:
    import MetaTrader5 as mt5  # optional Windows/local broker bridge
except Exception:  # pragma: no cover
    mt5 = None

UTC = timezone.utc

# Canonical app symbol -> provider symbol
DATABENTO_FUTURES = {
    "NQ=F": "NQ.v.0",
    "ES=F": "ES.v.0",
    "YM=F": "YM.v.0",
    "RTY=F": "RTY.v.0",
    "GC=F": "GC.v.0",
    "CL=F": "CL.v.0",
    "SI=F": "SI.v.0",
    "HG=F": "HG.v.0",
    "NG=F": "NG.v.0",
}

MASSIVE_INDICES = {
    "^GSPC": "I:SPX",
    "^NDX": "I:NDX",
    "^DJI": "I:DJI",
    "^RUT": "I:RUT",
    "^VIX": "I:VIX",
    "^VVIX": "I:VVIX",
    "^VIX9D": "I:VIX9D",
    # These may depend on plan/catalog coverage; unresolved subscriptions simply
    # remain on the fallback source rather than receiving synthetic values.
    "^TNX": "I:TNX",
    "DX-Y.NYB": "I:DXY",
}

MASSIVE_FOREX = {
    "EURUSD=X": "EUR/USD",
    "JPY=X": "USD/JPY",
    "CAD=X": "USD/CAD",
}

MASSIVE_CRYPTO = {
    "BTC-USD": "BTC-USD",
    "ETH-USD": "ETH-USD",
}


# Massive now exposes a dedicated futures market.  These are product roots; the
# active listed contract is resolved from the Futures Contracts REST endpoint at
# startup and then streamed by exact contract ticker.
MASSIVE_FUTURE_PRODUCTS = {
    "NQ=F": "NQ", "ES=F": "ES", "YM=F": "YM", "RTY=F": "RTY",
    "GC=F": "GC", "CL=F": "CL", "SI=F": "SI", "HG=F": "HG", "NG=F": "NG",
}

# Canonical app symbol -> common broker/MT5 symbols. Exact exchange feeds retain
# priority while fresh; broker quotes automatically become the active real level
# when an official cash/reference series stops publishing.
MT5_ALIASES = {
    "^NDX": ("NAS100", "USTEC", "US100", "NASDAQ100", "NDX100", "NAS100.CASH", "USTEC.CASH"),
    "NQ=F": ("NQ", "NQ100", "NAS100", "USTEC", "US100"),
    "^GSPC": ("US500", "SPX500", "SP500", "S&P500", "US500.CASH"),
    "ES=F": ("ES", "US500", "SPX500", "SP500"),
    "^DJI": ("US30", "DJ30", "DJI30", "DOW30"),
    "YM=F": ("YM", "US30", "DJ30", "DOW30"),
    "^RUT": ("US2000", "RUSSELL2000", "RUS2000"),
    "RTY=F": ("RTY", "US2000", "RUSSELL2000"),
    "DX-Y.NYB": ("DXY", "USDX", "USDINDEX"),
    "^TNX": ("US10Y", "UST10Y", "TNX", "10YUS"),
    "^VIX": ("VIX", "USVIX", "VOLX"),
    "^VVIX": ("VVIX",),
    "^VIX9D": ("VIX9D",),
    "GC=F": ("GC", "GOLD", "XAUUSD"),
    "CL=F": ("CL", "USOIL", "WTI", "WTICOUSD", "XTIUSD"),
    "SI=F": ("SI", "SILVER", "XAGUSD"),
    "HG=F": ("HG", "COPPER", "XCUUSD"),
    "NG=F": ("NG", "NATGAS", "NATURALGAS", "XNGUSD"),
    "EURUSD=X": ("EURUSD",),
    "JPY=X": ("USDJPY",),
    "CAD=X": ("USDCAD",),
    "BTC-USD": ("BTCUSD", "BTCUSD.", "BTCUSDm"),
    "ETH-USD": ("ETHUSD", "ETHUSD.", "ETHUSDm"),
}

# Non-traded/cash references that can remain actively monitored by a tradable proxy
# when the reference itself is closed. The proxy never overwrites the official price.
LIVE_PROXY_MAP = {
    "^NDX": "NQ=F",
    "^GSPC": "ES=F",
    "^DJI": "YM=F",
    "^RUT": "RTY=F",
    "^TNX": "ZN=F",  # if absent in the universe, app can fall back to TLT
    "DX-Y.NYB": "UUP",
    "^VIX": "NQ=F",
    "^VVIX": "^VIX",
    "^VIX9D": "^VIX",
}


@dataclass
class FeedStatus:
    provider: str
    channel: str
    configured: bool = False
    connected: bool = False
    authenticated: bool = False
    started_at: str | None = None
    last_message_at: str | None = None
    last_error: str = ""
    reconnects: int = 0
    subscribed: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "channel": self.channel,
            "configured": self.configured,
            "connected": self.connected,
            "authenticated": self.authenticated,
            "started_at": self.started_at,
            "last_message_at": self.last_message_at,
            "last_error": self.last_error,
            "reconnects": self.reconnects,
            "subscribed": self.subscribed,
        }


def _iso_from_ms(value: Any) -> str | None:
    try:
        return datetime.fromtimestamp(float(value) / 1000.0, tz=UTC).isoformat()
    except Exception:
        return None


def _iso_from_ns(value: Any) -> str | None:
    try:
        return datetime.fromtimestamp(float(value) / 1_000_000_000.0, tz=UTC).isoformat()
    except Exception:
        return None


def _now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _clean_price(value: Any, fixed_hint: bool = False) -> float | None:
    try:
        x = float(value)
        if not math.isfinite(x):
            return None
        if fixed_hint or abs(x) > 10_000_000:
            x /= 1_000_000_000.0
        return x
    except Exception:
        return None


class LiveMarketHub:
    """Thread-safe live market overlay for a Streamlit application.

    Background provider connections mutate only this object. Streamlit reruns read a
    copy via ``snapshot``. No UI session state is mutated from background threads.
    """

    def __init__(self, massive_key: str | None = None, databento_key: str | None = None, mt5_enabled: bool | None = None):
        self.massive_key = (massive_key or os.getenv("MASSIVE_API_KEY") or os.getenv("POLYGON_API_KEY") or "").strip()
        self.databento_key = (databento_key or os.getenv("DATABENTO_API_KEY") or "").strip()
        env_mt5_enabled = str(os.getenv("MT5_LIVE_ENABLE", "1")).strip().lower() not in {"0", "false", "off", "no"}
        self.mt5_enabled = env_mt5_enabled if mt5_enabled is None else bool(mt5_enabled and env_mt5_enabled)
        self.mt5_terminal_path = str(os.getenv("MT5_TERMINAL_PATH", "") or "").strip()
        self.lock = threading.RLock()
        self.rows: dict[str, dict[str, Any]] = {}
        self.history: dict[tuple[str, str], deque[tuple[float, float]]] = defaultdict(lambda: deque(maxlen=3600))
        self.session_volume_accum: dict[tuple[str, str], float] = defaultdict(float)
        self.massive_future_contracts: dict[str, str] = {}
        self.options_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
        self.mt5_symbol_map: dict[str, str] = {}
        self.db_instrument_map: dict[int, str] = {}
        self.started = False
        self.stop_event = threading.Event()
        self.threads: list[threading.Thread] = []
        self.status: dict[str, FeedStatus] = {}

    def ensure_started(self, all_symbols: list[str] | tuple[str, ...]) -> None:
        with self.lock:
            if self.started:
                return
            self.started = True

        # Local MT5/broker feed. This is the only source allowed to keep a cash-like
        # dashboard instrument moving with a genuine broker quote outside the official
        # index calculation window. It is auto-detected and never fabricated.
        mt5_configured = bool(self.mt5_enabled and mt5 is not None)
        self._start_status("mt5", "broker", mt5_configured)
        if mt5_configured:
            self._spawn(self._run_mt5, "mt5-broker", list(all_symbols))

        # Databento futures stream.
        db_symbols = [DATABENTO_FUTURES[s] for s in all_symbols if s in DATABENTO_FUTURES]
        self._start_status("databento", "futures", bool(self.databento_key and db is not None))
        if self.databento_key and db is not None and db_symbols:
            self._spawn(self._run_databento, "databento-futures", db_symbols)

        # Massive per-asset-class WebSocket streams. Stocks includes ETFs/equities.
        stock_symbols = [
            s for s in all_symbols
            if self._is_massive_stock_symbol(s)
        ]
        index_symbols = [MASSIVE_INDICES[s] for s in all_symbols if s in MASSIVE_INDICES]
        forex_symbols = [MASSIVE_FOREX[s] for s in all_symbols if s in MASSIVE_FOREX]
        crypto_symbols = [MASSIVE_CRYPTO[s] for s in all_symbols if s in MASSIVE_CRYPTO]

        configured = bool(self.massive_key and websocket is not None)
        for channel in ("stocks", "indices", "forex", "crypto", "futures", "options"):
            self._start_status("massive", channel, configured)

        if configured:
            if stock_symbols:
                subs = [x for s in stock_symbols for x in (f"A.{s}", f"Q.{s}")]
                reverse = {s: s for s in stock_symbols}
                self._spawn(self._run_massive, "massive-stocks", "stocks", subs, reverse)
            if index_symbols:
                subs = [f"V.{s}" for s in index_symbols]
                reverse = {provider: app for app, provider in MASSIVE_INDICES.items() if provider in index_symbols}
                self._spawn(self._run_massive, "massive-indices", "indices", subs, reverse)
            if forex_symbols:
                subs = [f"CAS.{s}" for s in forex_symbols]
                reverse = {provider: app for app, provider in MASSIVE_FOREX.items() if provider in forex_symbols}
                self._spawn(self._run_massive, "massive-forex", "forex", subs, reverse)
            if crypto_symbols:
                subs = [f"XAS.{s}" for s in crypto_symbols]
                reverse = {provider: app for app, provider in MASSIVE_CRYPTO.items() if provider in crypto_symbols}
                self._spawn(self._run_massive, "massive-crypto", "crypto", subs, reverse)
            # One Massive key can now cover the tracked exchange universe, including
            # CME/CBOT/NYMEX/COMEX futures. Resolve exact active contracts first.
            futures_reverse = self._resolve_massive_futures(all_symbols)
            if futures_reverse:
                subs = [x for ticker in futures_reverse for x in (f"A.{ticker}", f"Q.{ticker}")]
                self._spawn(self._run_massive, "massive-futures", "futures", subs, futures_reverse)

    def _start_status(self, provider: str, channel: str, configured: bool) -> None:
        key = f"{provider}:{channel}"
        with self.lock:
            self.status[key] = FeedStatus(
                provider=provider,
                channel=channel,
                configured=configured,
                started_at=_now_iso() if configured else None,
            )

    def _spawn(self, target: Callable[..., None], name: str, *args: Any) -> None:
        t = threading.Thread(target=target, args=args, name=name, daemon=True)
        self.threads.append(t)
        t.start()

    @staticmethod
    def _is_massive_stock_symbol(sym: str) -> bool:
        if sym in DATABENTO_FUTURES or sym in MASSIVE_INDICES or sym in MASSIVE_FOREX or sym in MASSIVE_CRYPTO:
            return False
        if sym.startswith("^") or "=" in sym or sym.endswith("-USD"):
            return False
        # DXY cash is not a US stock ticker; retain fallback source.
        if sym == "DX-Y.NYB":
            return False
        return True

    def _update_status(self, provider: str, channel: str, **kwargs: Any) -> None:
        key = f"{provider}:{channel}"
        with self.lock:
            stat = self.status.setdefault(key, FeedStatus(provider, channel))
            for k, v in kwargs.items():
                if hasattr(stat, k):
                    setattr(stat, k, v)

    def _record_tick(
        self,
        symbol: str,
        price: float | None,
        provider_ts: str | None,
        source: str,
        *,
        volume_1s: float | None = None,
        session_volume: float | None = None,
        open_price: float | None = None,
        feed_channel: str = "",
        raw_symbol: str = "",
        priority: int = 10,
        price_type: str = "DIRECT LIVE",
        source_id: str = "",
    ) -> None:
        if price is None or not math.isfinite(price):
            return
        now_epoch = time.time()
        source_id = source_id or source
        with self.lock:
            previous = self.rows.get(symbol, {})
            # Source router: a lower numeric priority wins while it is genuinely fresh.
            # If it stops producing events for >5 seconds, the next real provider can
            # take over immediately. This prevents random provider races and enables
            # automatic failover across the entire instrument universe.
            prev_priority = int(previous.get("_priority", 9999) or 9999)
            prev_received = previous.get("received_ts")
            prev_age = 999999.0
            if prev_received:
                try:
                    prev_age = max(0.0, time.time() - datetime.fromisoformat(str(prev_received)).timestamp())
                except Exception:
                    pass
            if prev_priority < int(priority) and prev_age <= 5.0:
                return
            h = self.history[(symbol, source_id)]
            h.append((now_epoch, float(price)))
            # 1-minute move from the closest observation at/older than 60 seconds.
            one_min_price = None
            cutoff = now_epoch - 60.0
            for ts, px in h:
                if ts <= cutoff:
                    one_min_price = px
                else:
                    break
            change_1m = ((price / one_min_price) - 1.0) * 100.0 if one_min_price else None
            session_pct = ((price / open_price) - 1.0) * 100.0 if open_price and open_price != 0 else None
            previous = self.rows.get(symbol, {})
            if volume_1s is not None and math.isfinite(float(volume_1s)):
                self.session_volume_accum[(symbol, source_id)] += max(0.0, float(volume_1s))
            stream_volume = self.session_volume_accum.get((symbol, source_id), 0.0)
            new_row = {
                **previous,
                "symbol": symbol,
                "latest_close": float(price),
                "provider_ts": provider_ts or _now_iso(),
                "received_ts": _now_iso(),
                "updated": provider_ts or _now_iso(),
                "source": source,
                "source_ok": True,
                "price_type": price_type,
                "active_provider_symbol": raw_symbol or symbol,
                "_priority": int(priority),
                "feed_mode": "STREAM",
                "feed_channel": feed_channel,
                "raw_symbol": raw_symbol,
                "change_pct": change_1m if change_1m is not None else previous.get("change_pct"),
                "session_pct": session_pct if session_pct is not None else previous.get("session_pct"),
                "volume_1m": previous.get("volume_1m"),
                "volume_1s": float(volume_1s) if volume_1s is not None else previous.get("volume_1s"),
                "stream_volume": float(stream_volume) if stream_volume > 0 else previous.get("stream_volume"),
                "session_volume": float(session_volume) if session_volume is not None else previous.get("session_volume"),
                "volume": float(session_volume) if session_volume is not None else previous.get("volume"),
                "open_price": float(open_price) if open_price is not None else previous.get("open_price"),
            }
            if price_type == "OFFICIAL INDEX":
                new_row["reference_price"] = float(price)
                new_row["reference_provider_ts"] = provider_ts or _now_iso()
                new_row["reference_source"] = source
            self.rows[symbol] = new_row

    def _record_orderflow(
        self,
        symbol: str,
        *,
        bid: float | None = None,
        ask: float | None = None,
        bid_size: float | None = None,
        ask_size: float | None = None,
        ts: str | None = None,
        source: str = "",
    ) -> None:
        with self.lock:
            previous = self.rows.get(symbol, {"symbol": symbol})
            if bid is not None:
                previous["bid"] = float(bid)
            if ask is not None:
                previous["ask"] = float(ask)
            if bid_size is not None:
                previous["bid_size"] = float(bid_size)
            if ask_size is not None:
                previous["ask_size"] = float(ask_size)
            if bid is not None and ask is not None:
                previous["mid"] = (float(bid) + float(ask)) / 2.0
                previous["spread"] = max(0.0, float(ask) - float(bid))
            if bid_size is not None and ask_size is not None and (float(bid_size) + float(ask_size)) > 0:
                previous["book_imbalance"] = (float(bid_size) - float(ask_size)) / (float(bid_size) + float(ask_size))
            previous["orderflow_ts"] = ts or _now_iso()
            previous["orderflow_source"] = source
            self.rows[symbol] = previous

    def _run_massive(self, channel: str, subscriptions: list[str], reverse: dict[str, str]) -> None:
        if websocket is None or not self.massive_key:
            return
        status_channel = channel
        url = f"wss://socket.massive.com/{channel}"
        backoff = 1.0
        while not self.stop_event.is_set():
            try:
                auth_done = threading.Event()

                def on_open(wsapp: Any) -> None:
                    self._update_status("massive", status_channel, connected=True, last_error="")
                    wsapp.send(json.dumps({"action": "auth", "params": self.massive_key}))

                def on_message(wsapp: Any, message: str) -> None:
                    self._update_status("massive", status_channel, last_message_at=_now_iso())
                    try:
                        payload = json.loads(message)
                        items = payload if isinstance(payload, list) else [payload]
                    except Exception:
                        return
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        ev = item.get("ev")
                        if ev == "status":
                            status = item.get("status", "")
                            if status == "auth_success":
                                self._update_status("massive", status_channel, authenticated=True, connected=True, last_error="")
                                if not auth_done.is_set():
                                    wsapp.send(json.dumps({"action": "subscribe", "params": ",".join(subscriptions)}))
                                    self._update_status("massive", status_channel, subscribed=True)
                                    auth_done.set()
                            elif status in {"auth_failed", "error"}:
                                self._update_status("massive", status_channel, authenticated=False, last_error=str(item.get("message", status)))
                            continue
                        self._handle_massive_item(channel, item, reverse)

                def on_error(_wsapp: Any, error: Any) -> None:
                    self._update_status("massive", status_channel, connected=False, last_error=str(error)[:300])

                def on_close(_wsapp: Any, _code: Any, reason: Any) -> None:
                    self._update_status("massive", status_channel, connected=False, authenticated=False, subscribed=False, last_error=str(reason or "socket closed")[:300])

                wsapp = websocket.WebSocketApp(url, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
                wsapp.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as exc:
                self._update_status("massive", status_channel, connected=False, authenticated=False, last_error=str(exc)[:300])
            if self.stop_event.is_set():
                break
            with self.lock:
                self.status[f"massive:{status_channel}"].reconnects += 1
            time.sleep(backoff)
            backoff = min(backoff * 1.7, 20.0)

    def _handle_massive_item(self, channel: str, item: dict[str, Any], reverse: dict[str, str]) -> None:
        ev = item.get("ev")
        if channel == "stocks" and ev == "Q":
            provider_symbol = str(item.get("sym", ""))
            symbol = reverse.get(provider_symbol)
            if not symbol:
                return
            bid = _clean_price(item.get("bp")); ask = _clean_price(item.get("ap")); ts = _iso_from_ms(item.get("t"))
            self._record_orderflow(
                symbol, bid=bid, ask=ask,
                bid_size=_clean_price(item.get("bs")), ask_size=_clean_price(item.get("as")),
                ts=ts, source="Massive · NBBO",
            )
            if bid is not None and ask is not None and bid > 0 and ask > 0:
                self._record_tick(
                    symbol, (bid + ask) / 2.0, ts, "Massive · NBBO Mid",
                    feed_channel="Q", raw_symbol=provider_symbol, priority=11,
                    price_type="EXCHANGE QUOTE", source_id="massive-stock-nbbo",
                )
            return

        if channel == "stocks" and ev in {"A", "AM"}:
            provider_symbol = str(item.get("sym", ""))
            symbol = reverse.get(provider_symbol)
            if not symbol:
                return
            self._record_tick(
                symbol,
                _clean_price(item.get("c")),
                _iso_from_ms(item.get("e") or item.get("s")),
                "Massive · Stocks",
                volume_1s=_clean_price(item.get("v")),
                session_volume=_clean_price(item.get("av")),
                open_price=_clean_price(item.get("op")),
                feed_channel=ev,
                raw_symbol=provider_symbol, priority=10, price_type="EXCHANGE LIVE", source_id="massive-stocks",
            )
            return

        if channel == "indices" and ev == "V":
            provider_symbol = str(item.get("T", ""))
            symbol = reverse.get(provider_symbol)
            if not symbol:
                return
            self._record_tick(
                symbol,
                _clean_price(item.get("val")),
                _iso_from_ms(item.get("t")),
                "Massive · Indices",
                feed_channel=ev,
                raw_symbol=provider_symbol, priority=8, price_type="OFFICIAL INDEX", source_id="massive-indices",
            )
            return

        if channel == "forex" and ev in {"CAS", "CA"}:
            provider_symbol = str(item.get("pair", ""))
            symbol = reverse.get(provider_symbol)
            if not symbol:
                return
            self._record_tick(
                symbol,
                _clean_price(item.get("c")),
                _iso_from_ms(item.get("e") or item.get("s")),
                "Massive · Forex",
                volume_1s=_clean_price(item.get("v")),
                feed_channel=ev,
                raw_symbol=provider_symbol, priority=10, price_type="DIRECT LIVE", source_id="massive-forex",
            )
            return

        if channel == "crypto" and ev in {"XAS", "XA"}:
            provider_symbol = str(item.get("pair", ""))
            symbol = reverse.get(provider_symbol)
            if not symbol:
                return
            self._record_tick(
                symbol,
                _clean_price(item.get("c")),
                _iso_from_ms(item.get("e") or item.get("s")),
                "Massive · Crypto",
                volume_1s=_clean_price(item.get("v")),
                feed_channel=ev,
                raw_symbol=provider_symbol, priority=10, price_type="DIRECT LIVE", source_id="massive-crypto",
            )

        if channel == "futures" and ev == "Q":
            provider_symbol = str(item.get("sym", ""))
            symbol = reverse.get(provider_symbol)
            if not symbol:
                return
            bid = _clean_price(item.get("bp")); ask = _clean_price(item.get("ap")); ts = _iso_from_ms(item.get("t"))
            self._record_orderflow(
                symbol, bid=bid, ask=ask,
                bid_size=_clean_price(item.get("bs")), ask_size=_clean_price(item.get("as")),
                ts=ts, source="Massive · Futures BBO",
            )
            if bid is not None and ask is not None and bid > 0 and ask > 0:
                self._record_tick(
                    symbol, (bid + ask) / 2.0, ts, "Massive · Futures BBO Mid",
                    feed_channel="Q", raw_symbol=provider_symbol, priority=8,
                    price_type="EXCHANGE FUTURES QUOTE", source_id="massive-futures-bbo",
                )
            return

        if channel == "futures" and ev in {"A", "AM"}:
            provider_symbol = str(item.get("sym", ""))
            symbol = reverse.get(provider_symbol)
            if not symbol:
                return
            self._record_tick(
                symbol, _clean_price(item.get("c")), _iso_from_ms(item.get("e") or item.get("s")),
                "Massive · Futures", volume_1s=_clean_price(item.get("v")),
                feed_channel=ev, raw_symbol=provider_symbol, priority=7,
                price_type="EXCHANGE FUTURES", source_id="massive-futures",
            )
            return

    def _resolve_massive_futures(self, all_symbols: list[str] | tuple[str, ...]) -> dict[str, str]:
        """Resolve the nearest active listed contract for each tracked futures product.

        Databento's volume-ranked continuous contract remains higher priority when it
        is entitled and fresh. Massive provides a universal second exchange path so a
        single provider can still cover the complete current dashboard universe.
        """
        if not self.massive_key:
            return {}
        reverse: dict[str, str] = {}
        today = datetime.now(tz=UTC).date().isoformat()
        for app_symbol in all_symbols:
            product = MASSIVE_FUTURE_PRODUCTS.get(app_symbol)
            if not product:
                continue
            try:
                resp = requests.get(
                    "https://api.massive.com/futures/v1/contracts",
                    params={"product_code": product, "active": "true", "date": today, "limit": 20, "sort": "last_trade_date.asc", "apiKey": self.massive_key},
                    timeout=8,
                )
                resp.raise_for_status()
                results = resp.json().get("results", []) or []
                candidates = [r for r in results if r.get("ticker") and (r.get("days_to_maturity") is None or int(r.get("days_to_maturity") or 0) >= 0)]
                if not candidates:
                    continue
                candidates.sort(key=lambda r: (int(r.get("days_to_maturity") or 999999), str(r.get("last_trade_date") or "9999")))
                ticker = str(candidates[0]["ticker"])
                # Prefer the genuinely active/lead contract by current session volume
                # when the account has Futures Snapshot access; otherwise nearest
                # active expiry remains the deterministic fallback.
                try:
                    snap = requests.get(
                        "https://api.massive.com/futures/v1/snapshot",
                        params={"product_code": product, "limit": 50, "apiKey": self.massive_key},
                        timeout=8,
                    )
                    if snap.ok:
                        active_tickers = {str(r.get("ticker")) for r in candidates}
                        snap_rows = [r for r in (snap.json().get("results", []) or []) if str(r.get("ticker")) in active_tickers]
                        if snap_rows:
                            snap_rows.sort(key=lambda r: float((r.get("session") or {}).get("volume") or 0.0), reverse=True)
                            if float((snap_rows[0].get("session") or {}).get("volume") or 0.0) > 0:
                                ticker = str(snap_rows[0].get("ticker"))
                except Exception:
                    pass
                reverse[ticker] = app_symbol
                self.massive_future_contracts[app_symbol] = ticker
            except Exception as exc:
                self._update_status("massive", "futures", last_error=f"contract resolve {product}: {str(exc)[:180]}")
        return reverse

    @staticmethod
    def _norm_symbol(value: str) -> str:
        return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())

    def _mt5_alias_candidates(self, canonical: str) -> list[str]:
        aliases = list(MT5_ALIASES.get(canonical, ()))
        if canonical.endswith("=X"):
            aliases.append(canonical.replace("=X", ""))
        elif canonical.endswith("-USD"):
            aliases.append(canonical.replace("-", ""))
        elif canonical.endswith("=F"):
            aliases.append(canonical.replace("=F", ""))
        elif not canonical.startswith("^") and canonical != "DX-Y.NYB":
            aliases.extend([canonical, f"#{canonical}", f"{canonical}.US", f"{canonical}.NYSE", f"{canonical}.NASDAQ"])
        return list(dict.fromkeys(a for a in aliases if a))

    def _resolve_mt5_symbols(self, all_symbols: list[str], available: list[Any]) -> dict[str, str]:
        names = [str(getattr(x, "name", "") or "") for x in available]
        exact = {n.upper(): n for n in names}
        normalized: dict[str, list[str]] = defaultdict(list)
        for n in names:
            normalized[self._norm_symbol(n)].append(n)
        resolved: dict[str, str] = {}
        for canonical in all_symbols:
            aliases = self._mt5_alias_candidates(canonical)
            hit = None
            for a in aliases:
                if a.upper() in exact:
                    hit = exact[a.upper()]
                    break
            if not hit:
                # Normalized equality supports broker suffixes/punctuation without
                # allowing a loose substring to mis-map a stock ticker.
                for a in aliases:
                    na = self._norm_symbol(a)
                    if na in normalized:
                        hit = sorted(normalized[na], key=len)[0]
                        break
            if (not hit) and (canonical.startswith("^") or canonical.endswith("=F") or canonical in {"DX-Y.NYB", "EURUSD=X", "JPY=X", "CAD=X", "BTC-USD", "ETH-USD"}):
                # For broker-native macro symbols only, allow a controlled prefix/
                # suffix match because brokers commonly append .cash, .m, -pro, etc.
                alias_norms = [self._norm_symbol(a) for a in aliases if len(self._norm_symbol(a)) >= 3]
                candidates = []
                for n in names:
                    nn = self._norm_symbol(n)
                    if any(nn.startswith(a) or a.startswith(nn) for a in alias_norms):
                        candidates.append(n)
                if candidates:
                    hit = sorted(candidates, key=len)[0]
            if hit:
                resolved[canonical] = hit
        return resolved

    def _run_mt5(self, all_symbols: list[str]) -> None:
        if mt5 is None or not self.mt5_enabled:
            return
        try:
            ok = mt5.initialize(self.mt5_terminal_path) if self.mt5_terminal_path else mt5.initialize()
            if not ok:
                self._update_status("mt5", "broker", connected=False, authenticated=False, last_error=f"initialize failed: {getattr(mt5, 'last_error', lambda: '')()}")
                return
            available = list(mt5.symbols_get() or [])
            self.mt5_symbol_map = self._resolve_mt5_symbols(all_symbols, available)
            for broker_symbol in self.mt5_symbol_map.values():
                try:
                    mt5.symbol_select(broker_symbol, True)
                except Exception:
                    pass
            self._update_status(
                "mt5", "broker", connected=True, authenticated=True, subscribed=bool(self.mt5_symbol_map),
                last_message_at=_now_iso(), last_error=f"resolved {len(self.mt5_symbol_map)}/{len(all_symbols)} symbols",
            )
            poll = max(0.10, min(1.0, float(os.getenv("MT5_POLL_MS", "250")) / 1000.0))
            while not self.stop_event.is_set():
                any_tick = False
                for canonical, broker_symbol in list(self.mt5_symbol_map.items()):
                    try:
                        tick = mt5.symbol_info_tick(broker_symbol)
                    except Exception:
                        tick = None
                    if tick is None:
                        continue
                    bid = _clean_price(getattr(tick, "bid", None))
                    ask = _clean_price(getattr(tick, "ask", None))
                    last = _clean_price(getattr(tick, "last", None))
                    price = ((bid + ask) / 2.0) if bid is not None and ask is not None and bid > 0 and ask > 0 else last or bid or ask
                    if price is None or price <= 0:
                        continue
                    tmsc = getattr(tick, "time_msc", None)
                    ts = _iso_from_ms(tmsc) if tmsc else datetime.fromtimestamp(float(getattr(tick, "time", time.time())), tz=UTC).isoformat()
                    # Exchange-native futures/stocks remain preferred while fresh. For
                    # cash/reference indices a broker quote becomes the real active
                    # level automatically once the official feed stops ticking.
                    priority = 15
                    if canonical in {"DX-Y.NYB", "^TNX", "^VIX", "^VVIX", "^VIX9D"}:
                        priority = 12
                    self._record_tick(
                        canonical, price, ts, f"MT5 Broker · {broker_symbol}",
                        volume_1s=_clean_price(getattr(tick, "volume_real", None)) or _clean_price(getattr(tick, "volume", None)),
                        feed_channel="tick", raw_symbol=broker_symbol, priority=priority,
                        price_type="BROKER LIVE", source_id=f"mt5:{broker_symbol}",
                    )
                    self._record_orderflow(
                        canonical, bid=bid, ask=ask, ts=ts, source=f"MT5 Broker · {broker_symbol}",
                    )
                    any_tick = True
                if any_tick:
                    self._update_status("mt5", "broker", connected=True, authenticated=True, subscribed=True, last_message_at=_now_iso())
                time.sleep(poll)
        except Exception as exc:
            self._update_status("mt5", "broker", connected=False, authenticated=False, subscribed=False, last_error=str(exc)[:300])
        finally:
            try:
                mt5.shutdown()
            except Exception:
                pass

    def _run_databento(self, symbols: list[str]) -> None:
        if db is None or not self.databento_key:
            return
        backoff = 1.0
        app_by_continuous = {v: k for k, v in DATABENTO_FUTURES.items()}
        while not self.stop_event.is_set():
            try:
                client = db.Live(key=self.databento_key)
                client.subscribe(
                    dataset="GLBX.MDP3",
                    schema="ohlcv-1s",
                    symbols=symbols,
                    stype_in="continuous",
                )
                client.subscribe(
                    dataset="GLBX.MDP3",
                    schema="mbp-1",
                    symbols=symbols,
                    stype_in="continuous",
                )

                def callback(record: Any) -> None:
                    self._update_status("databento", "futures", connected=True, authenticated=True, last_message_at=_now_iso(), last_error="")
                    try:
                        if isinstance(record, db.SymbolMappingMsg):
                            continuous = str(record.stype_in_symbol)
                            app_symbol = app_by_continuous.get(continuous)
                            if app_symbol:
                                with self.lock:
                                    self.db_instrument_map[int(record.instrument_id)] = app_symbol
                            return
                    except Exception:
                        pass
                    instrument_id = getattr(record, "instrument_id", None)
                    if instrument_id is None:
                        hd = getattr(record, "hd", None)
                        instrument_id = getattr(hd, "instrument_id", None) if hd is not None else None
                    with self.lock:
                        app_symbol = self.db_instrument_map.get(int(instrument_id)) if instrument_id is not None else None
                    if not app_symbol:
                        return
                    levels = getattr(record, "levels", None)
                    if levels:
                        try:
                            lvl = levels[0]
                            bid = _clean_price(getattr(lvl, "bid_px", None), fixed_hint=True)
                            ask = _clean_price(getattr(lvl, "ask_px", None), fixed_hint=True)
                            qts = _iso_from_ns(getattr(getattr(record, "hd", None), "ts_event", None) or getattr(record, "ts_event", None))
                            self._record_orderflow(
                                app_symbol, bid=bid, ask=ask,
                                bid_size=_clean_price(getattr(lvl, "bid_sz", None)),
                                ask_size=_clean_price(getattr(lvl, "ask_sz", None)),
                                ts=qts, source="Databento · MBP-1",
                            )
                            if bid is not None and ask is not None and bid > 0 and ask > 0:
                                self._record_tick(
                                    app_symbol, (bid + ask) / 2.0, qts, "Databento · MBP-1 Mid",
                                    feed_channel="mbp-1", raw_symbol="continuous", priority=6,
                                    price_type="EXCHANGE FUTURES QUOTE", source_id="databento-mbp1",
                                )
                        except Exception:
                            pass
                    close = _clean_price(getattr(record, "close", None), fixed_hint=True)
                    volume = _clean_price(getattr(record, "volume", None))
                    ts_event = getattr(record, "ts_event", None)
                    if ts_event is None:
                        hd = getattr(record, "hd", None)
                        ts_event = getattr(hd, "ts_event", None) if hd is not None else None
                    self._record_tick(
                        app_symbol,
                        close,
                        _iso_from_ns(ts_event),
                        "Databento · GLBX.MDP3",
                        volume_1s=volume,
                        feed_channel="ohlcv-1s",
                        raw_symbol=symbols[0] if len(symbols) == 1 else "continuous",
                        priority=5, price_type="EXCHANGE FUTURES", source_id="databento-futures",
                    )

                client.add_callback(callback)
                self._update_status("databento", "futures", connected=True, authenticated=True, subscribed=True, last_error="")
                client.start()
                client.block_for_close()
            except Exception as exc:
                self._update_status("databento", "futures", connected=False, authenticated=False, subscribed=False, last_error=str(exc)[:300])
            if self.stop_event.is_set():
                break
            with self.lock:
                self.status["databento:futures"].reconnects += 1
            time.sleep(backoff)
            backoff = min(backoff * 1.7, 20.0)

    def options_chain_snapshot(self, underlying: str, *, max_age_seconds: float = 20.0, limit: int = 250) -> list[dict[str, Any]]:
        """Return a current Massive options-chain page for an optionable underlying.

        The result is cached inside the live hub so Streamlit reruns do not hammer the
        REST endpoint. The provider's own ``timeframe`` fields remain intact, making
        delayed vs real-time entitlements visible rather than silently relabelled LIVE.
        """
        underlying = str(underlying or "").strip().upper()
        if not underlying or not self.massive_key:
            return []
        now = time.time()
        with self.lock:
            cached = self.options_cache.get(underlying)
            if cached and (now - cached[0]) <= max(1.0, float(max_age_seconds)):
                return [dict(x) for x in cached[1]]
        try:
            url = f"https://api.massive.com/v3/snapshot/options/{underlying}"
            params = {
                "apiKey": self.massive_key,
                "limit": max(1, min(int(limit), 250)),
                "order": "asc",
                "sort": "expiration_date",
            }
            r = requests.get(url, params=params, timeout=8)
            r.raise_for_status()
            payload = r.json() if r.content else {}
            results = payload.get("results", []) if isinstance(payload, dict) else []
            if not isinstance(results, list):
                results = []
            rows = [x for x in results if isinstance(x, dict)]
            with self.lock:
                self.options_cache[underlying] = (now, rows)
            self._update_status(
                "massive", "options", configured=True, connected=True, authenticated=True,
                subscribed=bool(rows), last_message_at=_now_iso(), last_error="",
            )
            return [dict(x) for x in rows]
        except Exception as exc:
            self._update_status(
                "massive", "options", configured=True, connected=False, authenticated=False,
                subscribed=False, last_error=str(exc)[:300],
            )
            return []

    def snapshot(self) -> dict[str, dict[str, Any]]:
        with self.lock:
            return {k: dict(v) for k, v in self.rows.items()}

    def provider_status(self) -> list[dict[str, Any]]:
        with self.lock:
            return [s.as_dict() for s in self.status.values()]

    def configured_summary(self) -> dict[str, bool]:
        return {
            "mt5": bool(self.mt5_enabled and mt5 is not None),
            "massive": bool(self.massive_key and websocket is not None),
            "databento": bool(self.databento_key and db is not None),
        }

    def stop(self) -> None:
        self.stop_event.set()
