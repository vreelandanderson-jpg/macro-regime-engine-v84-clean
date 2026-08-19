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

APP_VERSION = "v8.7 Global Session Engine"
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
    # Healthcare / science / life-science / defensive innovation
    Asset("VHT", "Vanguard Healthcare", "Healthcare", "Healthcare", "broad healthcare", -1),
    Asset("IYH", "US Healthcare", "Healthcare", "Healthcare", "broad healthcare", -1),
    Asset("ARKG", "Genomics Innovation", "Biotech / Science", "Science", "genomics / innovation", 1),
    Asset("GNOM", "Genomics ETF", "Biotech / Science", "Science", "genomics / biotech", 1),
    Asset("PJP", "Pharmaceuticals ETF", "Pharma", "Healthcare", "pharma basket", -1),
    Asset("IHE", "Pharmaceuticals", "Pharma", "Healthcare", "pharma basket", -1),
    Asset("LLY", "Eli Lilly", "Pharma", "Healthcare", "mega-cap pharma", -1),
    Asset("NVO", "Novo Nordisk", "Pharma", "Healthcare", "obesity / pharma", -1),
    Asset("MRK", "Merck", "Pharma", "Healthcare", "defensive pharma", -1),
    Asset("PFE", "Pfizer", "Pharma", "Healthcare", "pharma", -1),
    Asset("ABBV", "AbbVie", "Pharma", "Healthcare", "pharma", -1),
    Asset("BMY", "Bristol Myers", "Pharma", "Healthcare", "pharma", -1),
    Asset("JNJ", "Johnson & Johnson", "Pharma", "Healthcare", "defensive healthcare", -1),
    Asset("IHI", "Medical Devices", "Medical Devices", "Healthcare", "medical devices ETF", -1),
    Asset("MDT", "Medtronic", "Medical Devices", "Healthcare", "medical devices", -1),
    Asset("SYK", "Stryker", "Medical Devices", "Healthcare", "medical devices", -1),
    Asset("ISRG", "Intuitive Surgical", "Medical Devices", "Healthcare", "surgical robotics", 1),
    Asset("BSX", "Boston Scientific", "Medical Devices", "Healthcare", "medical devices", -1),
    Asset("ABT", "Abbott Labs", "Medical Devices", "Healthcare", "devices / diagnostics", -1),
    Asset("TMO", "Thermo Fisher", "Life Science Tools", "Science", "life science tools", 1),
    Asset("DHR", "Danaher", "Life Science Tools", "Science", "life science tools", 1),
    Asset("A", "Agilent", "Life Science Tools", "Science", "lab instruments", 1),
    Asset("ILMN", "Illumina", "Life Science Tools", "Science", "genomics tools", 1),
    Asset("IDXX", "IDEXX Labs", "Life Science Tools", "Science", "diagnostics", 1),
    Asset("IHF", "Healthcare Providers", "Healthcare Services", "Healthcare", "providers / insurers", -1),
    Asset("UNH", "UnitedHealth", "Healthcare Services", "Healthcare", "managed care", -1),
    Asset("CI", "Cigna", "Healthcare Services", "Healthcare", "managed care", -1),
    Asset("HUM", "Humana", "Healthcare Services", "Healthcare", "managed care", -1),
    Asset("ELV", "Elevance Health", "Healthcare Services", "Healthcare", "managed care", -1),
    Asset("CVS", "CVS Health", "Healthcare Services", "Healthcare", "healthcare services", -1),
    Asset("LMT", "Lockheed Martin", "Defense / Aerospace", "Defense", "defense prime", 0),
    Asset("RTX", "RTX", "Defense / Aerospace", "Defense", "defense / aerospace", 0),
    Asset("NOC", "Northrop Grumman", "Defense / Aerospace", "Defense", "defense prime", 0),
    Asset("GD", "General Dynamics", "Defense / Aerospace", "Defense", "defense prime", 0),
    Asset("BA", "Boeing", "Defense / Aerospace", "Defense", "aerospace / defense", 1),
    Asset("ICLN", "Clean Energy", "Clean Energy", "Climate / Energy", "clean energy ETF", 1),
    Asset("NLR", "Nuclear Energy", "Clean Energy", "Climate / Energy", "nuclear energy", 0),
    Asset("LIT", "Lithium Batteries", "Clean Energy", "Climate / Energy", "lithium / battery chain", 1),
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
CORE_TILES = ["^GSPC", "QQQ", "RSP", "UUP", "^TNX", "^VIX", "GC=F", "CL=F", "NVDA", "SMH", "HYG", "BTC-USD", "XLRE", "XLV", "IBB", "LLY", "IHI", "ITA", "ICLN", "EEM"]

