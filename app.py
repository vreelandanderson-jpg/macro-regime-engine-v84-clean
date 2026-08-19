from __future__ import annotations

import math
import time
from datetime import datetime, time as dtime, timedelta
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytz
import streamlit as st
import yfinance as yf

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:  # pragma: no cover
    st_autorefresh = None

ET = pytz.timezone("America/Toronto")
APP_VERSION = "v9"

st.set_page_config(
    page_title="Macro Regime Engine v9",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------- styling --------------------------
st.markdown(
    """
<style>
[data-testid="stHeader"]{background:rgba(2,8,18,0.88);backdrop-filter:blur(14px);}
[data-testid="stToolbar"]{display:none !important;}
footer{display:none !important;}
.block-container{padding-top:0.65rem;padding-bottom:1rem;max-width:1700px;}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#04101d 0%,#061626 48%,#02070d 100%);border-right:1px solid rgba(78,178,255,.20);}
section[data-testid="stSidebar"] *{font-size:13px !important;}
.main-bg{background:radial-gradient(circle at 80% 10%,rgba(95,53,255,.18),transparent 32%),radial-gradient(circle at 10% 35%,rgba(0,207,255,.14),transparent 28%),#030914;}
.neon-shell{border:1px solid rgba(0,174,255,.42);box-shadow:0 0 16px rgba(0,174,255,.18), inset 0 0 18px rgba(0,120,255,.06);border-radius:16px;background:linear-gradient(145deg,rgba(8,25,42,.88),rgba(5,12,27,.86));padding:12px;margin-bottom:10px;}
.green-shell{border:1px solid rgba(57,255,123,.42);box-shadow:0 0 14px rgba(57,255,123,.12);border-radius:16px;background:linear-gradient(145deg,rgba(7,26,27,.90),rgba(5,12,23,.86));padding:12px;margin-bottom:10px;}
.purple-shell{border:1px solid rgba(191,83,255,.44);box-shadow:0 0 16px rgba(191,83,255,.16);border-radius:16px;background:linear-gradient(145deg,rgba(19,10,39,.86),rgba(5,12,24,.88));padding:12px;margin-bottom:10px;}
.orange-shell{border:1px solid rgba(255,180,45,.40);box-shadow:0 0 16px rgba(255,160,28,.14);border-radius:16px;background:linear-gradient(145deg,rgba(33,19,8,.76),rgba(5,12,24,.88));padding:12px;margin-bottom:10px;}
.card{border:1px solid rgba(112,185,255,.22);border-radius:13px;background:linear-gradient(145deg,rgba(10,28,46,.92),rgba(4,13,27,.94));padding:12px;min-height:96px;box-shadow:inset 0 0 12px rgba(90,185,255,.04);}
.tile{border:1px solid rgba(105,202,255,.26);border-radius:13px;background:linear-gradient(160deg,rgba(10,25,42,.95),rgba(4,12,27,.96));padding:11px;min-height:138px;box-shadow:0 0 10px rgba(0,180,255,.06);}
.tile:hover{border-color:rgba(0,209,255,.75);box-shadow:0 0 18px rgba(0,209,255,.25);}
.kicker{font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:#93a8c4;font-weight:800;margin-bottom:5px;}
.big{font-size:22px;font-weight:900;color:#f1f7ff;line-height:1.1;}
.med{font-size:15px;font-weight:800;color:#e9f3ff;line-height:1.1;}
.small{font-size:11px;color:#9eb1c9;line-height:1.25;}
.value{font-size:19px;font-weight:900;color:#f5fbff;line-height:1.05;margin-top:6px;}
.pos{color:#31e981;font-weight:900;}.neg{color:#ff4d57;font-weight:900;}.warn{color:#ffd13b;font-weight:900;}.muted{color:#93a8c4;}
.chip{display:inline-block;padding:3px 8px;border-radius:999px;font-size:10px;font-weight:900;letter-spacing:.03em;}
.chip-red{background:rgba(255,55,65,.14);color:#ff4d57;border:1px solid rgba(255,55,65,.35);}
.chip-green{background:rgba(45,230,118,.13);color:#31e981;border:1px solid rgba(45,230,118,.35);}
.chip-yellow{background:rgba(255,209,59,.13);color:#ffd13b;border:1px solid rgba(255,209,59,.35);}
.chip-blue{background:rgba(50,176,255,.14);color:#63cfff;border:1px solid rgba(50,176,255,.35);}
.hr{height:1px;background:linear-gradient(90deg,transparent,rgba(90,190,255,.35),transparent);margin:8px 0;}
.stButton button{border-radius:12px !important;border:1px solid rgba(75,185,255,.34) !important;background:linear-gradient(180deg,rgba(18,54,86,.95),rgba(8,24,45,.95)) !important;color:#f3f8ff !important;font-weight:800 !important;min-height:42px;white-space:nowrap !important;}
.stButton button:hover{border-color:#33ceff !important;box-shadow:0 0 14px rgba(0,210,255,.22);}
.stTextInput input,.stSelectbox div[data-baseweb="select"]{background:rgba(4,14,28,.94) !important;border:1px solid rgba(83,175,255,.25) !important;border-radius:12px !important;color:#f4f8ff !important;}
div[data-testid="stDataFrame"]{font-size:12px !important;}
.plot-container,.svg-container{max-height:210px !important;}
</style>
""",
    unsafe_allow_html=True,
)

# ------------------------- instrument universe -------------------------
UNIVERSE: Dict[str, Dict] = {
    # Core indexes/futures/cash relationships
    "NQ=F": {"name": "Nasdaq Futures", "cat": "Indexes", "role": "primary NAS all-session driver", "proxy": ["QQQ", "^NDX", "SMH", "NVDA"], "type": "Futures"},
    "ES=F": {"name": "S&P Futures", "cat": "Indexes", "role": "primary S&P all-session driver", "proxy": ["SPY", "^GSPC", "RSP"], "type": "Futures"},
    "YM=F": {"name": "Dow Futures", "cat": "Indexes", "role": "Dow futures driver", "proxy": ["DIA", "^DJI"], "type": "Futures"},
    "RTY=F": {"name": "Russell Futures", "cat": "Indexes", "role": "small-cap futures driver", "proxy": ["IWM", "^RUT"], "type": "Futures"},
    "QQQ": {"name": "Nasdaq ETF", "cat": "Indexes", "role": "NAS ETF / extended proxy", "proxy": ["NQ=F", "^NDX", "SMH", "NVDA"], "type": "ETF"},
    "SPY": {"name": "S&P ETF", "cat": "Indexes", "role": "S&P ETF proxy", "proxy": ["ES=F", "^GSPC", "RSP"], "type": "ETF"},
    "^NDX": {"name": "Nasdaq 100 Cash", "cat": "Indexes", "role": "official NY cash reference", "proxy": ["NQ=F", "QQQ"], "type": "Cash Index"},
    "^GSPC": {"name": "S&P 500 Cash", "cat": "Indexes", "role": "official NY cash reference", "proxy": ["ES=F", "SPY", "RSP"], "type": "Cash Index"},
    "RSP": {"name": "Equal Weight S&P", "cat": "Internals", "role": "breadth / equal-weight confirmation", "proxy": ["SPY", "ES=F"], "type": "ETF"},
    # Dollar/rates/vol
    "DX-Y.NYB": {"name": "US Dollar Index", "cat": "Dollar", "role": "liquidity / dollar pressure", "proxy": ["UUP", "EURUSD=X", "JPY=X"], "type": "Index"},
    "UUP": {"name": "US Dollar ETF", "cat": "Dollar", "role": "dollar ETF proxy", "proxy": ["DX-Y.NYB"], "type": "ETF"},
    "^TNX": {"name": "US 10Y Yield", "cat": "Bonds", "role": "rate pressure", "proxy": ["TLT", "IEF", "QQQ"], "type": "Yield"},
    "^IRX": {"name": "13-Week Bill Yield", "cat": "Bonds", "role": "front-end / cash rate pressure", "proxy": ["SHY"], "type": "Yield"},
    "TLT": {"name": "20Y Treasury ETF", "cat": "Bonds", "role": "duration / bond bid", "proxy": ["^TNX"], "type": "ETF"},
    "IEF": {"name": "7-10Y Treasury ETF", "cat": "Bonds", "role": "intermediate duration", "proxy": ["^TNX"], "type": "ETF"},
    "HYG": {"name": "High Yield Credit", "cat": "Credit", "role": "risk appetite / credit stress", "proxy": ["JNK", "LQD", "SPY"], "type": "ETF"},
    "JNK": {"name": "Junk Bonds", "cat": "Credit", "role": "credit risk", "proxy": ["HYG"], "type": "ETF"},
    "LQD": {"name": "Investment Grade Credit", "cat": "Credit", "role": "IG credit stress", "proxy": ["HYG"], "type": "ETF"},
    "^VIX": {"name": "VIX", "cat": "Volatility", "role": "fear / volatility pressure", "proxy": ["VIXY", "SPY", "QQQ"], "type": "Index"},
    "^VVIX": {"name": "VVIX", "cat": "Volatility", "role": "vol-of-vol pressure", "proxy": ["^VIX"], "type": "Index"},
    # Commodities
    "GC=F": {"name": "Gold Futures", "cat": "Commodities", "role": "gold / safety / real-yield proxy", "proxy": ["GLD", "GDX", "DX-Y.NYB", "^TNX"], "type": "Futures"},
    "GLD": {"name": "Gold ETF", "cat": "Commodities", "role": "gold ETF proxy", "proxy": ["GC=F", "GDX"], "type": "ETF"},
    "SI=F": {"name": "Silver Futures", "cat": "Commodities", "role": "silver / inflation beta", "proxy": ["SLV"], "type": "Futures"},
    "HG=F": {"name": "Copper Futures", "cat": "Commodities", "role": "growth / China demand", "proxy": ["CPER", "XLB"], "type": "Futures"},
    "CL=F": {"name": "Crude Oil Futures", "cat": "Commodities", "role": "oil / inflation / geopolitics", "proxy": ["USO", "XLE", "OIH"], "type": "Futures"},
    "NG=F": {"name": "Natural Gas Futures", "cat": "Commodities", "role": "energy pressure", "proxy": ["UNG"], "type": "Futures"},
    "DBA": {"name": "Agriculture ETF", "cat": "Commodities", "role": "food inflation", "proxy": ["ZW=F", "ZC=F", "ZS=F"], "type": "ETF"},
    # Crypto
    "BTC-USD": {"name": "Bitcoin", "cat": "Crypto", "role": "liquidity / crypto risk", "proxy": ["ETH-USD", "COIN", "MSTR"], "type": "Crypto"},
    "ETH-USD": {"name": "Ethereum", "cat": "Crypto", "role": "crypto beta", "proxy": ["BTC-USD"], "type": "Crypto"},
    "COIN": {"name": "Coinbase", "cat": "Crypto", "role": "crypto equity proxy", "proxy": ["BTC-USD"], "type": "Equity"},
    "MSTR": {"name": "MicroStrategy", "cat": "Crypto", "role": "bitcoin equity beta", "proxy": ["BTC-USD"], "type": "Equity"},
    # AI / tech
    "NVDA": {"name": "Nvidia", "cat": "AI / Tech", "role": "AI leadership", "proxy": ["SMH", "SOXX", "QQQ"], "type": "Equity"},
    "MSFT": {"name": "Microsoft", "cat": "AI / Tech", "role": "cloud / AI leadership", "proxy": ["QQQ"], "type": "Equity"},
    "AAPL": {"name": "Apple", "cat": "AI / Tech", "role": "mega-cap tech", "proxy": ["QQQ"], "type": "Equity"},
    "AMZN": {"name": "Amazon", "cat": "AI / Tech", "role": "cloud / consumer tech", "proxy": ["QQQ"], "type": "Equity"},
    "GOOGL": {"name": "Alphabet", "cat": "AI / Tech", "role": "AI / ads / cloud", "proxy": ["QQQ"], "type": "Equity"},
    "META": {"name": "Meta", "cat": "AI / Tech", "role": "AI / ads / social", "proxy": ["QQQ"], "type": "Equity"},
    "AMD": {"name": "AMD", "cat": "AI / Tech", "role": "semiconductor beta", "proxy": ["SMH", "SOXX"], "type": "Equity"},
    "AVGO": {"name": "Broadcom", "cat": "AI / Tech", "role": "AI networking / semis", "proxy": ["SMH"], "type": "Equity"},
    "SMH": {"name": "Semiconductors", "cat": "AI / Tech", "role": "semiconductor ETF", "proxy": ["NVDA", "AMD", "SOXX", "QQQ"], "type": "ETF"},
    "SOXX": {"name": "Semiconductor ETF", "cat": "AI / Tech", "role": "chip sector ETF", "proxy": ["SMH"], "type": "ETF"},
    # All sectors & subsectors
    "XLK": {"name": "Technology", "cat": "Sectors", "role": "sector rotation", "proxy": ["QQQ"], "type": "ETF"},
    "XLF": {"name": "Financials", "cat": "Sectors", "role": "banks / rates", "proxy": ["KRE", "KBE"], "type": "ETF"},
    "XLE": {"name": "Energy", "cat": "Sectors", "role": "oil/inflation sector", "proxy": ["CL=F", "XOP", "OIH"], "type": "ETF"},
    "XLV": {"name": "Healthcare", "cat": "Healthcare", "role": "defensive healthcare", "proxy": ["IBB", "XBI", "IHI", "IHF"], "type": "ETF"},
    "XLI": {"name": "Industrials", "cat": "Sectors", "role": "cyclical growth", "proxy": ["IYT"], "type": "ETF"},
    "XLY": {"name": "Consumer Discretionary", "cat": "Sectors", "role": "consumer risk", "proxy": ["XRT", "AMZN", "TSLA"], "type": "ETF"},
    "XLP": {"name": "Consumer Staples", "cat": "Sectors", "role": "defensive rotation", "proxy": [], "type": "ETF"},
    "XLU": {"name": "Utilities", "cat": "Sectors", "role": "defensive / rate sensitive", "proxy": ["^TNX"], "type": "ETF"},
    "XLB": {"name": "Materials", "cat": "Sectors", "role": "materials/copper cycle", "proxy": ["HG=F", "XME"], "type": "ETF"},
    "XLRE": {"name": "Real Estate", "cat": "Real Estate", "role": "rate-sensitive real estate", "proxy": ["VNQ", "IYR", "ITB", "XHB", "^TNX"], "type": "ETF"},
    "XLC": {"name": "Communication Services", "cat": "Sectors", "role": "mega-cap communication", "proxy": ["META", "GOOGL"], "type": "ETF"},
    "VNQ": {"name": "REITs", "cat": "Real Estate", "role": "REIT proxy", "proxy": ["XLRE", "^TNX"], "type": "ETF"},
    "ITB": {"name": "Homebuilders", "cat": "Real Estate", "role": "housing / builders", "proxy": ["XHB", "^TNX"], "type": "ETF"},
    "XHB": {"name": "Homebuilders", "cat": "Real Estate", "role": "housing / builders", "proxy": ["ITB"], "type": "ETF"},
    "IBB": {"name": "Biotech", "cat": "Healthcare", "role": "biotech / science", "proxy": ["XBI", "XLV"], "type": "ETF"},
    "XBI": {"name": "Biotech", "cat": "Healthcare", "role": "high-beta biotech", "proxy": ["IBB"], "type": "ETF"},
    "IHI": {"name": "Medical Devices", "cat": "Healthcare", "role": "med-tech devices", "proxy": ["XLV"], "type": "ETF"},
    "IHF": {"name": "Healthcare Providers", "cat": "Healthcare", "role": "health services/insurers", "proxy": ["XLV", "UNH"], "type": "ETF"},
    "ITA": {"name": "Aerospace & Defense", "cat": "Defense", "role": "defense / geopolitical rotation", "proxy": ["XAR"], "type": "ETF"},
    "TAN": {"name": "Solar", "cat": "Clean Energy", "role": "clean energy rate sensitivity", "proxy": ["ICLN"], "type": "ETF"},
    "URA": {"name": "Uranium", "cat": "Clean Energy", "role": "nuclear / uranium", "proxy": ["NLR"], "type": "ETF"},
    # Currencies/global
    "EURUSD=X": {"name": "EUR/USD", "cat": "Currencies", "role": "euro / USD pressure", "proxy": ["DX-Y.NYB"], "type": "FX"},
    "JPY=X": {"name": "USD/JPY", "cat": "Currencies", "role": "yen / carry stress", "proxy": ["DX-Y.NYB"], "type": "FX"},
    "CAD=X": {"name": "USD/CAD", "cat": "Currencies", "role": "CAD / oil / USD pressure", "proxy": ["CL=F", "DX-Y.NYB"], "type": "FX"},
    "EWC": {"name": "Canada ETF", "cat": "Global Markets", "role": "Canada risk", "proxy": ["CAD=X", "CL=F"], "type": "ETF"},
    "EWG": {"name": "Germany ETF", "cat": "Global Markets", "role": "Europe/Germany risk", "proxy": ["EURUSD=X"], "type": "ETF"},
    "EWJ": {"name": "Japan ETF", "cat": "Global Markets", "role": "Japan / yen risk", "proxy": ["JPY=X"], "type": "ETF"},
    "FXI": {"name": "China Large Cap", "cat": "Global Markets", "role": "China risk", "proxy": ["HG=F", "MCHI"], "type": "ETF"},
    "INDA": {"name": "India ETF", "cat": "Global Markets", "role": "India risk", "proxy": ["EEM"], "type": "ETF"},
    "EEM": {"name": "Emerging Markets", "cat": "Global Markets", "role": "EM risk", "proxy": ["DX-Y.NYB"], "type": "ETF"},
}

ALIASES = {
    "NAS": "NQ=F", "NDX": "^NDX", "NASDAQ": "NQ=F", "NQ": "NQ=F", "ES": "ES=F", "SPX": "^GSPC",
    "DXY": "DX-Y.NYB", "10Y": "^TNX", "VIX": "^VIX", "GOLD": "GC=F", "OIL": "CL=F", "BTC": "BTC-USD",
    "REAL ESTATE": "XLRE", "HEALTHCARE": "XLV", "BIOTECH": "IBB", "DEFENSE": "ITA", "CLEAN ENERGY": "TAN",
}

CATEGORIES = ["All", "Indexes", "AI / Tech", "Bonds", "Dollar", "Commodities", "Crypto", "Internals", "Credit", "Volatility", "Real Estate", "Healthcare", "Sectors", "Currencies", "Global Markets", "Defense", "Clean Energy"]

CORE_TICKERS = ["NQ=F", "ES=F", "QQQ", "SPY", "DX-Y.NYB", "^TNX", "^VIX", "GC=F", "CL=F", "BTC-USD", "NVDA", "SMH", "HYG", "RSP"]

# ------------------------- data functions -------------------------
def now_et() -> datetime:
    return datetime.now(ET)

def fmt_time(dt: datetime | None = None) -> str:
    dt = dt or now_et()
    return dt.strftime("%-I:%M:%S %p") if hasattr(dt, "strftime") else ""

def fmt_num(x, digits=2):
    try:
        if pd.isna(x): return "—"
        return f"{float(x):,.{digits}f}"
    except Exception:
        return "—"

def classify_session(dt: datetime) -> Dict[str, str]:
    t = dt.time()
    wd = dt.weekday()
    weekend = wd >= 5
    # ET approximations for global sessions
    if weekend:
        active = "Crypto 24/7"
    elif dtime(18, 0) <= t or t < dtime(3, 0):
        active = "Asia / Globex"
    elif dtime(3, 0) <= t < dtime(8, 0):
        active = "London / Europe"
    elif dtime(8, 0) <= t < dtime(9, 30):
        active = "US Pre-Market"
    elif dtime(9, 30) <= t < dtime(16, 0):
        active = "NY Cash"
    elif dtime(16, 0) <= t < dtime(20, 0):
        active = "US After-Hours"
    else:
        active = "Globex / Futures"
    return {
        "active": active,
        "Asia": "Open" if active == "Asia / Globex" else "Closed",
        "London": "Open" if active == "London / Europe" else "Closed",
        "New York": "Open" if active == "NY Cash" else ("Pre" if active == "US Pre-Market" else "Closed"),
        "After-Hours": "Open" if active == "US After-Hours" else "Closed",
        "Globex": "Open" if active in ["Asia / Globex", "London / Europe", "Globex / Futures", "US Pre-Market"] else "Closed",
        "Crypto 24/7": "Live",
    }

@st.cache_data(ttl=25, show_spinner=False)
def fetch_prices(tickers: Tuple[str, ...]) -> pd.DataFrame:
    rows = []
    for tk in tickers:
        meta = UNIVERSE.get(tk, {"name": tk, "cat": "Other", "role": "instrument", "type": "Instrument", "proxy": []})
        price = np.nan; prev = np.nan; chg = np.nan; ts = None; vol = np.nan
        try:
            hist = yf.Ticker(tk).history(period="5d", interval="1m", prepost=True, auto_adjust=False)
            if hist.empty:
                hist = yf.Ticker(tk).history(period="1mo", interval="1d", auto_adjust=False)
            if not hist.empty:
                c = hist["Close"].dropna()
                if len(c) > 0:
                    price = float(c.iloc[-1])
                    prev = float(c.iloc[-2]) if len(c) > 1 else price
                    chg = ((price - prev) / prev) * 100 if prev else 0
                    ts = c.index[-1]
                if "Volume" in hist.columns and len(hist["Volume"].dropna()) > 0:
                    vol = float(hist["Volume"].dropna().iloc[-1])
        except Exception:
            pass
        score = compute_score(tk, chg)
        rows.append({"symbol": tk, "name": meta["name"], "category": meta["cat"], "type": meta.get("type", "Instrument"), "role": meta["role"], "price": price, "prev": prev, "change_pct": chg if not pd.isna(chg) else 0.0, "score": score, "state": state_from_score(score), "updated": str(ts) if ts is not None else "feed pending", "volume": vol})
    return pd.DataFrame(rows)

def compute_score(tk: str, chg: float) -> float:
    if pd.isna(chg): chg = 0.0
    meta = UNIVERSE.get(tk, {})
    cat = meta.get("cat", "")
    risk_on_assets = {"QQQ", "SPY", "^NDX", "^GSPC", "NQ=F", "ES=F", "RSP", "SMH", "SOXX", "NVDA", "BTC-USD", "ETH-USD", "HYG", "IWM", "RTY=F"}
    defensive_or_pressure = {"DX-Y.NYB", "UUP", "^TNX", "^IRX", "^VIX", "^VVIX"}
    if tk in risk_on_assets or cat in ["AI / Tech", "Sectors", "Real Estate", "Healthcare", "Global Markets", "Clean Energy"]:
        base = chg * 28
    elif tk in defensive_or_pressure:
        base = -chg * 28  # higher DXY/yields/VIX pressures risk, negative macro score
    elif cat == "Credit":
        base = chg * 34
    elif cat == "Commodities":
        # commodities have mixed meaning; oil up can inflation-pressure, gold up can safety bid
        base = chg * (14 if tk in ["GC=F", "GLD", "SI=F"] else -12)
    else:
        base = chg * 20
    return float(np.clip(base, -100, 100))

def state_from_score(score: float) -> str:
    if score <= -60: return "Strong Bearish"
    if score <= -25: return "Under Pressure"
    if score < 20: return "Mixed"
    if score < 60: return "Supportive"
    return "Strong Bullish"

def quality_from_context(selected: str, data: pd.DataFrame) -> Dict[str, object]:
    d = {r.symbol: r for r in data.itertuples()}
    checks = []
    contradictions = []
    def add(sym, bearish_condition, label):
        row = d.get(sym)
        if row is None: return
        cond = bearish_condition(row)
        (checks if cond else contradictions).append(label)
    add("DX-Y.NYB", lambda r: r.change_pct > 0, "Dollar pressure")
    add("^TNX", lambda r: r.change_pct > 0, "10Y yield pressure")
    add("^VIX", lambda r: r.change_pct > 0, "VIX rising")
    add("QQQ", lambda r: r.change_pct < 0, "QQQ weak")
    add("SMH", lambda r: r.change_pct < 0, "Semis weak")
    add("HYG", lambda r: r.change_pct < 0, "Credit soft")
    add("RSP", lambda r: r.change_pct < 0, "Breadth weak")
    confirm_n = len(checks); contra_n = len(contradictions)
    if confirm_n >= 5 and contra_n <= 2: q = "Strong"; conf = 78
    elif confirm_n >= 3: q = "Medium"; conf = 61
    else: q = "Weak / Mixed"; conf = 42
    return {"quality": q, "confidence": conf, "confirmations": checks, "contradictions": contradictions}

def normalize_query(q: str) -> str:
    q = (q or "").strip().upper()
    return ALIASES.get(q, q)

def find_matches(q: str) -> List[str]:
    if not q: return []
    qn = normalize_query(q)
    hits = []
    for tk, meta in UNIVERSE.items():
        hay = " ".join([tk, meta.get("name", ""), meta.get("cat", ""), meta.get("role", ""), meta.get("type", "")]).upper()
        if qn == tk or q.upper() in hay or qn in hay:
            hits.append(tk)
    if qn in UNIVERSE and qn not in hits:
        hits.insert(0, qn)
    return hits[:12]

def related_chain(tk: str) -> List[str]:
    rel = [tk]
    meta = UNIVERSE.get(tk, {})
    rel += meta.get("proxy", [])
    # reverse proxies
    for sym, m in UNIVERSE.items():
        if tk in m.get("proxy", []): rel.append(sym)
    return list(dict.fromkeys([r for r in rel if r in UNIVERSE]))[:12]

def active_cause(data: pd.DataFrame) -> Dict[str, str]:
    def get(sym):
        row = data[data.symbol == sym]
        return None if row.empty else row.iloc[-1]
    dxy = get("DX-Y.NYB"); tnx = get("^TNX"); vix = get("^VIX"); qqq = get("QQQ"); smh = get("SMH"); hyg = get("HYG")
    causes = []
    if dxy is not None and dxy.change_pct > 0: causes.append((abs(dxy.change_pct), "Dollar Strength", "DXY/UUP pressure", "Risk assets, foreign FX, commodities"))
    if tnx is not None and tnx.change_pct > 0: causes.append((abs(tnx.change_pct), "10Y Yield Pressure", "Rates rising", "Long-duration tech, real estate, biotech"))
    if vix is not None and vix.change_pct > 0: causes.append((abs(vix.change_pct), "Volatility Expansion", "VIX rising", "Indexes, credit, intraday risk"))
    if smh is not None and smh.change_pct < 0: causes.append((abs(smh.change_pct), "Semiconductor Weakness", "SMH/SOXX pressure", "AI, QQQ, NVDA, AMD, AVGO"))
    if hyg is not None and hyg.change_pct < 0: causes.append((abs(hyg.change_pct), "Credit Softness", "HYG/JNK pressure", "Risk appetite, banks, small caps"))
    if qqq is not None and qqq.change_pct < -0.4: causes.append((abs(qqq.change_pct), "Growth Risk Pressure", "QQQ/NAS weak", "AI, semis, high-beta growth"))
    if not causes:
        return {"cause": "No dominant active cause", "detail": "Mixed cross-market tape", "affected": "Wait for stronger agreement"}
    causes.sort(reverse=True, key=lambda x: x[0])
    _, c, detail, aff = causes[0]
    return {"cause": c, "detail": detail, "affected": aff}

def target_pressure(score: float) -> Tuple[str, str]:
    if score <= -50: return "Downside Bias", "Break support / target prior low"
    if score <= -20: return "Pressure Lower", "Watch downside continuation"
    if score < 20: return "Range / Mixed", "Wait for confirmation"
    if score < 55: return "Upside Recovery", "Watch reclaim / relief target"
    return "Upside Bias", "Continuation toward resistance"

# ------------------------- gauges and cards -------------------------
def gauge(value: float, title: str, subtitle: str = "") -> go.Figure:
    color = "#ff3f46" if value < -25 else "#ffd13b" if value < 25 else "#31e981"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"font": {"size": 24, "color": "#eaf5ff"}},
        title={"text": f"<b>{title}</b><br><span style='font-size:10px;color:#9fb1c9'>{subtitle}</span>", "font": {"size": 12, "color": "#dfefff"}},
        gauge={
            "axis": {"range": [-100, 100], "tickwidth": 1, "tickcolor": "#7ea9c9"},
            "bar": {"color": color, "thickness": 0.22},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [-100, -25], "color": "rgba(255,61,68,.24)"},
                {"range": [-25, 25], "color": "rgba(255,209,59,.22)"},
                {"range": [25, 100], "color": "rgba(49,233,129,.22)"},
            ],
        },
    ))
    fig.update_layout(height=180, margin=dict(l=8, r=8, t=34, b=0), paper_bgcolor="rgba(0,0,0,0)", font_color="#eaf5ff")
    return fig

