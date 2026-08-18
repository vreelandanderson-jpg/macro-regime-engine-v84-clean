from __future__ import annotations

import math
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Tuple
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf
from zoneinfo import ZoneInfo

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:  # pragma: no cover
    st_autorefresh = None

APP_VERSION = "v8.4 Clean Repository"
LOCAL_TZ = ZoneInfo("America/Toronto")
REFRESH_SECONDS = 30

@dataclass(frozen=True)
class Asset:
    symbol: str
    name: str
    category: str
    module: str
    role: str
    risk_sign: int = 1  # +1 means asset up supports risk, -1 means asset up pressures risk, 0 neutral/fear mixed

UNIVERSE: List[Asset] = [
    # Index / index proxies
    Asset("^GSPC", "S&P 500", "Indexes", "Macro", "risk asset", 1),
    Asset("^NDX", "Nasdaq 100", "Indexes", "Macro", "growth risk", 1),
    Asset("QQQ", "Nasdaq ETF", "Indexes", "Macro", "tradeable NAS proxy", 1),
    Asset("SPY", "S&P 500 ETF", "Indexes", "Macro", "tradeable SPX proxy", 1),
    Asset("RSP", "Equal Weight S&P", "Internals", "Internal", "breadth proxy", 1),
    Asset("IWM", "Russell 2000", "Indexes", "Macro", "small caps", 1),
    Asset("DIA", "Dow ETF", "Indexes", "Macro", "industrial index", 1),
    Asset("NQ=F", "Nasdaq Futures", "Indexes", "Extended Hours", "overnight NAS proxy", 1),
    # AI / tech / semis
    Asset("NVDA", "Nvidia", "AI / Tech", "AI", "AI leader", 1),
    Asset("MSFT", "Microsoft", "AI / Tech", "AI", "cloud / AI", 1),
    Asset("AAPL", "Apple", "AI / Tech", "AI", "mega-cap tech", 1),
    Asset("AMZN", "Amazon", "AI / Tech", "AI", "cloud / consumer", 1),
    Asset("GOOGL", "Alphabet", "AI / Tech", "AI", "AI / ads / cloud", 1),
    Asset("META", "Meta", "AI / Tech", "AI", "AI / ads", 1),
    Asset("AMD", "AMD", "AI / Tech", "AI", "chip leader", 1),
    Asset("AVGO", "Broadcom", "AI / Tech", "AI", "AI infrastructure", 1),
    Asset("ORCL", "Oracle", "AI / Tech", "AI", "cloud / data", 1),
    Asset("PLTR", "Palantir", "AI / Tech", "AI", "AI software", 1),
    Asset("TSLA", "Tesla", "AI / Tech", "AI", "AI / growth", 1),
    Asset("SMH", "Semiconductors", "Semiconductors", "AI", "semi ETF", 1),
    Asset("SOXX", "Semiconductor ETF", "Semiconductors", "AI", "semi ETF", 1),
    Asset("TSM", "TSMC", "Semiconductors", "AI", "foundry / supply chain", 1),
    Asset("ASML", "ASML", "Semiconductors", "AI", "semi equipment", 1),
    # Sectors
    Asset("XLK", "Technology", "Sectors", "Sector Rotation", "growth sector", 1),
    Asset("XLC", "Communication Services", "Sectors", "Sector Rotation", "growth sector", 1),
    Asset("XLY", "Consumer Discretionary", "Sectors", "Sector Rotation", "cyclical sector", 1),
    Asset("XLF", "Financials", "Sectors", "Sector Rotation", "bank / credit sensitive", 1),
    Asset("XLE", "Energy", "Sectors", "Sector Rotation", "oil / inflation", 0),
    Asset("XLI", "Industrials", "Sectors", "Sector Rotation", "cyclical sector", 1),
    Asset("XLV", "Healthcare", "Sectors", "Sector Rotation", "defensive sector", -1),
    Asset("XLP", "Consumer Staples", "Sectors", "Sector Rotation", "defensive sector", -1),
    Asset("XLU", "Utilities", "Sectors", "Sector Rotation", "defensive / rate sensitive", -1),
    Asset("XLB", "Materials", "Sectors", "Sector Rotation", "materials / global growth", 1),
    Asset("XLRE", "Real Estate", "Real Estate", "Real Estate", "rate-sensitive sector", 1),
    # Real estate / housing
    Asset("VNQ", "REITs", "Real Estate", "Real Estate", "REIT proxy", 1),
    Asset("IYR", "US Real Estate", "Real Estate", "Real Estate", "real estate ETF", 1),
    Asset("ITB", "Homebuilders", "Real Estate", "Housing", "homebuilder ETF", 1),
    Asset("XHB", "Homebuilders Broad", "Real Estate", "Housing", "housing sector", 1),
    Asset("MBB", "Mortgage Bonds", "Real Estate", "Housing", "mortgage credit", 1),
    Asset("REM", "Mortgage REITs", "Real Estate", "Housing", "mortgage REITs", 1),
    # Sub sectors
    Asset("IYT", "Transportation", "Sub-Sectors", "Sub-Sectors", "transport / economy", 1),
    Asset("XRT", "Retail", "Sub-Sectors", "Sub-Sectors", "consumer breadth", 1),
    Asset("XME", "Metals & Mining", "Sub-Sectors", "Sub-Sectors", "cyclical commodities", 1),
    Asset("XOP", "Oil Exploration", "Sub-Sectors", "Sub-Sectors", "oil beta", 0),
    Asset("OIH", "Oil Services", "Sub-Sectors", "Sub-Sectors", "oil services", 0),
    Asset("TAN", "Solar", "Sub-Sectors", "Sub-Sectors", "rate-sensitive clean energy", 1),
    Asset("JETS", "Airlines", "Sub-Sectors", "Sub-Sectors", "travel / oil sensitive", 1),
    Asset("IBB", "Biotech", "Sub-Sectors", "Sub-Sectors", "healthcare growth", 1),
    Asset("XBI", "Biotech Equal Weight", "Sub-Sectors", "Sub-Sectors", "speculative biotech", 1),
    Asset("ITA", "Aerospace Defense", "Sub-Sectors", "Sub-Sectors", "defense", 0),
    Asset("XAR", "Aerospace Defense Equal", "Sub-Sectors", "Sub-Sectors", "defense", 0),
    # Bonds / dollar / vol / credit
    Asset("UUP", "US Dollar ETF", "Dollar", "Dollar", "dollar pressure", -1),
    Asset("DX-Y.NYB", "Dollar Index", "Dollar", "Dollar", "DXY reference", -1),
    Asset("^TNX", "US 10Y Yield", "Bonds", "Rates", "long yield", -1),
    Asset("^FVX", "US 5Y Yield", "Bonds", "Rates", "mid yield", -1),
    Asset("^IRX", "13 Week Bill", "Bonds", "Rates", "front-end yield", -1),
    Asset("TLT", "20Y Treasury", "Bonds", "Rates", "duration / bond bid", 1),
    Asset("IEF", "7-10Y Treasury", "Bonds", "Rates", "intermediate bonds", 1),
    Asset("SHY", "1-3Y Treasury", "Bonds", "Rates", "front-end bonds", 1),
    Asset("HYG", "High Yield Credit", "Credit", "Credit", "credit risk appetite", 1),
    Asset("JNK", "Junk Bonds", "Credit", "Credit", "credit risk appetite", 1),
    Asset("LQD", "Investment Grade", "Credit", "Credit", "investment grade credit", 1),
    Asset("BKLN", "Senior Loans", "Credit", "Credit", "loan / funding stress", 1),
    Asset("KRE", "Regional Banks", "Credit", "Credit", "bank stress", 1),
    Asset("KBE", "Banks", "Credit", "Credit", "bank stress", 1),
    Asset("^VIX", "VIX", "Volatility", "Volatility", "equity fear", -1),
    Asset("^VVIX", "VVIX", "Volatility", "Volatility", "vol of vol", -1),
    Asset("^VIX9D", "VIX 9-Day", "Volatility", "Volatility", "event volatility", -1),
    Asset("^VIX3M", "VIX 3-Month", "Volatility", "Volatility", "medium vol", -1),
    Asset("^SKEW", "SKEW", "Volatility", "Volatility", "tail risk", -1),
    # Commodities
    Asset("GC=F", "Gold Futures", "Commodities", "Commodities", "gold / safety", 0),
    Asset("SI=F", "Silver Futures", "Commodities", "Commodities", "silver", 0),
    Asset("HG=F", "Copper Futures", "Commodities", "Commodities", "growth metal", 1),
    Asset("CL=F", "WTI Oil", "Commodities", "Commodities", "oil / inflation", -1),
    Asset("BZ=F", "Brent Oil", "Commodities", "Commodities", "oil / inflation", -1),
    Asset("NG=F", "Natural Gas", "Commodities", "Commodities", "energy shock", -1),
    Asset("URA", "Uranium", "Commodities", "Commodities", "uranium / power", 0),
    Asset("ZW=F", "Wheat", "Commodities", "Commodities", "food inflation", -1),
    Asset("ZC=F", "Corn", "Commodities", "Commodities", "food inflation", -1),
    Asset("ZS=F", "Soybeans", "Commodities", "Commodities", "food inflation", -1),
    Asset("DBA", "Agriculture ETF", "Commodities", "Commodities", "agriculture", -1),
    Asset("DBC", "Commodity Basket", "Commodities", "Commodities", "broad commodities", -1),
    # Currencies
    Asset("EURUSD=X", "EUR/USD", "Currencies", "Currencies", "euro dollar pair", 0),
    Asset("USDJPY=X", "USD/JPY", "Currencies", "Currencies", "yen carry / dollar", -1),
    Asset("GBPUSD=X", "GBP/USD", "Currencies", "Currencies", "sterling dollar", 0),
    Asset("CAD=X", "USD/CAD", "Currencies", "Currencies", "canada dollar pressure", -1),
    Asset("AUDUSD=X", "AUD/USD", "Currencies", "Currencies", "risk / China proxy", 1),
    Asset("CHF=X", "USD/CHF", "Currencies", "Currencies", "safe-haven cross", -1),
    Asset("CEW", "EM Currency ETF", "Currencies", "Currencies", "EM FX proxy", 1),
    # Crypto / liquidity risk
    Asset("BTC-USD", "Bitcoin", "Crypto", "Crypto", "liquidity beta", 1),
    Asset("ETH-USD", "Ethereum", "Crypto", "Crypto", "liquidity beta", 1),
    Asset("SOL-USD", "Solana", "Crypto", "Crypto", "speculative liquidity", 1),
    Asset("COIN", "Coinbase", "Crypto", "Crypto", "crypto equity", 1),
    Asset("MSTR", "MicroStrategy", "Crypto", "Crypto", "btc equity proxy", 1),
    Asset("MARA", "Marathon Digital", "Crypto", "Crypto", "bitcoin miner", 1),
    Asset("RIOT", "Riot Platforms", "Crypto", "Crypto", "bitcoin miner", 1),
    # Global markets
    Asset("EWC", "Canada", "Global", "Global Markets", "canada proxy", 1),
    Asset("VGK", "Europe", "Global", "Global Markets", "europe proxy", 1),
    Asset("FEZ", "Eurozone", "Global", "Global Markets", "eurozone proxy", 1),
    Asset("EWG", "Germany", "Global", "Global Markets", "germany proxy", 1),
    Asset("EWQ", "France", "Global", "Global Markets", "france proxy", 1),
    Asset("EWU", "United Kingdom", "Global", "Global Markets", "uk proxy", 1),
    Asset("EWJ", "Japan", "Global", "Global Markets", "japan proxy", 1),
    Asset("FXI", "China Large Cap", "Global", "Global Markets", "china proxy", 1),
    Asset("MCHI", "China Broad", "Global", "Global Markets", "china broad proxy", 1),
    Asset("EWH", "Hong Kong", "Global", "Global Markets", "hong kong proxy", 1),
    Asset("INDA", "India", "Global", "Global Markets", "india proxy", 1),
    Asset("EEM", "Emerging Markets", "Global", "Global Markets", "EM risk", 1),
    Asset("EFA", "Developed Markets", "Global", "Global Markets", "developed markets", 1),
]

