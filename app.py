from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, time
from typing import Any, Dict, Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:  # pragma: no cover
    st_autorefresh = None

TORONTO = ZoneInfo("America/Toronto")

st.set_page_config(
    page_title="Macro Regime Engine v8.9",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Universal instrument universe
# -----------------------------

@dataclass(frozen=True)
class Instrument:
    key: str
    label: str
    ticker: str
    category: str
    asset_type: str
    aliases: Tuple[str, ...]
    futures: Tuple[str, ...] = ()
    etf: Tuple[str, ...] = ()
    cash: Tuple[str, ...] = ()
    options_proxy: Tuple[str, ...] = ()
    sector: Tuple[str, ...] = ()
    related: Tuple[str, ...] = ()
    volatility: Tuple[str, ...] = ()
    credit: Tuple[str, ...] = ()
    currency: Tuple[str, ...] = ()
    commodity: Tuple[str, ...] = ()
    session_driver: Tuple[str, ...] = ()

UNIVERSE: Dict[str, Instrument] = {
    # Indexes / futures / ETFs
    "NAS": Instrument("NAS", "Nasdaq / NDX", "NQ=F", "Indexes", "Composite", ("nas", "ndx", "nasdaq", "qqq", "nq"), futures=("NQ=F",), etf=("QQQ",), cash=("^NDX",), options_proxy=("QQQ",), sector=("XLK", "SMH", "SOXX"), related=("NVDA", "MSFT", "AAPL", "AMZN", "META", "GOOGL", "AVGO", "AMD"), volatility=("^VIX",), credit=("HYG",), currency=("UUP",), session_driver=("NQ=F", "QQQ", "^NDX")),
    "SPX": Instrument("SPX", "S&P 500", "ES=F", "Indexes", "Composite", ("spx", "sp500", "s&p", "spy", "es"), futures=("ES=F",), etf=("SPY", "RSP"), cash=("^GSPC",), options_proxy=("SPY",), sector=("XLK", "XLF", "XLV", "XLY", "XLC", "XLI"), related=("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META"), volatility=("^VIX",), credit=("HYG", "LQD"), currency=("UUP",), session_driver=("ES=F", "SPY", "^GSPC")),
    "DOW": Instrument("DOW", "Dow Jones", "YM=F", "Indexes", "Composite", ("dow", "djia", "dia", "ym"), futures=("YM=F",), etf=("DIA",), cash=("^DJI",), options_proxy=("DIA",), sector=("XLI", "XLF", "XLV"), volatility=("^VIX",), session_driver=("YM=F", "DIA", "^DJI")),
    "RUSSELL": Instrument("RUSSELL", "Russell 2000", "RTY=F", "Indexes", "Composite", ("russell", "rut", "iwm", "rty"), futures=("RTY=F",), etf=("IWM",), cash=("^RUT",), options_proxy=("IWM",), sector=("KRE", "XLF", "XRT"), credit=("HYG",), volatility=("^VIX",), session_driver=("RTY=F", "IWM", "^RUT")),

    # Rates / dollar / volatility / credit
    "DOLLAR": Instrument("DOLLAR", "US Dollar", "UUP", "Macro", "ETF/FX Proxy", ("dxy", "dollar", "usd", "uup"), etf=("UUP",), cash=("DX-Y.NYB",), options_proxy=("UUP",), related=("EURUSD=X", "JPY=X", "GBPUSD=X", "CAD=X", "AUDUSD=X", "CHF=X"), session_driver=("UUP", "DX-Y.NYB")),
    "TENY": Instrument("TENY", "10Y Yield", "^TNX", "Rates", "Yield", ("10y", "10 year", "tnx", "yield", "rates"), futures=("ZN=F",), etf=("IEF", "TLT"), cash=("^TNX",), options_proxy=("TLT", "IEF"), related=("SHY", "TLT", "MBB", "XLRE", "ITB"), session_driver=("^TNX", "ZN=F")),
    "BONDS": Instrument("BONDS", "Bonds / Duration", "TLT", "Rates", "ETF", ("bonds", "tlt", "duration", "treasury"), futures=("ZB=F", "ZN=F"), etf=("TLT", "IEF", "SHY"), cash=("^TNX", "^TYX"), options_proxy=("TLT",), related=("XLRE", "VNQ", "ITB", "XBI", "ARKG"), session_driver=("TLT", "ZB=F", "ZN=F")),
    "VIX": Instrument("VIX", "Volatility", "^VIX", "Volatility", "Index", ("vix", "vol", "volatility", "fear"), futures=("VX=F",), etf=("VIXY", "UVXY"), cash=("^VIX",), options_proxy=("SPY", "QQQ"), related=("^VIX9D", "^VIX3M"), credit=("HYG",), session_driver=("^VIX", "VIXY")),
    "CREDIT": Instrument("CREDIT", "Credit Stress", "HYG", "Credit", "ETF", ("credit", "hyg", "junk", "jnd", "lqd"), etf=("HYG", "JNK", "LQD", "BKLN"), options_proxy=("HYG",), related=("KRE", "KBE", "XLF"), volatility=("^VIX",), session_driver=("HYG", "JNK", "LQD")),

    # Commodities
    "GOLD": Instrument("GOLD", "Gold", "GC=F", "Commodities", "Future", ("gold", "gc", "xau", "gld"), futures=("GC=F",), etf=("GLD", "GDX", "GDXJ"), options_proxy=("GLD", "GDX"), related=("UUP", "^TNX", "TLT"), currency=("UUP",), session_driver=("GC=F", "GLD")),
    "SILVER": Instrument("SILVER", "Silver", "SI=F", "Commodities", "Future", ("silver", "si", "slv"), futures=("SI=F",), etf=("SLV",), options_proxy=("SLV",), related=("GC=F", "GLD", "UUP"), session_driver=("SI=F", "SLV")),
    "OIL": Instrument("OIL", "Crude Oil", "CL=F", "Commodities", "Future", ("oil", "crude", "wti", "cl", "uso"), futures=("CL=F", "BZ=F"), etf=("USO", "XLE", "XOP", "OIH"), options_proxy=("USO", "XLE"), related=("XLE", "XOP", "OIH", "CAD=X"), commodity=("NG=F",), session_driver=("CL=F", "USO")),
    "COPPER": Instrument("COPPER", "Copper", "HG=F", "Commodities", "Future", ("copper", "hg", "cper"), futures=("HG=F",), etf=("CPER", "XLB", "XME"), options_proxy=("CPER",), related=("EEM", "FXI", "MCHI", "XLI"), session_driver=("HG=F", "CPER")),
    "NATGAS": Instrument("NATGAS", "Natural Gas", "NG=F", "Commodities", "Future", ("natural gas", "natgas", "ng", "ung"), futures=("NG=F",), etf=("UNG",), options_proxy=("UNG",), related=("XLE", "OIH"), session_driver=("NG=F", "UNG")),
    "AGRI": Instrument("AGRI", "Agriculture", "DBA", "Commodities", "ETF", ("agriculture", "wheat", "corn", "soybeans", "dba"), futures=("ZW=F", "ZC=F", "ZS=F"), etf=("DBA",), options_proxy=("DBA",), related=("DBC", "UUP"), session_driver=("DBA", "ZW=F", "ZC=F", "ZS=F")),

    # Sectors and sub-sectors
    "REAL_ESTATE": Instrument("REAL_ESTATE", "Real Estate / Housing", "XLRE", "Sectors", "Sector", ("real estate", "housing", "reit", "xlre", "vnq", "homebuilders"), etf=("XLRE", "VNQ", "IYR", "ITB", "XHB", "MBB", "REM"), options_proxy=("XLRE", "VNQ", "ITB"), related=("^TNX", "TLT", "KRE", "XLF"), session_driver=("XLRE", "VNQ", "ITB")),
    "HEALTHCARE": Instrument("HEALTHCARE", "Healthcare / Science", "XLV", "Sectors", "Sector", ("healthcare", "health", "science", "biotech", "pharma", "xlv", "xbi"), etf=("XLV", "VHT", "IYH", "IBB", "XBI", "ARKG", "GNOM", "PJP", "IHE", "IHI", "IHF"), options_proxy=("XLV", "XBI", "IBB"), related=("LLY", "NVO", "MRK", "PFE", "ABBV", "JNJ", "UNH", "TMO", "DHR", "ISRG"), session_driver=("XLV", "XBI", "IBB")),
    "TECH_AI": Instrument("TECH_AI", "AI / Technology", "XLK", "Sectors", "Sector", ("ai", "tech", "semis", "semiconductors", "chip", "xlk", "smh"), etf=("XLK", "SMH", "SOXX", "AIQ", "BOTZ", "ARKQ"), options_proxy=("XLK", "SMH", "QQQ"), related=("NVDA", "AMD", "AVGO", "MSFT", "GOOGL", "META", "AMZN", "TSM", "ASML", "PLTR"), session_driver=("SMH", "SOXX", "QQQ")),
    "FINANCIALS": Instrument("FINANCIALS", "Financials / Banks", "XLF", "Sectors", "Sector", ("financials", "banks", "bank", "xlf", "kre", "kbe"), etf=("XLF", "KRE", "KBE"), options_proxy=("XLF", "KRE"), related=("JPM", "BAC", "GS", "MS", "WFC", "C"), credit=("HYG", "LQD"), session_driver=("XLF", "KRE", "KBE")),
    "ENERGY": Instrument("ENERGY", "Energy", "XLE", "Sectors", "Sector", ("energy", "xle", "xop", "oil stocks"), etf=("XLE", "XOP", "OIH"), options_proxy=("XLE", "XOP"), related=("CL=F", "CVX", "XOM", "COP", "SLB"), commodity=("CL=F", "NG=F"), session_driver=("XLE", "XOP", "CL=F")),
    "DEFENSE": Instrument("DEFENSE", "Defense / Aerospace", "ITA", "Sectors", "Subsector", ("defense", "aerospace", "war", "ita", "xar"), etf=("ITA", "XAR"), options_proxy=("ITA",), related=("LMT", "RTX", "NOC", "GD", "BA"), session_driver=("ITA", "XAR")),
    "CLEAN_ENERGY": Instrument("CLEAN_ENERGY", "Clean Energy / Nuclear", "ICLN", "Sectors", "Subsector", ("clean energy", "solar", "nuclear", "uranium", "lithium"), etf=("ICLN", "TAN", "URA", "NLR", "LIT"), options_proxy=("ICLN", "TAN", "URA"), related=("TSLA", "ENPH", "FSLR", "CCJ", "ALB"), session_driver=("ICLN", "TAN", "URA", "LIT")),

    # Currencies / crypto / global
    "FX": Instrument("FX", "Currency Map", "UUP", "Currencies", "FX/ETF", ("fx", "currency", "currencies", "euro", "yen", "cad", "aud"), etf=("UUP", "CEW"), cash=("EURUSD=X", "JPY=X", "GBPUSD=X", "CAD=X", "AUDUSD=X", "CHF=X"), options_proxy=("UUP",), related=("GLD", "GC=F", "EEM", "DBC"), session_driver=("UUP", "EURUSD=X", "JPY=X")),
    "CRYPTO": Instrument("CRYPTO", "Crypto Liquidity", "BTC-USD", "Crypto", "Crypto", ("crypto", "btc", "bitcoin", "eth", "sol"), cash=("BTC-USD", "ETH-USD", "SOL-USD"), etf=("IBIT", "BITO", "COIN", "MSTR", "MARA", "RIOT"), options_proxy=("BITO", "COIN", "MSTR"), related=("QQQ", "UUP", "^VIX"), session_driver=("BTC-USD", "ETH-USD", "COIN")),
    "GLOBAL": Instrument("GLOBAL", "Global Markets", "EFA", "Global", "ETF", ("global", "europe", "china", "japan", "india", "emerging"), etf=("EWC", "VGK", "FEZ", "EWG", "EWQ", "EWU", "EWJ", "FXI", "MCHI", "EWH", "INDA", "EEM", "EFA"), options_proxy=("EEM", "FXI", "EFA"), related=("UUP", "CL=F", "HG=F"), currency=("UUP", "EURUSD=X", "JPY=X"), session_driver=("EFA", "EEM", "FXI", "EWJ")),
}

DIRECT_TICKERS: Dict[str, Instrument] = {}
for inst in UNIVERSE.values():
    for sym in (inst.ticker,) + inst.futures + inst.etf + inst.cash + inst.options_proxy + inst.related + inst.volatility + inst.credit + inst.currency + inst.commodity:
        if sym and sym not in DIRECT_TICKERS:
            DIRECT_TICKERS[sym.upper()] = Instrument(sym.upper(), sym, sym, inst.category, "Direct", (sym.lower(),), options_proxy=(sym,), session_driver=(sym,))

CORE_TILES = ["NAS", "SPX", "DOLLAR", "TENY", "VIX", "CREDIT", "GOLD", "OIL", "REAL_ESTATE", "HEALTHCARE", "TECH_AI", "CRYPTO"]
ALL_TILE_KEYS = list(UNIVERSE.keys())

SESSION_ORDER = ["Asia", "London", "US Pre-Market", "NY Cash", "US After-Hours", "Globex / Futures", "Crypto 24/7"]

# -----------------------------
# Utilities
# -----------------------------

def now_et() -> datetime:
    return datetime.now(TORONTO)


def fmt_time(dt: Optional[datetime] = None) -> str:
    dt = dt or now_et()
    return dt.strftime("%-I:%M:%S %p ET") if hasattr(dt, "strftime") else "--"


def fmt_date_time(dt: Optional[datetime] = None) -> str:
    dt = dt or now_et()
    # Windows does not support %-I; streamlit cloud does. Safe fallback below.
    text = dt.strftime("%a, %b %d, %Y %I:%M:%S %p ET")
    return text.replace(" 0", " ")


def safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def clamp(value: float, lo: float = -100, hi: float = 100) -> float:
    return max(lo, min(hi, value))


def pct_text(value: Optional[float]) -> str:
    if value is None or pd.isna(value):
        return "--"
    return f"{value:+.2f}%"


def price_text(value: Optional[float]) -> str:
    if value is None or pd.isna(value):
        return "--"
    if abs(value) >= 1000:
        return f"{value:,.2f}"
    if abs(value) >= 10:
        return f"{value:.2f}"
    return f"{value:.4f}"


def uniq(items: Iterable[str]) -> List[str]:
    seen = set()
    out = []
    for item in items:
        if not item:
            continue
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def resolve_instrument(query: str) -> Instrument:
    q = (query or "NAS").strip().lower()
    if not q:
        return UNIVERSE["NAS"]
    q_clean = q.replace("/", "").replace(" ", "")
    for inst in UNIVERSE.values():
        if q == inst.key.lower() or q == inst.label.lower() or q == inst.ticker.lower() or q in inst.aliases:
            return inst
        if any(q_clean == a.replace(" ", "") for a in inst.aliases):
            return inst
    upper = q.upper()
    if upper in DIRECT_TICKERS:
        return DIRECT_TICKERS[upper]
    # Try to detect ticker style
    if re.match(r"^[A-Z0-9^=\-.]{1,12}$", upper):
        return Instrument(upper, upper, upper, "Direct", "Direct", (q,), options_proxy=(upper,), session_driver=(upper,))
    return UNIVERSE["NAS"]


def symbols_for_fetch(keys_or_symbols: Iterable[str]) -> List[str]:
    symbols: List[str] = []
    for item in keys_or_symbols:
        inst = UNIVERSE.get(item, DIRECT_TICKERS.get(str(item).upper()))
        if inst:
            symbols.extend([inst.ticker, *inst.futures, *inst.etf, *inst.cash, *inst.related[:6], *inst.volatility, *inst.credit, *inst.currency[:2], *inst.commodity])
        else:
            symbols.append(str(item))
    # yfinance may fail on some symbols. Keep unique and limited.
    return uniq(symbols)[:120]

# -----------------------------
# Data fetch
# -----------------------------

@st.cache_data(ttl=60, show_spinner=False)
def fetch_daily(symbols: Tuple[str, ...], period: str = "5d") -> Dict[str, Dict[str, Any]]:
    if not symbols:
        return {}
    data: Dict[str, Dict[str, Any]] = {}
    try:
        raw = yf.download(list(symbols), period=period, interval="1d", group_by="ticker", threads=True, progress=False, auto_adjust=False, prepost=True)
    except Exception:
        raw = pd.DataFrame()
    for sym in symbols:
        try:
            df = raw[sym].dropna(how="all") if isinstance(raw.columns, pd.MultiIndex) and sym in raw.columns.get_level_values(0) else raw.dropna(how="all")
            if df.empty or "Close" not in df:
                data[sym] = empty_quote(sym)
                continue
            close = df["Close"].dropna()
            if close.empty:
                data[sym] = empty_quote(sym)
                continue
            last = safe_float(close.iloc[-1], np.nan)
            prev = safe_float(close.iloc[-2], last) if len(close) > 1 else last
            chg = ((last - prev) / prev * 100) if prev else 0.0
            high = safe_float(df["High"].dropna().iloc[-1] if "High" in df and not df["High"].dropna().empty else last, last)
            low = safe_float(df["Low"].dropna().iloc[-1] if "Low" in df and not df["Low"].dropna().empty else last, last)
            vol = safe_float(df["Volume"].dropna().iloc[-1] if "Volume" in df and not df["Volume"].dropna().empty else 0, 0)
            avg_vol = safe_float(df["Volume"].tail(20).mean() if "Volume" in df else 0, 0)
            data[sym] = {
                "symbol": sym,
                "price": last,
                "prev_close": prev,
                "change_pct": chg,
                "high": high,
                "low": low,
                "volume": vol,
                "avg_volume": avg_vol,
                "updated": fmt_time(),
                "ok": True,
            }
        except Exception:
            data[sym] = empty_quote(sym)
    return data


def empty_quote(symbol: str) -> Dict[str, Any]:
    return {"symbol": symbol, "price": np.nan, "prev_close": np.nan, "change_pct": np.nan, "high": np.nan, "low": np.nan, "volume": 0, "avg_volume": 0, "updated": fmt_time(), "ok": False}

@st.cache_data(ttl=45, show_spinner=False)
def fetch_intraday(symbol: str, period: str = "5d", interval: str = "15m") -> pd.DataFrame:
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False, prepost=True, auto_adjust=False)
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna(how="all")
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC").tz_convert(TORONTO)
        else:
            df.index = df.index.tz_convert(TORONTO)
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=600, show_spinner=False)
def fetch_options_pressure(symbol: str) -> Dict[str, Any]:
    # Free yfinance options are limited and not true options flow.
    try:
        tk = yf.Ticker(symbol)
        expirations = list(tk.options or [])
        if not expirations:
            return {"status": "Unavailable", "summary": "No public option chain returned", "put_call": np.nan, "iv_state": "Unknown", "oi_zone": "--"}
        expiry = expirations[0]
        chain = tk.option_chain(expiry)
        calls = chain.calls.copy()
        puts = chain.puts.copy()
        call_vol = safe_float(calls.get("volume", pd.Series(dtype=float)).fillna(0).sum(), 0)
        put_vol = safe_float(puts.get("volume", pd.Series(dtype=float)).fillna(0).sum(), 0)
        call_oi = safe_float(calls.get("openInterest", pd.Series(dtype=float)).fillna(0).sum(), 0)
        put_oi = safe_float(puts.get("openInterest", pd.Series(dtype=float)).fillna(0).sum(), 0)
        pc_ratio = put_vol / call_vol if call_vol > 0 else np.nan
        all_oi = pd.concat([calls[["strike", "openInterest"]], puts[["strike", "openInterest"]]], ignore_index=True).dropna()
        oi_zone = "--"
        if not all_oi.empty:
            row = all_oi.sort_values("openInterest", ascending=False).iloc[0]
            oi_zone = f"{safe_float(row['strike']):.2f}"
        call_iv = safe_float(calls.get("impliedVolatility", pd.Series(dtype=float)).replace([np.inf, -np.inf], np.nan).dropna().mean(), np.nan)
        put_iv = safe_float(puts.get("impliedVolatility", pd.Series(dtype=float)).replace([np.inf, -np.inf], np.nan).dropna().mean(), np.nan)
        mean_iv = np.nanmean([call_iv, put_iv])
        if pd.isna(pc_ratio):
            pressure = "Mixed / limited"
        elif pc_ratio >= 1.25:
            pressure = "Put pressure"
        elif pc_ratio <= 0.75:
            pressure = "Call pressure"
        else:
            pressure = "Balanced"
        return {
            "status": "Chain available",
            "expiry": expiry,
            "summary": pressure,
            "put_call": pc_ratio,
            "call_volume": call_vol,
            "put_volume": put_vol,
            "call_oi": call_oi,
            "put_oi": put_oi,
            "iv_state": f"IV ~ {mean_iv:.1%}" if not pd.isna(mean_iv) else "IV unknown",
            "oi_zone": oi_zone,
        }
    except Exception as exc:
        return {"status": "Unavailable", "summary": f"Options chain not available from public feed", "put_call": np.nan, "iv_state": "Unknown", "oi_zone": "--"}