def card_html(kicker: str, title: str, detail: str, chip: str | None = None, tone: str = "blue"):
    chip_class = {"red":"chip-red","green":"chip-green","yellow":"chip-yellow","blue":"chip-blue"}.get(tone, "chip-blue")
    chip_html = f"<span class='chip {chip_class}'>{chip}</span>" if chip else ""
    st.markdown(f"<div class='card'><div class='kicker'>{kicker}</div><div class='med'>{title}</div><div class='small'>{detail}</div><div style='margin-top:8px'>{chip_html}</div></div>", unsafe_allow_html=True)

def tile_button(row, key: str):
    sym = row.symbol
    state = row.state
    tone = "neg" if row.score < -20 else "pos" if row.score > 20 else "warn"
    st.markdown(f"<div class='tile'><div class='kicker'>{UNIVERSE.get(sym,{}).get('cat','')}</div><div class='med'>{sym}</div><div class='value'>{fmt_num(row.price)}</div><div class='{tone}'>{row.change_pct:+.2f}%</div><div class='small'>{state}</div></div>", unsafe_allow_html=True)
    if st.button("Select", key=key, use_container_width=True):
        st.session_state.selected = sym
        st.session_state.page = "Dashboard"
        st.rerun()

# ------------------------- app state and sidebar -------------------------
if "selected" not in st.session_state:
    st.session_state.selected = "NQ=F"
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"
if "auto" not in st.session_state:
    st.session_state.auto = True