ASSET_MAP = {a.symbol: a for a in UNIVERSE}
RISK_ON = {"^GSPC", "SPY", "^NDX", "QQQ", "RSP", "IWM", "HYG", "JNK", "NVDA", "SMH", "SOXX", "XLK", "XLY", "XLF", "XLRE", "VNQ", "ITB", "BTC-USD"}
RISK_OFF = {"UUP", "DX-Y.NYB", "^TNX", "^FVX", "^IRX", "^VIX", "^VVIX", "^VIX9D", "^VIX3M", "^SKEW"}
CORE_TILES = ["^GSPC", "QQQ", "RSP", "UUP", "^TNX", "^VIX", "GC=F", "CL=F", "NVDA", "SMH", "HYG", "BTC-USD", "XLRE", "VNQ", "ITB", "XLF", "KRE", "EEM"]

NEWS_QUERIES = [
    "Federal Reserve markets", "CPI inflation stocks", "China semiconductor Nvidia", "oil prices geopolitics",
    "regional banks credit stress", "real estate mortgage rates", "Treasury yields auction", "AI stocks earnings",
]

EVENTS = [
    ("Initial Jobless Claims", "weekly", 3, "8:30 AM"),
    ("EIA Crude Oil Inventories", "weekly", 2, "10:30 AM"),
    ("ISM Manufacturing", "monthly", 1, "10:00 AM"),
    ("Employment Situation / NFP", "monthly", 4, "8:30 AM"),
    ("CPI Inflation", "monthly", 10, "8:30 AM"),
    ("PPI Inflation", "monthly", 11, "8:30 AM"),
    ("Retail Sales", "monthly", 15, "8:30 AM"),
    ("FOMC Watch Window", "monthly", 20, "2:00 PM"),
]

