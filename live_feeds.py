from __future__ import annotations

import json
import math
import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

try:
    import websocket  # websocket-client
except Exception:  # pragma: no cover
    websocket = None

try:
    import databento as db
except Exception:  # pragma: no cover
    db = None

UTC = timezone.utc

# Canonical app symbol -> provider symbol
DATABENTO_FUTURES = {
    "NQ=F": "NQ.c.0",
    "ES=F": "ES.c.0",
    "YM=F": "YM.c.0",
    "RTY=F": "RTY.c.0",
    "GC=F": "GC.c.0",
    "CL=F": "CL.c.0",
    "SI=F": "SI.c.0",
    "HG=F": "HG.c.0",
    "NG=F": "NG.c.0",
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

    def __init__(self, massive_key: str | None = None, databento_key: str | None = None):
        self.massive_key = (massive_key or os.getenv("MASSIVE_API_KEY") or os.getenv("POLYGON_API_KEY") or "").strip()
        self.databento_key = (databento_key or os.getenv("DATABENTO_API_KEY") or "").strip()
        self.lock = threading.RLock()
        self.rows: dict[str, dict[str, Any]] = {}
        self.history: dict[str, deque[tuple[float, float]]] = defaultdict(lambda: deque(maxlen=3600))
        self.session_volume_accum: dict[str, float] = defaultdict(float)
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
        for channel in ("stocks", "indices", "forex", "crypto"):
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
    ) -> None:
        if price is None or not math.isfinite(price):
            return
        now_epoch = time.time()
        with self.lock:
            h = self.history[symbol]
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
                self.session_volume_accum[symbol] += max(0.0, float(volume_1s))
            stream_volume = self.session_volume_accum.get(symbol, 0.0)
            self.rows[symbol] = {
                **previous,
                "symbol": symbol,
                "latest_close": float(price),
                "provider_ts": provider_ts or _now_iso(),
                "received_ts": _now_iso(),
                "updated": provider_ts or _now_iso(),
                "source": source,
                "source_ok": True,
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
                                    auth_done.set()
                            elif status in {"auth_failed", "error"}:
                                self._update_status("massive", status_channel, authenticated=False, last_error=str(item.get("message", status)))
                            continue
                        self._handle_massive_item(channel, item, reverse)

                def on_error(_wsapp: Any, error: Any) -> None:
                    self._update_status("massive", status_channel, connected=False, last_error=str(error)[:300])

                def on_close(_wsapp: Any, _code: Any, reason: Any) -> None:
                    self._update_status("massive", status_channel, connected=False, authenticated=False, last_error=str(reason or "socket closed")[:300])

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
            self._record_orderflow(
                symbol,
                bid=_clean_price(item.get("bp")), ask=_clean_price(item.get("ap")),
                bid_size=_clean_price(item.get("bs")), ask_size=_clean_price(item.get("as")),
                ts=_iso_from_ms(item.get("t")), source="Massive · NBBO",
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
                raw_symbol=provider_symbol,
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
                raw_symbol=provider_symbol,
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
                raw_symbol=provider_symbol,
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
                raw_symbol=provider_symbol,
            )

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
                            self._record_orderflow(
                                app_symbol,
                                bid=_clean_price(getattr(lvl, "bid_px", None), fixed_hint=True),
                                ask=_clean_price(getattr(lvl, "ask_px", None), fixed_hint=True),
                                bid_size=_clean_price(getattr(lvl, "bid_sz", None)),
                                ask_size=_clean_price(getattr(lvl, "ask_sz", None)),
                                ts=_iso_from_ns(getattr(getattr(record, "hd", None), "ts_event", None) or getattr(record, "ts_event", None)),
                                source="Databento · MBP-1",
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
                    )

                client.add_callback(callback)
                self._update_status("databento", "futures", connected=True, authenticated=True, last_error="")
                client.start()
                client.block_for_close()
            except Exception as exc:
                self._update_status("databento", "futures", connected=False, authenticated=False, last_error=str(exc)[:300])
            if self.stop_event.is_set():
                break
            with self.lock:
                self.status["databento:futures"].reconnects += 1
            time.sleep(backoff)
            backoff = min(backoff * 1.7, 20.0)

    def snapshot(self) -> dict[str, dict[str, Any]]:
        with self.lock:
            return {k: dict(v) for k, v in self.rows.items()}

    def provider_status(self) -> list[dict[str, Any]]:
        with self.lock:
            return [s.as_dict() for s in self.status.values()]

    def configured_summary(self) -> dict[str, bool]:
        return {
            "massive": bool(self.massive_key and websocket is not None),
            "databento": bool(self.databento_key and db is not None),
        }

    def stop(self) -> None:
        self.stop_event.set()