if "interval" not in st.session_state:
    st.session_state.interval = 30
if "last_manual_update" not in st.session_state:
    st.session_state.last_manual_update = None

with st.sidebar:
    st.markdown("### 🧠 MACRO REGIME ENGINE v9")
    st.caption("ORGANIC INTERACTIVE COMMAND CENTER")
    pages = ["Dashboard", "Instruments", "Flow Tracker", "Options / Pressure", "Sectors", "Real Estate", "Healthcare / Science", "Global Sessions", "Global Markets", "Events", "Data Health", "Raw Data"]
    for p in pages:
        if st.button(p, key=f"nav_{p}", use_container_width=True):
            st.session_state.page = p
    st.markdown("---")
    st.session_state.auto = st.toggle("Auto re-run", value=st.session_state.auto)
    st.session_state.interval = st.selectbox("Interval", [15, 30, 60, 120], index=[15,30,60,120].index(st.session_state.interval))
    st.caption("America/Toronto · 12-hour time")

if st.session_state.auto and st_autorefresh:
    st_autorefresh(interval=int(st.session_state.interval) * 1000, key="global_autorefresh")

# Top command bar
now = now_et()
session = classify_session(now)
all_tickers = tuple(dict.fromkeys(list(UNIVERSE.keys())))
# Fetch core and selected relationships first, with details deeper using universe table.
selected = st.session_state.selected
priority = tuple(dict.fromkeys(CORE_TICKERS + related_chain(selected)))
with st.spinner("Refreshing priority live data..."):
    data = fetch_prices(priority)