def now_et() -> datetime:
    return datetime.now(LOCAL_TZ)

def fmt_time(dt: datetime | pd.Timestamp | None) -> str:
    if dt is None or pd.isna(dt):
        return "N/A"
    if isinstance(dt, pd.Timestamp):
        if dt.tzinfo is None:
            dt = dt.tz_localize("UTC")
        dt = dt.tz_convert(LOCAL_TZ).to_pydatetime()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=LOCAL_TZ)
    return dt.astimezone(LOCAL_TZ).strftime("%-I:%M %p") if hasattr(dt, "strftime") else str(dt)

def fmt_date_time(dt: datetime | pd.Timestamp | None) -> str:
    if dt is None or pd.isna(dt):
        return "N/A"
    if isinstance(dt, pd.Timestamp):
        if dt.tzinfo is None:
            dt = dt.tz_localize("UTC")
        dt = dt.tz_convert(LOCAL_TZ).to_pydatetime()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=LOCAL_TZ)
    return dt.astimezone(LOCAL_TZ).strftime("%a, %b %-d, %Y — %-I:%M %p")

def session_name(dt: datetime | None = None) -> str:
    dt = dt or now_et()
    t = dt.time()
    if t >= datetime.strptime("04:00", "%H:%M").time() and t < datetime.strptime("09:30", "%H:%M").time():
        return "Pre-market"
    if t >= datetime.strptime("09:30", "%H:%M").time() and t < datetime.strptime("16:00", "%H:%M").time():
        return "Regular NY"
    if t >= datetime.strptime("16:00", "%H:%M").time() and t < datetime.strptime("20:00", "%H:%M").time():
        return "After-hours"
    return "Overnight"

def chunked(seq: List[str], n: int) -> Iterable[List[str]]:
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

def _normalize_download(raw: pd.DataFrame, symbols: List[str]) -> Dict[str, pd.DataFrame]:
    out: Dict[str, pd.DataFrame] = {}
    if raw is None or raw.empty:
        return out
    if isinstance(raw.columns, pd.MultiIndex):
        first = raw.columns.get_level_values(0)
        if set(symbols).intersection(set(first)):
            for sym in symbols:
                if sym in first:
                    df = raw[sym].dropna(how="all")
                    if not df.empty:
                        out[sym] = df
        else:
            second = raw.columns.get_level_values(1)
            for sym in symbols:
                if sym in second:
                    df = raw.xs(sym, axis=1, level=1).dropna(how="all")
                    if not df.empty:
                        out[sym] = df
    elif len(symbols) == 1:
        out[symbols[0]] = raw.dropna(how="all")
    return out

@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def fetch_intraday(symbols: Tuple[str, ...], interval: str = "15m", period: str = "5d") -> Dict[str, pd.DataFrame]:
    data: Dict[str, pd.DataFrame] = {}
    symbols_list = list(symbols)
    for group in chunked(symbols_list, 30):
        try:
            raw = yf.download(
                tickers=" ".join(group), period=period, interval=interval,
                group_by="ticker", auto_adjust=False, prepost=True, progress=False,
                threads=True, timeout=20,
            )
            data.update(_normalize_download(raw, group))
        except Exception:
            for sym in group:
                try:
                    raw_one = yf.download(sym, period=period, interval=interval, auto_adjust=False, prepost=True, progress=False, timeout=15)
                    if raw_one is not None and not raw_one.empty:
                        data[sym] = raw_one.dropna(how="all")
                except Exception:
                    continue
    return data

@st.cache_data(ttl=900, show_spinner=False)
def fetch_daily(symbols: Tuple[str, ...]) -> Dict[str, pd.DataFrame]:
    data: Dict[str, pd.DataFrame] = {}
    for group in chunked(list(symbols), 30):
        try:
            raw = yf.download(" ".join(group), period="3mo", interval="1d", group_by="ticker", auto_adjust=False, progress=False, threads=True, timeout=20)
            data.update(_normalize_download(raw, group))
        except Exception:
            continue
    return data

def get_close_series(df: pd.DataFrame) -> pd.Series:
    if "Close" in df.columns:
        return df["Close"].dropna()
    if "Adj Close" in df.columns:
        return df["Adj Close"].dropna()
    return pd.Series(dtype=float)