# -----------------------------
# Session engine
# -----------------------------

def session_state(dt: Optional[datetime] = None) -> Dict[str, Any]:
    dt = dt or now_et()
    wd = dt.weekday()
    t = dt.time()
    is_weekday = wd < 5
    active = []
    if time(20, 0) <= t or t < time(4, 0):
        active.append("Asia")
    if time(3, 0) <= t < time(11, 30):
        active.append("London")
    if is_weekday and time(4, 0) <= t < time(9, 30):
        active.append("US Pre-Market")
    if is_weekday and time(9, 30) <= t < time(16, 0):
        active.append("NY Cash")
    if is_weekday and time(16, 0) <= t < time(20, 0):
        active.append("US After-Hours")
    active.append("Globex / Futures")
    active.append("Crypto 24/7")
    primary = "NY Cash" if "NY Cash" in active else "US Pre-Market" if "US Pre-Market" in active else "US After-Hours" if "US After-Hours" in active else "London" if "London" in active else "Asia"
    return {"primary": primary, "active": active, "time": fmt_date_time(dt)}


def session_cards(quotes: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
    stt = session_state()
    rows = []
    session_to_symbol = {
        "Asia": "NQ=F",
        "London": "NQ=F",
        "US Pre-Market": "QQQ",
        "NY Cash": "^NDX",
        "US After-Hours": "QQQ",
        "Globex / Futures": "NQ=F",
        "Crypto 24/7": "BTC-USD",
    }
    for sess in SESSION_ORDER:
        sym = session_to_symbol.get(sess, "NQ=F")
        q = quotes.get(sym, empty_quote(sym))
        state = "ACTIVE" if sess in stt["active"] else "Closed / Watch"
        rows.append({"Session": sess, "Status": state, "Driver": sym, "Price": price_text(q.get("price")), "Change": pct_text(q.get("change_pct"))})
    return pd.DataFrame(rows)

# -----------------------------
# Scoring / action engine
# -----------------------------

def quote_for(inst: Instrument, quotes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    # Pick primary driver based on session and data availability.
    for sym in inst.session_driver + (inst.ticker,):
        q = quotes.get(sym)
        if q and q.get("ok"):
            return q
    return quotes.get(inst.ticker, empty_quote(inst.ticker))


def score_from_change(change: float, category: str = "") -> float:
    if pd.isna(change):
        return 0.0
    # Normalize asset move to score; retain directional semantics.
    multiplier = 18
    if category in {"Volatility", "Credit", "Rates"}:
        multiplier = 16
    if category == "Crypto":
        multiplier = 10
    return clamp(change * multiplier)


def state_from_score(score: float) -> str:
    if score >= 60:
        return "Strong Support"
    if score >= 25:
        return "Supportive"
    if score <= -60:
        return "Strong Pressure"
    if score <= -25:
        return "Under Pressure"
    return "Mixed"


def score_quality(score: float, confirmations: int, contradictions: int) -> Tuple[str, int]:
    total = confirmations + contradictions
    evidence = confirmations - contradictions
    confidence = int(clamp(abs(score) * 0.55 + evidence * 9 + 20, 0, 100))
    if confirmations >= 5 and contradictions <= 1 and abs(score) >= 30:
        return "Strong", confidence
    if confirmations >= 3 and contradictions <= 2:
        return "Medium", confidence
    return "Weak / Mixed", max(10, confidence)


def market_conditions(quotes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    def ch(sym: str) -> float:
        return safe_float(quotes.get(sym, {}).get("change_pct"), 0.0)
    dxy = ch("UUP")
    teny = ch("^TNX")
    qqq = ch("QQQ") or ch("NQ=F")
    vix = ch("^VIX")
    hyg = ch("HYG")
    smh = ch("SMH")
    xle = ch("XLE")
    gold = ch("GC=F") or ch("GLD")
    xlv = ch("XLV")
    xlre = ch("XLRE")
    confirmations = []
    contradictions = []
    if dxy > 0.15:
        confirmations.append("Dollar firm")
    if teny > 0.15:
        confirmations.append("Yields firm")
    if vix > 0.25:
        confirmations.append("Volatility rising")
    if qqq < -0.15:
        confirmations.append("Growth weak")
    if smh < -0.15:
        confirmations.append("Semis/AI weak")
    if hyg < -0.10:
        confirmations.append("Credit soft")
    if qqq > 0.15:
        contradictions.append("Growth holding")
    if vix < -0.15:
        contradictions.append("Volatility fading")
    if hyg > 0.10:
        contradictions.append("Credit holding")
    pressure_score = clamp((-qqq * 16) + (dxy * 12) + (teny * 10) + (vix * 8) + (-hyg * 10) + (-smh * 8))
    if pressure_score >= 25:
        state = "Risk-Off Pressure"
    elif pressure_score <= -25:
        state = "Risk-On Support"
    else:
        state = "Mixed / Rotation"
    active_causes = []
    if dxy > 0.25 or teny > 0.25:
        active_causes.append({"Cause": "Dollar / Yield Pressure", "Effect": "Pressures QQQ, AI, crypto, real estate, biotech", "Strength": abs(dxy) + abs(teny)})
    if smh < -0.35:
        active_causes.append({"Cause": "Semiconductor / AI Weakness", "Effect": "Pressures NDX, QQQ, AI basket", "Strength": abs(smh)})
    if xle > 0.35 or ch("CL=F") > 0.35:
        active_causes.append({"Cause": "Energy / Oil Inflation Pressure", "Effect": "Supports energy, pressures inflation-sensitive risk assets", "Strength": abs(xle) + abs(ch("CL=F"))})
    if gold > 0.35:
        active_causes.append({"Cause": "Gold / Safety Bid", "Effect": "Signals safety demand or yield relief", "Strength": abs(gold)})
    if xlre < -0.25 or ch("ITB") < -0.25:
        active_causes.append({"Cause": "Real Estate / Housing Rate Pressure", "Effect": "Pressures XLRE, REITs, homebuilders", "Strength": abs(xlre) + abs(ch("ITB"))})
    if xlv > 0.25 and qqq < 0:
        active_causes.append({"Cause": "Defensive Healthcare Rotation", "Effect": "Signals defensive rotation away from growth", "Strength": abs(xlv)})
    if not active_causes:
        active_causes.append({"Cause": "No dominant active cause", "Effect": "Market is mixed; wait for confirmation", "Strength": 0})
    active_causes = sorted(active_causes, key=lambda x: x["Strength"], reverse=True)
    return {"state": state, "score": pressure_score, "confirmations": confirmations, "contradictions": contradictions, "active_causes": active_causes, "raw": {"dxy": dxy, "teny": teny, "qqq": qqq, "vix": vix, "hyg": hyg, "smh": smh}}


def instrument_action(inst: Instrument, quotes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    q = quote_for(inst, quotes)
    change = safe_float(q.get("change_pct"), 0.0)
    base_score = score_from_change(change, inst.category)
    conditions = market_conditions(quotes)

    confirmations: List[str] = []
    contradictions: List[str] = []
    if change > 0.15:
        confirmations.append(f"{inst.label} positive")
    elif change < -0.15:
        confirmations.append(f"{inst.label} weak")
    raw = conditions["raw"]
    # Category-aware confirmations
    if inst.key in {"NAS", "SPX", "TECH_AI", "CRYPTO"} or inst.category in {"Indexes", "Crypto"}:
        if raw["dxy"] > 0.15:
            confirmations.append("Dollar pressure active")
        if raw["teny"] > 0.15:
            confirmations.append("Yield pressure active")
        if raw["vix"] > 0.15:
            confirmations.append("VIX confirming pressure")
        if raw["smh"] < -0.15:
            confirmations.append("Semis/AI confirming weakness")
        if raw["hyg"] > 0.10:
            contradictions.append("Credit still holding")
        if raw["vix"] < -0.15:
            contradictions.append("VIX not confirming fear")
    elif inst.key in {"GOLD", "SILVER"}:
        if raw["dxy"] < -0.15:
            confirmations.append("Dollar weakness supports metals")
        elif raw["dxy"] > 0.15 and change > 0:
            confirmations.append("Rising despite dollar = possible fear bid")
        if raw["teny"] > 0.15 and change < 0:
            confirmations.append("Yields pressuring metals")
    elif inst.key in {"REAL_ESTATE", "HEALTHCARE", "BONDS", "TENY"}:
        if raw["teny"] > 0.15 and change < 0:
            confirmations.append("Rate pressure confirms weakness")
        if raw["teny"] < -0.15 and change > 0:
            confirmations.append("Yield relief supports move")
    else:
        if abs(conditions["score"]) > 25:
            confirmations.append(f"Macro state: {conditions['state']}")

    # If opposite macro pressure, mark contradictions
    if inst.key in {"NAS", "SPX", "TECH_AI"} and change > 0 and conditions["score"] > 25:
        contradictions.append("Risk asset rising while macro pressure is risk-off")
    if inst.key in {"NAS", "SPX", "TECH_AI"} and change < 0 and conditions["score"] < -25:
        contradictions.append("Risk asset falling while macro support is risk-on")

    quality, confidence = score_quality(base_score, len(confirmations), len(contradictions))
    state = state_from_score(base_score)
    active_cause = conditions["active_causes"][0]["Cause"]
    target = target_pressure(inst, q, base_score, conditions)
    return {
        "inst": inst,
        "quote": q,
        "score": base_score,
        "state": state,
        "quality": quality,
        "confidence": confidence,
        "confirmations": confirmations[:8] or ["No clean confirmation yet"],
        "contradictions": contradictions[:6] or ["No major contradiction detected"],
        "active_cause": active_cause,
        "target_pressure": target,
        "avoid": avoid_logic(inst, base_score, contradictions, conditions),
        "conditions": conditions,
    }


def target_pressure(inst: Instrument, q: Dict[str, Any], score: float, conditions: Dict[str, Any]) -> str:
    price = safe_float(q.get("price"), np.nan)
    high = safe_float(q.get("high"), np.nan)
    low = safe_float(q.get("low"), np.nan)
    if pd.isna(price):
        return "No live target until price feed updates"
    if score <= -25:
        level = low if not pd.isna(low) else price * 0.995
        return f"Downside pressure toward {price_text(level)} unless reclaim/flow flips"
    if score >= 25:
        level = high if not pd.isna(high) else price * 1.005
        return f"Upside/support pressure toward {price_text(level)} if confirmation holds"
    return "Mixed target; wait for range break or active cause confirmation"


def avoid_logic(inst: Instrument, score: float, contradictions: List[str], conditions: Dict[str, Any]) -> str:
    if contradictions:
        return "Avoid chasing; contradictions are active"
    if abs(score) < 25:
        return "Avoid oversized trades; score is mixed"
    if inst.category in {"Indexes", "Crypto"} and conditions["score"] > 25 and score > 0:
        return "Avoid trusting risk-on if dollar/yields/VIX remain firm"
    if inst.category in {"Indexes", "Crypto"} and conditions["score"] < -25 and score < 0:
        return "Avoid chasing risk-off if macro support is improving"
    return "No major avoid flag beyond normal risk control"


def order_flow_proxy(inst: Instrument, quotes: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    q = quote_for(inst, quotes)
    chg = safe_float(q.get("change_pct"), 0.0)
    price = safe_float(q.get("price"), np.nan)
    high = safe_float(q.get("high"), np.nan)
    low = safe_float(q.get("low"), np.nan)
    vol = safe_float(q.get("volume"), 0.0)
    avg = safe_float(q.get("avg_volume"), 0.0)
    rng = high - low if not (pd.isna(high) or pd.isna(low)) else 0
    pos = (price - low) / rng if rng > 0 and not pd.isna(price) else 0.5
    if chg > 0.25 and pos > 0.60:
        pressure = "Buyers aggressive"
        liquidity = "Offers being lifted / upside pressure"
        absorption = "Seller absorption weak"
        delta = "Positive proxy"
    elif chg < -0.25 and pos < 0.40:
        pressure = "Sellers aggressive"
        liquidity = "Bids being hit / downside pressure"
        absorption = "Buyer absorption weak"
        delta = "Negative proxy"
    else:
        pressure = "Mixed flow"
        liquidity = "No clear dominance"
        absorption = "Balanced / uncertain"
        delta = "Neutral proxy"
    quality = "High" if avg and vol > avg * 1.2 and abs(chg) > 0.25 else "Medium" if abs(chg) > 0.20 else "Proxy / limited"
    return {"Pressure": pressure, "Liquidity": liquidity, "Absorption": absorption, "Delta": delta, "Quality": quality, "Source": "Price/volume proxy unless Level II feed is connected"}

# -----------------------------
# UI Components
# -----------------------------

def indicator_gauge(title: str, value: float, subtitle: str) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": "", "font": {"size": 24}},
        title={"text": f"{title}<br><span style='font-size:0.65em'>{subtitle}</span>", "font": {"size": 14}},
        gauge={"axis": {"range": [-100, 100]}, "bar": {"thickness": 0.25}, "steps": [
            {"range": [-100, -60], "color": "#f8d7da"},
            {"range": [-60, -25], "color": "#ffe5d0"},
            {"range": [-25, 25], "color": "#eeeeee"},
            {"range": [25, 60], "color": "#d7f5df"},
            {"range": [60, 100], "color": "#b6edc6"},
        ]},
    ))
    fig.update_layout(height=210, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)")
    return fig


def metric_card(title: str, value: str, note: str = "") -> None:
    st.container(border=True).metric(title, value, help=note or None)


def render_tile(inst: Instrument, action: Dict[str, Any]) -> bool:
    q = action["quote"]
    selected = st.session_state.get("selected_key", "NAS") == inst.key
    label = f"{'✓ ' if selected else ''}{inst.label}"
    with st.container(border=True):
        st.caption(inst.category.upper())
        st.subheader(label)
        c1, c2 = st.columns(2)
        c1.metric("Price", price_text(q.get("price")))
        c2.metric("Change", pct_text(q.get("change_pct")))
        st.write(f"**{action['state']}**")
        st.caption(f"Score {action['score']:.1f} • {action['quality']}")
        return st.button("Select", key=f"select_{inst.key}", use_container_width=True)


def relationship_df(inst: Instrument, quotes: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    groups = [
        ("Primary", (inst.ticker,)),
        ("Futures", inst.futures),
        ("ETF / Proxy", inst.etf),
        ("Cash / Spot", inst.cash),
        ("Options Proxy", inst.options_proxy),
        ("Sector / Basket", inst.sector),
        ("Related Stocks", inst.related),
        ("Volatility", inst.volatility),
        ("Credit", inst.credit),
        ("Currency", inst.currency),
        ("Commodity", inst.commodity),
    ]
    for group, syms in groups:
        for sym in syms:
            q = quotes.get(sym, empty_quote(sym))
            rows.append({"Layer": group, "Symbol": sym, "Price": price_text(q.get("price")), "Change %": pct_text(q.get("change_pct")), "State": state_from_score(score_from_change(safe_float(q.get("change_pct"), 0.0), inst.category))})
    return pd.DataFrame(rows)


def render_action_panel(action: Dict[str, Any], quotes: Dict[str, Dict[str, Any]]) -> None:
    inst = action["inst"]
    q = action["quote"]
    st.header(f"{inst.label} Action Read")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Live Price", price_text(q.get("price")))
    c2.metric("Change %", pct_text(q.get("change_pct")))
    c3.metric("Score", f"{action['score']:.1f}")
    c4.metric("Quality", action["quality"])
    c5.metric("Confidence", f"{action['confidence']}%")

    c1, c2, c3 = st.columns([1.2, 1.2, 1])
    with c1.container(border=True):
        st.subheader("Active Cause")
        st.write(action["active_cause"])
        st.caption("Cause ranked from current cross-market evidence.")
    with c2.container(border=True):
        st.subheader("Target Pressure")
        st.write(action["target_pressure"])
    with c3.container(border=True):
        st.subheader("Session")
        st.write(session_state()["primary"])
        st.caption(fmt_date_time())

    c1, c2, c3 = st.columns(3)
    with c1.container(border=True):
        st.subheader("Confirm")
        for item in action["confirmations"][:6]:
            st.write(f"• {item}")
    with c2.container(border=True):
        st.subheader("Contradict")
        for item in action["contradictions"][:6]:
            st.write(f"• {item}")
    with c3.container(border=True):
        st.subheader("Avoid")
        st.write(action["avoid"])

    st.subheader("Universal Instrument Map")
    st.dataframe(relationship_df(inst, quotes), hide_index=True, use_container_width=True)

    flow = order_flow_proxy(inst, quotes)
    opt_symbol = (inst.options_proxy[0] if inst.options_proxy else inst.ticker)
    options = fetch_options_pressure(opt_symbol)
    c1, c2 = st.columns(2)
    with c1.container(border=True):
        st.subheader("Order Flow Read")
        for k, v in flow.items():
            st.write(f"**{k}:** {v}")
    with c2.container(border=True):
        st.subheader("Options / Instrument Pressure")
        st.write(f"**Proxy:** {opt_symbol}")
        st.write(f"**Status:** {options.get('status', '--')}")
        st.write(f"**Pressure:** {options.get('summary', '--')}")
        st.write(f"**Put/Call:** {options.get('put_call', np.nan):.2f}" if not pd.isna(options.get('put_call', np.nan)) else "**Put/Call:** --")
        st.write(f"**High OI Zone:** {options.get('oi_zone', '--')}")
        st.write(f"**IV:** {options.get('iv_state', '--')}")
        st.caption("Public options feed is delayed/limited unless a professional options/order-flow provider is connected.")


def render_session_map(quotes: Dict[str, Dict[str, Any]]) -> None:
    st.subheader("Live Global Session Map")
    df = session_cards(quotes)
    cols = st.columns(len(df))
    for col, (_, row) in zip(cols, df.iterrows()):
        with col.container(border=True):
            st.caption(row["Session"])
            st.write(f"**{row['Status']}**")
            st.write(row["Driver"])
            st.metric("Price", row["Price"], row["Change"])


def render_active_causes(conditions: Dict[str, Any]) -> None:
    st.subheader("Active Cause Board")
    cols = st.columns(3)
    for i, cause in enumerate(conditions["active_causes"][:3]):
        with cols[i].container(border=True):
            st.caption("ACTIVE" if i == 0 else "CONFIRM / WATCH")
            st.subheader(cause["Cause"])
            st.write(cause["Effect"])
            st.metric("Strength", f"{safe_float(cause.get('Strength')):.2f}")


def render_outcomes(conditions: Dict[str, Any]) -> None:
    st.subheader("Outcome Board")
    score = conditions["score"]
    if score >= 25:
        outcomes = [
            ("Risk-Off Continues", "Highest", "Risk assets pressured; watch QQQ/AI/crypto downside."),
            ("Relief Bounce", "Secondary", "Needs DXY/yields/VIX to cool."),
            ("Mixed Chop", "Fallback", "Likely if confirmations break apart."),
        ]
    elif score <= -25:
        outcomes = [
            ("Risk-On Support", "Highest", "Risk assets supported if dollar/yields stay soft."),
            ("Fade / Trap", "Secondary", "Risk if VIX/credit fail to confirm."),
            ("Rotation", "Fallback", "Sector-specific action without broad confirmation."),
        ]
    else:
        outcomes = [
            ("Mixed Chop", "Highest", "No dominant clean pressure."),
            ("Breakout Pending", "Secondary", "Wait for DXY/yields/VIX alignment."),
            ("Rotation", "Fallback", "Trade only the clean sector/asset."),
        ]
    cols = st.columns(3)
    for col, (name, prob, text) in zip(cols, outcomes):
        with col.container(border=True):
            st.subheader(name)
            st.metric("Priority", prob)
            st.write(text)


def render_search(query: str, quotes: Dict[str, Dict[str, Any]]) -> None:
    inst = resolve_instrument(query)
    needed = symbols_for_fetch([inst.key])
    # Merge additional requested quotes; available after next run if not already present.
    if not set(needed).issubset(quotes.keys()):
        extra = fetch_daily(tuple(needed), period="5d")
        quotes.update(extra)
    action = instrument_action(inst, quotes)
    render_action_panel(action, quotes)

# -----------------------------
# Main app
# -----------------------------

if "selected_key" not in st.session_state:
    st.session_state.selected_key = "NAS"

st.sidebar.title("Macro Regime Engine")
st.sidebar.caption("v8.9 Universal Instruments + Order Flow")
page = st.sidebar.radio("Navigate", ["Action Console", "Universal Search", "Sessions", "Data Health"], index=0)
auto_on = st.sidebar.toggle("Auto Re-run", value=True)
interval = st.sidebar.selectbox("Interval", [15, 30, 60], index=1)
category_filter = st.sidebar.selectbox("Tile Filter", ["Core", "All", "Indexes", "Macro", "Rates", "Volatility", "Credit", "Commodities", "Sectors", "Currencies", "Crypto", "Global"], index=0)

if auto_on and st_autorefresh is not None:
    st_autorefresh(interval=interval * 1000, key="engine_autorefresh")

st.title("Macro Regime Engine v8.9")
query = st.text_input("Search anything: NDX, QQQ, gold, oil, healthcare, real estate, options, order flow, DXY, SPX", value="", placeholder="Type an instrument or theme...")

# Fetch core data. If a user has searched, include that relationship map.
keys = CORE_TILES if category_filter == "Core" else ALL_TILE_KEYS
if category_filter not in {"Core", "All"}:
    keys = [k for k in ALL_TILE_KEYS if UNIVERSE[k].category == category_filter]
selected_inst_for_fetch = resolve_instrument(query) if query else UNIVERSE.get(st.session_state.selected_key, UNIVERSE["NAS"])
fetch_symbols = tuple(symbols_for_fetch(keys + [selected_inst_for_fetch.key, "VIX", "CREDIT", "DOLLAR", "TENY"]))
quotes = fetch_daily(fetch_symbols, period="5d")
conditions = market_conditions(quotes)

# Top command bar
c1, c2, c3, c4 = st.columns([1.4, 1, 1, 1])
c1.metric("State", conditions["state"], f"Score {conditions['score']:.1f}")
c2.metric("Local Time", fmt_time())
c3.metric("Auto Re-run", "ON" if auto_on else "OFF", f"{interval}s")
c4.metric("Data", f"{sum(1 for q in quotes.values() if q.get('ok'))}/{len(quotes)} live", "public feeds")

if query:
    st.divider()
    render_search(query, quotes)
else:
    if page == "Action Console":
        st.subheader("Action Console")
        # Gauges
        g1, g2, g3, g4, g5 = st.columns(5)
        g1.plotly_chart(indicator_gauge("Macro", conditions["score"], conditions["state"]), use_container_width=True)
        ai_score = instrument_action(UNIVERSE["TECH_AI"], quotes)["score"]
        g2.plotly_chart(indicator_gauge("AI", ai_score, state_from_score(ai_score)), use_container_width=True)
        internal_score = (instrument_action(UNIVERSE["SPX"], quotes)["score"] + instrument_action(UNIVERSE["RUSSELL"], quotes)["score"]) / 2
        g3.plotly_chart(indicator_gauge("Internals", internal_score, state_from_score(internal_score)), use_container_width=True)
        liq_score = -instrument_action(UNIVERSE["DOLLAR"], quotes)["score"] - instrument_action(UNIVERSE["TENY"], quotes)["score"] * 0.5
        g4.plotly_chart(indicator_gauge("Liquidity", clamp(liq_score), state_from_score(clamp(liq_score))), use_container_width=True)
        risk_score = -conditions["score"]
        g5.plotly_chart(indicator_gauge("Risk", clamp(risk_score), state_from_score(clamp(risk_score))), use_container_width=True)

        render_active_causes(conditions)
        render_outcomes(conditions)

        st.subheader("Live Market Pulse")
        tile_cols = st.columns(4)
        for idx, key in enumerate(keys[:24]):
            inst = UNIVERSE[key]
            action = instrument_action(inst, quotes)
            with tile_cols[idx % 4]:
                if render_tile(inst, action):
                    st.session_state.selected_key = inst.key
                    st.rerun()

        st.divider()
        selected_inst = UNIVERSE.get(st.session_state.selected_key, UNIVERSE["NAS"])
        render_action_panel(instrument_action(selected_inst, quotes), quotes)

    elif page == "Universal Search":
        st.info("Use the search bar above. Every result shows price, change %, score, quality, instrument relationships, options proxy, order-flow proxy, active cause, target pressure, confirm/invalidate/avoid.")
        render_action_panel(instrument_action(UNIVERSE.get(st.session_state.selected_key, UNIVERSE["NAS"]), quotes), quotes)
    elif page == "Sessions":
        render_session_map(quotes)
        st.subheader("Session Rule")
        st.write("Cash indexes are references during NY cash. Futures drive Asia/London/Globex. ETFs drive US pre-market/after-hours where public feeds allow.")
    elif page == "Data Health":
        st.subheader("Data Health")
        rows = []
        for sym, q in quotes.items():
            rows.append({"Symbol": sym, "OK": q.get("ok"), "Price": price_text(q.get("price")), "Change %": pct_text(q.get("change_pct")), "Updated": q.get("updated")})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.caption("Public yfinance feeds are delayed/limited. True Level II order flow and professional options flow require a connected broker/data provider.")