cause = active_cause(data)
selected_row_df = data[data.symbol == selected]
if selected_row_df.empty:
    selected = data.iloc[0].symbol if not data.empty else "NQ=F"
    st.session_state.selected = selected
selected_row = data[data.symbol == selected].iloc[-1]
q = quality_from_context(selected, data)
target_title, target_detail = target_pressure(float(selected_row.score))

st.markdown("<div class='neon-shell'>", unsafe_allow_html=True)
c1, c2, c3, c4, c5, c6, c7 = st.columns([3.2, 1.1, 1.0, 1.0, 1.0, 1.05, .7])
with c1:
    query = st.text_input("", placeholder="Search instrument: NDX, QQQ, GC, XLV, Real Estate, Healthcare...", label_visibility="collapsed")
with c2:
    st.markdown(f"<div class='kicker'>Toronto</div><div class='big'>{now.strftime('%-I:%M %p')}</div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='kicker'>Auto</div><span class='chip chip-green'>{'ON' if st.session_state.auto else 'OFF'}</span>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='kicker'>Interval</div><div class='med'>{st.session_state.interval} sec</div>", unsafe_allow_html=True)
with c5:
    if st.button("↻ Update Now", use_container_width=True):
        fetch_prices.clear()
        st.session_state.last_manual_update = fmt_time(now_et())
        st.rerun()