def build_market_frame(intra: Dict[str, pd.DataFrame], daily: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for asset in UNIVERSE:
        df = intra.get(asset.symbol)
        if df is None or df.empty:
            df = daily.get(asset.symbol)
        if df is None or df.empty:
            continue
        close = get_close_series(df)
        if close.empty:
            continue
        latest = float(close.iloc[-1])
        prev = float(close.iloc[-2]) if len(close) > 1 and close.iloc[-2] != 0 else latest
        change_pct = ((latest / prev) - 1) * 100 if prev else 0.0
        raw_score = change_pct * 25 * asset.risk_sign
        if asset.risk_sign == 0:
            raw_score = change_pct * 10
        score = float(np.clip(raw_score, -100, 100))
        direction = "supportive" if score > 15 else "pressure" if score < -15 else "mixed"
        state = state_label(asset.symbol, change_pct, score)
        latest_ts = close.index[-1]
        rows.append({
            "symbol": asset.symbol, "name": asset.name, "category": asset.category, "module": asset.module,
            "role": asset.role, "latest_time": latest_ts, "latest_date": str(pd.Timestamp(latest_ts).date()),
            "latest_close": latest, "change_pct": change_pct, "score": score, "direction": direction,
            "state": state, "risk_sign": asset.risk_sign,
        })
    return pd.DataFrame(rows)

def state_label(symbol: str, change_pct: float, score: float) -> str:
    if symbol in RISK_OFF:
        if change_pct > 0.15:
            return "PRESSURE UP"
        if change_pct < -0.15:
            return "PRESSURE DOWN"
        return "MIXED"
    if score > 35:
        return "STRONG"
    if score > 10:
        return "SUPPORTIVE"
    if score < -35:
        return "WEAK"
    if score < -10:
        return "PRESSURE"
    return "MIXED"

def value(df: pd.DataFrame, symbol: str, column: str, default: float = 0.0) -> float:
    try:
        row = df.loc[df.symbol == symbol]
        if row.empty:
            return default
        return float(row.iloc[0][column])
    except Exception:
        return default

def score_group(df: pd.DataFrame, symbols: List[str]) -> float:
    part = df[df.symbol.isin(symbols)]
    if part.empty:
        return 0.0
    return float(part["score"].mean())

def calc_scores(df: pd.DataFrame) -> Dict[str, float]:
    scores = {
        "Macro": score_group(df, ["^GSPC", "SPY", "^NDX", "QQQ", "RSP", "IWM", "HYG", "JNK", "UUP", "^TNX", "^VIX"]),
        "AI": score_group(df, ["NVDA", "MSFT", "AAPL", "AMZN", "GOOGL", "META", "AMD", "AVGO", "ORCL", "PLTR", "SMH", "SOXX", "TSM", "ASML"]),
        "Internals": score_group(df, ["RSP", "IWM", "HYG", "JNK", "KRE", "KBE", "XRT", "IYT", "XLK", "XLF", "XLRE"]),
        "Liquidity": score_group(df, ["UUP", "DX-Y.NYB", "^TNX", "^FVX", "^IRX", "TLT", "IEF", "HYG", "JNK"]),
        "Risk": score_group(df, ["^GSPC", "QQQ", "RSP", "HYG", "BTC-USD", "^VIX", "UUP", "^TNX"]),
        "Real Estate": score_group(df, ["XLRE", "VNQ", "IYR", "ITB", "XHB", "MBB", "REM"]),
        "Global": score_group(df, ["EWC", "VGK", "EWG", "EWJ", "FXI", "MCHI", "INDA", "EEM", "EFA"]),
    }
    return {k: round(v, 1) for k, v in scores.items()}

def regime_from_score(score: float) -> str:
    if score >= 60: return "STRONG RISK-ON"
    if score >= 25: return "RISK-ON"
    if score > -25: return "MIXED / WAIT"
    if score > -60: return "RISK-OFF PRESSURE"
    return "STRONG RISK-OFF"

def quality(score: float, confirms: int, contradicts: int) -> Tuple[str, int]:
    base = min(100, int(abs(score) * 0.75 + confirms * 8 - contradicts * 10))
    if abs(score) < 20 or confirms < 2:
        return "WEAK / MIXED", max(20, base)
    if confirms >= 5 and contradicts <= 1:
        return "STRONG", max(base, 75)
    if confirms >= 3:
        return "MEDIUM", max(base, 55)
    return "WEAK / MIXED", max(20, base)

def detect_active_causes(df: pd.DataFrame) -> List[Dict[str, object]]:
    causes = []
    qqq = value(df, "QQQ", "score")
    ai = score_group(df, ["NVDA", "SMH", "SOXX", "AMD", "AVGO"])
    dxy_chg = value(df, "UUP", "change_pct")
    teny_chg = value(df, "^TNX", "change_pct")
    vix_chg = value(df, "^VIX", "change_pct")
    hyg = value(df, "HYG", "score")
    xre = score_group(df, ["XLRE", "VNQ", "ITB", "XHB"])
    oil = value(df, "CL=F", "change_pct")
    gold = value(df, "GC=F", "change_pct")
    rsp = value(df, "RSP", "score")
    btc = value(df, "BTC-USD", "score")
    semis = score_group(df, ["SMH", "SOXX", "NVDA", "AMD", "AVGO", "TSM", "ASML"])
    confirms, contradictions = [], []
    if dxy_chg > 0.2 and teny_chg > 0.1:
        confirms = ["Dollar rising", "10Y firm"]
        if qqq < -10: confirms.append("QQQ weak")
        else: contradictions.append("QQQ not confirming")
        if vix_chg > 0: confirms.append("VIX firm")
        else: contradictions.append("VIX not confirming")
        if ai < -10: confirms.append("AI / semis weak")
        else: contradictions.append("AI not confirming")
        causes.append({"cause":"Dollar + yield pressure", "status":"ACTIVE", "category":"Macro / Liquidity", "affected":"QQQ, AI, crypto, real estate, credit", "effect":"Risk assets under pressure", "target":"QQQ downside / VIX up / credit watch", "confirm":confirms, "contradict":contradictions, "severity":70 + len(confirms)*4 - len(contradictions)*8})
    if semis < -20:
        confirms = ["SMH/SOXX under pressure"]
        if value(df, "NVDA", "score") < -10: confirms.append("NVDA weak")
        if qqq < -10: confirms.append("QQQ confirming")
        if dxy_chg < 0 and teny_chg < 0: contradictions.append("Macro pressure not adding")
        causes.append({"cause":"Semiconductor / AI leadership weakness", "status":"ACTIVE", "category":"Sector / AI", "affected":"SMH, SOXX, NVDA, AMD, AVGO, TSM, ASML, QQQ", "effect":"Growth leadership under pressure", "target":"QQQ / NDX downside unless semis reclaim", "confirm":confirms, "contradict":contradictions, "severity":68 + len(confirms)*4})
    if vix_chg > 2:
        confirms = ["VIX rising"]
        if qqq < -10: confirms.append("QQQ weak")
        if rsp < -10: confirms.append("breadth weak")
        if hyg < -10: confirms.append("credit weak")
        causes.append({"cause":"Volatility expansion", "status":"ACTIVE", "category":"Volatility", "affected":"Indexes, AI, crypto, intraday range", "effect":"Faster tape / hedging pressure", "target":"VIX continuation / risk assets lower", "confirm":confirms, "contradict":[], "severity":60 + len(confirms)*5})
    if xre < -20 and teny_chg > 0:
        causes.append({"cause":"Real estate rate pressure", "status":"ACTIVE", "category":"Real Estate / Housing", "affected":"XLRE, VNQ, IYR, ITB, XHB, mortgage-sensitive assets", "effect":"Housing/REIT weakness", "target":"Real estate downside until yields cool", "confirm":["Real estate weak", "10Y yield firm"], "contradict":[], "severity":62})
    if hyg < -20 or value(df, "KRE", "score") < -20:
        causes.append({"cause":"Credit / bank stress", "status":"ACTIVE", "category":"Credit", "affected":"HYG, JNK, KRE, KBE, financials, small caps", "effect":"Risk appetite not trusted", "target":"Equity downside if credit keeps weakening", "confirm":["credit/banks weak"], "contradict":[], "severity":58})
    if oil > 1.0:
        causes.append({"cause":"Oil / inflation pressure", "status":"WATCH", "category":"Commodity", "affected":"Energy, yields, inflation expectations, airlines, consumers", "effect":"Inflation-risk pressure", "target":"Yields/dollar may firm if oil pressure persists", "confirm":["oil rising"], "contradict":[], "severity":48})
    if gold > 0.5 and (vix_chg > 0 or qqq < 0):
        causes.append({"cause":"Gold safety bid", "status":"ACTIVE", "category":"Commodity / Fear", "affected":"Gold, miners, dollar/yields relationship", "effect":"Defensive demand active", "target":"Gold continuation if fear/yields support it", "confirm":["gold up", "risk/fear context"], "contradict":[], "severity":54})
    if btc < -20 and qqq < -10:
        causes.append({"cause":"Liquidity beta unwind", "status":"ACTIVE", "category":"Crypto / Risk", "affected":"BTC, ETH, crypto equities, QQQ", "effect":"Speculative risk appetite weakening", "target":"Crypto lower unless QQQ/liquidity recover", "confirm":["BTC weak", "QQQ weak"], "contradict":[], "severity":55})
    if not causes:
        causes.append({"cause":"No clean dominant driver", "status":"MIXED", "category":"Cross-market", "affected":"Market broad", "effect":"Chop / wait state", "target":"Wait for dollar/yields/VIX/internals alignment", "confirm":[], "contradict":["No clean agreement"], "severity":20})
    return sorted(causes, key=lambda x: x["severity"], reverse=True)

def compute_action(df: pd.DataFrame, causes: List[Dict[str, object]]) -> Dict[str, object]:
    scores = calc_scores(df)
    macro = scores["Macro"]
    confirms = 0
    contradicts = 0
    for key in ["UUP", "^TNX", "^VIX", "QQQ", "NVDA", "SMH", "HYG", "RSP"]:
        s = value(df, key, "score")
        if macro < -25 and s < -10:
            confirms += 1
        elif macro > 25 and s > 10:
            confirms += 1
        elif abs(s) > 15:
            contradicts += 1
    q, conf = quality(macro, confirms, contradicts)
    primary = causes[0]
    return {
        "state": regime_from_score(macro),
        "primary_driver": primary["cause"],
        "pressure_asset": "QQQ / AI / Growth" if macro < 0 else "Dollar / VIX / Shorts",
        "support_asset": "Gold / Bonds / Defensive" if macro < 0 else "QQQ / AI / Cyclicals",
        "target_pressure": primary["target"],
        "quality": q,
        "confidence": conf,
        "confirmations": confirms,
        "contradictions": contradicts,
        "scores": scores,
    }

def next_events() -> pd.DataFrame:
    base = now_et()
    rows = []
    for name, freq, day, event_time in EVENTS:
        hour, minute_part = event_time.split(":")
        minute = int(minute_part.split()[0])
        hour_int = int(hour)
        if "PM" in event_time and hour_int != 12:
            hour_int += 12
        candidate = base.replace(day=min(day, 28), hour=hour_int, minute=minute, second=0, microsecond=0)
        if freq == "weekly":
            # day uses Python weekday target roughly: 0 Mon. input weekly target day 2 Wed or 3 Thu.
            target_weekday = day
            delta = (target_weekday - base.weekday()) % 7
            candidate = base + timedelta(days=delta)
            candidate = candidate.replace(hour=hour_int, minute=minute, second=0, microsecond=0)
            if candidate < base:
                candidate += timedelta(days=7)
        elif candidate < base:
            month = base.month + 1
            year = base.year + (1 if month > 12 else 0)
            month = 1 if month > 12 else month
            candidate = candidate.replace(year=year, month=month)
        days = max(0, (candidate.date() - base.date()).days)
        rows.append({"event": name, "time": fmt_date_time(candidate), "days": days, "impact": "HIGH" if any(k in name for k in ["CPI", "FOMC", "NFP", "Employment"]) else "MEDIUM"})
    return pd.DataFrame(rows).sort_values(["days", "event"]).head(6)

@st.cache_data(ttl=600, show_spinner=False)
def fetch_headlines() -> pd.DataFrame:
    records = []
    for q in NEWS_QUERIES:
        url = f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=en-US&gl=US&ceid=US:en"
        try:
            resp = requests.get(url, timeout=8, headers={"User-Agent":"Mozilla/5.0"})
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            for item in root.findall("./channel/item")[:3]:
                title = item.findtext("title", default="").strip()
                pub = item.findtext("pubDate", default="")
                if title:
                    records.append({"query": q, "headline": title, "published": pub, "affected": headline_affected(title)})
        except Exception:
            continue
    return pd.DataFrame(records).drop_duplicates(subset=["headline"]).head(12)

def headline_affected(title: str) -> str:
    low = title.lower()
    if any(k in low for k in ["chip", "semiconductor", "nvidia", "export", "china"]):
        return "Semiconductors / AI / QQQ"
    if any(k in low for k in ["fed", "rate", "yield", "treasury"]):
        return "Dollar / yields / bonds / growth"
    if any(k in low for k in ["oil", "opec", "middle east"]):
        return "Oil / inflation / energy"
    if any(k in low for k in ["bank", "credit"]):
        return "Credit / banks / financials"
    if any(k in low for k in ["home", "housing", "mortgage", "real estate"]):
        return "Real estate / housing"
    return "Broad market"

def extended_hours_read(intra: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for sym in ["QQQ", "NQ=F", "^NDX"]:
        df = intra.get(sym)
        if df is None or df.empty:
            continue
        close = get_close_series(df)
        if close.empty:
            continue
        idx = pd.to_datetime(close.index)
        if idx.tz is None:
            idx = idx.tz_localize("UTC")
        idx = idx.tz_convert(LOCAL_TZ)
        s = pd.Series(close.values, index=idx).dropna()
        today = now_et().date()
        today_s = s[s.index.date == today]
        pre = today_s.between_time("04:00", "09:29") if not today_s.empty else pd.Series(dtype=float)
        reg = today_s.between_time("09:30", "15:59") if not today_s.empty else pd.Series(dtype=float)
        aft = today_s.between_time("16:00", "20:00") if not today_s.empty else pd.Series(dtype=float)
        one_h = s.resample("60min").last().dropna()
        four_h = s.resample("4h").last().dropna()
        rows.append({
            "symbol": sym,
            "session": session_name(),
            "last_extended": float(s.iloc[-1]),
            "last_time": fmt_time(s.index[-1].to_pydatetime()),
            "pre_high": float(pre.max()) if not pre.empty else np.nan,
            "pre_low": float(pre.min()) if not pre.empty else np.nan,
            "regular_high": float(reg.max()) if not reg.empty else np.nan,
            "regular_low": float(reg.min()) if not reg.empty else np.nan,
            "after_high": float(aft.max()) if not aft.empty else np.nan,
            "after_low": float(aft.min()) if not aft.empty else np.nan,
            "1H_close": float(one_h.iloc[-1]) if not one_h.empty else np.nan,
            "4H_close": float(four_h.iloc[-1]) if not four_h.empty else np.nan,
        })
    return pd.DataFrame(rows)

def make_gauge(title: str, score: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"font":{"size":34}},
        title={"text":title, "font":{"size":14}},
        gauge={
            "axis":{"range":[-100,100], "tickwidth":1},
            "bar":{"color":"#ffd23f" if -25 <= score <= 25 else "#35d07f" if score > 25 else "#ff4b4b"},
            "steps":[
                {"range":[-100,-25], "color":"rgba(255,75,75,0.25)"},
                {"range":[-25,25], "color":"rgba(255,210,63,0.18)"},
                {"range":[25,100], "color":"rgba(53,208,127,0.18)"},
            ],
            "threshold":{"line":{"color":"white", "width":3}, "value":score},
        }
    ))
    fig.update_layout(height=230, margin=dict(l=10,r=10,t=40,b=10), paper_bgcolor="rgba(0,0,0,0)", font_color="#f2f6ff")
    return fig