NEWS_QUERIES = [
    "Federal Reserve markets", "CPI inflation stocks", "China semiconductor Nvidia", "oil prices geopolitics",
    "regional banks credit stress", "real estate mortgage rates", "Treasury yields auction", "AI stocks earnings", "healthcare stocks FDA", "biotech stocks clinical trial", "pharmaceutical earnings", "defense stocks geopolitics", "clean energy nuclear lithium",
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


def _hm(text: str):
    return datetime.strptime(text, "%H:%M").time()

def in_window(dt: datetime, start: str, end: str) -> bool:
    """Return True when dt's Eastern time is inside a possibly overnight time window."""
    t = dt.astimezone(LOCAL_TZ).time()
    a, b = _hm(start), _hm(end)
    if a <= b:
        return a <= t < b
    return t >= a or t < b

def minutes_until_time(dt: datetime, target: str) -> int:
    t = _hm(target)
    base = dt.astimezone(LOCAL_TZ)
    target_dt = base.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
    if target_dt <= base:
        target_dt += timedelta(days=1)
    return int((target_dt - base).total_seconds() // 60)

def fmt_minutes(mins: int) -> str:
    if mins < 60:
        return f"{mins}m"
    h, m = divmod(mins, 60)
    return f"{h}h {m}m" if m else f"{h}h"

SESSION_DEFS = [
    {"name":"Asia", "window":"8:00 PM–3:00 AM ET", "start":"20:00", "end":"03:00", "driver":"Overnight risk tone, China/Japan, USD/JPY, commodities", "watch":"NQ Globex, USD/JPY, FXI/MCHI, copper, oil"},
    {"name":"London / Europe", "window":"3:00 AM–11:30 AM ET", "start":"03:00", "end":"11:30", "driver":"DXY, European equities, bond/yield pressure", "watch":"DXY/UUP, VGK/FEZ/EWG, yields, gold, oil"},
    {"name":"US Pre-Market", "window":"4:00 AM–9:30 AM ET", "start":"04:00", "end":"09:30", "driver":"QQQ/SPY premarket, NQ futures, news, data releases", "watch":"QQQ, SPY, NQ=F, NVDA, SMH, VIX"},
    {"name":"NY Cash", "window":"9:30 AM–4:00 PM ET", "start":"09:30", "end":"16:00", "driver":"Main US liquidity and opening/closing range control", "watch":"QQQ, SPY, RSP, HYG, VIX, sectors"},
    {"name":"US After-Hours", "window":"4:00 PM–8:00 PM ET", "start":"16:00", "end":"20:00", "driver":"Earnings, guidance, late news, position unwind", "watch":"QQQ, mega-cap tech, AI leaders, after-hours range"},
    {"name":"Globex / Futures", "window":"6:00 PM–5:00 PM ET", "start":"18:00", "end":"17:00", "driver":"Overnight futures continuation and pre-NY pressure", "watch":"NQ=F, ES=F proxy via SPY/QQQ, yields, DXY"},
    {"name":"Crypto", "window":"24/7", "start":"00:00", "end":"00:00", "driver":"Liquidity beta and speculative risk appetite", "watch":"BTC, ETH, SOL, COIN, MSTR"},
]

def session_status(row: Dict[str, str], dt: datetime | None = None) -> Dict[str, str]:
    dt = dt or now_et()
    if row["name"] == "Crypto":
        return {"status":"ACTIVE", "next":"Always open", "tone":"good"}
    active = in_window(dt, row["start"], row["end"])
    if active:
        mins = minutes_until_time(dt, row["end"])
        return {"status":"ACTIVE", "next":f"Closes in {fmt_minutes(mins)}", "tone":"good"}
    mins = minutes_until_time(dt, row["start"])
    return {"status":"WATCH", "next":f"Opens in {fmt_minutes(mins)}", "tone":"warn"}

def current_active_sessions(dt: datetime | None = None) -> List[str]:
    dt = dt or now_et()
    active = []
    for row in SESSION_DEFS:
        if row["name"] == "Crypto" or in_window(dt, row["start"], row["end"]):
            active.append(row["name"])
    return active

def session_tone_from_market(df: pd.DataFrame, session: str) -> Tuple[str, str]:
    if df.empty:
        return "Waiting for data", "No loaded market data yet"
    if session == "Asia":
        syms = ["EWJ", "FXI", "MCHI", "EWH", "AUDUSD=X", "HG=F", "NQ=F"]
    elif session == "London / Europe":
        syms = ["VGK", "FEZ", "EWG", "EWU", "UUP", "DX-Y.NYB", "GC=F", "CL=F"]
    elif session == "US Pre-Market":
        syms = ["QQQ", "SPY", "NQ=F", "NVDA", "SMH", "^VIX", "UUP", "^TNX"]
    elif session == "NY Cash":
        syms = ["QQQ", "SPY", "RSP", "IWM", "HYG", "^VIX", "XLK", "XLF"]
    elif session == "US After-Hours":
        syms = ["QQQ", "NQ=F", "NVDA", "MSFT", "AMZN", "META", "GOOGL", "SMH"]
    elif session == "Globex / Futures":
        syms = ["NQ=F", "QQQ", "UUP", "^TNX", "GC=F", "CL=F", "BTC-USD"]
    else:
        syms = ["BTC-USD", "ETH-USD", "SOL-USD", "COIN", "MSTR"]
    score = score_group(df, syms)
    if score > 20:
        return "Supportive", f"{score:.1f} session score"
    if score < -20:
        return "Pressure", f"{score:.1f} session score"
    return "Mixed", f"{score:.1f} session score"

def session_range_from_series(s: pd.Series, start: str, end: str, date=None) -> Tuple[float, float, float | None]:
    if s.empty:
        return np.nan, np.nan, None
    date = date or now_et().date()
    if start == "00:00" and end == "00:00":
        part = s[s.index.date == date]
    elif _hm(start) <= _hm(end):
        day_s = s[s.index.date == date]
        part = day_s.between_time(start, end)
    else:
        # Overnight: combine yesterday after start and today before end.
        yday = date - timedelta(days=1)
        part = pd.concat([
            s[s.index.date == yday].between_time(start, "23:59"),
            s[s.index.date == date].between_time("00:00", end),
        ])
    if part.empty:
        return np.nan, np.nan, None
    return float(part.max()), float(part.min()), float(part.iloc[-1])

def nas_session_read(intra: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, object]]:
    out = {}
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
        one_h = s.resample("60min").last().dropna()
        four_h = s.resample("4h").last().dropna()
        session_ranges = {}
        for label, start, end in [
            ("Asia", "20:00", "03:00"),
            ("London", "03:00", "11:30"),
            ("Pre-Market", "04:00", "09:30"),
            ("NY Cash", "09:30", "16:00"),
            ("After-Hours", "16:00", "20:00"),
            ("Globex", "18:00", "17:00"),
        ]:
            hi, lo, last = session_range_from_series(s, start, end)
            session_ranges[label] = {"high": hi, "low": lo, "last": last}
        out[sym] = {
            "last": float(s.iloc[-1]),
            "last_time": fmt_time(s.index[-1].to_pydatetime()),
            "1H_close": float(one_h.iloc[-1]) if not one_h.empty else np.nan,
            "4H_close": float(four_h.iloc[-1]) if not four_h.empty else np.nan,
            "ranges": session_ranges,
        }
    return out

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
        "Healthcare": score_group(df, ["XLV", "VHT", "IYH", "IBB", "XBI", "PJP", "IHE", "LLY", "NVO", "UNH", "IHI"]),
        "Science": score_group(df, ["ARKG", "GNOM", "TMO", "DHR", "A", "ILMN", "IDXX", "ISRG"]),
        "Defense": score_group(df, ["ITA", "XAR", "LMT", "RTX", "NOC", "GD", "BA"]),
        "Clean Energy": score_group(df, ["TAN", "ICLN", "URA", "NLR", "LIT"]),
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
    healthcare = score_group(df, ["XLV", "VHT", "IYH", "IBB", "XBI", "PJP", "IHE", "LLY", "NVO", "UNH", "IHI"])
    biotech = score_group(df, ["IBB", "XBI", "ARKG", "GNOM", "ILMN"])
    pharma = score_group(df, ["PJP", "IHE", "LLY", "NVO", "MRK", "PFE", "ABBV", "BMY", "JNJ"])
    devices = score_group(df, ["IHI", "MDT", "SYK", "ISRG", "BSX", "ABT"])
    defense = score_group(df, ["ITA", "XAR", "LMT", "RTX", "NOC", "GD", "BA"])
    clean_energy = score_group(df, ["TAN", "ICLN", "URA", "NLR", "LIT"])
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
    if healthcare > 20 and value(df, "QQQ", "score") < -10:
        causes.append({"cause":"Defensive healthcare rotation", "status":"ACTIVE", "category":"Healthcare", "affected":"XLV, VHT, IYH, pharma, insurers, devices", "effect":"Capital rotating away from growth into defensive healthcare", "target":"Healthcare relative strength; QQQ risk-on needs healthcare rotation to cool", "confirm":["Healthcare bid", "Growth weak"], "contradict":[], "severity":56})
    if biotech < -20 and (teny_chg > 0 or dxy_chg > 0):
        causes.append({"cause":"Biotech / genomics rate pressure", "status":"ACTIVE", "category":"Biotech / Science", "affected":"IBB, XBI, ARKG, GNOM, ILMN", "effect":"Speculative science growth under funding-rate pressure", "target":"Biotech downside until yields/dollar cool", "confirm":["Biotech weak", "Rates/dollar firm"], "contradict":[], "severity":54})
    if pharma > 20 and qqq < -10:
        causes.append({"cause":"Pharma defensive bid", "status":"ACTIVE", "category":"Pharma", "affected":"PJP, IHE, LLY, NVO, MRK, PFE, ABBV, JNJ", "effect":"Defensive healthcare leadership active", "target":"Pharma relative strength; risk assets need broad reclaim", "confirm":["Pharma positive", "QQQ weak"], "contradict":[], "severity":50})
    if devices < -20:
        causes.append({"cause":"Medical device weakness", "status":"WATCH", "category":"Medical Devices", "affected":"IHI, MDT, SYK, ISRG, BSX, ABT", "effect":"Healthcare growth/device pocket under pressure", "target":"Device weakness can drag healthcare if XLV also turns", "confirm":["Devices weak"], "contradict":[], "severity":44})
    if defense > 20 and (gold > 0 or vix_chg > 0):
        causes.append({"cause":"Defense / geopolitical safety rotation", "status":"ACTIVE", "category":"Defense / Aerospace", "affected":"ITA, XAR, LMT, RTX, NOC, GD, BA", "effect":"Defense leadership can signal geopolitical or safety positioning", "target":"Defense bid continuation if fear/oil/gold confirm", "confirm":["Defense bid", "Fear context"], "contradict":[], "severity":52})
    if clean_energy < -20 and teny_chg > 0:
        causes.append({"cause":"Clean energy rate pressure", "status":"WATCH", "category":"Clean Energy", "affected":"TAN, ICLN, LIT, URA, NLR", "effect":"Rate-sensitive climate/energy assets under pressure", "target":"Clean energy downside until yields cool", "confirm":["Clean energy weak", "10Y firm"], "contradict":[], "severity":43})
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
    if any(k in low for k in ["healthcare", "pharma", "drug", "fda", "medicare", "unitedhealth", "lilly", "novo"]):
        return "Healthcare / pharma"
    if any(k in low for k in ["biotech", "genomics", "clinical trial", "science", "medical device"]):
        return "Biotech / science / medical devices"
    if any(k in low for k in ["defense", "aerospace", "missile", "pentagon", "war"]):
        return "Defense / aerospace"
    if any(k in low for k in ["solar", "clean energy", "nuclear", "uranium", "lithium", "battery"]):
        return "Clean energy / nuclear / lithium"
    return "Broad market"

def extended_hours_read(intra: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Legacy table helper retained for exports only; UI now renders session cards, not an extended-hours column."""
    rows = []
    read = nas_session_read(intra)
    for sym, payload in read.items():
        row = {
            "symbol": sym,
            "last_price": payload.get("last", np.nan),
            "last_time_et": payload.get("last_time", "N/A"),
            "1H_close": payload.get("1H_close", np.nan),
            "4H_close": payload.get("4H_close", np.nan),
        }
        for label, rng in payload.get("ranges", {}).items():
            safe = label.lower().replace("-", "_").replace(" ", "_")
            row[f"{safe}_high"] = rng.get("high", np.nan)
            row[f"{safe}_low"] = rng.get("low", np.nan)
        rows.append(row)
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

st.markdown("""
<style>
    #MainMenu, footer {visibility: hidden;}
    header {visibility: hidden; height: 0px;}
    .block-container {padding-top: 1.15rem; padding-bottom: 2rem; max-width: 1500px;}
    [data-testid="stSidebar"] {background: #07111f; border-right: 1px solid rgba(120,160,220,.16);}
    [data-testid="stSidebar"] * {font-size: 14px;}
    div[data-testid="stMetric"] {background: rgba(14,30,48,.80); border: 1px solid rgba(111,159,213,.18); border-radius: 14px; padding: 12px 14px; min-height: 78px;}
    div[data-testid="stMetric"] label {color: #9fb1c6 !important; font-size: .73rem !important; letter-spacing: .06em; text-transform: uppercase;}
    div[data-testid="stMetricValue"] {font-size: 1.35rem !important; font-weight: 800 !important;}
    div.stButton > button {border-radius: 14px; border: 1px solid rgba(95,150,210,.35); background: rgba(13,31,51,.96); color: #f5f8ff; min-height: 42px; white-space: pre-line; line-height: 1.18; font-weight: 750; overflow: hidden;}
    div.stButton > button:hover {border-color: rgba(80,190,255,.85); background: rgba(20,48,78,.98); color: white;}
    .top-shell {border: 1px solid rgba(122,164,220,.24); background: linear-gradient(90deg, rgba(8,24,40,.94), rgba(28,20,58,.82)); border-radius: 22px; padding: 12px 16px; margin: 0 0 14px 0;}
    .mini-label {color:#91a4ba; font-size:.72rem; letter-spacing:.12em; text-transform:uppercase; font-weight:800; margin-bottom:4px;}
    .big-read {font-size:2rem; font-weight:900; letter-spacing:.01em; margin: 0;}
    .sub-read {font-size:.94rem; color:#aab9cc; margin-top:6px;}
    .good {color:#35d07f; font-weight:900;}
    .bad {color:#ff4b4b; font-weight:900;}
    .warn {color:#ffd23f; font-weight:900;}
    .card-title {font-size:.76rem; color:#b8c6d8; letter-spacing:.10em; text-transform:uppercase; font-weight:900; margin-bottom:.25rem;}
    .section-title {font-size:1.15rem; font-weight:900; margin: 1.2rem 0 .45rem 0; letter-spacing:.03em;}
    .muted {color:#9fb1c6; font-size:.90rem;}
    .chip {display:inline-block; padding:.22rem .55rem; border-radius:999px; border:1px solid rgba(120,160,220,.24); background:rgba(12,30,48,.9); color:#c9d9ee; font-size:.72rem; font-weight:800; margin:.12rem .18rem .12rem 0;}
    .chip-good {border-color:rgba(53,208,127,.45); color:#35d07f;}
    .chip-bad {border-color:rgba(255,75,75,.45); color:#ff6666;}
    .chip-warn {border-color:rgba(255,210,63,.45); color:#ffd23f;}
    .tile-caption {font-size:.78rem; color:#9fb1c6; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
    .tile-main {font-size:1.08rem; font-weight:900; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
    .tile-price {font-size:1.28rem; font-weight:900; margin-top:.1rem;}
    .tile-foot {font-size:.78rem; font-weight:800; margin-top:.2rem;}
    .tight-table div[data-testid="stDataFrame"] {font-size: 0.78rem;}
</style>
""", unsafe_allow_html=True)

if "selected_symbol" not in st.session_state:
    st.session_state.selected_symbol = "QQQ"
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = True
if "refresh_interval" not in st.session_state:
    st.session_state.refresh_interval = REFRESH_SECONDS

# Sidebar: clean nav only
with st.sidebar:
    st.markdown(f"### MACRO REGIME ENGINE\n<span class='muted'>{APP_VERSION}</span>", unsafe_allow_html=True)
    page = st.radio(
        "Navigation",
        [
            "Action Console", "Live Pulse", "Active Causes", "Session Map", "Real Estate",
            "Healthcare", "Biotech / Science", "Pharma", "Medical Devices", "Life Science Tools",
            "Healthcare Services", "Defense / Aerospace", "Clean Energy",
            "Sectors", "Sub-Sectors", "Currencies", "Credit", "Volatility", "Global Markets",
            "Events", "Search", "Data Health", "Raw Tables"
        ],
        label_visibility="collapsed",
    )
    st.divider()
    st.toggle("Auto re-run", key="auto_refresh")
    st.selectbox("Interval", [15, 30, 60, 120], key="refresh_interval")
    st.caption("America/Toronto · 12-hour time")

if st.session_state.auto_refresh and st_autorefresh is not None:
    st_autorefresh(interval=int(st.session_state.refresh_interval) * 1000, key="global_live_refresh")

# Data load
symbols_tuple = tuple([a.symbol for a in UNIVERSE])
with st.spinner("Loading live market state..."):
    intra = fetch_intraday(symbols_tuple)
    daily = fetch_daily(symbols_tuple)
market = build_market_frame(intra, daily)
causes = detect_active_causes(market) if not market.empty else []
action = compute_action(market, causes) if not market.empty else {
    "state":"NO DATA", "primary_driver":"No data loaded", "pressure_asset":"N/A", "support_asset":"N/A",
    "target_pressure":"N/A", "quality":"N/A", "confidence":0, "confirmations":0, "contradictions":0,
    "scores": {"Macro":0,"AI":0,"Internals":0,"Liquidity":0,"Risk":0,"Real Estate":0,"Healthcare":0,"Science":0,"Defense":0,"Clean Energy":0,"Global":0}
}

def cls_for_score(score: float) -> str:
    return "good" if score > 25 else "bad" if score < -25 else "warn"

def change_class(chg: float, risk_sign: int = 1) -> str:
    aligned = chg * risk_sign
    return "good" if aligned > 0 else "bad" if aligned < 0 else "warn"

def short_state(s: str) -> str:
    mapping = {
        "PRESSURE UP":"PRESSURE UP", "PRESSURE DOWN":"PRESSURE DOWN", "SUPPORTIVE":"SUPPORT", "STRONG":"STRONG",
        "WEAK":"WEAK", "PRESSURE":"PRESSURE", "MIXED":"MIXED"
    }
    return mapping.get(str(s), str(s)[:14])

def action_statement(action: Dict[str, object]) -> str:
    state = str(action.get("state", ""))
    driver = str(action.get("primary_driver", ""))
    if "RISK-OFF" in state:
        return f"Risk-off pressure is active. Respect downside pressure until {driver} weakens or the confirming markets reverse."
    if "RISK-ON" in state:
        return f"Risk-on pressure is active. Upside is cleaner while internals, credit, and volatility keep confirming."
    return "Market is mixed. Use the active cause and confirmation count before trusting direction."

def chips(items: Iterable[str], kind: str = "") -> str:
    css = "chip " + ("chip-good" if kind == "good" else "chip-bad" if kind == "bad" else "chip-warn" if kind == "warn" else "")
    vals = [str(x) for x in items if str(x).strip()]
    if not vals:
        vals = ["Waiting for signal"]
    return " ".join([f"<span class='{css}'>{v}</span>" for v in vals])

def clean_card(title: str, main: str, sub: str = "", tone: str = ""):
    with st.container(border=True):
        st.markdown(f"<div class='card-title'>{title}</div>", unsafe_allow_html=True)
        tone_class = tone if tone in ["good","bad","warn"] else ""
        st.markdown(f"<div class='big-read {tone_class}'>{main}</div>", unsafe_allow_html=True)
        if sub:
            st.markdown(f"<div class='sub-read'>{sub}</div>", unsafe_allow_html=True)

def small_card(title: str, main: str, sub: str = "", tone: str = ""):
    with st.container(border=True):
        st.markdown(f"<div class='card-title'>{title}</div>", unsafe_allow_html=True)
        tone_class = tone if tone in ["good","bad","warn"] else ""
        st.markdown(f"<div class='tile-main {tone_class}'>{main}</div>", unsafe_allow_html=True)
        if sub:
            st.markdown(f"<div class='muted'>{sub}</div>", unsafe_allow_html=True)

def asset_row(sym: str) -> pd.Series | None:
    if market.empty:
        return None
    rows = market[market.symbol == sym]
    return None if rows.empty else rows.iloc[0]

def render_asset_tile_v2(row: pd.Series, selected: str) -> bool:
    is_sel = str(row.symbol) == selected
    with st.container(border=True):
        st.markdown(f"<div class='tile-caption'>{row.category}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='tile-main'>{row.symbol}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='tile-price'>{fmt_num(float(row.latest_close))}</div>", unsafe_allow_html=True)
        tone = change_class(float(row.change_pct), int(row.risk_sign))
        st.markdown(f"<div class='tile-foot {tone}'>{float(row.change_pct):+.2f}% · {short_state(row.state)}</div>", unsafe_allow_html=True)
        return st.button("Selected" if is_sel else "Select", key=f"tile_select_{row.symbol}", use_container_width=True, type="primary" if is_sel else "secondary")

def render_asset_strip(symbols: List[str], ncols: int = 4):
    tile_df = market[market.symbol.isin(symbols)].copy()
    if tile_df.empty:
        st.info("No live tile data loaded yet.")
        return
    for row_start in range(0, len(tile_df), ncols):
        cols = st.columns(ncols)
        for col, (_, r) in zip(cols, tile_df.iloc[row_start:row_start+ncols].iterrows()):
            with col:
                if render_asset_tile_v2(r, st.session_state.selected_symbol):
                    st.session_state.selected_symbol = str(r.symbol)
                    st.rerun()

def render_target_cards():
    tb = target_board(market, action)
    if tb.empty:
        st.info("Targets unavailable until live data loads.")
        return
    cols = st.columns(4)
    for i, (_, r) in enumerate(tb.head(8).iterrows()):
        with cols[i % 4]:
            tone = "good" if "Upside" in str(r.pressure) else "bad" if "Downside" in str(r.pressure) else "warn"
            small_card(str(r.asset).split()[0], str(r.pressure), f"Score {r.score} · {r.state}", tone)

def render_outcome_cards():
    ob = outcome_board(action)
    cols = st.columns(3)
    for i, (_, r) in enumerate(ob.iterrows()):
        with cols[i]:
            with st.container(border=True):
                st.markdown(f"<div class='card-title'>OUTCOME {i+1} · {r.probability}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='tile-main'>{r.outcome}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='muted'><b>Target:</b> {r.target}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='muted'><b>Confirm:</b> {r.confirm}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='muted'><b>Invalid:</b> {r.invalidate}</div>", unsafe_allow_html=True)

def render_session_map():
    st.markdown("<div class='section-title'>LIVE GLOBAL SESSION MAP</div>", unsafe_allow_html=True)
    active_names = current_active_sessions()
    st.caption("Session times shown in America/Toronto / Eastern 12-hour market time. Extended hours is now a session map, not a table column.")
    cols = st.columns(3)
    for i, sess in enumerate(SESSION_DEFS):
        status = session_status(sess)
        tone, note = session_tone_from_market(market, sess["name"])
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"<div class='card-title'>{status['status']} · {sess['window']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='tile-main'>{sess['name']}</div>", unsafe_allow_html=True)
                st.metric("Live read", tone, status["next"])
                st.caption(f"Driver: {sess['driver']}")
                st.caption(f"Watch: {sess['watch']}")
                st.caption(note)
    if active_names:
        st.success("Active now: " + " · ".join(active_names))


def render_nas_session_panel():
    st.markdown("<div class='section-title'>NAS / QQQ SESSION READ</div>", unsafe_allow_html=True)
    read = nas_session_read(intra)
    if not read:
        st.warning("NAS/QQQ session data not loaded yet. Use QQQ/NQ live feed when available.")
        return
    tabs = st.tabs([sym for sym in ["QQQ", "NQ=F", "^NDX"] if sym in read])
    for tab, sym in zip(tabs, [sym for sym in ["QQQ", "NQ=F", "^NDX"] if sym in read]):
        with tab:
            payload = read[sym]
            c1, c2, c3 = st.columns(3)
            c1.metric("Last", fmt_num(float(payload.get("last", np.nan))), payload.get("last_time", "N/A"))
            c2.metric("1H Close", fmt_num(float(payload.get("1H_close", np.nan))))
            c3.metric("4H Close", fmt_num(float(payload.get("4H_close", np.nan))))
            st.caption("Use these ranges for session-aware targets/reclaims: Asia → London → Pre-Market → NY Cash → After-Hours → Globex.")
            rcols = st.columns(3)
            for i, (label, rng) in enumerate(payload.get("ranges", {}).items()):
                hi, lo, last = rng.get("high", np.nan), rng.get("low", np.nan), rng.get("last", None)
                with rcols[i % 3]:
                    with st.container(border=True):
                        st.markdown(f"<div class='card-title'>{label}</div>", unsafe_allow_html=True)
                        st.metric("High", fmt_num(float(hi)) if not pd.isna(hi) else "N/A")
                        st.metric("Low", fmt_num(float(lo)) if not pd.isna(lo) else "N/A")
                        st.caption(f"Last in range: {fmt_num(float(last)) if last is not None and not pd.isna(last) else 'N/A'}")

def render_selected_panel():
    read = asset_action(st.session_state.selected_symbol, market, causes)
    st.markdown("<div class='section-title'>SELECTED ASSET ACTION PANEL</div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1])
    with c1:
        clean_card(read.get("title", "Selected"), read.get("now", "N/A"), f"Cause: {read.get('cause','N/A')}")
    with c2:
        small_card("TARGET", read.get("target", "N/A"), read.get("related", ""), "warn")
    with c3:
        small_card("CONFIRM", read.get("confirm", "N/A"), "What must agree", "good")
    with c4:
        small_card("INVALIDATE / AVOID", read.get("invalidate", "N/A"), read.get("avoid", ""), "bad")

# Top command strip
st.markdown("<div class='top-shell'><span class='mini-label'>LIVE ACTION COMMAND CENTER · SEARCH · CAUSE · TARGET · OUTCOME</span></div>", unsafe_allow_html=True)
cmd_cols = st.columns([3.4, .72, .84, .78, .85, .74])
with cmd_cols[0]:
    global_query = st.text_input("Search", placeholder="Search: QQQ, NDX, real estate, semis, credit, gold, yields, oil", label_visibility="collapsed")
with cmd_cols[1]:
    st.metric("Local", now_et().strftime("%-I:%M %p"))
with cmd_cols[2]:
    st.metric("Session", " / ".join(current_active_sessions()[:2]) or session_name())
with cmd_cols[3]:
    st.metric("Data", "LIVE" if not market.empty else "NO DATA", f"{len(market)} series")
with cmd_cols[4]:
    if st.button("Update", use_container_width=True):
        fetch_intraday.clear(); fetch_daily.clear(); fetch_headlines.clear(); st.rerun()
with cmd_cols[5]:
    st.metric("Auto", "ON" if st.session_state.auto_refresh else "OFF", f"{st.session_state.refresh_interval}s")

if global_query:
    page = "Search"

# ------------------------- Pages -------------------------
if page == "Action Console":
    st.markdown("<div class='section-title'>ACTION CONSOLE</div>", unsafe_allow_html=True)
    score_tone = cls_for_score(float(action["scores"].get("Macro", 0)))
    top_cause = causes[0] if causes else {"confirm": [], "contradict": [], "cause":"No data", "category":"N/A", "effect":"N/A", "target":"N/A", "affected":"N/A"}

    h1, h2 = st.columns([1.25, 1])
    with h1:
        clean_card("NOW", str(action["state"]), action_statement(action), score_tone)
    with h2:
        clean_card("ACTIVE CAUSE", str(action["primary_driver"]), f"Quality {action['quality']} · Confidence {action['confidence']}% · {action['confirmations']}C/{action['contradictions']}X", "warn")

    a1, a2, a3, a4 = st.columns(4)
    with a1: small_card("PRESSURE ASSET", str(action["pressure_asset"]), "Most affected now", "bad" if "RISK-OFF" in str(action["state"]) else "good")
    with a2: small_card("SUPPORT ASSET", str(action["support_asset"]), "Current defensive/supportive pocket", "good")
    with a3: small_card("TARGET PRESSURE", str(action["target_pressure"]), "Current pull direction", "warn")
    with a4: small_card("FUTURE RISK", next_events().iloc[0]["event"] if not next_events().empty else "No event", next_events().iloc[0]["time"] if not next_events().empty else "", "warn")

    st.markdown("<div class='section-title'>REGIME GAUGES</div>", unsafe_allow_html=True)
    gcols = st.columns(5)
    for i, key in enumerate(["Macro", "AI", "Internals", "Liquidity", "Risk"]):
        with gcols[i]:
            score = float(action["scores"].get(key, 0))
            st.plotly_chart(make_gauge(key, score), use_container_width=True, config={"displayModeBar": False})
            st.caption(f"{regime_from_score(score)} · {score:.1f}")

    st.markdown("<div class='section-title'>TARGET BOARD</div>", unsafe_allow_html=True)
    render_target_cards()

    st.markdown("<div class='section-title'>OUTCOME BOARD</div>", unsafe_allow_html=True)
    render_outcome_cards()

    st.markdown("<div class='section-title'>CONFIRM · CONTRADICT · AVOID</div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True):
            st.markdown("<div class='card-title'>CONFIRMING NOW</div>", unsafe_allow_html=True)
            st.markdown(chips(top_cause.get("confirm", []), "good"), unsafe_allow_html=True)
    with c2:
        with st.container(border=True):
            st.markdown("<div class='card-title'>CONTRADICTING NOW</div>", unsafe_allow_html=True)
            st.markdown(chips(top_cause.get("contradict", []), "bad"), unsafe_allow_html=True)
    with c3:
        with st.container(border=True):
            st.markdown("<div class='card-title'>AVOID</div>", unsafe_allow_html=True)
            st.markdown(chips(["Chasing against location", "Weak score quality", "Mixed confirmations"], "warn"), unsafe_allow_html=True)

    render_session_map()
    render_nas_session_panel()

    st.markdown("<div class='section-title'>LIVE MARKET PULSE</div>", unsafe_allow_html=True)
    render_asset_strip(CORE_TILES, ncols=4)
    render_selected_panel()

    with st.expander("Detail tables", expanded=False):
        st.dataframe(market, use_container_width=True, hide_index=True)

elif page == "Live Pulse":
    st.markdown("<div class='section-title'>LIVE MARKET PULSE</div>", unsafe_allow_html=True)
    cats = ["All", "Indexes", "AI / Tech", "Semiconductors", "Real Estate", "Healthcare", "Biotech / Science", "Pharma", "Medical Devices", "Life Science Tools", "Healthcare Services", "Defense / Aerospace", "Clean Energy", "Sectors", "Sub-Sectors", "Bonds", "Dollar", "Commodities", "Currencies", "Crypto", "Credit", "Volatility", "Global"]
    cat = st.radio("Filter", cats, horizontal=True)
    data = market if cat == "All" else market[market.category == cat]
    symbols = data.symbol.tolist()
    render_asset_strip(symbols, ncols=4)
    render_selected_panel()

elif page == "Active Causes":
    st.markdown("<div class='section-title'>ACTIVE CAUSE ENGINE</div>", unsafe_allow_html=True)
    for c in causes:
        with st.container(border=True):
            t1, t2, t3, t4 = st.columns([1.2,.7,.7,.7])
            t1.markdown(f"<div class='card-title'>{c['status']} · {c['category']}</div><div class='tile-main'>{c['cause']}</div>", unsafe_allow_html=True)
            t2.metric("Severity", int(c["severity"]))
            t3.metric("Confirms", len(c.get("confirm", [])))
            t4.metric("Contradicts", len(c.get("contradict", [])))
            st.markdown(f"<div class='muted'><b>Affected:</b> {c['affected']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='muted'><b>Effect:</b> {c['effect']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='muted'><b>Target:</b> {c['target']}</div>", unsafe_allow_html=True)
            st.markdown(chips(c.get("confirm", []), "good") + chips(c.get("contradict", []), "bad"), unsafe_allow_html=True)
    with st.expander("Headline / catalyst watch", expanded=False):
        headlines = fetch_headlines()
        if headlines.empty:
            st.info("Headline watch unavailable or no current items returned. Market-data active causes remain live.")
        else:
            st.dataframe(headlines, use_container_width=True, hide_index=True)

elif page == "Session Map":
    render_session_map()
    render_nas_session_panel()
    with st.expander("Exportable NAS session levels", expanded=False):
        eh = extended_hours_read(intra)
        if eh.empty:
            st.warning("Session-level data not loaded yet.")
        else:
            st.dataframe(eh, use_container_width=True, hide_index=True)

elif page in ["Real Estate", "Healthcare", "Biotech / Science", "Pharma", "Medical Devices", "Life Science Tools", "Healthcare Services", "Defense / Aerospace", "Clean Energy", "Sectors", "Sub-Sectors", "Currencies", "Credit", "Volatility", "Global Markets"]:
    cat_map = {"Global Markets":"Global"}
    cat = cat_map.get(page, page)
    st.markdown(f"<div class='section-title'>{page.upper()}</div>", unsafe_allow_html=True)
    part = market[market.category == cat].copy()
    if not part.empty:
        avg = float(part.score.mean())
        pos = float((part.score > 0).mean() * 100)
        c1, c2, c3 = st.columns(3)
        c1.metric("Category Score", f"{avg:.1f}", regime_from_score(avg))
        c2.metric("Positive Participation", f"{pos:.0f}%")
        c3.metric("Loaded Series", len(part))
        st.markdown("<div class='section-title'>LIVE TILES</div>", unsafe_allow_html=True)
        render_asset_strip(part.symbol.tolist(), ncols=4)
        with st.expander("Series table", expanded=False):
            st.dataframe(part[["symbol","name","latest_close","change_pct","score","state","role"]], use_container_width=True, hide_index=True)
    else:
        st.warning("No live series loaded for this category.")

elif page == "Events":
    st.markdown("<div class='section-title'>EVENT RISK</div>", unsafe_allow_html=True)
    ev = next_events()
    cols = st.columns(3)
    for i, (_, r) in enumerate(ev.iterrows()):
        with cols[i % 3]:
            small_card(str(r.event), f"{r.days} days", f"{r.time} · {r.impact}", "warn" if r.impact == "HIGH" else "")

elif page == "Search":
    q = (global_query or st.text_input("Search", placeholder="NDX, real estate, gold, credit, semis, yields")).lower().strip()
    st.markdown(f"<div class='section-title'>ACTION SEARCH {q.upper() if q else ''}</div>", unsafe_allow_html=True)
    if q:
        mask = market.apply(lambda r: q in str(r.symbol).lower() or q in str(r["name"]).lower() or q in str(r.category).lower() or q in str(r.role).lower(), axis=1)
        res = market[mask]
        if not res.empty:
            selected_sym = str(res.iloc[0].symbol)
            read = asset_action(selected_sym, market, causes)
            c1, c2 = st.columns([1,1])
            with c1: clean_card("ACTION READ", read["now"], f"Cause: {read['cause']}")
            with c2: clean_card("TARGET", read["target"], f"Related: {read['related']}", "warn")
            c3, c4, c5 = st.columns(3)
            with c3: small_card("CONFIRM", read["confirm"], "", "good")
            with c4: small_card("INVALIDATE", read["invalidate"], "", "bad")
            with c5: small_card("AVOID", read["avoid"], "", "warn")
            st.markdown("<div class='section-title'>RELATED MATCHES</div>", unsafe_allow_html=True)
            render_asset_strip(res.symbol.tolist(), ncols=4)
            with st.expander("Direct match table", expanded=False):
                st.dataframe(res[["symbol","name","category","latest_close","change_pct","score","state","role"]], use_container_width=True, hide_index=True)
        else:
            st.info("No direct match. Try QQQ, NDX, real estate, healthcare, biotech, pharma, science, defense, clean energy, semis, gold, yields, credit, volatility, oil.")

elif page == "Data Health":
    st.markdown("<div class='section-title'>DATA HEALTH</div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Loaded Series", len(market))
    c2.metric("Local Time", now_et().strftime("%-I:%M %p"))
    c3.metric("Active Sessions", " / ".join(current_active_sessions()[:2]) or session_name())
    c4.metric("Auto Re-run", "ON" if st.session_state.auto_refresh else "OFF")
    st.write("Live source: yfinance prices with pre/post where available; public Google News RSS for headline watch; no FRED; no demo logic.")
    missing = sorted(set([a.symbol for a in UNIVERSE]) - set(market.symbol.tolist()))
    if missing:
        st.warning(f"Missing/failed symbols: {', '.join(missing[:50])}{'...' if len(missing) > 50 else ''}")
    else:
        st.success("All configured symbols loaded.")

elif page == "Raw Tables":
    st.markdown("<div class='section-title'>RAW TABLES</div>", unsafe_allow_html=True)
    st.dataframe(market, use_container_width=True, hide_index=True)
