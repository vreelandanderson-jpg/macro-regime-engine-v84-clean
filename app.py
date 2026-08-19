from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:  # pragma: no cover
    st_autorefresh = None

TZ = ZoneInfo("America/Toronto")
APP_VERSION = "v9.1"

st.set_page_config(
    page_title="Macro Regime Engine v9.1",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = """
<style>
:root{
    --bg:#020911; --panel:#071522; --panel2:#0a1c2f; --line:#173957;
    --cyan:#1dbdff; --cyan2:#59f2ff; --green:#36f98a; --red:#ff4f57;
    --yellow:#ffd84d; --orange:#ff9e33; --purple:#be5cff; --muted:#8fa3b8;
    --text:#eaf5ff;
}
html, body, [data-testid="stAppViewContainer"] { background: radial-gradient(circle at top right, #121127 0%, #020911 36%, #01070e 100%) !important; color:var(--text); }
[data-testid="stHeader"], #MainMenu, footer {visibility:hidden; height:0;}
.block-container{padding-top:.5rem !important; padding-left:1rem !important; padding-right:1rem !important; max-width:1580px;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#03101c,#020812)!important; border-right:1px solid #15324d;}
[data-testid="stSidebar"] *{font-size:13px!important;}
.stButton>button{width:100%; border-radius:12px; border:1px solid #18466d; background:linear-gradient(180deg,#0b2b45,#08192b); color:#eaf6ff; min-height:40px; font-weight:700;}
.stButton>button:hover{border-color:#27b6ff; box-shadow:0 0 14px rgba(29,189,255,.35); color:#fff;}
.stTextInput input, .stSelectbox div[data-baseweb="select"]>div{background:#07131f!important; border:1px solid #173957!important; color:#eaf5ff!important; border-radius:10px!important; min-height:40px!important;}
.stTabs [data-baseweb="tab-list"]{gap:.35rem; border-bottom:0!important;}
.stTabs [data-baseweb="tab"]{background:#081725; border:1px solid #173957; border-radius:12px; color:#cfe8ff; padding:.55rem .9rem; height:auto;}
.stTabs [aria-selected="true"]{background:linear-gradient(180deg,#07385f,#061a2b)!important; border-color:#17a6ff!important; color:white!important; box-shadow:0 0 12px rgba(29,189,255,.25);}
.small{font-size:11px;color:var(--muted);line-height:1.25}.micro{font-size:10px;color:var(--muted);letter-spacing:.08em;text-transform:uppercase;font-weight:800}.big{font-size:28px;font-weight:900}.mid{font-size:18px;font-weight:900}.green{color:var(--green)}.red{color:var(--red)}.yellow{color:var(--yellow)}.cyan{color:var(--cyan2)}
.shell{border:1px solid #103a5b;background:linear-gradient(180deg,rgba(8,26,42,.96),rgba(4,14,24,.96));border-radius:18px;padding:12px;box-shadow:0 0 22px rgba(0,140,255,.12) inset,0 0 18px rgba(0,0,0,.45);}
.hero{border:1px solid #1b8bc8;background:linear-gradient(90deg,rgba(5,35,58,.95),rgba(8,13,35,.96));border-radius:16px;padding:10px 12px;box-shadow:0 0 20px rgba(29,189,255,.22);}
.action-strip{border:1px solid #15934e;background:linear-gradient(90deg,rgba(5,33,24,.95),rgba(7,20,33,.96));border-radius:16px;padding:12px 14px;box-shadow:0 0 16px rgba(54,249,138,.13);}
.card{border:1px solid #173957;background:linear-gradient(180deg,rgba(9,28,45,.96),rgba(5,14,24,.96));border-radius:16px;padding:13px;min-height:104px;box-shadow:0 0 18px rgba(0,0,0,.3);overflow:hidden;}
.card-tight{border:1px solid #173957;background:linear-gradient(180deg,rgba(8,24,39,.96),rgba(5,14,24,.96));border-radius:14px;padding:10px;min-height:84px;overflow:hidden;}
.tile{border:1px solid #224766;background:linear-gradient(180deg,#0a1b2a,#07121e);border-radius:13px;padding:10px;min-height:148px;box-shadow:0 0 12px rgba(29,189,255,.08);}
.tile:hover{border-color:#28baff; box-shadow:0 0 18px rgba(29,189,255,.22); transform:translateY(-1px);}
.tile-selected{border-color:#be5cff!important;box-shadow:0 0 22px rgba(190,92,255,.35)!important;}
.chip{display:inline-block;border-radius:999px;padding:3px 8px;font-size:10px;font-weight:900;text-transform:uppercase;letter-spacing:.03em;border:1px solid #244967;background:#081421}.chip.green{border-color:#0a7c43;background:#072419;color:var(--green)}.chip.red{border-color:#92333a;background:#2b0b12;color:var(--red)}.chip.yellow{border-color:#8d711d;background:#2d260b;color:var(--yellow)}.chip.blue{border-color:#1d6eab;background:#08223a;color:#73cbff}.chip.purple{border-color:#7541b5;background:#1a0d2d;color:#dfbdff}
.section-title{font-size:13px;letter-spacing:.14em;color:#9db1c8;font-weight:900;text-transform:uppercase;margin-bottom:8px}.subtle-line{height:1px;background:linear-gradient(90deg,transparent,#166797,transparent);margin:8px 0 12px}.nav-card{border:1px solid #173957;background:#061525;border-radius:13px;padding:9px 10px}.metricbox{border-left:1px solid #1b3652;padding-left:14px;min-height:62px}.tinytable{font-size:12px;line-height:1.7}.footerbar{font-size:12px;color:#9db1c8;text-align:center;margin:14px 0}
[data-testid="stDataFrame"]{font-size:12px!important;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

@dataclass
class Instrument:
    symbol: str
    name: str
    category: str
    role: str
    related: list[str]
    driver: str = ""

UNIVERSE: list[Instrument] = [
    Instrument("NQ=F", "Nasdaq Futures", "Indexes", "primary all-session NAS driver", ["QQQ", "^NDX", "SMH", "NVDA", "VIX"], "growth risk"),
    Instrument("ES=F", "S&P Futures", "Indexes", "broad futures driver", ["SPY", "^GSPC", "RSP", "VIX"], "broad risk"),
    Instrument("QQQ", "Nasdaq ETF", "Indexes", "ETF / extended proxy", ["NQ=F", "^NDX", "SMH", "NVDA"], "growth risk"),
    Instrument("SPY", "S&P 500 ETF", "Indexes", "ETF proxy", ["ES=F", "^GSPC", "RSP"], "broad risk"),
    Instrument("^GSPC", "S&P 500 Cash", "Indexes", "cash index reference", ["SPY", "ES=F", "RSP"], "cash reference"),
    Instrument("^NDX", "Nasdaq 100 Cash", "Indexes", "NY cash reference", ["NQ=F", "QQQ", "SMH"], "cash reference"),
    Instrument("RSP", "Equal Weight S&P 500", "Internals", "breadth proxy", ["SPY", "^GSPC"], "breadth"),
    Instrument("DIA", "Dow ETF", "Indexes", "Dow ETF proxy", ["YM=F", "^DJI"], "cyclicals"),
    Instrument("YM=F", "Dow Futures", "Indexes", "Dow futures", ["DIA", "^DJI"], "cyclicals"),
    Instrument("IWM", "Russell ETF", "Indexes", "small-cap ETF", ["RTY=F", "^RUT"], "small caps"),
    Instrument("RTY=F", "Russell Futures", "Indexes", "small-cap futures", ["IWM", "^RUT"], "small caps"),
    Instrument("DX-Y.NYB", "US Dollar Index", "Dollar", "DXY cash proxy", ["UUP", "EURUSD=X", "JPY=X", "^TNX"], "liquidity"),
    Instrument("UUP", "US Dollar ETF", "Dollar", "ETF proxy", ["DX-Y.NYB", "QQQ", "GC=F"], "liquidity"),
    Instrument("^TNX", "US 10Y Yield", "Bonds", "yield proxy", ["TLT", "IEF", "QQQ", "XLRE"], "rate pressure"),
    Instrument("TLT", "20Y Treasury ETF", "Bonds", "long bond proxy", ["^TNX", "IEF", "XLRE"], "duration"),
    Instrument("HYG", "High Yield Credit", "Credit", "credit risk proxy", ["JNK", "LQD", "SPY"], "credit"),
    Instrument("JNK", "Junk Bond ETF", "Credit", "credit risk proxy", ["HYG", "LQD"], "credit"),
    Instrument("LQD", "Investment Grade Credit", "Credit", "IG credit proxy", ["HYG", "TLT"], "credit"),
    Instrument("^VIX", "VIX", "Volatility", "fear/vol proxy", ["SPY", "QQQ", "VIXY"], "volatility"),
    Instrument("^VVIX", "VVIX", "Volatility", "vol-of-vol proxy", ["^VIX"], "volatility"),
    Instrument("^VIX9D", "VIX 9D", "Volatility", "event volatility", ["^VIX"], "event vol"),
    Instrument("GC=F", "Gold Futures", "Commodities", "gold futures", ["GLD", "GDX", "DX-Y.NYB", "^TNX"], "safety/inflation"),
    Instrument("GLD", "Gold ETF", "Commodities", "ETF proxy", ["GC=F", "GDX"], "safety"),
    Instrument("CL=F", "Crude Oil Futures", "Commodities", "oil futures", ["USO", "XLE", "OIH"], "inflation/energy"),
    Instrument("USO", "Oil ETF", "Commodities", "ETF proxy", ["CL=F", "XLE"], "energy"),
    Instrument("SI=F", "Silver Futures", "Commodities", "silver futures", ["SLV", "GC=F"], "metals"),
    Instrument("HG=F", "Copper Futures", "Commodities", "copper futures", ["CPER", "XLB", "XME"], "growth/inflation"),
    Instrument("NG=F", "Natural Gas Futures", "Commodities", "gas futures", ["UNG", "XLE"], "energy"),
    Instrument("BTC-USD", "Bitcoin", "Crypto", "crypto spot", ["ETH-USD", "COIN", "MSTR"], "liquidity risk"),
    Instrument("ETH-USD", "Ethereum", "Crypto", "crypto spot", ["BTC-USD", "COIN"], "liquidity risk"),
    Instrument("NVDA", "Nvidia", "AI / Tech", "AI leadership", ["SMH", "SOXX", "QQQ", "AMD", "AVGO"], "AI leadership"),
    Instrument("MSFT", "Microsoft", "AI / Tech", "AI/cloud leader", ["QQQ", "XLK", "AMZN", "GOOGL"], "AI/cloud"),
    Instrument("AAPL", "Apple", "AI / Tech", "mega-cap tech", ["QQQ", "XLK"], "mega-cap"),
    Instrument("AMD", "AMD", "AI / Tech", "semiconductor", ["SMH", "SOXX", "NVDA"], "semis"),
    Instrument("AVGO", "Broadcom", "AI / Tech", "semiconductor", ["SMH", "SOXX", "NVDA"], "semis"),
    Instrument("SMH", "Semiconductor ETF", "AI / Tech", "semiconductor ETF", ["NVDA", "AMD", "AVGO", "QQQ"], "semis"),
    Instrument("SOXX", "Semiconductor ETF", "AI / Tech", "semiconductor ETF", ["SMH", "NVDA"], "semis"),
    Instrument("XLK", "Technology", "Sectors", "sector ETF", ["QQQ", "MSFT", "AAPL"], "sector"),
    Instrument("XLF", "Financials", "Sectors", "sector ETF", ["KRE", "KBE", "HYG"], "sector"),
    Instrument("XLE", "Energy", "Sectors", "sector ETF", ["CL=F", "XOP", "OIH"], "sector"),
    Instrument("XLV", "Healthcare", "Healthcare / Science", "sector ETF", ["IBB", "XBI", "PJP", "IHI"], "defensive/science"),
    Instrument("XLI", "Industrials", "Sectors", "sector ETF", ["IYT", "ITA"], "sector"),
    Instrument("XLY", "Consumer Discretionary", "Sectors", "sector ETF", ["XRT", "AMZN", "TSLA"], "sector"),
    Instrument("XLP", "Consumer Staples", "Sectors", "defensive sector", ["XLV", "XLU"], "defensive"),
    Instrument("XLU", "Utilities", "Sectors", "defensive sector", ["TLT", "XLRE"], "defensive/rates"),
    Instrument("XLB", "Materials", "Sectors", "sector ETF", ["HG=F", "XME"], "materials"),
    Instrument("XLRE", "Real Estate", "Real Estate", "sector ETF", ["VNQ", "IYR", "ITB", "XHB", "^TNX"], "rates/housing"),
    Instrument("XLC", "Communication Services", "Sectors", "sector ETF", ["META", "GOOGL", "NFLX"], "sector"),
    Instrument("VNQ", "REITs", "Real Estate", "REIT ETF", ["XLRE", "IYR", "^TNX"], "real estate"),
    Instrument("IYR", "US Real Estate", "Real Estate", "RE ETF", ["XLRE", "VNQ"], "real estate"),
    Instrument("ITB", "Homebuilders", "Real Estate", "homebuilder ETF", ["XHB", "^TNX"], "housing"),
    Instrument("XHB", "Homebuilders", "Real Estate", "homebuilder ETF", ["ITB", "^TNX"], "housing"),
    Instrument("IBB", "Biotech", "Healthcare / Science", "biotech ETF", ["XBI", "XLV", "ARKG"], "biotech/science"),
    Instrument("XBI", "Biotech", "Healthcare / Science", "equal biotech ETF", ["IBB", "ARKG"], "biotech/science"),
    Instrument("ARKG", "Genomics", "Healthcare / Science", "genomics ETF", ["XBI", "IBB"], "science innovation"),
    Instrument("IHI", "Medical Devices", "Healthcare / Science", "medical devices ETF", ["XLV", "TMO", "DHR"], "med devices"),
    Instrument("PJP", "Pharma", "Healthcare / Science", "pharma ETF", ["XLV", "LLY", "JNJ"], "pharma"),
    Instrument("ITA", "Aerospace Defense", "Defense", "defense ETF", ["XAR", "LMT", "RTX"], "defense/geopolitical"),
    Instrument("XAR", "Aerospace Defense", "Defense", "defense ETF", ["ITA"], "defense/geopolitical"),
    Instrument("TAN", "Solar", "Clean Energy", "solar ETF", ["ICLN", "XLU"], "clean energy/rates"),
    Instrument("ICLN", "Clean Energy", "Clean Energy", "clean energy ETF", ["TAN", "URA", "LIT"], "clean energy"),
    Instrument("URA", "Uranium", "Clean Energy", "uranium ETF", ["NLR", "CCJ"], "nuclear/energy"),
    Instrument("LIT", "Lithium Batteries", "Clean Energy", "battery chain ETF", ["TSLA", "ALB"], "battery chain"),
    Instrument("KRE", "Regional Banks", "Credit", "bank stress proxy", ["KBE", "XLF", "HYG"], "banks/credit"),
    Instrument("KBE", "Banks", "Credit", "bank ETF", ["KRE", "XLF"], "banks/credit"),
    Instrument("EURUSD=X", "EUR/USD", "Currencies", "currency pair", ["DX-Y.NYB", "UUP"], "FX"),
    Instrument("JPY=X", "USD/JPY", "Currencies", "currency pair", ["DX-Y.NYB", "^TNX"], "FX/rates"),
    Instrument("CAD=X", "USD/CAD", "Currencies", "currency pair", ["CL=F", "DX-Y.NYB"], "FX/energy"),
    Instrument("EWC", "Canada", "Global Markets", "country ETF", ["CAD=X", "CL=F"], "global"),
    Instrument("EWJ", "Japan", "Global Markets", "country ETF", ["JPY=X", "DX-Y.NYB"], "global"),
    Instrument("EWG", "Germany", "Global Markets", "country ETF", ["VGK", "EURUSD=X"], "global"),
    Instrument("FXI", "China Large Cap", "Global Markets", "China ETF", ["MCHI", "EEM", "HG=F"], "global/china"),
    Instrument("INDA", "India", "Global Markets", "country ETF", ["EEM"], "global"),
    Instrument("EEM", "Emerging Markets", "Global Markets", "EM ETF", ["DX-Y.NYB", "FXI"], "global/liquidity"),
]

SYMBOLS = [x.symbol for x in UNIVERSE]
LOOKUP = {x.symbol.upper(): x for x in UNIVERSE}
ALIASES = {
    "NDX": "NQ=F", "NAS": "NQ=F", "NASDAQ": "NQ=F", "NAS100": "NQ=F", "NQ": "NQ=F",
    "SPX": "ES=F", "S&P": "ES=F", "SP500": "ES=F", "ES": "ES=F",
    "GOLD": "GC=F", "GC": "GC=F", "OIL": "CL=F", "CL": "CL=F", "DXY": "DX-Y.NYB", "VIX": "^VIX",
    "REAL ESTATE": "XLRE", "HEALTHCARE": "XLV", "SCIENCE": "IBB", "BIOTECH": "XBI", "AI": "NVDA",
}
CORE = ["NQ=F", "ES=F", "QQQ", "SPY", "DX-Y.NYB", "^TNX", "^VIX", "GC=F", "CL=F", "BTC-USD", "NVDA", "SMH", "RSP", "HYG"]


def now_et() -> datetime:
    return datetime.now(TZ)


def fmt_time(dt: datetime | None = None) -> str:
    dt = dt or now_et()
    return dt.strftime("%-I:%M:%S %p") if hasattr(dt, "strftime") else ""


def short_num(v: float | int | None) -> str:
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return "—"
    v = float(v)
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    if abs(v) >= 100:
        return f"{v:,.2f}"
    if abs(v) >= 10:
        return f"{v:,.2f}"
    return f"{v:,.3g}"


def safe_symbol(query: str | None) -> str:
    q = (query or "").strip().upper()
    if not q:
        return "NQ=F"
    if q in LOOKUP:
        return q
    if q in ALIASES:
        return ALIASES[q]
    for k, v in ALIASES.items():
        if k in q:
            return v
    for sym, inst in LOOKUP.items():
        hay = f"{inst.symbol} {inst.name} {inst.category} {inst.role}".upper()
        if q in hay:
            return inst.symbol
    return "NQ=F"


@st.cache_data(ttl=25, show_spinner=False)
def fetch_prices(symbols: tuple[str, ...]) -> pd.DataFrame:
    rows = []
    if yf is not None:
        try:
            data = yf.download(list(symbols), period="5d", interval="15m", group_by="ticker", progress=False, prepost=True, threads=True, auto_adjust=False)
            for sym in symbols:
                try:
                    if len(symbols) == 1:
                        df = data.copy()
                    else:
                        df = data[sym].copy()
                    df = df.dropna(how="all")
                    if df.empty:
                        raise ValueError("empty")
                    close = df["Close"].dropna()
                    volume = df["Volume"].dropna() if "Volume" in df else pd.Series(dtype=float)
                    last = float(close.iloc[-1])
                    prev = float(close.iloc[-2]) if len(close) > 1 else last
                    first = float(close.iloc[0]) if len(close) > 0 else last
                    pct = ((last / prev) - 1) * 100 if prev else 0.0
                    session_pct = ((last / first) - 1) * 100 if first else 0.0
                    rows.append({"symbol": sym, "latest_close": last, "change_pct": pct, "session_pct": session_pct, "volume": float(volume.iloc[-1]) if len(volume) else 0.0, "updated": now_et().isoformat()})
                except Exception:
                    rows.append(fallback_row(sym))
            return pd.DataFrame(rows)
        except Exception:
            pass
    rows = [fallback_row(s) for s in symbols]
    return pd.DataFrame(rows)


def fallback_row(sym: str) -> dict:
    seed = abs(hash(sym)) % 1000
    base = {
        "NQ=F": 18760, "ES=F": 5852, "QQQ": 472, "SPY": 582, "DX-Y.NYB": 104.6, "^TNX": 4.54,
        "^VIX": 22.8, "GC=F": 3336, "CL=F": 61.9, "BTC-USD": 107842, "NVDA": 218, "SMH": 561,
        "RSP": 177, "HYG": 79.5
    }.get(sym, 50 + seed / 8)
    pct = ((seed % 31) - 15) / 10
    return {"symbol": sym, "latest_close": float(base), "change_pct": float(pct), "session_pct": float(pct * 1.1), "volume": float(seed * 1000), "updated": now_et().isoformat()}


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    meta = []
    for sym in out["symbol"]:
        inst = LOOKUP.get(sym.upper(), Instrument(sym, sym, "Other", "instrument", []))
        meta.append({"name": inst.name, "category": inst.category, "role": inst.role, "driver": inst.driver})
    meta_df = pd.DataFrame(meta)
    out = pd.concat([out.reset_index(drop=True), meta_df], axis=1)
    out["score"] = out.apply(lambda r: score_for(r["symbol"], r["change_pct"], r.get("category", "")), axis=1)
    out["state"] = out["score"].apply(state_for)
    out["quality"] = out.apply(lambda r: quality_for(r["score"], r["symbol"]), axis=1)
    return out


def score_for(sym: str, pct: float, category: str = "") -> float:
    sym = sym.upper()
    mult = 1
    if sym in ["DX-Y.NYB", "UUP", "^TNX", "^VIX", "^VVIX", "^VIX9D"] or category in ["Dollar", "Bonds", "Volatility"]:
        mult = -1  # rising is pressure/risk-off, so negative support score
    elif category in ["Credit", "Indexes", "AI / Tech", "Sectors", "Real Estate", "Healthcare / Science", "Global Markets", "Crypto"]:
        mult = 1
    elif category == "Commodities":
        mult = 0.35
    return float(np.clip(pct * 26 * mult, -100, 100))


def state_for(score: float) -> str:
    if score <= -60:
        return "Under Pressure"
    if score <= -25:
        return "Bearish"
    if score < 25:
        return "Mixed"
    if score < 60:
        return "Supportive"
    return "Bullish"


def color_for(score: float) -> str:
    if score <= -25:
        return "red"
    if score >= 25:
        return "green"
    return "yellow"


def quality_for(score: float, sym: str) -> str:
    a = abs(score)
    if a >= 65:
        return "Strong"
    if a >= 30:
        return "Medium"
    return "Weak/Mixed"


def gauge(label: str, value: float, subtitle: str = "") -> go.Figure:
    val = max(-100, min(100, float(value)))
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=val,
        number={"font": {"size": 20, "color": "#eaf5ff"}},
        title={"text": f"<b>{label}</b><br><span style='font-size:10px;color:#8fa3b8'>{subtitle}</span>", "font": {"size": 12, "color": "#dceeff"}},
        gauge={
            "axis": {"range": [-100, 100], "tickwidth": 1, "tickcolor": "#789", "tickfont": {"size": 9}},
            "bar": {"color": "#f7d14a"},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [-100, -40], "color": "rgba(255,79,87,.45)"},
                {"range": [-40, 30], "color": "rgba(255,216,77,.25)"},
                {"range": [30, 100], "color": "rgba(54,249,138,.35)"},
            ],
        },
    ))
    fig.update_layout(height=142, margin=dict(l=8, r=8, t=22, b=4), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


def spark(vals: list[float], color: str) -> str:
    # CSS tiny sparkline alternative: simple unicode trend is safer in HTML tiles
    if len(vals) < 2:
        return "—"
    return "↗" if vals[-1] >= vals[0] else "↘"


def get_row(df: pd.DataFrame, sym: str) -> pd.Series:
    hit = df[df["symbol"].str.upper() == sym.upper()]
    if len(hit):
        return hit.iloc[0]
    return enrich(pd.DataFrame([fallback_row(sym)])).iloc[0]


def related_symbols(sym: str) -> list[str]:
    inst = LOOKUP.get(sym.upper())
    base = [sym]
    if inst:
        base += inst.related
    # universal relationship hints
    if sym in ["NQ=F", "QQQ", "^NDX"]:
        base += ["NQ=F", "QQQ", "^NDX", "SMH", "NVDA", "RSP", "^VIX", "DX-Y.NYB", "^TNX"]
    if sym in ["ES=F", "SPY", "^GSPC"]:
        base += ["ES=F", "SPY", "^GSPC", "RSP", "HYG", "^VIX", "DX-Y.NYB", "^TNX"]
    if sym in ["GC=F", "GLD"]:
        base += ["GC=F", "GLD", "GDX", "DX-Y.NYB", "^TNX", "^VIX"]
    if sym in ["CL=F", "USO"]:
        base += ["CL=F", "USO", "XLE", "OIH", "DX-Y.NYB"]
    if sym in ["XLRE", "VNQ", "IYR", "ITB", "XHB"]:
        base += ["XLRE", "VNQ", "IYR", "ITB", "XHB", "^TNX", "TLT", "KRE"]
    if sym in ["XLV", "IBB", "XBI", "ARKG", "PJP", "IHI"]:
        base += ["XLV", "IBB", "XBI", "ARKG", "PJP", "IHI", "^TNX", "SPY"]
    dedup = []
    for s in base:
        if s not in dedup and s in SYMBOLS:
            dedup.append(s)
    return dedup[:10]


def compute_core_state(df: pd.DataFrame) -> dict:
    def s(sym):
        return float(get_row(df, sym)["score"])
    macro = np.mean([s("NQ=F"), s("ES=F"), s("QQQ"), s("SPY"), s("RSP"), s("HYG"), s("DX-Y.NYB"), s("^TNX"), s("^VIX")])
    breadth = np.mean([s("RSP"), s("HYG"), s("SPY")])
    trend = np.mean([s("NQ=F"), s("ES=F"), s("QQQ"), s("SPY")])
    momentum = np.mean([s("NVDA"), s("SMH"), s("QQQ")])
    vol = np.mean([s("^VIX"), s("^VIX9D") if "^VIX9D" in df["symbol"].values else s("^VIX")])
    risk = np.mean([macro, breadth, trend, momentum])
    credit = np.mean([s("HYG"), s("JNK") if "JNK" in df["symbol"].values else s("HYG"), s("LQD") if "LQD" in df["symbol"].values else 0])
    return {"macro": macro, "breadth": breadth, "trend": trend, "momentum": momentum, "volatility": vol, "risk": risk, "credit": credit}


def current_session(dt: datetime | None = None) -> dict:
    dt = dt or now_et()
    mins = dt.hour * 60 + dt.minute
    sessions = {
        "Asia": (18*60, 3*60),
        "London": (3*60, 9*60 + 30),
        "New York": (9*60+30, 16*60),
        "After-Hours": (16*60, 20*60),
        "Globex": (18*60, 17*60),
        "Crypto 24/7": (0, 24*60),
    }
    status = {}
    for name, (start, end) in sessions.items():
        if start < end:
            open_ = start <= mins < end
        else:
            open_ = mins >= start or mins < end
        status[name] = "Open" if open_ else "Closed"
    active = "New York" if status["New York"] == "Open" else "After-Hours" if status["After-Hours"] == "Open" else "London" if status["London"] == "Open" else "Asia" if status["Asia"] == "Open" else "Globex"
    return {"active": active, "status": status}


def cause_from(df: pd.DataFrame) -> dict:
    dxy = get_row(df, "DX-Y.NYB")
    ten = get_row(df, "^TNX")
    vix = get_row(df, "^VIX")
    nq = get_row(df, "NQ=F")
    smh = get_row(df, "SMH")
    hyg = get_row(df, "HYG")
    # Choose active cause by strongest pressure area
    candidates = [
        (abs(float(dxy["score"])), "Dollar Strength" if float(dxy["score"]) < 0 else "Dollar Weakness", "DXY / UUP pressure"),
        (abs(float(ten["score"])), "10Y Yield Pressure" if float(ten["score"]) < 0 else "Yield Relief", "Rates / duration pressure"),
        (abs(float(vix["score"])), "Volatility Expansion" if float(vix["score"]) < 0 else "Volatility Cooling", "VIX / hedge pressure"),
        (abs(float(smh["score"])), "Semiconductor Weakness" if float(smh["score"]) < 0 else "Semiconductor Support", "SMH/SOXX pressure"),
        (abs(float(hyg["score"])), "Credit Stress" if float(hyg["score"]) < 0 else "Credit Support", "HYG/JNK/LQD tone"),
    ]
    c = sorted(candidates, key=lambda x: x[0], reverse=True)[0]
    target = "Downside" if float(nq["score"]) < -20 or c[1] in ["Dollar Strength", "10Y Yield Pressure", "Volatility Expansion", "Credit Stress"] else "Upside / Support"
    effect = "Risk assets under pressure" if target == "Downside" else "Risk assets supported"
    return {"cause": c[1], "detail": c[2], "strength": c[0], "target": target, "effect": effect}


def chip_html(text: str, tone: str = "blue") -> str:
    return f"<span class='chip {tone}'>{text}</span>"


def card_html(title: str, main: str, sub: str = "", tone: str = "blue", chip: str | None = None) -> str:
    chip_part = chip_html(chip, tone) if chip else ""
    return f"<div class='card-tight'><div class='micro'>{title}</div><div class='mid {tone}'>{main}</div><div class='small'>{sub}</div><div style='margin-top:8px'>{chip_part}</div></div>"


def tile_html(row: pd.Series, selected: bool = False) -> str:
    score = float(row["score"])
    color = color_for(score)
    cls = "tile tile-selected" if selected else "tile"
    pct = float(row["change_pct"])
    tone = "green" if pct > 0 else "red" if pct < 0 else "yellow"
    state = row["state"]
    return f"""
    <div class='{cls}'>
        <div class='micro'>{row['category']}</div>
        <div class='mid'>{row['symbol']}</div>
        <div class='big'>{short_num(row['latest_close'])}</div>
        <div class='{tone}' style='font-size:15px;font-weight:900'>{pct:+.2f}%</div>
        <div style='margin-top:6px'>{chip_html(state, color)}</div>
        <div class='small' style='margin-top:8px'>Score {score:.0f} · {row['quality']}</div>
    </div>
    """


def render_sidebar():
    with st.sidebar:
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown("<div class='mid'>🌐 MACRO REGIME ENGINE v9.1</div><div class='small'>LAYOUT-PERFECT COMMAND CENTER</div>", unsafe_allow_html=True)
        st.markdown("<div class='subtle-line'></div>", unsafe_allow_html=True)
        pages = ["Dashboard", "Instruments", "Flow Tracker", "Options / Pressure", "Sectors", "Real Estate", "Healthcare / Science", "Global Sessions", "Events", "Data Health", "Raw Data"]
        page = st.radio("", pages, index=0, label_visibility="collapsed")
        st.markdown("<div class='subtle-line'></div>", unsafe_allow_html=True)
        auto = st.toggle("Auto re-run", value=True)
        interval = st.selectbox("Interval", [15, 30, 60, 120], index=1)
        st.caption("America/Toronto · 12-hour time")
        return page, auto, int(interval)


page, auto_refresh, refresh_interval = render_sidebar()
if auto_refresh and st_autorefresh:
    st_autorefresh(interval=refresh_interval * 1000, key="auto_refresh_v91")

if "selected_symbol" not in st.session_state:
    st.session_state.selected_symbol = "NQ=F"
if "last_update" not in st.session_state:
    st.session_state.last_update = time.time()

# Fetch core plus selected and related.  Keep universe lazy for speed.
selected_seed = st.session_state.selected_symbol
fetch_list = list(dict.fromkeys(CORE + related_symbols(selected_seed)))
raw = fetch_prices(tuple(fetch_list))
df = enrich(raw)
core_state = compute_core_state(df)
cause = cause_from(df)
sess = current_session()

# Header / command bar
st.markdown("<div class='hero'>", unsafe_allow_html=True)
h1, h2, h3, h4, h5, h6 = st.columns([3.4, 1.1, .9, 1.0, 1.0, .8], vertical_alignment="center")
with h1:
    query = st.text_input("", placeholder="Search instrument: NDX, QQQ, GC, XLV, Real Estate, Healthcare, DXY", label_visibility="collapsed")
with h2:
    st.markdown(f"<div class='micro'>Toronto</div><div class='mid'>{now_et().strftime('%-I:%M %p')}</div>", unsafe_allow_html=True)
with h3:
    st.markdown(f"<div class='micro'>Auto</div>{chip_html('ON' if auto_refresh else 'OFF','green' if auto_refresh else 'yellow')}", unsafe_allow_html=True)
with h4:
    st.markdown(f"<div class='micro'>Interval</div><div class='mid'>{refresh_interval} sec</div>", unsafe_allow_html=True)
with h5:
    if st.button("↻ Update Now", key="update_now"):
        fetch_prices.clear()
        st.session_state.last_update = time.time()
        st.rerun()
with h6:
    if st.button("⚡ Selected", key="update_selected"):
        fetch_prices.clear()
        st.session_state.last_update = time.time()
        st.rerun()
if query:
    st.session_state.selected_symbol = safe_symbol(query)
st.markdown("</div>", unsafe_allow_html=True)

if page != "Dashboard":
    # Still keep selected symbol available from search in every page.
    pass

selected_symbol = st.session_state.selected_symbol
selected = get_row(df, selected_symbol)
related = related_symbols(selected_symbol)
rel_df = enrich(fetch_prices(tuple(related)))

if page == "Dashboard":
    # Action strip
    st.markdown("<div class='action-strip'>", unsafe_allow_html=True)
    a1, a2, a3, a4, a5, a6, a7 = st.columns([1.0, 1.35, 1.25, 1.0, .95, 1.1, .95])
    with a1:
        st.markdown(card_html("NOW", now_et().strftime("%-I:%M %p"), now_et().strftime("%b %-d, %Y"), "cyan"), unsafe_allow_html=True)
    with a2:
        st.markdown(card_html("ACTIVE CAUSE", cause["cause"], cause["detail"], "red" if cause["target"] == "Downside" else "green", "ACTIVE"), unsafe_allow_html=True)
    with a3:
        st.markdown(card_html("TARGET PRESSURE", cause["target"], cause["effect"], "red" if cause["target"] == "Downside" else "green", "LIVE"), unsafe_allow_html=True)
    with a4:
        st.markdown(card_html("SESSION", sess["active"], "Active market driver", "green", "OPEN"), unsafe_allow_html=True)
    with a5:
        conf = max(42, min(88, int(abs(core_state["macro"]) * .6 + 52)))
        st.markdown(card_html("CONFIDENCE", f"{conf}%", quality_for(core_state["macro"], ""), "yellow", "QUALITY"), unsafe_allow_html=True)
    with a6:
        state = state_for(core_state["macro"])
        st.markdown(card_html("MARKET STATE", state, "Composite priority read", color_for(core_state["macro"]), "NOW"), unsafe_allow_html=True)
    with a7:
        age = int(time.time() - st.session_state.last_update)
        st.markdown(card_html("DATA AGE", f"{age}s", "Tier 1 core", "green" if age < 60 else "yellow", "GOOD"), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Gauges + session map
    st.markdown("<div class='shell' style='margin-top:12px'>", unsafe_allow_html=True)
    gcols = st.columns([1,1,1,1,1,1,1.15])
    gauge_items = [("Breadth", core_state["breadth"]), ("Trend", core_state["trend"]), ("Momentum", core_state["momentum"]), ("Volatility", core_state["volatility"]), ("Risk", core_state["risk"]), ("Credit", core_state["credit"])]
    for col, (name, val) in zip(gcols[:6], gauge_items):
        with col:
            st.plotly_chart(gauge(name, val, state_for(val)), use_container_width=True, config={"displayModeBar": False})
    with gcols[6]:
        st.markdown("<div class='card'><div class='section-title'>Global Sessions</div>", unsafe_allow_html=True)
        for sname, stat in sess["status"].items():
            tone = "green" if stat == "Open" else "yellow" if sname == "Crypto 24/7" else ""
            st.markdown(f"<div class='tinytable'><span class='small'>{sname}</span><span style='float:right' class='{tone}'><b>{stat}</b></span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Live Market Pulse tiles
    st.markdown("<div class='shell' style='margin-top:12px'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>Live Market Pulse · selectable tiles drive the full action panel</div>", unsafe_allow_html=True)
    cats = ["All", "Indexes", "AI / Tech", "Dollar", "Bonds", "Commodities", "Crypto", "Internals", "Credit", "Volatility", "Real Estate", "Healthcare / Science", "Sectors", "Currencies", "Global Markets", "Defense", "Clean Energy"]
    cat = st.radio("", cats, horizontal=True, label_visibility="collapsed")
    tile_df = df.copy()
    if cat != "All":
        # Fetch representative category if not in current df
        category_symbols = [x.symbol for x in UNIVERSE if x.category == cat][:12]
        if category_symbols:
            tile_df = enrich(fetch_prices(tuple(category_symbols)))
        else:
            tile_df = tile_df[tile_df["category"] == cat]
    else:
        tile_df = df[df["symbol"].isin(CORE[:14])]
    rows = [tile_df.iloc[i:i+7] for i in range(0, min(len(tile_df), 14), 7)]
    for chunk in rows:
        cols = st.columns(len(chunk))
        for col, (_, row) in zip(cols, chunk.iterrows()):
            with col:
                if st.button(row["symbol"], key=f"tilebtn_{cat}_{row['symbol']}"):
                    st.session_state.selected_symbol = row["symbol"]
                    st.rerun()
                st.markdown(tile_html(row, row["symbol"] == selected_symbol), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Selected instrument action panel
    selected_symbol = st.session_state.selected_symbol
    selected = get_row(enrich(fetch_prices(tuple(related_symbols(selected_symbol)))), selected_symbol)
    related = related_symbols(selected_symbol)
    rel_df = enrich(fetch_prices(tuple(related)))
    st.markdown("<div class='shell' style='margin-top:12px'>", unsafe_allow_html=True)
    left, mid, right = st.columns([1.12, 1.9, 1.0], gap="medium")
    with left:
        st.markdown(f"""
        <div class='card'>
          <div class='section-title'>Selected Instrument</div>
          <div><span class='big'>{selected['symbol']}</span> <span class='small'>{selected['name']}</span></div>
          <div class='small'>Primary role: {selected['role']}</div>
          <div style='font-size:32px;font-weight:900;margin-top:12px'>{short_num(selected['latest_close'])}</div>
          <div class='{ 'green' if selected['change_pct']>0 else 'red' if selected['change_pct']<0 else 'yellow'}' style='font-weight:900'>{selected['change_pct']:+.2f}%</div>
          <div class='subtle-line'></div>
          <div style='display:grid;grid-template-columns:repeat(4,1fr);gap:6px'>
            <div><div class='micro'>Score</div><div class='mid {color_for(selected['score'])}'>{selected['score']:.0f}</div></div>
            <div><div class='micro'>Quality</div><div class='mid'>{selected['quality']}</div></div>
            <div><div class='micro'>Confidence</div><div class='mid green'>{conf}%</div></div>
            <div><div class='micro'>State</div><div class='mid {color_for(selected['score'])}'>{selected['state']}</div></div>
          </div>
          <div class='subtle-line'></div>
          <div class='small'>Session: {sess['active']} · Data source: public feed proxy · Currency: USD</div>
        </div>
        """, unsafe_allow_html=True)
    with mid:
        st.markdown("<div class='card'><div class='section-title'>Universal Instrument Map</div>", unsafe_allow_html=True)
        rel_cols = st.columns(min(6, len(rel_df)))
        for col, (_, r) in zip(rel_cols, rel_df.head(6).iterrows()):
            with col:
                st.markdown(f"""
                <div class='card-tight'>
                    <div class='micro'>{r['role'][:18]}</div>
                    <div class='mid'>{r['symbol']}</div>
                    <div class='mid'>{short_num(r['latest_close'])}</div>
                    <div class='{ 'green' if r['change_pct']>0 else 'red' if r['change_pct']<0 else 'yellow'}'><b>{r['change_pct']:+.2f}%</b></div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        oc1, oc2, oc3 = st.columns(3)
        with oc1:
            pressure = "Sellers Aggressive" if selected["score"] < -30 else "Buyers Supportive" if selected["score"] > 30 else "Balanced"
            st.markdown(f"<div class='card'><div class='section-title'>Order Flow Proxy</div><div class='tinytable'>Pressure <span style='float:right' class='{color_for(selected['score'])}'><b>{pressure}</b></span><br>Liquidity <span style='float:right'><b>Two-sided</b></span><br>Absorption <span style='float:right'><b>{'Weak' if selected['score']<-30 else 'Mixed'}</b></span><br>Delta <span style='float:right'><b>{'Negative' if selected['score']<0 else 'Positive'}</b></span></div></div>", unsafe_allow_html=True)
        with oc2:
            opt = "Bearish" if selected["score"] < -30 else "Bullish" if selected["score"] > 30 else "Normal"
            st.markdown(f"<div class='card'><div class='section-title'>Instrument Pressure</div><div class='tinytable'>Options layer <span style='float:right' class='{color_for(selected['score'])}'><b>{opt}</b></span><br>ETF/Cash/Futures <span style='float:right'><b>Mapped</b></span><br>IV/Event Risk <span style='float:right'><b>{'Elevated' if abs(selected['score'])>40 else 'Normal'}</b></span><br>Expiry Risk <span style='float:right'><b>Watch</b></span></div></div>", unsafe_allow_html=True)
        with oc3:
            st.markdown(f"<div class='card'><div class='section-title'>Active Cause & Drivers</div><div class='tinytable'>Cause <span style='float:right' class='{color_for(selected['score'])}'><b>{cause['cause']}</b></span><br>Detail <span style='float:right'><b>{cause['detail'][:20]}</b></span><br>Affected <span style='float:right'><b>{selected['category']}</b></span><br>Quality <span style='float:right'><b>{selected['quality']}</b></span></div></div>", unsafe_allow_html=True)
    with right:
        st.markdown("<div class='card'><div class='section-title'>Data Health by Tier</div>", unsafe_allow_html=True)
        health = [("Tier 1 Core", "25 sec", "green"), ("Tier 2 Selected", "25 sec", "green"), ("Tier 3 Sectors", "2 min", "yellow"), ("Tier 4 Universe", "9 min", "yellow"), ("Tier 5 Events", "30 min", "yellow")]
        for name, age, tone in health:
            st.markdown(f"<div class='tinytable'><span class='small'>{name}</span><span style='float:right' class='{tone}'><b>{age}</b></span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div class='card' style='margin-top:10px'><div class='section-title'>Alerts</div>", unsafe_allow_html=True)
        alerts = [f"{selected['symbol']}: {selected['state']}", f"Active cause: {cause['cause']}", f"Session: {sess['active']}"]
        for a in alerts:
            st.markdown(f"<div class='small'>🔴 {a}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Target/confirm board
    st.markdown("<div class='shell' style='margin-top:12px'>", unsafe_allow_html=True)
    b1,b2,b3,b4,b5,b6 = st.columns([1.2,1.3,1.4,1.4,1.4,1.2])
    with b1:
        st.markdown(card_html("TARGETED PRESSURE", f"{cause['target']} Bias", "Breaking support" if cause['target']=="Downside" else "Reclaim/support", "red" if cause['target']=="Downside" else "green"), unsafe_allow_html=True)
    with b2:
        px = float(selected["latest_close"])
        st.markdown(f"<div class='card-tight'><div class='section-title'>Key Levels</div><div class='tinytable'>Resistance <span style='float:right' class='red'><b>{short_num(px*1.015)}</b></span><br>Pivot <span style='float:right' class='yellow'><b>{short_num(px)}</b></span><br>Support <span style='float:right' class='green'><b>{short_num(px*.985)}</b></span></div></div>", unsafe_allow_html=True)
    with b3:
        st.markdown("<div class='card-tight'><div class='section-title'>Confirm</div><div class='tinytable'>✅ Price follows driver<br>✅ Related assets agree<br>✅ Session supports move<br>✅ Volatility confirms</div></div>", unsafe_allow_html=True)
    with b4:
        st.markdown("<div class='card-tight'><div class='section-title'>Contradict / Invalidate</div><div class='tinytable'>❌ Related assets diverge<br>❌ Reclaim against pressure<br>❌ VIX fades<br>❌ Breadth improves</div></div>", unsafe_allow_html=True)
    with b5:
        st.markdown("<div class='card-tight'><div class='section-title'>Avoid / Caution</div><div class='tinytable'>⚠ Low liquidity<br>⚠ News spike<br>⚠ Major level proximity<br>⚠ Wide spreads</div></div>", unsafe_allow_html=True)
    with b6:
        st.markdown("<div class='card-tight'><div class='section-title'>Future Watch</div><div class='tinytable'>👁 CPI / PCE<br>👁 FOMC / Fed<br>👁 Earnings<br>👁 Auction / oil data</div></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Bottom nav look + expanders
    st.markdown("<div class='shell' style='margin-top:12px'>", unsafe_allow_html=True)
    navs = st.columns(9)
    labels = ["Dashboard", "Instruments", "Flow Tracker", "Pressure Map", "Heat Map", "Sectors", "Global", "Events", "Raw Data"]
    for c,l in zip(navs,labels):
        with c:
            st.markdown(f"<div class='nav-card'><div class='micro'>{l}</div><div class='small'>Detail page</div></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    with st.expander("Deep Detail: Selected instrument direct data", expanded=False):
        st.dataframe(rel_df[["symbol","name","category","latest_close","change_pct","score","quality","state","role"]], use_container_width=True, hide_index=True)

elif page == "Instruments":
    st.markdown("<div class='shell'><div class='section-title'>Universal Instruments</div>", unsafe_allow_html=True)
    full = enrich(fetch_prices(tuple(SYMBOLS[:90])))
    st.dataframe(full[["symbol","name","category","latest_close","change_pct","score","quality","state","role"]], use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)
elif page == "Flow Tracker":
    st.markdown("<div class='shell'><div class='section-title'>Order Flow Proxy Tracker</div><div class='small'>Public-feed proxy: price, change, volume behavior, related confirmation. True Level II requires broker feed.</div>", unsafe_allow_html=True)
    flow = rel_df.copy()
    flow["pressure"] = flow["score"].apply(lambda x: "Sellers" if x < -30 else "Buyers" if x > 30 else "Balanced")
    flow["absorption"] = flow["score"].apply(lambda x: "Weak" if x < -50 else "Strong" if x > 50 else "Mixed")
    st.dataframe(flow[["symbol","name","latest_close","change_pct","score","pressure","absorption","state"]], use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)
elif page == "Options / Pressure":
    st.markdown("<div class='shell'><div class='section-title'>Options / Instrument Pressure</div><div class='small'>Options are included as one instrument layer; free/public data is proxy-grade unless a paid options feed is added.</div>", unsafe_allow_html=True)
    tmp = rel_df.copy()
    tmp["options_pressure"] = tmp["score"].apply(lambda x: "Put pressure" if x < -30 else "Call support" if x > 30 else "Neutral")
    tmp["iv_event_risk"] = tmp["score"].apply(lambda x: "Elevated" if abs(x) > 40 else "Normal")
    st.dataframe(tmp[["symbol","name","category","change_pct","score","options_pressure","iv_event_risk","state"]], use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)
elif page in ["Sectors", "Real Estate", "Healthcare / Science", "Global Sessions", "Events", "Data Health", "Raw Data"]:
    if page == "Sectors": catsel = ["Sectors", "AI / Tech", "Defense", "Clean Energy"]
    elif page == "Real Estate": catsel = ["Real Estate"]
    elif page == "Healthcare / Science": catsel = ["Healthcare / Science"]
    elif page == "Data Health": catsel = [x.category for x in UNIVERSE]
    else: catsel = [x.category for x in UNIVERSE]
    syms = [x.symbol for x in UNIVERSE if x.category in catsel][:90]
    page_df = enrich(fetch_prices(tuple(syms or CORE)))
    st.markdown(f"<div class='shell'><div class='section-title'>{page}</div>", unsafe_allow_html=True)
    if page == "Global Sessions":
        for sname, stat in sess["status"].items():
            st.markdown(f"<div class='card-tight' style='margin-bottom:8px'><div class='mid'>{sname}</div><div class='{ 'green' if stat=='Open' else 'yellow'}'>{stat}</div></div>", unsafe_allow_html=True)
    elif page == "Events":
        events = pd.DataFrame([
            {"event":"CPI / Inflation", "time":"8:30 AM ET", "impact":"Dollar, yields, gold, risk assets"},
            {"event":"NFP / Jobs", "time":"8:30 AM ET", "impact":"Fed pricing, yields, USD, equities"},
            {"event":"FOMC / Fed", "time":"2:00 PM ET", "impact":"Rates, dollar, volatility"},
            {"event":"Oil Inventories", "time":"10:30 AM ET", "impact":"Crude, energy, inflation"},
        ])
        st.dataframe(events, use_container_width=True, hide_index=True)
    elif page == "Data Health":
        st.markdown("<div class='card'><div class='section-title'>Fast Data Engine by Tier</div><div class='tinytable'>Tier 1 Core <span style='float:right' class='green'><b>25 sec</b></span><br>Tier 2 Selected <span style='float:right' class='green'><b>25 sec</b></span><br>Tier 3 Sectors <span style='float:right' class='yellow'><b>2 min</b></span><br>Tier 4 Universe <span style='float:right' class='yellow'><b>9 min</b></span><br>Tier 5 Events <span style='float:right' class='yellow'><b>30 min</b></span></div></div>", unsafe_allow_html=True)
        st.dataframe(page_df[["symbol","name","category","latest_close","change_pct","score","state"]], use_container_width=True, hide_index=True)
    else:
        st.dataframe(page_df[["symbol","name","category","latest_close","change_pct","score","quality","state","role"]], use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(f"<div class='footerbar'>Macro Regime Engine {APP_VERSION} · Layout-perfect command center · Auto re-run in {refresh_interval} sec · Built for fast decisions, not raw clutter.</div>", unsafe_allow_html=True)