def fmt_num(x: float) -> str:
    if pd.isna(x):
        return "N/A"
    if abs(x) >= 1000:
        return f"{x:,.0f}"
    return f"{x:,.2f}"

def asset_action(symbol: str, df: pd.DataFrame, causes: List[Dict[str, object]]) -> Dict[str, str]:
    row = df[df.symbol == symbol]
    if row.empty:
        return {"title":"No asset selected", "now":"Select a tile.", "target":"N/A", "confirm":"N/A", "invalidate":"N/A", "avoid":"N/A"}
    r = row.iloc[0]
    related_cause = next((c for c in causes if symbol in str(c.get("affected", "")) or r.category in str(c.get("affected", ""))), causes[0])
    score = float(r.score)
    q, conf = quality(score, len(related_cause.get("confirm", [])), len(related_cause.get("contradict", [])))
    direction = "upside/reclaim" if score > 20 else "downside/breakdown" if score < -20 else "mixed/range"
    return {
        "title": f"{r.symbol} — {r['name']}",
        "now": f"{r.state} | Score {score:.1f} | Quality {q} | Confidence {conf}%",
        "cause": str(related_cause["cause"]),
        "target": f"{direction} pressure. Watch session high/low, previous close, and 1H/4H close response.",
        "confirm": ", ".join(related_cause.get("confirm", [])) or "Need cross-market confirmation.",
        "invalidate": ", ".join(related_cause.get("contradict", [])) or "Opposite reclaim/rollover with score weakening.",
        "avoid": "Avoid chasing if score quality is weak/mixed or key related markets contradict the read.",
        "related": str(related_cause.get("affected", "Broad market")),
    }