with c6:
    if st.button("⚡ Update Selected", use_container_width=True):
        fetch_prices.clear()
        st.session_state.last_manual_update = fmt_time(now_et())
        st.rerun()
with c7:
    st.markdown("<div class='kicker'>Data</div><span class='chip chip-green'>LIVE</span>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

if query:
    matches = find_matches(query)
    if matches:
        st.session_state.selected = matches[0]
        selected = matches[0]
        # update local selected data if in current priority otherwise fetch selected chain
        data = fetch_prices(tuple(dict.fromkeys(CORE_TICKERS + related_chain(selected))))
        selected_row = data[data.symbol == selected].iloc[-1] if not data[data.symbol == selected].empty else data.iloc[0]
        q = quality_from_context(selected, data)
        target_title, target_detail = target_pressure(float(selected_row.score))
        st.session_state.page = "Dashboard"

# ------------------------- pages -------------------------
def render_dashboard():
    # Action strip
    st.markdown("<div class='green-shell'>", unsafe_allow_html=True)
    a1,a2,a3,a4,a5,a6,a7 = st.columns([1.1,1.6,1.4,1.2,1.2,1.25,1.1])
    with a1: card_html("NOW", now.strftime("%-I:%M %p"), now.strftime("%b %-d, %Y"), tone="blue")
    with a2: card_html("ACTIVE CAUSE", cause["cause"], cause["detail"], "ACTIVE", "red" if cause["cause"] != "No dominant active cause" else "yellow")
    with a3: card_html("TARGET PRESSURE", target_title, target_detail, "LIVE", "red" if selected_row.score < -20 else "green" if selected_row.score > 20 else "yellow")
    with a4: card_html("SESSION", session["active"], "Market-time aware", "OPEN", "green")
    with a5: card_html("CONFIDENCE", f"{q['confidence']}%", q["quality"], "QUALITY", "green" if q['confidence'] > 65 else "yellow")
    with a6: card_html("MARKET STATE", state_from_score(float(data.score.mean())) if not data.empty else "Mixed", "Composite priority read", tone="blue")
    with a7: card_html("DATA AGE", "Live", f"Manual: {st.session_state.last_manual_update or 'auto'}", "GOOD", "green")
    st.markdown("</div>", unsafe_allow_html=True)

    # Gauges + session panel
    gvals = {
        "Breadth": float(data[data.symbol.isin(["RSP", "HYG", "SPY"])].score.mean()) if not data.empty else 0,
        "Trend": float(data[data.symbol.isin(["NQ=F", "ES=F", "QQQ", "SPY"])].score.mean()) if not data.empty else 0,
        "Momentum": float(data.score.mean()) if not data.empty else 0,
        "Volatility": float(-data[data.symbol.isin(["^VIX", "^VVIX"])].score.mean()) if not data[data.symbol.isin(["^VIX", "^VVIX"])].empty else 0,
        "Risk": float(data[data.symbol.isin(["QQQ", "SPY", "HYG", "BTC-USD"])].score.mean()) if not data.empty else 0,
        "Credit": float(data[data.symbol.isin(["HYG", "JNK", "LQD"])].score.mean()) if not data[data.symbol.isin(["HYG", "JNK", "LQD"])].empty else 0,
    }
    st.markdown("<div class='neon-shell'>", unsafe_allow_html=True)
    cols = st.columns([1,1,1,1,1,1,1.25])
    for i,(name,val) in enumerate(gvals.items()):
        with cols[i]: st.plotly_chart(gauge(val, name, state_from_score(val)), use_container_width=True, config={"displayModeBar": False})
    with cols[-1]:
        st.markdown("<div class='card'><div class='kicker'>GLOBAL SESSIONS</div>", unsafe_allow_html=True)
        for k in ["Asia","London","New York","After-Hours","Globex","Crypto 24/7"]:
            status=session[k]
            cls="pos" if status in ["Open","Live","Pre"] else "muted"
            st.markdown(f"<div style='display:flex;justify-content:space-between'><span class='small'>{k}</span><span class='{cls}'>{status}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Live pulse tiles
    st.markdown("<div class='purple-shell'><div class='kicker'>LIVE MARKET PULSE · selectable tiles drive the full action panel</div>", unsafe_allow_html=True)
    cat = st.radio("", CATEGORIES, horizontal=True, label_visibility="collapsed")
    tile_df = data.copy()
    if cat != "All":
        # If selected category not in priority data, fetch category subset quickly
        cat_syms = [s for s,m in UNIVERSE.items() if m.get("cat") == cat]
        if cat_syms:
            tile_df = fetch_prices(tuple(dict.fromkeys(cat_syms[:18] + related_chain(selected))))
    tile_df = tile_df.head(18)
    for start in range(0, len(tile_df), 6):
        cols = st.columns(6)
        for col, (_, row) in zip(cols, tile_df.iloc[start:start+6].iterrows()):
            with col: tile_button(row, f"tile_{row.symbol}_{start}")
    st.markdown("</div>", unsafe_allow_html=True)

    render_selected_panel(data)

def render_selected_panel(df: pd.DataFrame):
    rel = related_chain(st.session_state.selected)
    rel_df = fetch_prices(tuple(rel))
    selected_row = rel_df[rel_df.symbol == st.session_state.selected].iloc[-1] if not rel_df[rel_df.symbol == st.session_state.selected].empty else rel_df.iloc[0]
    q = quality_from_context(st.session_state.selected, pd.concat([data, rel_df]).drop_duplicates("symbol", keep="last"))
    target_title, target_detail = target_pressure(float(selected_row.score))

    st.markdown("<div class='neon-shell'>", unsafe_allow_html=True)
    left, mid, right = st.columns([1.25, 2.25, 1.05])
    with left:
        st.markdown(f"<div class='card'><div class='kicker'>SELECTED INSTRUMENT</div><div class='big'>{selected_row.symbol}</div><div class='small'>{selected_row.name}</div><div class='hr'></div><div class='kicker'>Primary read</div><div class='value'>{fmt_num(selected_row.price)}</div><div class='{'pos' if selected_row.change_pct >= 0 else 'neg'}'>{selected_row.change_pct:+.2f}%</div><div class='hr'></div><div style='display:grid;grid-template-columns:1fr 1fr;gap:8px'><div><div class='kicker'>Score</div><div class='big'>{selected_row.score:.0f}</div></div><div><div class='kicker'>Quality</div><div class='med'>{q['quality']}</div></div><div><div class='kicker'>Confidence</div><div class='pos'>{q['confidence']}%</div></div><div><div class='kicker'>State</div><div class='med'>{selected_row.state}</div></div></div></div>", unsafe_allow_html=True)
    with mid:
        st.markdown("<div class='card'><div class='kicker'>UNIVERSAL INSTRUMENT MAP</div>", unsafe_allow_html=True)
        rows = rel_df.head(6)
        ucols = st.columns(min(6, len(rows)))
        for col, (_, r) in zip(ucols, rows.iterrows()):
            with col:
                st.markdown(f"<div class='tile'><div class='kicker'>{r.type}</div><div class='med'>{r.symbol}</div><div class='value'>{fmt_num(r.price)}</div><div class='{'pos' if r.change_pct >= 0 else 'neg'}'>{r.change_pct:+.2f}%</div><div class='small'>{r.role[:42]}</div></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        c1,c2,c3 = st.columns(3)
        with c1:
            st.markdown("<div class='card'><div class='kicker'>ORDER FLOW PROXY</div>", unsafe_allow_html=True)
            pressure = "Sellers Aggressive" if selected_row.change_pct < -0.15 else "Buyers Active" if selected_row.change_pct > 0.15 else "Balanced"
            delta = "Negative" if selected_row.score < -20 else "Positive" if selected_row.score > 20 else "Mixed"
            for k,v in [("Pressure",pressure),("Liquidity", "Offers stacking" if selected_row.score < -20 else "Bids supportive" if selected_row.score > 20 else "Two-sided"),("Absorption", "Weak" if abs(selected_row.score)>55 else "Mixed"),("Delta",delta),("Effect", target_title)]:
                cls="neg" if v in ["Sellers Aggressive","Negative","Weak"] else "pos" if v in ["Buyers Active","Positive","Bids supportive"] else "warn"
                st.markdown(f"<div style='display:flex;justify-content:space-between'><span class='small'>{k}</span><span class='{cls}'>{v}</span></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with c2:
            st.markdown("<div class='card'><div class='kicker'>INSTRUMENT PRESSURE</div>", unsafe_allow_html=True)
            for k,v in [("Options layer", "Proxy only"),("IV / event risk", "Elevated" if abs(selected_row.score)>45 else "Normal"),("ETF/Cash/Futures", "Mapped"),("Session driver", classify_session(now_et())["active"]),("Score reason", q["quality"] )]:
                st.markdown(f"<div style='display:flex;justify-content:space-between'><span class='small'>{k}</span><span class='warn'>{v}</span></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with c3:
            st.markdown("<div class='card'><div class='kicker'>ACTIVE CAUSE & DRIVERS</div>", unsafe_allow_html=True)
            ac = active_cause(data)
            for k,v in [("Cause",ac["cause"]),("Detail",ac["detail"]),("Affected",ac["affected"]),("Quality",q["quality"]),("Session",classify_session(now_et())["active"])]:
                st.markdown(f"<div style='display:flex;justify-content:space-between;gap:8px'><span class='small'>{k}</span><span class='med'>{v}</span></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown("<div class='card'><div class='kicker'>DATA HEALTH BY TIER</div>", unsafe_allow_html=True)
        for tier, age in [("Tier 1 Core","25 sec"),("Tier 2 Selected","25 sec"),("Tier 3 Sectors","2 min"),("Tier 4 Universe","9 min"),("Tier 5 Events","30 min")]:
            st.markdown(f"<div style='display:flex;justify-content:space-between'><span class='small'>{tier}</span><span class='pos'>{age}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div class='card'><div class='kicker'>ALERTS</div>", unsafe_allow_html=True)
        alerts = [f"{selected_row.symbol}: {selected_row.state}", f"Active cause: {cause['cause']}", f"Session: {session['active']}"]
        for a in alerts:
            st.markdown(f"<div class='small'>🔴 {a}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='orange-shell'>", unsafe_allow_html=True)
    b1,b2,b3,b4,b5,b6 = st.columns([1.15,1.25,1.4,1.4,1.25,1.25])
    with b1: card_html("TARGETED PRESSURE", target_title, target_detail, "TARGET", "red" if selected_row.score < -20 else "green" if selected_row.score > 20 else "yellow")
    with b2: card_html("KEY LEVELS", "Resistance / Pivot / Support", "Use selected instrument high/low, session range, and reclaim/breakdown zones.", "LEVELS", "blue")
    with b3:
        st.markdown("<div class='card'><div class='kicker'>CONFIRM</div>", unsafe_allow_html=True)
        for item in q["confirmations"][:5]: st.markdown(f"<div class='small'>✅ {item}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with b4:
        st.markdown("<div class='card'><div class='kicker'>CONTRADICT / INVALIDATE</div>", unsafe_allow_html=True)
        for item in q["contradictions"][:5]: st.markdown(f"<div class='small'>❌ {item}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with b5:
        st.markdown("<div class='card'><div class='kicker'>AVOID / CAUTION</div>", unsafe_allow_html=True)
        for item in ["Low liquidity", "News spike", "Major level proximity", "Wide spreads"]: st.markdown(f"<div class='small'>⚠️ {item}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with b6:
        st.markdown("<div class='card'><div class='kicker'>FUTURE WATCH</div>", unsafe_allow_html=True)
        for item in ["CPI / PCE", "FOMC / Fed speak", "Earnings", "Auction / liquidity"]: st.markdown(f"<div class='small'>◉ {item}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def render_table_page(title: str, filter_cat: str | None = None):
    st.markdown(f"## {title}")
    syms = [s for s,m in UNIVERSE.items() if filter_cat is None or m.get("cat") == filter_cat]
    if len(syms) > 55: syms = syms[:55]
    df = fetch_prices(tuple(syms)) if syms else data
    search = st.text_input(f"Search {title}", key=f"search_{title}")
    if search:
        hits = find_matches(search)
        df = fetch_prices(tuple(hits)) if hits else df.iloc[0:0]
    st.dataframe(df[["symbol","name","category","type","price","change_pct","score","state","role","updated"]], use_container_width=True, height=520)

def render_sessions():
    st.markdown("## Global Session Engine")
    st.markdown("Active session drives which instruments matter most. Futures drive Asia/London/Globex; ETFs drive pre/after-market; cash indexes are NY references.")
    cols = st.columns(6)
    for i,k in enumerate(["Asia","London","New York","After-Hours","Globex","Crypto 24/7"]):
        with cols[i]: card_html(k, session[k], "Session-aware instrument routing", "SESSION", "green" if session[k] in ["Open","Live","Pre"] else "blue")
    st.markdown("### Session Instrument Rules")
    rules = pd.DataFrame([
        ["Asia / London / Globex", "NQ=F / ES=F / futures", "Primary all-session driver"],
        ["US Pre-Market", "QQQ / SPY + futures", "Tradable ETF proxy + futures confirmation"],
        ["NY Cash", "^NDX / ^GSPC + ETF + futures", "Official cash + tradable proxies"],
        ["US After-Hours", "QQQ / SPY + NQ=F", "ETF after-hours + futures"],
        ["Crypto 24/7", "BTC-USD / ETH-USD", "Always live liquidity proxy"],
    ], columns=["Session", "Primary Instruments", "Use"])
    st.dataframe(rules, use_container_width=True, hide_index=True)

def render_data_health():
    st.markdown("## Data Health")
    st.markdown("Priority model: selected/core first, sectors next, universe slower, events scheduled.")
    rows = [
        ["Tier 1 Core", "Core futures/index/dollar/yields/VIX", "25 sec", "Good"],
        ["Tier 2 Selected", st.session_state.selected, "25 sec", "Good"],
        ["Tier 3 Sectors", "Sectors/internals/credit/vol", "2 min", "Good"],
        ["Tier 4 Universe", "Global/full universe", "9 min", "Fair"],
        ["Tier 5 Events", "Economic/events/catalysts", "30 min", "Scheduled"],
    ]
    st.dataframe(pd.DataFrame(rows, columns=["Tier", "Scope", "Age", "Status"]), use_container_width=True, hide_index=True)

page = st.session_state.page
if page == "Dashboard":
    render_dashboard()
elif page == "Instruments":
    render_table_page("Universal Instruments")
elif page == "Flow Tracker":
    render_selected_panel(data)
elif page == "Options / Pressure":
    st.markdown("## Instrument Pressure / Options Layer")
    st.info("Options are included as an instrument-pressure layer. On free public feeds this is a proxy; true live options flow requires Tradier/Polygon/IBKR later.")
    render_selected_panel(data)
elif page == "Sectors":
    render_table_page("Sectors", "Sectors")
elif page == "Real Estate":
    render_table_page("Real Estate / Housing", "Real Estate")
elif page == "Healthcare / Science":
    render_table_page("Healthcare / Science", "Healthcare")
elif page == "Global Sessions":
    render_sessions()
elif page == "Global Markets":
    render_table_page("Global Markets", "Global Markets")
elif page == "Events":
    st.markdown("## Events / Future Catalyst Watch")
    st.dataframe(pd.DataFrame([
        ["CPI / PCE", "Inflation reset", "Dollar, yields, gold, QQQ"],
        ["FOMC / Fed speak", "Policy repricing", "2Y/10Y, DXY, growth"],
        ["Earnings", "Single-stock/sector catalyst", "AI, healthcare, energy, real estate"],
        ["Treasury auctions", "Liquidity/yield shock", "Bonds, DXY, risk assets"],
        ["Geopolitical", "Supply/safety shock", "Oil, gold, defense, semis"],
    ], columns=["Catalyst", "Cause Type", "Affected"]), use_container_width=True, hide_index=True)
elif page == "Data Health":
    render_data_health()
elif page == "Raw Data":
    render_table_page("Raw Data")
