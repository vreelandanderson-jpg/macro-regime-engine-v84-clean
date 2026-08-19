from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import datetime, date, timedelta
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
APP_VERSION = "v9.5"
MAX_DATA_AGE_SECONDS = 25
CACHE_TTL_SECONDS = 20
DEFAULT_REFRESH_SECONDS = 20

st.set_page_config(
    page_title=f"Macro Regime Engine {APP_VERSION}",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = """
<style>
:root{
    --bg:#020812; --panel:#071522; --panel2:#0a1c2f; --line:#163653;
    --cyan:#31c6ff; --green:#36f98a; --red:#ff5260; --yellow:#ffd84d;
    --purple:#c877ff; --muted:#8fa3b8; --text:#eaf5ff;
}
html, body, [data-testid="stAppViewContainer"]{
    background:radial-gradient(circle at 88% 0%,#101128 0%,#020812 34%,#01060d 100%)!important;
    color:var(--text);
}
[data-testid="stHeader"], #MainMenu, footer{visibility:hidden;height:0;}
.block-container{padding:.45rem .9rem 1.1rem!important;max-width:1660px;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#03101b,#020812)!important;border-right:1px solid #14304a;}
[data-testid="stSidebar"] > div:first-child{padding-top:.25rem;}
[data-testid="stSidebar"] *{font-size:12px!important;}
[data-testid="stSidebar"] [data-testid="stRadio"] label{padding:.12rem 0!important;}
[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"]{gap:.08rem!important;}
[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label{border-radius:8px;padding:.2rem .3rem!important;}
[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:hover{background:#071a2b;}
.stButton>button{
    width:100%;min-height:34px;border-radius:10px;border:1px solid #1b4669;
    background:linear-gradient(180deg,#0b2941,#071725);color:#eaf6ff;font-weight:800;
    padding:.28rem .48rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}
.stButton>button:hover{border-color:#31c6ff;box-shadow:0 0 12px rgba(49,198,255,.22);color:#fff;}
.stTextInput input,.stSelectbox div[data-baseweb="select"]>div{
    background:#07131f!important;border:1px solid #173957!important;color:#eaf5ff!important;
    border-radius:10px!important;min-height:36px!important;
}
.stTabs [data-baseweb="tab-list"]{gap:.28rem;border-bottom:0!important;margin-bottom:.35rem;}
.stTabs [data-baseweb="tab"]{
    background:#071522;border:1px solid #173957;border-radius:10px;color:#bcd0e5;
    padding:.42rem .78rem;height:auto;font-size:12px;font-weight:800;
}
.stTabs [aria-selected="true"]{background:linear-gradient(180deg,#0b3554,#071c2f)!important;border-color:#26b8ff!important;color:white!important;}
.small{font-size:11px;color:var(--muted);line-height:1.28;}
.micro{font-size:9px;color:#9cb0c7;letter-spacing:.12em;text-transform:uppercase;font-weight:900;line-height:1.25;}
.big{font-size:27px;font-weight:950;line-height:1.05;white-space:nowrap;}
.mid{font-size:16px;font-weight:900;line-height:1.2;}
.green{color:var(--green)!important}.red{color:var(--red)!important}.yellow{color:var(--yellow)!important}.cyan{color:#64ddff!important}.purple{color:var(--purple)!important}
.shell{border:1px solid #103a5b;background:linear-gradient(180deg,rgba(8,26,42,.95),rgba(4,14,24,.96));border-radius:15px;padding:10px;box-shadow:0 0 16px rgba(0,0,0,.36);}
.hero{border:1px solid #166a9d;background:linear-gradient(90deg,rgba(5,35,58,.94),rgba(8,13,35,.95));border-radius:14px;padding:8px 10px;box-shadow:0 0 18px rgba(29,189,255,.12);}
.card{border:1px solid #173957;background:linear-gradient(180deg,rgba(9,28,45,.96),rgba(5,14,24,.97));border-radius:14px;padding:11px;min-height:102px;overflow:hidden;}
.card.compact{min-height:78px;padding:9px 10px;}
.section-title{font-size:10px;letter-spacing:.13em;color:#9fb4ca;font-weight:900;text-transform:uppercase;margin-bottom:7px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.value{font-size:17px;font-weight:900;line-height:1.15;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.subvalue{font-size:11px;color:#9cb0c5;line-height:1.3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:3px;}
.metric-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;margin-top:8px;}
.metric-cell{border:1px solid #122f48;background:#06111d;border-radius:9px;padding:6px;min-width:0;}
.metric-label{font-size:8px;letter-spacing:.09em;color:#8197ad;text-transform:uppercase;font-weight:900;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.metric-value{font-size:14px;font-weight:900;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.instrument-strip{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:7px;}
.mini-inst{border:1px solid #1b405e;background:linear-gradient(180deg,#0a1b2a,#06111c);border-radius:11px;padding:8px;min-width:0;transition:.15s ease;}
.mini-inst:hover{border-color:#2fc4ff;box-shadow:0 0 14px rgba(49,198,255,.16);transform:translateY(-1px);}
.mini-inst.selected{border-color:#bb67ff;box-shadow:0 0 14px rgba(187,103,255,.24);}
.mini-symbol{font-size:14px;font-weight:950;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.mini-price{font-size:13px;font-weight:850;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:3px;}
.mini-change{font-size:11px;font-weight:900;margin-top:2px;white-space:nowrap;}
.rowline{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:center;font-size:11px;line-height:1.72;}
.rowline span:first-child{color:#96a9bd;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.rowline b{white-space:nowrap;}
.statusline{display:flex;align-items:center;gap:6px;min-width:0;}
.dot{width:7px;height:7px;border-radius:50%;display:inline-block;flex:0 0 auto;box-shadow:0 0 9px currentColor;}
.chip{display:inline-block;border-radius:999px;padding:2px 7px;font-size:9px;font-weight:900;text-transform:uppercase;letter-spacing:.04em;border:1px solid #244967;background:#081421;white-space:nowrap;}
.chip.green{border-color:#0a7c43;background:#072419;color:var(--green)}.chip.red{border-color:#92333a;background:#2b0b12;color:var(--red)}.chip.yellow{border-color:#8d711d;background:#2d260b;color:var(--yellow)}.chip.blue{border-color:#1d6eab;background:#08223a;color:#73cbff}.chip.purple{border-color:#7541b5;background:#1a0d2d;color:#dfbdff}
.decision-grid{display:grid;grid-template-columns:1.05fr 1fr 1.35fr 1.35fr;gap:8px;}
.decision-card{border:1px solid #173957;background:linear-gradient(180deg,#081927,#05101b);border-radius:12px;padding:9px;min-height:92px;overflow:hidden;}
.decision-card .item{font-size:10.5px;line-height:1.55;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.health-grid{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:4px 8px;font-size:10.5px;line-height:1.5;}
.health-grid div:nth-child(odd){color:#96a9bd;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.health-grid div:nth-child(even){font-weight:900;white-space:nowrap;}
.kicker{font-size:10px;color:#8fa3b8;letter-spacing:.08em;text-transform:uppercase;font-weight:900;}
.footerbar{font-size:10px;color:#7890a8;text-align:center;margin:9px 0 2px;}
[data-testid="stDataFrame"]{font-size:11px!important;}
[data-testid="stExpander"]{border:1px solid #173957!important;border-radius:11px!important;background:#06131f!important;}
[data-testid="stPopover"] button{min-height:32px!important;}
/* v9.5 persistent interactive strip cards + live volume diagnostics */
[data-testid="stExpander"]{margin:.32rem 0!important;border:1px solid #173957!important;border-radius:13px!important;background:linear-gradient(90deg,rgba(7,24,39,.98),rgba(5,14,25,.98))!important;overflow:hidden;box-shadow:0 0 12px rgba(0,0,0,.20);}
[data-testid="stExpander"]:hover{border-color:#2a84b8!important;box-shadow:0 0 14px rgba(49,198,255,.10);}
[data-testid="stExpander"] summary{padding:.62rem .8rem!important;min-height:42px!important;}
[data-testid="stExpander"] summary p{font-size:12px!important;font-weight:850!important;letter-spacing:.01em!important;color:#eaf5ff!important;}
.strip-toolbar{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin:4px 0 8px;}
.strip-pill{display:inline-flex;align-items:center;border:1px solid #1d4566;background:#071623;border-radius:999px;padding:3px 8px;font-size:9px;color:#9eb4c9;font-weight:850;white-space:nowrap;}
.detail-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;margin:6px 0 4px;}
.detail-cell{border:1px solid #132f49;background:#06111c;border-radius:9px;padding:7px 8px;min-width:0;}
.detail-key{font-size:8px;letter-spacing:.09em;color:#7f96ad;text-transform:uppercase;font-weight:900;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.detail-val{font-size:11px;color:#eaf5ff;font-weight:800;line-height:1.3;margin-top:2px;overflow-wrap:anywhere;}
.event-strip{display:grid;grid-template-columns:110px 120px minmax(170px,1.2fr) 90px minmax(180px,1.5fr);gap:8px;align-items:center;border:1px solid #173957;background:linear-gradient(90deg,#081827,#05101b);border-radius:12px;padding:8px 10px;margin:6px 0;}
.event-strip .ev-date{font-weight:900;color:#dff4ff;font-size:11px}.event-strip .ev-time{font-weight:850;color:#a8bed2;font-size:10px}.event-strip .ev-name{font-weight:900;font-size:11px}.event-strip .ev-region{font-size:9px;color:#8fa3b8;text-transform:uppercase;font-weight:900}.event-strip .ev-impact{font-size:10px;color:#9fb4ca;line-height:1.25;}
.calendar-note{border:1px solid #143b5a;background:#061521;border-radius:11px;padding:8px 10px;font-size:10px;color:#94abc1;margin-bottom:7px;}
@media(max-width:1200px){
    .instrument-strip{grid-template-columns:repeat(3,minmax(0,1fr));}
    .decision-grid{grid-template-columns:repeat(2,minmax(0,1fr));}
    .big{font-size:23px}.mid{font-size:14px}
    .detail-grid{grid-template-columns:repeat(2,minmax(0,1fr));}
    .event-strip{grid-template-columns:90px 90px minmax(150px,1fr);}
    .event-strip .ev-region,.event-strip .ev-impact{display:none;}
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


@dataclass(frozen=True)
class Instrument:
    symbol: str
    name: str
    category: str
    role: str
    related: tuple[str, ...]
    driver: str = ""


UNIVERSE: list[Instrument] = [
    Instrument("NQ=F", "Nasdaq Futures", "Indexes", "primary all-session NAS driver", ("QQQ", "^NDX", "SMH", "NVDA", "RSP", "^VIX"), "growth risk"),
    Instrument("ES=F", "S&P Futures", "Indexes", "broad futures driver", ("SPY", "^GSPC", "RSP", "^VIX"), "broad risk"),
    Instrument("QQQ", "Nasdaq ETF", "Indexes", "ETF / extended proxy", ("NQ=F", "^NDX", "SMH", "NVDA", "RSP"), "growth risk"),
    Instrument("SPY", "S&P 500 ETF", "Indexes", "ETF proxy", ("ES=F", "^GSPC", "RSP", "HYG"), "broad risk"),
    Instrument("^GSPC", "S&P 500 Cash", "Indexes", "cash index reference", ("SPY", "ES=F", "RSP"), "cash reference"),
    Instrument("^NDX", "Nasdaq 100 Cash", "Indexes", "NY cash reference", ("NQ=F", "QQQ", "SMH"), "cash reference"),
    Instrument("RSP", "Equal Weight S&P 500", "Internals", "breadth proxy", ("SPY", "^GSPC", "HYG"), "breadth"),
    Instrument("DIA", "Dow ETF", "Indexes", "Dow ETF proxy", ("YM=F", "^DJI"), "cyclicals"),
    Instrument("YM=F", "Dow Futures", "Indexes", "Dow futures", ("DIA", "^DJI"), "cyclicals"),
    Instrument("^DJI", "Dow Cash", "Indexes", "Dow cash reference", ("DIA", "YM=F"), "cash reference"),
    Instrument("IWM", "Russell ETF", "Indexes", "small-cap ETF", ("RTY=F", "^RUT"), "small caps"),
    Instrument("RTY=F", "Russell Futures", "Indexes", "small-cap futures", ("IWM", "^RUT"), "small caps"),
    Instrument("^RUT", "Russell 2000 Cash", "Indexes", "small-cap cash reference", ("IWM", "RTY=F"), "small caps"),
    Instrument("DX-Y.NYB", "US Dollar Index", "Dollar", "DXY cash proxy", ("UUP", "EURUSD=X", "JPY=X", "^TNX"), "liquidity"),
    Instrument("UUP", "US Dollar ETF", "Dollar", "ETF proxy", ("DX-Y.NYB", "QQQ", "GC=F"), "liquidity"),
    Instrument("^TNX", "US 10Y Yield", "Bonds", "yield proxy", ("TLT", "IEF", "QQQ", "XLRE"), "rate pressure"),
    Instrument("TLT", "20Y Treasury ETF", "Bonds", "long bond proxy", ("^TNX", "IEF", "XLRE"), "duration"),
    Instrument("IEF", "7-10Y Treasury ETF", "Bonds", "intermediate duration", ("^TNX", "TLT"), "duration"),
    Instrument("HYG", "High Yield Credit", "Credit", "credit risk proxy", ("JNK", "LQD", "SPY"), "credit"),
    Instrument("JNK", "Junk Bond ETF", "Credit", "credit risk proxy", ("HYG", "LQD"), "credit"),
    Instrument("LQD", "Investment Grade Credit", "Credit", "IG credit proxy", ("HYG", "TLT"), "credit"),
    Instrument("^VIX", "VIX", "Volatility", "fear / volatility proxy", ("SPY", "QQQ", "^VVIX", "^VIX9D"), "volatility"),
    Instrument("^VVIX", "VVIX", "Volatility", "vol-of-vol proxy", ("^VIX",), "volatility"),
    Instrument("^VIX9D", "VIX 9D", "Volatility", "event volatility", ("^VIX",), "event vol"),
    Instrument("GC=F", "Gold Futures", "Commodities", "gold futures", ("GLD", "GDX", "DX-Y.NYB", "^TNX"), "safety / inflation"),
    Instrument("GLD", "Gold ETF", "Commodities", "gold ETF proxy", ("GC=F", "GDX"), "safety"),
    Instrument("GDX", "Gold Miners", "Commodities", "gold miner equity proxy", ("GC=F", "GLD"), "metals equity"),
    Instrument("CL=F", "Crude Oil Futures", "Commodities", "oil futures", ("USO", "XLE", "OIH"), "inflation / energy"),
    Instrument("USO", "Oil ETF", "Commodities", "oil ETF proxy", ("CL=F", "XLE"), "energy"),
    Instrument("OIH", "Oil Services", "Commodities", "oil services proxy", ("CL=F", "XLE"), "energy"),
    Instrument("SI=F", "Silver Futures", "Commodities", "silver futures", ("SLV", "GC=F"), "metals"),
    Instrument("SLV", "Silver ETF", "Commodities", "silver ETF proxy", ("SI=F", "GC=F"), "metals"),
    Instrument("HG=F", "Copper Futures", "Commodities", "copper futures", ("CPER", "XLB", "XME"), "growth / inflation"),
    Instrument("CPER", "Copper ETF", "Commodities", "copper proxy", ("HG=F", "XME"), "growth / inflation"),
    Instrument("NG=F", "Natural Gas Futures", "Commodities", "gas futures", ("UNG", "XLE"), "energy"),
    Instrument("UNG", "Natural Gas ETF", "Commodities", "gas ETF proxy", ("NG=F", "XLE"), "energy"),
    Instrument("BTC-USD", "Bitcoin", "Crypto", "crypto spot", ("ETH-USD", "COIN", "MSTR"), "liquidity risk"),
    Instrument("ETH-USD", "Ethereum", "Crypto", "crypto spot", ("BTC-USD", "COIN"), "liquidity risk"),
    Instrument("COIN", "Coinbase", "Crypto", "crypto equity proxy", ("BTC-USD", "ETH-USD", "MSTR"), "crypto risk"),
    Instrument("MSTR", "Strategy", "Crypto", "bitcoin equity proxy", ("BTC-USD", "COIN"), "crypto beta"),
    Instrument("NVDA", "Nvidia", "AI / Tech", "AI leadership", ("SMH", "SOXX", "QQQ", "AMD", "AVGO"), "AI leadership"),
    Instrument("MSFT", "Microsoft", "AI / Tech", "AI / cloud leader", ("QQQ", "XLK", "AMZN", "GOOGL"), "AI / cloud"),
    Instrument("AAPL", "Apple", "AI / Tech", "mega-cap tech", ("QQQ", "XLK"), "mega-cap"),
    Instrument("AMD", "AMD", "AI / Tech", "semiconductor", ("SMH", "SOXX", "NVDA"), "semis"),
    Instrument("AVGO", "Broadcom", "AI / Tech", "semiconductor", ("SMH", "SOXX", "NVDA"), "semis"),
    Instrument("SMH", "Semiconductor ETF", "AI / Tech", "semiconductor ETF", ("NVDA", "AMD", "AVGO", "QQQ"), "semis"),
    Instrument("SOXX", "Semiconductor ETF", "AI / Tech", "semiconductor ETF", ("SMH", "NVDA"), "semis"),
    Instrument("XLK", "Technology", "Sectors", "sector ETF", ("QQQ", "MSFT", "AAPL"), "sector"),
    Instrument("XLF", "Financials", "Sectors", "sector ETF", ("KRE", "KBE", "HYG"), "sector"),
    Instrument("XLE", "Energy", "Sectors", "sector ETF", ("CL=F", "XOP", "OIH"), "sector"),
    Instrument("XLV", "Healthcare", "Healthcare / Science", "sector ETF", ("IBB", "XBI", "PJP", "IHI"), "defensive / science"),
    Instrument("XLI", "Industrials", "Sectors", "sector ETF", ("IYT", "ITA"), "sector"),
    Instrument("XLY", "Consumer Discretionary", "Sectors", "sector ETF", ("XRT", "AMZN", "TSLA"), "sector"),
    Instrument("XLP", "Consumer Staples", "Sectors", "defensive sector", ("XLV", "XLU"), "defensive"),
    Instrument("XLU", "Utilities", "Sectors", "defensive sector", ("TLT", "XLRE"), "defensive / rates"),
    Instrument("XLB", "Materials", "Sectors", "sector ETF", ("HG=F", "XME"), "materials"),
    Instrument("XLRE", "Real Estate", "Real Estate", "sector ETF", ("VNQ", "IYR", "ITB", "XHB", "^TNX"), "rates / housing"),
    Instrument("XLC", "Communication Services", "Sectors", "sector ETF", ("META", "GOOGL", "NFLX"), "sector"),
    Instrument("VNQ", "REITs", "Real Estate", "REIT ETF", ("XLRE", "IYR", "^TNX"), "real estate"),
    Instrument("IYR", "US Real Estate", "Real Estate", "real-estate ETF", ("XLRE", "VNQ"), "real estate"),
    Instrument("ITB", "Homebuilders", "Real Estate", "homebuilder ETF", ("XHB", "^TNX"), "housing"),
    Instrument("XHB", "Homebuilders", "Real Estate", "homebuilder ETF", ("ITB", "^TNX"), "housing"),
    Instrument("IBB", "Biotech", "Healthcare / Science", "biotech ETF", ("XBI", "XLV", "ARKG"), "biotech / science"),
    Instrument("XBI", "Biotech", "Healthcare / Science", "equal-weight biotech ETF", ("IBB", "ARKG"), "biotech / science"),
    Instrument("ARKG", "Genomics", "Healthcare / Science", "genomics ETF", ("XBI", "IBB"), "science innovation"),
    Instrument("IHI", "Medical Devices", "Healthcare / Science", "medical devices ETF", ("XLV",), "med devices"),
    Instrument("PJP", "Pharma", "Healthcare / Science", "pharma ETF", ("XLV",), "pharma"),
    Instrument("ITA", "Aerospace & Defense ETF", "Defense / Aero", "aerospace / defense basket", ("XAR", "LMT", "RTX", "NOC", "GD"), "defense / geopolitical"),
    Instrument("XAR", "Aerospace & Defense ETF", "Defense / Aero", "equal-weight aerospace / defense", ("ITA", "LMT", "RTX", "NOC"), "defense / geopolitical"),
    Instrument("LMT", "Lockheed Martin", "Defense / Aero", "defense prime", ("ITA", "XAR", "RTX", "NOC"), "defense"),
    Instrument("RTX", "RTX", "Defense / Aero", "aerospace / defense prime", ("ITA", "XAR", "LMT"), "defense / aero"),
    Instrument("NOC", "Northrop Grumman", "Defense / Aero", "defense prime", ("ITA", "XAR", "LMT"), "defense"),
    Instrument("GD", "General Dynamics", "Defense / Aero", "defense prime", ("ITA", "XAR", "LMT"), "defense"),
    Instrument("BA", "Boeing", "Defense / Aero", "commercial / defense aerospace", ("ITA", "XAR", "RTX"), "aerospace"),
    Instrument("TAN", "Solar", "Clean Energy", "solar ETF", ("ICLN", "XLU"), "clean energy / rates"),
    Instrument("ICLN", "Clean Energy", "Clean Energy", "clean-energy ETF", ("TAN", "URA", "LIT"), "clean energy"),
    Instrument("URA", "Uranium", "Clean Energy", "uranium ETF", ("CCJ",), "nuclear / energy"),
    Instrument("LIT", "Lithium Batteries", "Clean Energy", "battery-chain ETF", ("TSLA",), "battery chain"),
    Instrument("KRE", "Regional Banks", "Credit", "bank stress proxy", ("KBE", "XLF", "HYG"), "banks / credit"),
    Instrument("KBE", "Banks", "Credit", "bank ETF", ("KRE", "XLF"), "banks / credit"),
    Instrument("EURUSD=X", "EUR/USD", "Currencies", "currency pair", ("DX-Y.NYB", "UUP"), "FX"),
    Instrument("JPY=X", "USD/JPY", "Currencies", "currency pair", ("DX-Y.NYB", "^TNX"), "FX / rates"),
    Instrument("CAD=X", "USD/CAD", "Currencies", "currency pair", ("CL=F", "DX-Y.NYB"), "FX / energy"),
    Instrument("EWC", "Canada", "Global Markets", "country ETF", ("CAD=X", "CL=F"), "global"),
    Instrument("EWJ", "Japan", "Global Markets", "country ETF", ("JPY=X", "DX-Y.NYB"), "global"),
    Instrument("EWG", "Germany", "Global Markets", "country ETF", ("EURUSD=X",), "global"),
    Instrument("FXI", "China Large Cap", "Global Markets", "China ETF", ("EEM", "HG=F"), "global / China"),
    Instrument("INDA", "India", "Global Markets", "country ETF", ("EEM",), "global"),
    Instrument("EEM", "Emerging Markets", "Global Markets", "EM ETF", ("DX-Y.NYB", "FXI"), "global / liquidity"),
]

SYMBOLS = list(dict.fromkeys(x.symbol for x in UNIVERSE))
LOOKUP = {x.symbol.upper(): x for x in UNIVERSE}
ALIASES = {
    "NDX": "NQ=F", "NAS": "NQ=F", "NASDAQ": "NQ=F", "NAS100": "NQ=F", "NQ": "NQ=F",
    "SPX": "ES=F", "S&P": "ES=F", "SP500": "ES=F", "ES": "ES=F",
    "GOLD": "GC=F", "GC": "GC=F", "OIL": "CL=F", "CL": "CL=F", "DXY": "DX-Y.NYB", "VIX": "^VIX",
    "REAL ESTATE": "XLRE", "HEALTHCARE": "XLV", "SCIENCE": "IBB", "BIOTECH": "XBI", "AI": "NVDA",
    "DEFENSE": "ITA", "DEFENCE": "ITA", "AEROSPACE": "ITA", "AERO": "ITA",
}
CORE = ["NQ=F", "ES=F", "QQQ", "SPY", "DX-Y.NYB", "^TNX", "^VIX", "GC=F", "CL=F", "BTC-USD", "NVDA", "SMH", "RSP", "HYG"]



# Instruments that do not publish reliable native traded volume use a clearly-labelled
# liquid proxy. The displayed value is never silently represented as native volume.
VOLUME_PROXY_MAP = {
    "^NDX": "NQ=F",
    "^GSPC": "ES=F",
    "^DJI": "YM=F",
    "^RUT": "RTY=F",
    "DX-Y.NYB": "UUP",
    "^TNX": "TLT",
    "^VIX": "SPY",
    "^VVIX": "SPY",
    "^VIX9D": "SPY",
    "EURUSD=X": "UUP",
    "JPY=X": "UUP",
    "CAD=X": "UUP",
}


def now_et() -> datetime:
    return datetime.now(TZ)


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
        return st.session_state.get("selected_symbol", "NQ=F")
    if q in LOOKUP:
        return q
    if q in ALIASES:
        return ALIASES[q]
    for key, value in ALIASES.items():
        if key in q:
            return value
    for sym, inst in LOOKUP.items():
        hay = f"{inst.symbol} {inst.name} {inst.category} {inst.role}".upper()
        if q in hay:
            return inst.symbol
    return st.session_state.get("selected_symbol", "NQ=F")


def fallback_row(sym: str, snapshot_iso: str) -> dict:
    seed = abs(hash(sym)) % 1000
    base = {
        "NQ=F": 18760, "ES=F": 5852, "QQQ": 472, "SPY": 582, "DX-Y.NYB": 104.6, "^TNX": 4.54,
        "^VIX": 22.8, "GC=F": 3336, "CL=F": 61.9, "BTC-USD": 107842, "NVDA": 218, "SMH": 561,
        "RSP": 177, "HYG": 79.5,
    }.get(sym, 50 + seed / 8)
    pct = ((seed % 31) - 15) / 10
    return {
        "symbol": sym, "latest_close": float(base), "change_pct": float(pct), "session_pct": float(pct * 1.1),
        # Fallback rows must never manufacture traded volume.
        "volume": np.nan, "volume_1m": np.nan, "session_volume": np.nan,
        "relative_volume": np.nan, "volume_delta_pct": np.nan,
        "volume_source": "N/A · fallback", "volume_proxy_symbol": "",
        "updated": snapshot_iso, "source": "fallback", "source_ok": False,
    }


def _volume_metrics(volume: pd.Series) -> dict:
    """Return robust volume fields without treating a zero latest bar as zero activity."""
    if volume is None or len(volume) == 0:
        return {"volume_1m": np.nan, "session_volume": np.nan, "relative_volume": np.nan, "volume_delta_pct": np.nan}
    v = pd.to_numeric(volume, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    positive = v[v > 0]
    if positive.empty:
        return {"volume_1m": np.nan, "session_volume": np.nan, "relative_volume": np.nan, "volume_delta_pct": np.nan}
    latest = float(positive.iloc[-1])
    session = float(positive.sum())
    prior_window = positive.iloc[-21:-1] if len(positive) > 1 else pd.Series(dtype=float)
    baseline = float(prior_window.median()) if len(prior_window) else np.nan
    relative = float(latest / baseline) if baseline and np.isfinite(baseline) and baseline > 0 else np.nan
    previous = float(positive.iloc[-2]) if len(positive) > 1 else np.nan
    delta = ((latest / previous) - 1.0) * 100.0 if previous and np.isfinite(previous) and previous > 0 else np.nan
    return {"volume_1m": latest, "session_volume": session, "relative_volume": relative, "volume_delta_pct": delta}


def _apply_volume_proxies(df: pd.DataFrame) -> pd.DataFrame:
    """Fill unavailable native volume from an explicit proxy and label the source."""
    out = df.copy()
    if out.empty or "symbol" not in out.columns:
        return out
    by_symbol = {str(r["symbol"]): r for _, r in out.iterrows()}
    metric_cols = ["volume_1m", "session_volume", "relative_volume", "volume_delta_pct"]
    for idx, row in out.iterrows():
        native = row.get("session_volume", np.nan)
        if pd.notna(native) and float(native) > 0:
            out.at[idx, "volume"] = float(native)
            out.at[idx, "volume_source"] = "Actual"
            out.at[idx, "volume_proxy_symbol"] = ""
            continue
        sym = str(row.get("symbol", ""))
        proxy_sym = VOLUME_PROXY_MAP.get(sym)
        proxy = by_symbol.get(proxy_sym) if proxy_sym else None
        if proxy is not None and pd.notna(proxy.get("session_volume", np.nan)) and float(proxy.get("session_volume", 0)) > 0:
            for col in metric_cols:
                out.at[idx, col] = proxy.get(col, np.nan)
            out.at[idx, "volume"] = proxy.get("session_volume", np.nan)
            out.at[idx, "volume_source"] = f"Proxy · {proxy_sym}"
            out.at[idx, "volume_proxy_symbol"] = proxy_sym
        else:
            out.at[idx, "volume"] = np.nan
            out.at[idx, "volume_source"] = "N/A"
            out.at[idx, "volume_proxy_symbol"] = proxy_sym or ""
    return out


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_universe_snapshot(symbols: tuple[str, ...]) -> pd.DataFrame:
    """One synchronized universe snapshot. All dashboard layers derive from this exact frame."""
    snapshot_iso = now_et().isoformat()
    rows: list[dict] = []
    if yf is not None:
        try:
            data = yf.download(
                list(symbols), period="1d", interval="1m", group_by="ticker", progress=False,
                prepost=True, threads=True, auto_adjust=False,
            )
            snapshot_iso = now_et().isoformat()
            for sym in symbols:
                try:
                    frame = data.copy() if len(symbols) == 1 else data[sym].copy()
                    frame = frame.dropna(how="all")
                    if frame.empty:
                        raise ValueError("empty")
                    close = frame["Close"].dropna()
                    volume = frame["Volume"] if "Volume" in frame else pd.Series(dtype=float)
                    if close.empty:
                        raise ValueError("no close")
                    last = float(close.iloc[-1])
                    prev = float(close.iloc[-2]) if len(close) > 1 else last
                    first = float(close.iloc[0])
                    pct = ((last / prev) - 1) * 100 if prev else 0.0
                    session_pct = ((last / first) - 1) * 100 if first else 0.0
                    vm = _volume_metrics(volume)
                    rows.append({
                        "symbol": sym, "latest_close": last, "change_pct": pct, "session_pct": session_pct,
                        "volume": vm["session_volume"], **vm,
                        "volume_source": "Actual" if pd.notna(vm["session_volume"]) else "N/A",
                        "volume_proxy_symbol": "",
                        "updated": snapshot_iso, "source": "yfinance", "source_ok": True,
                    })
                except Exception:
                    rows.append(fallback_row(sym, snapshot_iso))
            return _apply_volume_proxies(pd.DataFrame(rows))
        except Exception:
            pass
    snapshot_iso = now_et().isoformat()
    return _apply_volume_proxies(pd.DataFrame([fallback_row(sym, snapshot_iso) for sym in symbols]))


def score_for(sym: str, pct: float, category: str = "") -> float:
    sym = sym.upper()
    mult = 1.0
    if sym in {"DX-Y.NYB", "UUP", "^TNX", "^VIX", "^VVIX", "^VIX9D"} or category in {"Dollar", "Bonds", "Volatility"}:
        mult = -1.0
    elif category == "Commodities":
        mult = 0.35
    return float(np.clip(float(pct) * 26 * mult, -100, 100))


def state_for(score: float) -> str:
    if score <= -60:
        return "Pressure"
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


def quality_for(score: float) -> str:
    a = abs(float(score))
    if a >= 65:
        return "Strong"
    if a >= 30:
        return "Medium"
    return "Weak/Mixed"


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    meta = []
    for sym in out["symbol"]:
        inst = LOOKUP.get(sym.upper(), Instrument(sym, sym, "Other", "instrument", tuple()))
        meta.append({"name": inst.name, "category": inst.category, "role": inst.role, "driver": inst.driver})
    out = pd.concat([out, pd.DataFrame(meta)], axis=1)
    out["score"] = out.apply(lambda r: score_for(r["symbol"], r["change_pct"], r["category"]), axis=1)
    out["state"] = out["score"].apply(state_for)
    out["quality"] = out["score"].apply(quality_for)
    out["age_sec"] = out["updated"].apply(age_from_iso)
    out["freshness"] = out["age_sec"].apply(lambda x: health_state(x)[0])
    return out


def age_from_iso(value: str) -> int:
    try:
        dt = datetime.fromisoformat(str(value))
        return max(0, int((now_et() - dt.astimezone(TZ)).total_seconds()))
    except Exception:
        return 999


def health_state(age: int) -> tuple[str, str]:
    age = int(age)
    if age <= 15:
        return "LIVE", "green"
    if age <= MAX_DATA_AGE_SECONDS:
        return "CURRENT", "yellow"
    return "STALE", "red"


def get_row(df: pd.DataFrame, sym: str) -> pd.Series:
    hit = df[df["symbol"].str.upper() == sym.upper()]
    if len(hit):
        return hit.iloc[0]
    return enrich(pd.DataFrame([fallback_row(sym, now_et().isoformat())])).iloc[0]


def related_symbols(sym: str) -> list[str]:
    inst = LOOKUP.get(sym.upper())
    base = [sym] + (list(inst.related) if inst else [])
    if sym in {"NQ=F", "QQQ", "^NDX"}:
        base += ["NQ=F", "QQQ", "^NDX", "SMH", "NVDA", "RSP", "^VIX", "DX-Y.NYB", "^TNX"]
    elif sym in {"ES=F", "SPY", "^GSPC"}:
        base += ["ES=F", "SPY", "^GSPC", "RSP", "HYG", "^VIX", "DX-Y.NYB", "^TNX"]
    elif sym in {"GC=F", "GLD", "GDX"}:
        base += ["GC=F", "GLD", "GDX", "DX-Y.NYB", "^TNX", "^VIX"]
    elif sym in {"CL=F", "USO", "OIH"}:
        base += ["CL=F", "USO", "XLE", "OIH", "DX-Y.NYB"]
    elif sym in {"XLRE", "VNQ", "IYR", "ITB", "XHB"}:
        base += ["XLRE", "VNQ", "IYR", "ITB", "XHB", "^TNX", "TLT", "KRE"]
    elif sym in {"XLV", "IBB", "XBI", "ARKG", "PJP", "IHI"}:
        base += ["XLV", "IBB", "XBI", "ARKG", "PJP", "IHI", "^TNX", "SPY"]
    elif sym in {"ITA", "XAR", "LMT", "RTX", "NOC", "GD", "BA"}:
        base += ["ITA", "XAR", "LMT", "RTX", "NOC", "GD", "BA", "XLI", "^VIX"]
    out: list[str] = []
    for item in base:
        if item in SYMBOLS and item not in out:
            out.append(item)
    return out[:10]


def compute_core_state(df: pd.DataFrame) -> dict:
    def s(sym: str) -> float:
        return float(get_row(df, sym)["score"])
    macro = np.mean([s("NQ=F"), s("ES=F"), s("QQQ"), s("SPY"), s("RSP"), s("HYG"), s("DX-Y.NYB"), s("^TNX"), s("^VIX")])
    breadth = np.mean([s("RSP"), s("HYG"), s("SPY")])
    trend = np.mean([s("NQ=F"), s("ES=F"), s("QQQ"), s("SPY")])
    momentum = np.mean([s("NVDA"), s("SMH"), s("QQQ")])
    vol = np.mean([s("^VIX"), s("^VIX9D")])
    risk = np.mean([macro, breadth, trend, momentum])
    credit = np.mean([s("HYG"), s("JNK"), s("LQD")])
    return {"macro": macro, "breadth": breadth, "trend": trend, "momentum": momentum, "volatility": vol, "risk": risk, "credit": credit}


def current_session(dt: datetime | None = None) -> dict:
    dt = dt or now_et()
    mins = dt.hour * 60 + dt.minute
    sessions = {
        "Asia": (18 * 60, 3 * 60), "London": (3 * 60, 9 * 60 + 30), "New York": (9 * 60 + 30, 16 * 60),
        "After-Hours": (16 * 60, 20 * 60), "Globex": (18 * 60, 17 * 60), "Crypto 24/7": (0, 24 * 60),
    }
    status = {}
    for name, (start, end) in sessions.items():
        open_ = start <= mins < end if start < end else mins >= start or mins < end
        status[name] = "Open" if open_ else "Closed"
    active = "New York" if status["New York"] == "Open" else "After-Hours" if status["After-Hours"] == "Open" else "London" if status["London"] == "Open" else "Asia" if status["Asia"] == "Open" else "Globex"
    return {"active": active, "status": status}


def cause_from(df: pd.DataFrame, selected_symbol: str) -> dict:
    dxy, ten, vix = get_row(df, "DX-Y.NYB"), get_row(df, "^TNX"), get_row(df, "^VIX")
    smh, hyg, selected = get_row(df, "SMH"), get_row(df, "HYG"), get_row(df, selected_symbol)
    candidates = [
        (abs(float(dxy["score"])), "Dollar Strength" if float(dxy["score"]) < 0 else "Dollar Weakness", "DXY / UUP"),
        (abs(float(ten["score"])), "10Y Yield Pressure" if float(ten["score"]) < 0 else "Yield Relief", "rates / duration"),
        (abs(float(vix["score"])), "Volatility Expansion" if float(vix["score"]) < 0 else "Volatility Cooling", "VIX / hedge"),
        (abs(float(smh["score"])), "Semiconductor Weakness" if float(smh["score"]) < 0 else "Semiconductor Support", "SMH / SOXX"),
        (abs(float(hyg["score"])), "Credit Stress" if float(hyg["score"]) < 0 else "Credit Support", "HYG / JNK / LQD"),
    ]
    c = max(candidates, key=lambda item: item[0])
    downside_causes = {"Dollar Strength", "10Y Yield Pressure", "Volatility Expansion", "Credit Stress", "Semiconductor Weakness"}
    target = "Downside" if float(selected["score"]) < -20 or c[1] in downside_causes else "Upside / Support"
    return {
        "cause": c[1], "detail": c[2], "strength": c[0], "target": target,
        "effect": "Pressure / defense" if target == "Downside" else "Support / continuation",
    }


def gauge(label: str, value: float) -> go.Figure:
    val = max(-100, min(100, float(value)))
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=val,
        number={"font": {"size": 18, "color": "#eaf5ff"}},
        title={"text": f"<b>{label}</b>", "font": {"size": 11, "color": "#dceeff"}},
        gauge={
            "axis": {"range": [-100, 100], "tickfont": {"size": 8}, "tickcolor": "#789"},
            "bar": {"color": "#f7d14a"}, "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0,
            "steps": [
                {"range": [-100, -40], "color": "rgba(255,82,96,.38)"},
                {"range": [-40, 30], "color": "rgba(255,216,77,.18)"},
                {"range": [30, 100], "color": "rgba(54,249,138,.28)"},
            ],
        },
    ))
    fig.update_layout(height=128, margin=dict(l=4, r=4, t=18, b=2), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


def chip_html(text: str, tone: str = "blue") -> str:
    return f"<span class='chip {tone}'>{text}</span>"


def card_html(title: str, main: str, sub: str = "", tone: str = "blue", chip: str | None = None) -> str:
    chip_part = f"<div style='margin-top:6px'>{chip_html(chip, tone)}</div>" if chip else ""
    return f"<div class='card compact'><div class='section-title'>{title}</div><div class='value {tone}'>{main}</div><div class='subvalue'>{sub}</div>{chip_part}</div>"


def mini_instrument_html(row: pd.Series, selected: bool = False) -> str:
    pct = float(row["change_pct"])
    tone = "green" if pct > 0 else "red" if pct < 0 else "yellow"
    cls = "mini-inst selected" if selected else "mini-inst"
    return (
        f"<div class='{cls}'><div class='mini-symbol'>{row['symbol']}</div>"
        f"<div class='mini-price'>{short_num(row['latest_close'])}</div>"
        f"<div class='mini-change {tone}'>{format_change(pct)}</div></div>"
    )



def _display_value(key: str, value) -> str:
    if value is None:
        return "—"
    try:
        if pd.isna(value):
            return "—"
    except Exception:
        pass
    if isinstance(value, (np.floating, float)):
        if key in {"change_pct", "session_pct"}:
            mode = st.session_state.get("global_change_format", "Percentage")
            if mode == "Decimal":
                return f"{float(value):+.6f}"
            return f"{float(value):+.4f}%"
        if key == "score":
            return format_score(float(value))
        if key in {"volume", "volume_1m", "session_volume"}:
            return f"{float(value):,.0f}"
        if key == "relative_volume":
            return f"{float(value):.2f}×"
        if key == "volume_delta_pct":
            return f"{float(value):+.2f}%"
        return short_num(float(value))
    if isinstance(value, (np.integer, int)):
        return f"{int(value):,}"
    if isinstance(value, (np.bool_, bool)):
        return "Yes" if bool(value) else "No"
    return str(value)


def format_score(value: float) -> str:
    mode = st.session_state.get("global_score_format", "Percentage")
    if mode == "Percentage":
        return f"{float(value):+.2f}%"
    if mode == "Whole":
        return f"{float(value):+.0f}"
    return f"{float(value):+.3f}"


def format_change(value: float) -> str:
    mode = st.session_state.get("global_change_format", "Percentage")
    if mode == "Decimal":
        return f"{float(value):+.6f}"
    return f"{float(value):+.4f}%"


def _table_column_config(columns: list[str]) -> dict:
    cfg = {}
    score_mode = st.session_state.get("global_score_format", "Percentage")
    change_mode = st.session_state.get("global_change_format", "Percentage")
    for col in columns:
        low = str(col).lower()
        if low == "score":
            fmt = "%.2f%%" if score_mode == "Percentage" else "%.0f" if score_mode == "Whole" else "%.3f"
            cfg[col] = st.column_config.NumberColumn(str(col), format=fmt)
        elif low in {"change_pct", "session_pct", "δ %", "change %", "change"}:
            fmt = "%.4f%%" if change_mode == "Percentage" else "%.6f"
            cfg[col] = st.column_config.NumberColumn(str(col), format=fmt)
        elif low in {"volume", "volume_1m", "session_volume"}:
            cfg[col] = st.column_config.NumberColumn(str(col), format="%.0f")
        elif low == "relative_volume":
            cfg[col] = st.column_config.NumberColumn(str(col), format="%.2f×")
        elif low == "volume_delta_pct":
            cfg[col] = st.column_config.NumberColumn(str(col), format="%+.2f%%")
        elif low in {"age_sec", "age sec"}:
            cfg[col] = st.column_config.NumberColumn(str(col), format="%d")
    return cfg


def _display_override_store() -> dict:
    if "instrument_display_overrides" not in st.session_state:
        st.session_state.instrument_display_overrides = {}
    return st.session_state.instrument_display_overrides


def apply_row_display_overrides(row: pd.Series) -> pd.Series:
    """Apply persistent UI-only overrides for a symbol without mutating the feed snapshot."""
    effective = row.copy()
    symbol = str(row.get("symbol", ""))
    overrides = _display_override_store().get(symbol, {})
    for key, value in overrides.items():
        if key in effective.index:
            effective[key] = value
    return effective


def apply_df_display_overrides(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty or "symbol" not in out.columns:
        return out
    for idx, row in out.iterrows():
        effective = apply_row_display_overrides(row)
        for col in out.columns:
            if col in effective.index:
                out.at[idx, col] = effective[col]
    return out


def save_symbol_display_overrides(symbol: str, baseline: pd.Series, edited: pd.Series, columns: list[str]) -> bool:
    """Persist changed display fields for a symbol. Returns True when state changed."""
    store = _display_override_store()
    current = dict(store.get(symbol, {}))
    changed = False
    changed_cols: set[str] = set()
    for col in columns:
        if col == "symbol" or col not in edited.index:
            continue
        new_val = edited[col]
        old_val = baseline.get(col, np.nan)
        same = False
        try:
            same = (pd.isna(new_val) and pd.isna(old_val)) or (new_val == old_val)
        except Exception:
            same = str(new_val) == str(old_val)
        if not same:
            if current.get(col, object()) != new_val:
                current[col] = new_val
                changed = True
                changed_cols.add(col)
    if changed:
        # Keep score-dependent display fields coherent. Manual state/quality edits still win.
        if "score" in changed_cols:
            try:
                score = float(current["score"])
                if "state" not in changed_cols:
                    current["state"] = state_for(score)
                if "quality" not in changed_cols:
                    current["quality"] = quality_for(score)
            except Exception:
                pass
        store[symbol] = current
        st.session_state.instrument_display_overrides = store
    return changed


def _set_global_score_format(value: str) -> None:
    # Widget callbacks run before the script is rebuilt. This is intentionally
    # used instead of mutating a selectbox-owned session_state key after that
    # selectbox has already been instantiated in the current run.
    st.session_state["global_score_format"] = value


def _set_global_change_format(value: str) -> None:
    st.session_state["global_change_format"] = value


def _reset_symbol_display_overrides(symbol: str, editor_key: str) -> None:
    store = dict(_display_override_store())
    store.pop(symbol, None)
    st.session_state.instrument_display_overrides = store
    # Callback executes before the next render, so removing editor state here is safe.
    st.session_state.pop(editor_key, None)


def _format_buttons(key_prefix: str) -> None:
    st.caption("Display format · applies globally across every module")
    a, b, c, d, e = st.columns(5)
    with a:
        st.button(
            "Score %",
            key=f"{key_prefix}_score_pct",
            on_click=_set_global_score_format,
            args=("Percentage",),
            use_container_width=True,
        )
    with b:
        st.button(
            "Score dec",
            key=f"{key_prefix}_score_dec",
            on_click=_set_global_score_format,
            args=("Decimal",),
            use_container_width=True,
        )
    with c:
        st.button(
            "Score whole",
            key=f"{key_prefix}_score_whole",
            on_click=_set_global_score_format,
            args=("Whole",),
            use_container_width=True,
        )
    with d:
        st.button(
            "Change %",
            key=f"{key_prefix}_chg_pct",
            on_click=_set_global_change_format,
            args=("Percentage",),
            use_container_width=True,
        )
    with e:
        st.button(
            "Change dec",
            key=f"{key_prefix}_chg_dec",
            on_click=_set_global_change_format,
            args=("Decimal",),
            use_container_width=True,
        )


def render_editable_table(df: pd.DataFrame, key: str, *, disabled: list[str] | None = None) -> pd.DataFrame:
    """Interactive working table. Edits are local to the UI and do not mutate the live market snapshot."""
    return st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key=key,
        disabled=disabled or [],
        column_config=_table_column_config(list(df.columns)),
    )


def strip_summary(row: pd.Series) -> str:
    pct = float(row.get("change_pct", 0.0))
    return (
        f"{row.get('symbol','—')}  ·  {row.get('name','—')}   |   "
        f"{short_num(row.get('latest_close'))}   {format_change(pct)}   ·   "
        f"{row.get('state','—')}   ·   {int(row.get('age_sec',999)):02d}s"
    )


def render_strip_cards(view: pd.DataFrame, key_prefix: str, raw_columns: list[str] | None = None) -> None:
    """Persistent strip cards. Open state and display edits survive timed/manual refreshes."""
    if view.empty:
        st.info("No instruments match this filter.")
        return
    mode = st.radio(
        "View",
        ["Strip Cards", "Editable Table", "Raw Table"],
        index=0,
        horizontal=True,
        key=f"{key_prefix}_view_mode",
        label_visibility="collapsed",
    )
    cols = raw_columns or [c for c in view.columns if not str(c).startswith("_")]
    cols = [c for c in cols if c in view.columns]

    if mode == "Editable Table":
        st.caption("Editable display table · edits persist through refresh and immediately propagate back into the matching strip card. Live feed values remain untouched underneath.")
        effective = apply_df_display_overrides(view[cols].copy())
        edited = render_editable_table(effective, f"{key_prefix}_editable_table", disabled=["symbol"] if "symbol" in cols else [])
        any_change = False
        if "symbol" in effective.columns:
            for i in range(min(len(effective), len(edited))):
                symbol = str(effective.iloc[i]["symbol"])
                if save_symbol_display_overrides(symbol, effective.iloc[i], edited.iloc[i], cols):
                    any_change = True
        if any_change:
            st.rerun()
        return

    if mode == "Raw Table":
        st.caption("Raw synchronized feed view · display overrides are intentionally not applied here.")
        st.dataframe(
            view[cols],
            use_container_width=True,
            hide_index=True,
            column_config=_table_column_config(cols),
        )
        return

    st.markdown(
        "<div class='strip-toolbar'>"
        "<span class='strip-pill'>OPEN UNTIL YOU CLOSE IT</span>"
        "<span class='strip-pill'>EDITS PERSIST THROUGH REFRESH</span>"
        "<span class='strip-pill'>RAW FEED REMAINS AUDITABLE</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    for idx, (_, source_row) in enumerate(view.iterrows()):
        row = apply_row_display_overrides(source_row)
        symbol = str(row.get("symbol", "—"))
        safe_symbol_key = "".join(ch if ch.isalnum() else "_" for ch in symbol)
        open_key = f"strip_open__{key_prefix}__{safe_symbol_key}"
        if open_key not in st.session_state:
            st.session_state[open_key] = False
        chevron = "▼" if st.session_state[open_key] else "▶"
        if st.button(f"{chevron}  {strip_summary(row)}", key=f"strip_toggle__{key_prefix}__{safe_symbol_key}", use_container_width=True):
            st.session_state[open_key] = not st.session_state[open_key]

        if st.session_state[open_key]:
            a, b, c, d, e = st.columns([1.1, 1.15, 1.05, 1.05, .8])
            with a:
                st.markdown(card_html("Price", short_num(row.get("latest_close")), str(row.get("category", "")), "cyan"), unsafe_allow_html=True)
            with b:
                pct = float(row.get("change_pct", 0.0))
                st.markdown(card_html("Change", format_change(pct), f"session {format_change(float(row.get('session_pct',0.0)))}", "green" if pct > 0 else "red" if pct < 0 else "yellow"), unsafe_allow_html=True)
            with c:
                score = float(row.get("score", 0.0))
                st.markdown(card_html("Score", format_score(score), str(row.get("quality", "—")), color_for(score)), unsafe_allow_html=True)
            with d:
                st.markdown(card_html("State", str(row.get("state", "—")), str(row.get("freshness", "—")), color_for(float(row.get("score",0.0)))), unsafe_allow_html=True)
            with e:
                if st.button("SELECT", key=f"{key_prefix}_select_{idx}_{symbol}"):
                    st.session_state.selected_symbol = symbol
                    st.rerun()

            fields = [(str(k), row[k]) for k in view.columns if not str(k).startswith("_")]
            cells = ["<div class='detail-grid'>"]
            for field_key, value in fields:
                label = field_key.replace("_", " ")
                cells.append(
                    f"<div class='detail-cell'><div class='detail-key'>{label}</div>"
                    f"<div class='detail-val'>{_display_value(field_key, value)}</div></div>"
                )
            cells.append("</div>")
            st.markdown("".join(cells), unsafe_allow_html=True)

            with st.popover("EDIT / FORMAT THIS INSTRUMENT", use_container_width=True):
                _format_buttons(f"{key_prefix}_{safe_symbol_key}")
                one_row = pd.DataFrame([{c: row.get(c) for c in cols}])
                edited = render_editable_table(
                    one_row,
                    f"{key_prefix}_row_editor_{safe_symbol_key}",
                    disabled=["symbol"] if "symbol" in cols else [],
                )
                if len(edited) and save_symbol_display_overrides(symbol, row, edited.iloc[0], cols):
                    st.rerun()
                if _display_override_store().get(symbol):
                    st.caption("Display override active for this instrument. It will survive refresh until reset.")
                    editor_key = f"{key_prefix}_row_editor_{safe_symbol_key}"
                    st.button(
                        "RESET DISPLAY OVERRIDES",
                        key=f"{key_prefix}_reset_{safe_symbol_key}",
                        use_container_width=True,
                        on_click=_reset_symbol_display_overrides,
                        args=(symbol, editor_key),
                    )


def _first_friday(year: int, month: int) -> date:
    d = date(year, month, 1)
    return d + timedelta(days=(4 - d.weekday()) % 7)


def event_watch_for_month(anchor: date) -> pd.DataFrame:
    """UI calendar layer. Only deterministic recurring watch windows are dated; provider-only events remain explicitly unscheduled."""
    first_fri = _first_friday(anchor.year, anchor.month)
    # Weekly Wednesday watch windows are deterministic schedule placeholders, not release verification.
    d = date(anchor.year, anchor.month, 1)
    wednesdays = []
    while d.month == anchor.month:
        if d.weekday() == 2:
            wednesdays.append(d)
        d += timedelta(days=1)
    rows = [
        {"date": first_fri, "time": "8:30 AM ET", "event": "NFP / Jobs watch", "region": "US", "level": "HIGH", "impact": "Fed pricing, yields, USD, equities", "status": "schedule watch"},
        {"date": None, "time": "8:30 AM ET", "event": "CPI / Inflation", "region": "US", "level": "HIGH", "impact": "Dollar, yields, gold, risk assets", "status": "provider date required"},
        {"date": None, "time": "2:00 PM ET", "event": "FOMC / Fed", "region": "US", "level": "HIGH", "impact": "Rates, dollar, volatility", "status": "provider date required"},
        {"date": None, "time": "continuous", "event": "Geopolitical / Defense", "region": "GLOBAL", "level": "HIGH", "impact": "Defense, energy, gold, volatility", "status": "continuous"},
    ]
    for wd in wednesdays:
        rows.append({"date": wd, "time": "10:30 AM ET", "event": "Oil Inventories watch", "region": "US", "level": "MED", "impact": "Crude, energy, inflation", "status": "weekly watch"})
    return pd.DataFrame(rows)


def render_event_strips(events: pd.DataFrame) -> None:
    if events.empty:
        st.info("No event watches for the selected calendar date.")
        return
    for _, ev in events.iterrows():
        d = ev.get("date")
        date_text = d.strftime("%a · %b %d") if isinstance(d, date) else "DATE TBA"
        tone = "red" if str(ev.get("level")) == "HIGH" else "yellow"
        st.markdown(
            f"<div class='event-strip'>"
            f"<div class='ev-date'>{date_text}</div>"
            f"<div class='ev-time'>{ev.get('time','—')}</div>"
            f"<div class='ev-name'>{ev.get('event','—')} &nbsp; {chip_html(str(ev.get('level','')), tone)}</div>"
            f"<div class='ev-region'>{ev.get('region','—')}</div>"
            f"<div class='ev-impact'>{ev.get('impact','—')}<br><span class='micro'>{ev.get('status','')}</span></div>"
            f"</div>",
            unsafe_allow_html=True,
        )


def health_rows(snapshot_age: int) -> list[tuple[str, int, str, str]]:
    status, tone = health_state(snapshot_age)
    return [
        ("Core", snapshot_age, status, tone),
        ("Selected", snapshot_age, status, tone),
        ("Sectors", snapshot_age, status, tone),
        ("Universe", snapshot_age, status, tone),
        ("Geo / Events", snapshot_age, status, tone),
    ]


def health_card(snapshot_age: int) -> str:
    pieces = ["<div class='card'><div class='section-title'>Data Health · Max 25s</div><div class='health-grid'>"]
    for name, age, status, tone in health_rows(snapshot_age):
        pieces.append(f"<div>{name}</div><div class='{tone}'>{age:02d}s · {status}</div>")
    pieces.append("</div></div>")
    return "".join(pieces)


def render_sidebar() -> tuple[str, bool, int]:
    with st.sidebar:
        st.markdown("<div class='mid'>🌐 MACRO REGIME ENGINE <span class='cyan'>v9.6</span></div><div class='small'>SYNCHRONIZED GEO + MARKET COMMAND CENTER</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:5px'></div>", unsafe_allow_html=True)
        pages = [
            "Dashboard", "Instruments", "Flow Tracker", "Options / Pressure", "Sectors", "Defense / Aero",
            "Real Estate", "Healthcare / Science", "Geo / Global", "Global Sessions", "Events", "Data Health", "Raw Data",
        ]
        page = st.radio("", pages, index=0, label_visibility="collapsed")
        st.markdown("---")
        auto = st.toggle("Auto refresh", value=True)
        interval = st.selectbox("Refresh", [10, 15, 20, 25], index=2, format_func=lambda x: f"{x} sec")
        st.caption("All visible data uses one snapshot · SLA ≤25s")
        with st.expander("DISPLAY / TABLES", expanded=False):
            st.selectbox(
                "Score format",
                ["Percentage", "Decimal", "Whole"],
                index=0,
                key="global_score_format",
                help="Applies everywhere: strip cards, expanded fields, editable tables and raw tables.",
            )
            st.selectbox(
                "Change format",
                ["Percentage", "Decimal"],
                index=0,
                key="global_change_format",
                help="Applies everywhere live change/session values are displayed.",
            )
            st.caption("Formatting is global across all modules. The same controls are also available inside every instrument editor.")
        return page, auto, int(interval)


if "selected_symbol" not in st.session_state:
    st.session_state.selected_symbol = "NQ=F"
if "last_manual_update" not in st.session_state:
    st.session_state.last_manual_update = 0.0
# Defaults are created before the sidebar widgets are instantiated.
st.session_state.setdefault("global_score_format", "Percentage")
st.session_state.setdefault("global_change_format", "Percentage")

page, auto_refresh, refresh_interval = render_sidebar()
if auto_refresh and st_autorefresh:
    st_autorefresh(interval=min(refresh_interval, MAX_DATA_AGE_SECONDS) * 1000, key="global_refresh_v96")

# One synchronized universe fetch drives every module. No page has its own independent data clock.
raw_universe = fetch_universe_snapshot(tuple(SYMBOLS))
universe_df = enrich(raw_universe)
snapshot_age = int(universe_df["age_sec"].max()) if not universe_df.empty else 999
snapshot_state, snapshot_tone = health_state(snapshot_age)

# Header / command bar
st.markdown("<div class='hero'>", unsafe_allow_html=True)
h1, h2, h3, h4, h5 = st.columns([4.0, 1.15, 1.0, 1.3, .95], vertical_alignment="center")
with h1:
    query = st.text_input("", placeholder="Search: NQ, QQQ, Gold, Defense, Healthcare, Real Estate, DXY…", label_visibility="collapsed")
    if query:
        st.session_state.selected_symbol = safe_symbol(query)
with h2:
    st.markdown(f"<div class='micro'>Toronto</div><div class='mid'>{now_et().strftime('%-I:%M %p')}</div>", unsafe_allow_html=True)
with h3:
    st.markdown(f"<div class='micro'>Snapshot</div><div class='{snapshot_tone}' style='font-weight:900'>{snapshot_age:02d}s · {snapshot_state}</div>", unsafe_allow_html=True)
with h4:
    st.markdown(f"<div class='micro'>Global Clock</div><div class='mid'>{refresh_interval}s / max 25s</div>", unsafe_allow_html=True)
with h5:
    if st.button("↻ UPDATE", key="global_update"):
        fetch_universe_snapshot.clear()
        st.session_state.last_manual_update = time.time()
        st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

selected_symbol = st.session_state.selected_symbol
selected = get_row(universe_df, selected_symbol)
related = related_symbols(selected_symbol)
rel_df = universe_df[universe_df["symbol"].isin(related)].copy()
rel_df["_order"] = rel_df["symbol"].apply(lambda x: related.index(x) if x in related else 99)
rel_df = rel_df.sort_values("_order")
core_state = compute_core_state(universe_df)
cause = cause_from(universe_df, selected_symbol)
sess = current_session()
conf = max(42, min(92, int(abs(core_state["macro"]) * .62 + 52)))


if page == "Dashboard":
    command_tab, pulse_tab, regime_tab, diag_tab = st.tabs(["Command", "Market Pulse", "Regime", "Diagnostics"])

    with command_tab:
        # Compact command strip
        s1, s2, s3, s4, s5, s6 = st.columns([1.2, 1.45, 1.35, 1.1, 1.05, 1.05])
        with s1:
            st.markdown(card_html("Session", sess["active"], "active market window", "green", "OPEN"), unsafe_allow_html=True)
        with s2:
            st.markdown(card_html("Active Driver", cause["cause"], cause["detail"], "red" if cause["target"] == "Downside" else "green", "ACTIVE"), unsafe_allow_html=True)
        with s3:
            st.markdown(card_html("Target Pressure", cause["target"], cause["effect"], "red" if cause["target"] == "Downside" else "green", "LIVE"), unsafe_allow_html=True)
        with s4:
            st.markdown(card_html("Confidence", f"{conf}%", quality_for(core_state["macro"]), "yellow", "QUALITY"), unsafe_allow_html=True)
        with s5:
            st.markdown(card_html("Market State", state_for(core_state["macro"]), "composite", color_for(core_state["macro"]), "NOW"), unsafe_allow_html=True)
        with s6:
            st.markdown(card_html("Data Age", f"{snapshot_age:02d}s", "all layers ≤25s", snapshot_tone, snapshot_state), unsafe_allow_html=True)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        left, center, right = st.columns([1.05, 2.35, .95], gap="small")

        with left:
            pct = float(selected["change_pct"])
            tone = "green" if pct > 0 else "red" if pct < 0 else "yellow"
            st.markdown(
                f"""
                <div class='card'>
                  <div class='section-title'>Selected Instrument</div>
                  <div class='statusline'><div class='big'>{selected['symbol']}</div><span class='small'>{selected['name']}</span></div>
                  <div class='subvalue'>{selected['role']}</div>
                  <div style='font-size:30px;font-weight:950;margin-top:9px;white-space:nowrap'>{short_num(selected['latest_close'])}</div>
                  <div class='{tone}' style='font-size:14px;font-weight:900'>{format_change(pct)}</div>
                  <div class='metric-grid'>
                    <div class='metric-cell'><div class='metric-label'>Score</div><div class='metric-value {color_for(selected['score'])}'>{format_score(float(selected['score']))}</div></div>
                    <div class='metric-cell'><div class='metric-label'>Quality</div><div class='metric-value'>{selected['quality']}</div></div>
                    <div class='metric-cell'><div class='metric-label'>Confidence</div><div class='metric-value green'>{conf}%</div></div>
                    <div class='metric-cell'><div class='metric-label'>State</div><div class='metric-value {color_for(selected['score'])}'>{selected['state']}</div></div>
                  </div>
                </div>
                """, unsafe_allow_html=True,
            )
            with st.popover("Instrument details", use_container_width=True):
                st.caption(f"Category: {selected['category']}")
                st.caption(f"Driver: {selected['driver']}")
                st.caption(f"Source: {selected['source']}")
                st.caption(f"Snapshot age: {int(selected['age_sec'])} sec")
                st.caption("Public-feed proxy. Provider latency can differ from dashboard refresh age.")

        with center:
            st.markdown("<div class='shell'><div class='section-title'>Universal Instrument Map · click symbol to focus</div>", unsafe_allow_html=True)
            shown = rel_df.head(6)
            btn_cols = st.columns(max(1, len(shown)))
            for col, (_, row) in zip(btn_cols, shown.iterrows()):
                with col:
                    if st.button(str(row["symbol"]), key=f"rel_{row['symbol']}"):
                        st.session_state.selected_symbol = str(row["symbol"])
                        st.rerun()
            cards = "".join(mini_instrument_html(row, str(row["symbol"]) == selected_symbol) for _, row in shown.iterrows())
            st.markdown(f"<div class='instrument-strip'>{cards}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3, gap="small")
            pressure = "Seller-led" if selected["score"] < -30 else "Buyer-led" if selected["score"] > 30 else "Balanced"
            absorption = "Weak" if selected["score"] < -45 else "Strong" if selected["score"] > 45 else "Mixed"
            rv = float(selected.get("relative_volume", np.nan)) if pd.notna(selected.get("relative_volume", np.nan)) else np.nan
            vd = float(selected.get("volume_delta_pct", np.nan)) if pd.notna(selected.get("volume_delta_pct", np.nan)) else np.nan
            volume_activity = "N/A" if pd.isna(rv) else "Elevated" if rv >= 1.35 else "Thin" if rv < 0.70 else "Normal"
            volume_delta_text = "N/A" if pd.isna(vd) else f"{vd:+.1f}%"
            opt = "Put pressure" if selected["score"] < -30 else "Call support" if selected["score"] > 30 else "Neutral"
            with c1:
                st.markdown(
                    f"<div class='card compact'><div class='section-title'>Order Flow</div>"
                    f"<div class='rowline'><span>Pressure</span><b class='{color_for(selected['score'])}'>{pressure}</b></div>"
                    f"<div class='rowline'><span>Rel volume</span><b>{volume_activity}{'' if pd.isna(rv) else f' · {rv:.2f}×'}</b></div>"
                    f"<div class='rowline'><span>Volume Δ</span><b>{volume_delta_text}</b></div>"
                    f"<div class='rowline'><span>Absorption</span><b>{absorption}</b></div></div>",
                    unsafe_allow_html=True,
                )
                with st.popover("Open flow", use_container_width=True):
                    st.write("Flow proxy uses synchronized price, volume, breadth and related-asset agreement from the active snapshot.")
                    mini_cols = ["symbol", "change_pct", "volume_1m", "session_volume", "relative_volume", "volume_delta_pct", "volume_source", "score", "state"]
                    st.dataframe(rel_df[mini_cols].head(10), use_container_width=True, hide_index=True, column_config=_table_column_config(mini_cols))
            with c2:
                st.markdown(
                    f"<div class='card compact'><div class='section-title'>Instrument Pressure</div>"
                    f"<div class='rowline'><span>Options layer</span><b class='{color_for(selected['score'])}'>{opt}</b></div>"
                    f"<div class='rowline'><span>ETF / Cash / Futures</span><b>Mapped</b></div>"
                    f"<div class='rowline'><span>IV / Event risk</span><b>{'Elevated' if abs(selected['score']) > 40 else 'Normal'}</b></div>"
                    f"<div class='rowline'><span>Expiry risk</span><b>Watch</b></div></div>",
                    unsafe_allow_html=True,
                )
                with st.popover("Open pressure", use_container_width=True):
                    st.caption("Options pressure remains proxy-grade until a dedicated options feed is connected.")
                    st.metric("Composite pressure", format_score(float(selected['score'])))
            with c3:
                st.markdown(
                    f"<div class='card compact'><div class='section-title'>Active Driver</div>"
                    f"<div class='rowline'><span>Cause</span><b class='{color_for(selected['score'])}'>{cause['cause']}</b></div>"
                    f"<div class='rowline'><span>Detail</span><b>{cause['detail']}</b></div>"
                    f"<div class='rowline'><span>Affected</span><b>{selected['category']}</b></div>"
                    f"<div class='rowline'><span>Quality</span><b>{selected['quality']}</b></div></div>",
                    unsafe_allow_html=True,
                )
                with st.popover("Open driver", use_container_width=True):
                    drivers = universe_df[universe_df["symbol"].isin(["DX-Y.NYB", "^TNX", "^VIX", "SMH", "HYG"])][["symbol", "name", "change_pct", "score", "state"]]
                    st.dataframe(drivers, use_container_width=True, hide_index=True, column_config=_table_column_config(list(drivers.columns)))

        with right:
            st.markdown(health_card(snapshot_age), unsafe_allow_html=True)
            st.markdown("<div style='height:7px'></div>", unsafe_allow_html=True)
            alerts = [
                (selected["symbol"], selected["state"]),
                ("Driver", cause["cause"]),
                ("Session", sess["active"]),
                ("Snapshot", f"{snapshot_age:02d}s {snapshot_state}"),
            ]
            alert_html = "<div class='card compact'><div class='section-title'>Alerts</div>" + "".join(
                f"<div class='rowline'><span>{a}</span><b>{b}</b></div>" for a, b in alerts
            ) + "</div>"
            st.markdown(alert_html, unsafe_allow_html=True)
            with st.popover("Data details", use_container_width=True):
                st.write("All dashboard modules read from the same synchronized universe snapshot. No tier is allowed a refresh cadence above 25 seconds.")
                st.caption(f"Snapshot created: {universe_df['updated'].iloc[0] if len(universe_df) else '—'}")
                st.caption(f"Provider rows OK: {int(universe_df['source_ok'].sum())}/{len(universe_df)}")

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        px = float(selected["latest_close"])
        decision_html = f"""
        <div class='shell'>
          <div class='section-title'>Decision Board</div>
          <div class='decision-grid'>
            <div class='decision-card'><div class='section-title'>Target</div><div class='value {'red' if cause['target']=='Downside' else 'green'}'>{cause['target']}</div><div class='subvalue'>{cause['effect']}</div></div>
            <div class='decision-card'><div class='section-title'>Key Levels</div><div class='item'>Resistance <b class='red' style='float:right'>{short_num(px*1.015)}</b></div><div class='item'>Pivot <b class='yellow' style='float:right'>{short_num(px)}</b></div><div class='item'>Support <b class='green' style='float:right'>{short_num(px*.985)}</b></div></div>
            <div class='decision-card'><div class='section-title'>Confirm</div><div class='item'>✓ Price follows driver</div><div class='item'>✓ Related assets agree</div><div class='item'>✓ Session supports move</div><div class='item'>✓ Volatility confirms</div></div>
            <div class='decision-card'><div class='section-title'>Contradict / Invalidate</div><div class='item'>✕ Related assets diverge</div><div class='item'>✕ Reclaim against pressure</div><div class='item'>✕ Volatility fades</div><div class='item'>✕ Breadth improves</div></div>
          </div>
        </div>
        """
        st.markdown(decision_html, unsafe_allow_html=True)
        q1, q2 = st.columns(2)
        with q1:
            with st.popover("⚠ Caution conditions", use_container_width=True):
                st.write("Low liquidity · news spike · major-level proximity · wide spreads")
        with q2:
            with st.popover("◉ Future watch", use_container_width=True):
                st.write("CPI / PCE · FOMC / Fed · earnings · auctions · oil data · geopolitical events")

    with pulse_tab:
        st.markdown("<div class='shell'><div class='section-title'>Live Market Pulse · compact selectable grid</div>", unsafe_allow_html=True)
        categories = ["All", "Indexes", "AI / Tech", "Dollar", "Bonds", "Commodities", "Crypto", "Internals", "Credit", "Volatility", "Sectors", "Defense / Aero", "Real Estate", "Healthcare / Science", "Currencies", "Global Markets", "Clean Energy"]
        cat = st.selectbox("Category", categories, index=0, label_visibility="collapsed")
        tile_df = universe_df if cat == "All" else universe_df[universe_df["category"] == cat]
        tile_df = tile_df.head(18)
        for start in range(0, len(tile_df), 6):
            chunk = tile_df.iloc[start:start + 6]
            cols = st.columns(len(chunk))
            for col, (_, row) in zip(cols, chunk.iterrows()):
                with col:
                    if st.button(str(row["symbol"]), key=f"pulse_{cat}_{row['symbol']}"):
                        st.session_state.selected_symbol = str(row["symbol"])
                        st.rerun()
                    st.markdown(mini_instrument_html(row, str(row["symbol"]) == selected_symbol), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with regime_tab:
        st.markdown("<div class='shell'><div class='section-title'>Regime Matrix</div>", unsafe_allow_html=True)
        gcols = st.columns(6)
        gauge_items = [
            ("Breadth", core_state["breadth"]), ("Trend", core_state["trend"]), ("Momentum", core_state["momentum"]),
            ("Volatility", core_state["volatility"]), ("Risk", core_state["risk"]), ("Credit", core_state["credit"]),
        ]
        for col, (label, value) in zip(gcols, gauge_items):
            with col:
                st.plotly_chart(gauge(label, value), use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)
        sleft, sright = st.columns([1.3, 2.2])
        with sleft:
            session_html = "<div class='card'><div class='section-title'>Global Sessions</div>"
            for name, status in sess["status"].items():
                tone = "green" if status == "Open" else "yellow"
                session_html += f"<div class='rowline'><span>{name}</span><b class='{tone}'>{status}</b></div>"
            session_html += "</div>"
            st.markdown(session_html, unsafe_allow_html=True)
        with sright:
            cat_summary = universe_df.groupby("category", as_index=False).agg(score=("score", "mean"), change_pct=("change_pct", "mean"))
            cat_summary["state"] = cat_summary["score"].apply(state_for)
            cat_summary = cat_summary.sort_values("score", ascending=False)
            st.dataframe(cat_summary, use_container_width=True, hide_index=True, column_config=_table_column_config(list(cat_summary.columns)))

    with diag_tab:
        st.markdown("<div class='shell'><div class='section-title'>Selected Instrument · synchronized direct data</div>", unsafe_allow_html=True)
        diag_cols = ["symbol", "name", "category", "latest_close", "change_pct", "score", "quality", "state", "age_sec", "source", "role"]
        render_editable_table(rel_df[diag_cols].copy(), "dashboard_diagnostics_table")
        st.markdown("</div>", unsafe_allow_html=True)


elif page == "Instruments":
    st.markdown("<div class='shell'><div class='section-title'>Universal Instruments · Interactive Strip Matrix</div><div class='small'>Strip Cards are the primary presentation only. Click any instrument to expose 100% of its current fields; switch to Raw Table at any time.</div>", unsafe_allow_html=True)
    f1, f2 = st.columns([1.1, 2.3])
    with f1:
        cat = st.selectbox("Filter", ["All"] + sorted(universe_df["category"].unique().tolist()))
    with f2:
        inst_search = st.text_input("Search instruments", placeholder="symbol, name, category, role, driver…", label_visibility="collapsed")
    view = universe_df if cat == "All" else universe_df[universe_df["category"] == cat]
    if inst_search:
        q = inst_search.upper()
        view = view[view.apply(lambda r: q in f"{r['symbol']} {r['name']} {r['category']} {r['role']} {r['driver']}".upper(), axis=1)]
    render_strip_cards(view, "instruments", ["symbol", "name", "category", "latest_close", "change_pct", "session_pct", "volume", "volume_1m", "session_volume", "relative_volume", "volume_delta_pct", "volume_source", "volume_proxy_symbol", "score", "quality", "state", "age_sec", "freshness", "source", "source_ok", "role", "driver", "updated"])
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Flow Tracker":
    flow = universe_df.copy()
    flow["pressure"] = flow["score"].apply(lambda x: "Sellers" if x < -30 else "Buyers" if x > 30 else "Balanced")
    flow["absorption"] = flow["score"].apply(lambda x: "Weak" if x < -50 else "Strong" if x > 50 else "Mixed")
    flow["volume_activity"] = flow["relative_volume"].apply(
        lambda x: "N/A" if pd.isna(x) else "Elevated" if float(x) >= 1.35 else "Thin" if float(x) < 0.70 else "Normal"
    )
    st.markdown("<div class='shell'><div class='section-title'>Order Flow Proxy Tracker · Interactive Strips</div><div class='small'>Synchronized price / volume / breadth / related-asset proxy. True Level II still requires a broker-grade order-flow feed.</div>", unsafe_allow_html=True)
    scope = st.selectbox("Scope", ["Selected cluster", "All instruments"], label_visibility="collapsed")
    view = flow[flow["symbol"].isin(related)] if scope == "Selected cluster" else flow
    render_strip_cards(view, "flow")
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Options / Pressure":
    tmp = universe_df.copy()
    tmp["options_pressure"] = tmp["score"].apply(lambda x: "Put pressure" if x < -30 else "Call support" if x > 30 else "Neutral")
    tmp["iv_event_risk"] = tmp["score"].apply(lambda x: "Elevated" if abs(x) > 40 else "Normal")
    st.markdown("<div class='shell'><div class='section-title'>Options / Instrument Pressure · Interactive Strips</div><div class='small'>Options remains a mapped pressure layer; dedicated greeks / chain / dealer positioning requires a connected options data provider.</div>", unsafe_allow_html=True)
    render_strip_cards(tmp, "options")
    st.markdown("</div>", unsafe_allow_html=True)

elif page in {"Sectors", "Defense / Aero", "Real Estate", "Healthcare / Science", "Geo / Global"}:
    category_map = {
        "Sectors": ["Sectors", "AI / Tech", "Clean Energy"],
        "Defense / Aero": ["Defense / Aero"],
        "Real Estate": ["Real Estate"],
        "Healthcare / Science": ["Healthcare / Science"],
        "Geo / Global": ["Global Markets", "Currencies", "Commodities", "Defense / Aero", "Dollar", "Bonds"],
    }
    cats = category_map[page]
    view = universe_df[universe_df["category"].isin(cats)].copy()
    if page == "Geo / Global":
        view["geo_role"] = view["driver"].replace("", "macro linkage")
    st.markdown(f"<div class='shell'><div class='section-title'>{page} · Interactive Strip Matrix</div><div class='small'>Compact surface, full field expansion. No tracked fields are removed.</div>", unsafe_allow_html=True)
    render_strip_cards(view, f"category_{page.replace(' ','_').replace('/','_')}")
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Global Sessions":
    cols = st.columns(3)
    for idx, (name, status) in enumerate(sess["status"].items()):
        with cols[idx % 3]:
            st.markdown(card_html(name, status, "session state", "green" if status == "Open" else "yellow"), unsafe_allow_html=True)

elif page == "Events":
    st.markdown("<div class='shell'><div class='section-title'>Event Watch · Calendar Layer</div><div class='small'>Calendar is integrated into the Events workspace. Scheduled items without a verified calendar provider are explicitly marked instead of inventing dates.</div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.35, 1.0, 2.2], vertical_alignment="center")
    with c1:
        with st.popover("📅 OPEN MINI CALENDAR", use_container_width=True):
            cal_date = st.date_input("Calendar date", value=now_et().date(), key="event_calendar_date")
            cal_scope = st.radio("Calendar scope", ["Selected day", "Selected week", "Full month"], horizontal=True, key="event_calendar_scope")
    with c2:
        st.markdown(f"<div class='micro'>Selected</div><div class='mid'>{st.session_state.get('event_calendar_date', now_et().date()).strftime('%b %d, %Y')}</div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='calendar-note'>Red = high-impact watch · Yellow = medium. DATE TBA means the build needs a verified calendar provider for that release; it is not silently guessed.</div>", unsafe_allow_html=True)

    selected_date = st.session_state.get("event_calendar_date", now_et().date())
    scope_mode = st.session_state.get("event_calendar_scope", "Selected day")
    month_events = event_watch_for_month(selected_date)
    scheduled = month_events[month_events["date"].notna()].copy()
    unscheduled = month_events[month_events["date"].isna()].copy()
    if scope_mode == "Selected day":
        chosen = scheduled[scheduled["date"] == selected_date]
    elif scope_mode == "Selected week":
        week_start = selected_date - timedelta(days=selected_date.weekday())
        week_end = week_start + timedelta(days=6)
        chosen = scheduled[scheduled["date"].apply(lambda x: isinstance(x, date) and week_start <= x <= week_end)]
    else:
        chosen = scheduled

    st.markdown("<div class='section-title' style='margin-top:8px'>Scheduled Watch Windows</div>", unsafe_allow_html=True)
    render_event_strips(chosen)
    st.markdown("<div class='section-title' style='margin-top:10px'>Provider-Dated / Continuous Watches</div>", unsafe_allow_html=True)
    render_event_strips(unscheduled)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Data Health":
    st.markdown("<div class='shell'><div class='section-title'>Data Health · synchronized SLA</div>", unsafe_allow_html=True)
    st.markdown(health_card(snapshot_age), unsafe_allow_html=True)
    st.caption("Refresh cadence is capped at 25 seconds for every tier. Dashboard freshness measures the app snapshot age; upstream provider latency is separate.")
    health_df = universe_df[["symbol", "name", "category", "age_sec", "freshness", "source", "source_ok"]].copy()
    render_editable_table(health_df, "data_health_table")
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Raw Data":
    st.markdown("<div class='shell'><div class='section-title'>Raw Data Diagnostic Console</div><div class='small'>SOURCE · DOMAIN · VALUE · Δ · AGE · STATUS. Click/filter here instead of exposing raw payload clutter on the command dashboard.</div>", unsafe_allow_html=True)
    domains = ["All"] + sorted(universe_df["category"].unique().tolist())
    d1, d2 = st.columns([1.2, 2.8])
    with d1:
        domain = st.selectbox("Domain", domains)
    with d2:
        raw_search = st.text_input("Filter symbol / name", placeholder="e.g. NQ, ITA, Gold, Canada")
    raw_view = universe_df.copy()
    if domain != "All":
        raw_view = raw_view[raw_view["category"] == domain]
    if raw_search:
        q = raw_search.upper()
        raw_view = raw_view[raw_view.apply(lambda r: q in f"{r['symbol']} {r['name']} {r['category']} {r['role']}".upper(), axis=1)]
    raw_view = raw_view.rename(columns={
        "symbol": "SOURCE", "category": "DOMAIN", "latest_close": "VALUE", "change_pct": "Δ %",
        "age_sec": "AGE SEC", "freshness": "STATUS", "source": "FEED",
    })
    raw_cols = ["SOURCE", "name", "DOMAIN", "VALUE", "Δ %", "volume", "volume_1m", "session_volume", "relative_volume", "volume_delta_pct", "volume_source", "volume_proxy_symbol", "AGE SEC", "STATUS", "FEED", "source_ok"]
    render_editable_table(raw_view[raw_cols].copy(), "raw_data_table")
    with st.expander("Selected raw payload", expanded=False):
        r = selected.to_dict()
        st.json({k: (float(v) if isinstance(v, np.floating) else int(v) if isinstance(v, np.integer) else v) for k, v in r.items()})
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    f"<div class='footerbar'>Macro Regime Engine {APP_VERSION} · one synchronized universe snapshot · global refresh {refresh_interval}s · maximum dashboard tier age {MAX_DATA_AGE_SECONDS}s</div>",
    unsafe_allow_html=True,
)