def target_board(df: pd.DataFrame, action: Dict[str, object]) -> pd.DataFrame:
    targets = []
    for sym in ["QQQ", "UUP", "^TNX", "^VIX", "GC=F", "NVDA", "SMH", "XLRE"]:
        row = df[df.symbol == sym]
        if row.empty:
            continue
        r = row.iloc[0]
        bias = "Upside/Reclaim" if r.score > 15 else "Downside/Breakdown" if r.score < -15 else "Range/Wait"
        targets.append({"asset": f"{r.symbol} {r['name']}", "pressure": bias, "state": r.state, "score": round(r.score, 1), "watch": "Session range + 1H/4H close"})
    return pd.DataFrame(targets)

def outcome_board(action: Dict[str, object]) -> pd.DataFrame:
    macro = float(action["scores"]["Macro"])
    if macro < -25:
        data = [
            {"outcome":"Risk-off continues", "probability":"55%", "target":"QQQ/AI lower, VIX firm, credit watch", "confirm":"DXY/yields/VIX stay firm", "invalidate":"DXY rolls over + QQQ reclaims"},
            {"outcome":"Relief bounce", "probability":"30%", "target":"QQQ bounce / AI recovery", "confirm":"Yields cool + VIX fades", "invalidate":"AI leaders fail"},
            {"outcome":"Mixed chop", "probability":"15%", "target":"Range-bound", "confirm":"internals split", "invalidate":"broad confirmation appears"},
        ]
    elif macro > 25:
        data = [
            {"outcome":"Risk-on extends", "probability":"55%", "target":"QQQ/AI/cyclicals higher", "confirm":"DXY down + VIX down + breadth strong", "invalidate":"yields/dollar spike"},
            {"outcome":"Fake risk-on", "probability":"30%", "target":"failed breakout", "confirm":"AI narrow + credit weak", "invalidate":"internals broaden"},
            {"outcome":"Pause/chop", "probability":"15%", "target":"sideways", "confirm":"low volatility", "invalidate":"vol expansion"},
        ]
    else:
        data = [
            {"outcome":"Mixed chop", "probability":"50%", "target":"range-bound", "confirm":"scores stay mixed", "invalidate":"clean driver appears"},
            {"outcome":"Risk-off break", "probability":"30%", "target":"QQQ lower", "confirm":"DXY/yields/VIX up", "invalidate":"breadth improves"},
            {"outcome":"Risk-on reclaim", "probability":"20%", "target":"QQQ higher", "confirm":"DXY/VIX down", "invalidate":"credit weakens"},
        ]
    return pd.DataFrame(data)

def render_metric_card(label: str, value_text: str, help_text: str | None = None):
    with st.container(border=True):
        st.caption(label)
        st.subheader(value_text)
        if help_text:
            st.caption(help_text)

def render_tile(row: pd.Series, selected: str) -> bool:
    label = f"{row.symbol}\n{fmt_num(row.latest_close)}\n{row.change_pct:+.2f}%\n{row.state}"
    return st.button(label, key=f"tile_{row.symbol}", use_container_width=True, type="primary" if row.symbol == selected else "secondary")

# ------------------------- UI -------------------------
st.set_page_config(page_title="Macro Regime Engine", layout="wide", page_icon="📡")

if "selected_symbol" not in st.session_state:
    st.session_state.selected_symbol = "QQQ"
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = True
if "refresh_interval" not in st.session_state:
    st.session_state.refresh_interval = REFRESH_SECONDS

with st.sidebar:
    st.title(f"MACRO REGIME ENGINE {APP_VERSION}")
    page = st.radio("Navigation", [
        "Action Console", "Live Market Pulse", "Active Causes", "Extended Hours", "Real Estate", "Sectors", "Sub-Sectors",
        "Currencies", "Credit", "Volatility", "Global Markets", "Events", "Search", "Data Health", "Raw Tables"
    ], label_visibility="collapsed")
    st.divider()
    st.toggle("Auto re-run", key="auto_refresh")
    st.selectbox("Refresh interval", [15, 30, 60, 120], key="refresh_interval")
    st.caption("Toronto / Eastern 12-hour time")

if st.session_state.auto_refresh and st_autorefresh is not None:
    st_autorefresh(interval=int(st.session_state.refresh_interval) * 1000, key="global_live_refresh")

symbols_tuple = tuple([a.symbol for a in UNIVERSE])
with st.spinner("Loading live market data..."):
    intra = fetch_intraday(symbols_tuple)
    daily = fetch_daily(symbols_tuple)
market = build_market_frame(intra, daily)
causes = detect_active_causes(market) if not market.empty else []
action = compute_action(market, causes) if not market.empty else {"state":"NO DATA", "primary_driver":"No data loaded", "pressure_asset":"N/A", "support_asset":"N/A", "target_pressure":"N/A", "quality":"N/A", "confidence":0, "confirmations":0, "contradictions":0, "scores":{}}

# Top command bar: native Streamlit only
cmd_cols = st.columns([3.2, 0.8, 0.9, 1.0, 0.9, 0.9])
with cmd_cols[0]:
    global_query = st.text_input("Search everything", placeholder="NDX, QQQ, NVDA, internals, real estate, credit, gold, yields, oil", label_visibility="collapsed")
with cmd_cols[1]:
    st.metric("Local", now_et().strftime("%-I:%M %p"))
with cmd_cols[2]:
    st.metric("Session", session_name())
with cmd_cols[3]:
    status = "LIVE" if not market.empty else "NO DATA"
    st.metric("Data", status, f"{len(market)} series")
with cmd_cols[4]:
    if st.button("Update now", use_container_width=True):
        fetch_intraday.clear(); fetch_daily.clear(); fetch_headlines.clear(); st.rerun()
with cmd_cols[5]:
    st.metric("Auto", "ON" if st.session_state.auto_refresh else "OFF", f"{st.session_state.refresh_interval}s")

if global_query:
    page = "Search"

if page == "Action Console":
    st.header("ACTION CONSOLE")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: render_metric_card("NOW", str(action["state"]), f"Quality: {action['quality']} | {action['confidence']}%")
    with c2: render_metric_card("ACTIVE CAUSE", str(action["primary_driver"]), "Highest ranked live driver")
    with c3: render_metric_card("PRESSURE", str(action["pressure_asset"]), "Most affected right now")
    with c4: render_metric_card("TARGET PRESSURE", str(action["target_pressure"]), "Live directional pressure")
    with c5: render_metric_card("CONFIRM / CONTRADICT", f"{action['confirmations']} / {action['contradictions']}", "Cross-market agreement")

    st.subheader("Regime Meter Gauges")
    gcols = st.columns(5)
    for i, key in enumerate(["Macro", "AI", "Internals", "Liquidity", "Risk"]):
        with gcols[i]:
            score = float(action["scores"].get(key, 0))
            st.plotly_chart(make_gauge(key, score), use_container_width=True, config={"displayModeBar": False})
            st.caption(regime_from_score(score))

    st.subheader("Target Board")
    st.dataframe(target_board(market, action), use_container_width=True, hide_index=True)

    st.subheader("Outcome Board")
    st.dataframe(outcome_board(action), use_container_width=True, hide_index=True)

    st.subheader("Confirm / Invalidate / Avoid")
    top_cause = causes[0] if causes else {}
    cc1, cc2, cc3 = st.columns(3)
    with cc1: render_metric_card("CONFIRM", " | ".join(top_cause.get("confirm", [])) or "Need confirmation", "Signals proving the read")
    with cc2: render_metric_card("INVALIDATE", " | ".join(top_cause.get("contradict", [])) or "Opposite reclaim/rollover", "Signals canceling the read")
    with cc3: render_metric_card("AVOID", "Weak score quality / mixed confirmations", "Do not chase when contradiction is high")

    st.subheader("Live Market Pulse")
    tile_df = market[market.symbol.isin(CORE_TILES)].copy()
    for row_start in range(0, len(tile_df), 6):
        cols = st.columns(6)
        for col, (_, r) in zip(cols, tile_df.iloc[row_start:row_start+6].iterrows()):
            with col:
                if render_tile(r, st.session_state.selected_symbol):
                    st.session_state.selected_symbol = str(r.symbol)
                    st.rerun()
    st.subheader("Selected Asset Action Read")
    read = asset_action(st.session_state.selected_symbol, market, causes)
    ac1, ac2, ac3 = st.columns(3)
    with ac1: render_metric_card(read["title"], read["now"], f"Active cause: {read['cause']}")
    with ac2: render_metric_card("TARGET", read["target"], f"Related: {read['related']}")
    with ac3: render_metric_card("CONFIRM / INVALIDATE", f"Confirm: {read['confirm']}", f"Invalidate: {read['invalidate']}")
    render_metric_card("AVOID", read["avoid"], "Use score quality as timing filter, not location replacement")

elif page == "Live Market Pulse":
    st.header("LIVE MARKET PULSE")
    cats = ["All", "Indexes", "AI / Tech", "Semiconductors", "Real Estate", "Sectors", "Sub-Sectors", "Bonds", "Dollar", "Commodities", "Currencies", "Crypto", "Credit", "Volatility", "Global"]
    cat = st.radio("Filter", cats, horizontal=True)
    data = market if cat == "All" else market[market.category == cat]
    for row_start in range(0, len(data), 5):
        cols = st.columns(5)
        for col, (_, r) in zip(cols, data.iloc[row_start:row_start+5].iterrows()):
            with col:
                if render_tile(r, st.session_state.selected_symbol):
                    st.session_state.selected_symbol = str(r.symbol); st.rerun()
    st.subheader("Selected Asset Action Panel")
    read = asset_action(st.session_state.selected_symbol, market, causes)
    for k in ["now", "cause", "target", "confirm", "invalidate", "avoid", "related"]:
        render_metric_card(k.upper(), read[k], None)

elif page == "Active Causes":
    st.header("ACTIVE CAUSE ENGINE")
    for c in causes:
        with st.container(border=True):
            st.subheader(f"{c['status']} — {c['cause']}")
            cols = st.columns(4)
            cols[0].metric("Category", str(c["category"]))
            cols[1].metric("Severity", int(c["severity"]))
            cols[2].metric("Confirmations", len(c.get("confirm", [])))
            cols[3].metric("Contradictions", len(c.get("contradict", [])))
            st.write("Affected:", c["affected"])
            st.write("Effect:", c["effect"])
            st.write("Target Pressure:", c["target"])
            st.write("Confirm:", ", ".join(c.get("confirm", [])) or "None")
            st.write("Contradict:", ", ".join(c.get("contradict", [])) or "None")
    st.subheader("Headline / Catalyst Watch")
    headlines = fetch_headlines()
    if headlines.empty:
        st.info("Headline watch unavailable or no current items returned. Market-data active causes remain live.")
    else:
        st.dataframe(headlines, use_container_width=True, hide_index=True)

elif page == "Extended Hours":
    st.header("NAS / QQQ EXTENDED HOURS")
    eh = extended_hours_read(intra)
    st.dataframe(eh, use_container_width=True, hide_index=True)
    st.caption("Tracks pre-market, regular NY, after-hours, overnight, and latest 1H/4H closes where Yahoo/yfinance feed provides intraday bars.")

elif page in ["Real Estate", "Sectors", "Sub-Sectors", "Currencies", "Credit", "Volatility", "Global Markets"]:
    cat_map = {"Global Markets":"Global"}
    cat = cat_map.get(page, page)
    st.header(page.upper())
    part = market[market.category == cat].copy()
    if not part.empty:
        avg = part.score.mean()
        pos = (part.score > 0).mean() * 100
        c1, c2, c3 = st.columns(3)
        c1.metric("Category Score", f"{avg:.1f}")
        c2.metric("Positive Participation", f"{pos:.0f}%")
        c3.metric("Loaded Series", len(part))
        st.dataframe(part[["symbol","name","latest_close","change_pct","score","state","role"]], use_container_width=True, hide_index=True)
    else:
        st.warning("No live series loaded for this category.")

elif page == "Events":
    st.header("EVENT RISK")
    st.dataframe(next_events(), use_container_width=True, hide_index=True)

elif page == "Search":
    q = (global_query or st.text_input("Search", placeholder="NDX, real estate, gold, credit, semis, yields")).lower().strip()
    st.header(f"ACTION SEARCH: {q.upper() if q else ''}")
    if q:
        mask = market.apply(lambda r: q in str(r.symbol).lower() or q in str(r["name"]).lower() or q in str(r.category).lower() or q in str(r.role).lower(), axis=1)
        res = market[mask]
        if not res.empty:
            selected_sym = str(res.iloc[0].symbol)
            read = asset_action(selected_sym, market, causes)
            render_metric_card("ACTION READ", read["now"], f"Cause: {read['cause']}")
            render_metric_card("TARGET", read["target"], f"Related: {read['related']}")
            render_metric_card("CONFIRM", read["confirm"], None)
            render_metric_card("INVALIDATE / AVOID", f"{read['invalidate']} | {read['avoid']}", None)
            st.subheader("Direct matches")
            st.dataframe(res[["symbol","name","category","latest_close","change_pct","score","state","role"]], use_container_width=True, hide_index=True)
        else:
            st.info("No direct match. Try QQQ, NDX, real estate, semis, gold, yields, credit, volatility, oil.")

elif page == "Data Health":
    st.header("DATA HEALTH")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Loaded Series", len(market))
    c2.metric("Last Local Time", now_et().strftime("%-I:%M %p"))
    c3.metric("Session", session_name())
    c4.metric("Auto Re-run", "ON" if st.session_state.auto_refresh else "OFF")
    st.write("Live source: yfinance prices with pre/post where available; public Google News RSS for headline watch; no FRED; no demo logic.")
    missing = sorted(set([a.symbol for a in UNIVERSE]) - set(market.symbol.tolist()))
    if missing:
        st.warning(f"Missing/failed symbols: {', '.join(missing[:50])}{'...' if len(missing) > 50 else ''}")
    else:
        st.success("All configured symbols loaded.")

elif page == "Raw Tables":
    st.header("RAW TABLES")
    st.dataframe(market, use_container_width=True, hide_index=True)
