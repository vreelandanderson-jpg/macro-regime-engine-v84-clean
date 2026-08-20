from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from live_feeds import LiveMarketHub, LIVE_PROXY_MAP

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:  # pragma: no cover
    st_autorefresh = None


TZ = ZoneInfo("America/Toronto")
APP_VERSION = "v10.3"
MAX_DATA_AGE_SECONDS = 25
CACHE_TTL_SECONDS = 10
DEFAULT_REFRESH_SECONDS = 2

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
/* persistent interactive strip cards + live volume diagnostics */
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
.connection-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;margin:7px 0;}
.connection-cell{border:1px solid #173957;background:#06131f;border-radius:10px;padding:8px;min-width:0;}
.connection-provider{font-size:9px;letter-spacing:.10em;text-transform:uppercase;color:#8fa6bc;font-weight:900;}
.connection-state{font-size:13px;font-weight:950;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.clock-live{color:var(--green)}.clock-stale{color:var(--red)}.clock-closed{color:#9db1c5}.clock-current{color:var(--yellow)}
/* v10.3 immediate-intelligence surfaces */
.action-read{border:1px solid #1a4c70;background:linear-gradient(180deg,#071a2a,#05101b);border-radius:12px;padding:9px 10px;margin-top:7px;}
.action-read .headline{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px;}
.action-read .headline b{font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.action-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px 8px;}
.action-cell{min-width:0;border-top:1px solid #102c43;padding-top:4px;}
.action-cell .k{font-size:8px;letter-spacing:.08em;text-transform:uppercase;color:#7f96ad;font-weight:900;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.action-cell .v{font-size:10.5px;color:#eaf5ff;font-weight:850;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px;}
.attention-head{display:flex;align-items:center;justify-content:space-between;gap:8px;margin:2px 0 6px;}
[data-testid="stDataFrame"]{border:1px solid #173957;border-radius:10px;overflow:hidden;}
[data-testid="stDataFrame"] [role="columnheader"]{font-weight:900!important;}
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
    "NDX": "^NDX", "NASDAQ CASH": "^NDX", "NQ CASH": "^NDX", "NAS": "NQ=F", "NASDAQ": "NQ=F", "NAS100": "NQ=F", "NQ": "NQ=F",
    "SPX": "ES=F", "S&P": "ES=F", "SP500": "ES=F", "ES": "ES=F",
    "GOLD": "GC=F", "GC": "GC=F", "OIL": "CL=F", "CL": "CL=F", "DXY": "DX-Y.NYB", "VIX": "^VIX",
    "REAL ESTATE": "XLRE", "HEALTHCARE": "XLV", "SCIENCE": "IBB", "BIOTECH": "XBI", "AI": "NVDA",
    "DEFENSE": "ITA", "DEFENCE": "ITA", "AEROSPACE": "ITA", "AERO": "ITA",
}

# Optionable underlyings used by the live Options page. For futures/cash references
# the dashboard uses the closest liquid listed options proxy and labels that proxy.
OPTION_UNDERLYING_MAP = {
    "NQ=F": "QQQ", "^NDX": "QQQ",
    "ES=F": "SPY", "^GSPC": "SPY",
    "YM=F": "DIA", "^DJI": "DIA",
    "RTY=F": "IWM", "^RUT": "IWM",
    "GC=F": "GLD", "CL=F": "USO", "SI=F": "SLV", "HG=F": "CPER", "NG=F": "UNG",
    "DX-Y.NYB": "UUP", "^TNX": "TLT", "^VIX": "VIX", "^VVIX": "VIX", "^VIX9D": "VIX",
    "EURUSD=X": "UUP", "JPY=X": "UUP", "CAD=X": "UUP",
    "BTC-USD": "IBIT", "ETH-USD": "ETHA",
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
    """Unavailable-data constructor. A collection attempt is recorded, but no price is invented."""
    return {
        "symbol": sym, "latest_close": np.nan, "change_pct": np.nan, "session_pct": np.nan,
        "volume": np.nan, "volume_1m": np.nan, "session_volume": np.nan,
        "relative_volume": np.nan, "volume_delta_pct": np.nan,
        "volume_source": "N/A", "volume_proxy_symbol": "",
        "provider_ts": None, "received_ts": snapshot_iso, "updated": None,
        "check_ts": snapshot_iso, "check_attempted": True, "check_ok": False,
        "source": "unavailable", "source_ok": False, "feed_mode": "UNAVAILABLE",
        "data_quality": "NO VALID QUOTE",
    }


@st.cache_resource(show_spinner=False)
def _last_verified_store() -> dict:
    # Prevent a transient provider miss from erasing the last genuine value on the next UI rerun.
    return {"rows": {}}


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
    """Timestamp-correct public collection baseline.

    Collection freshness and market-event freshness are deliberately separate:
    ``received_ts`` means the engine checked the source now, while ``provider_ts`` is
    the provider's actual last market event. A quiet instrument is therefore not
    falsely treated as an un-checked instrument, and a delayed venue is never promoted
    to direct LIVE merely because the HTTP request was fresh.
    """
    received_iso = now_et().isoformat()
    rows: list[dict] = []
    frames: dict[str, pd.DataFrame] = {}
    store = _last_verified_store()["rows"]
    if yf is not None:
        try:
            data = yf.download(
                list(symbols), period="1d", interval="1m", group_by="ticker", progress=False,
                prepost=True, threads=True, auto_adjust=False, timeout=12,
            )
            for sym in symbols:
                try:
                    frame = data.copy() if len(symbols) == 1 else data[sym].copy()
                    frame = frame.dropna(how="all")
                    if not frame.empty:
                        frames[sym] = frame
                except Exception:
                    pass
        except Exception:
            pass

        # Missing-symbol retries are isolated; one bad ticker cannot poison the universe.
        for sym in symbols:
            if sym in frames:
                continue
            try:
                one = yf.download(
                    sym, period="1d", interval="1m", progress=False, prepost=True,
                    threads=False, auto_adjust=False, timeout=8,
                )
                one = one.dropna(how="all")
                if not one.empty:
                    frames[sym] = one
            except Exception:
                pass

    for sym in symbols:
        frame = frames.get(sym)
        if frame is None or frame.empty:
            prior = store.get(sym)
            if prior:
                held = dict(prior)
                held.update({
                    "received_ts": received_iso, "check_ts": received_iso,
                    "check_attempted": True, "check_ok": False, "source_ok": False,
                    "feed_mode": "HOLD LAST VERIFIED",
                    "source": f"{prior.get('source','public')} · retry failed",
                    "data_quality": "LAST VERIFIED · COLLECTION DEGRADED",
                })
                rows.append(held)
            else:
                rows.append(fallback_row(sym, received_iso))
            continue
        try:
            close = frame["Close"].dropna()
            if close.empty:
                raise ValueError("no close")
            volume = frame["Volume"] if "Volume" in frame else pd.Series(dtype=float)
            last = float(close.iloc[-1])
            prev = float(close.iloc[-2]) if len(close) > 1 else last
            first = float(close.iloc[0])
            pct = ((last / prev) - 1) * 100 if prev else 0.0
            session_pct = ((last / first) - 1) * 100 if first else 0.0
            vm = _volume_metrics(volume)
            try:
                ts = pd.Timestamp(close.index[-1])
                if ts.tzinfo is None:
                    ts = ts.tz_localize("UTC")
                provider_ts = ts.tz_convert(TZ).isoformat()
            except Exception:
                provider_ts = None
            row = {
                "symbol": sym, "latest_close": last, "change_pct": pct, "session_pct": session_pct,
                "volume": vm["session_volume"], **vm,
                "volume_source": "Actual" if pd.notna(vm["session_volume"]) else "N/A",
                "volume_proxy_symbol": "",
                "provider_ts": provider_ts, "received_ts": received_iso, "updated": provider_ts,
                "check_ts": received_iso, "check_attempted": True, "check_ok": True,
                "source": "yfinance · public check", "source_ok": True, "feed_mode": "POLL",
                "data_quality": "PUBLIC MARKET EVENT",
            }
            store[sym] = dict(row)
            rows.append(row)
        except Exception:
            prior = store.get(sym)
            if prior:
                held = dict(prior)
                held.update({
                    "received_ts": received_iso, "check_ts": received_iso,
                    "check_attempted": True, "check_ok": False, "source_ok": False,
                    "feed_mode": "HOLD LAST VERIFIED", "data_quality": "LAST VERIFIED · PARSE DEGRADED",
                })
                rows.append(held)
            else:
                rows.append(fallback_row(sym, received_iso))
    return _apply_volume_proxies(pd.DataFrame(rows))


def _stored_secret(name: str) -> str:
    """Read a deployment secret/environment key without ever rendering it back to the UI."""
    try:
        value = st.secrets.get(name, "")
        if value:
            return str(value).strip()
    except Exception:
        pass
    return str(os.getenv(name, "") or "").strip()


def _resolved_provider_key(name: str) -> str:
    """Session-entered credentials override deployment secrets. Pause disables both."""
    if not bool(st.session_state.get("live_providers_enabled", True)):
        return ""
    session_key = f"runtime_{name.lower()}"
    runtime = str(st.session_state.get(session_key, "") or "").strip()
    return runtime or _stored_secret(name)


def _credential_origin(name: str) -> str:
    if not bool(st.session_state.get("live_providers_enabled", True)):
        return "PAUSED"
    runtime = str(st.session_state.get(f"runtime_{name.lower()}", "") or "").strip()
    if runtime:
        return "SESSION"
    if _stored_secret(name):
        return "DEPLOYMENT SECRET"
    return "NOT CONFIGURED"


@st.cache_resource(show_spinner=False)
def get_live_hub(
    massive_key: str, databento_key: str, dxfeed_url: str, dxfeed_user: str,
    dxfeed_password: str, dxfeed_token: str, dxfeed_symbol_map_json: str,
    providers_enabled: bool = True,
) -> LiveMarketHub:
    return LiveMarketHub(
        massive_key=massive_key, databento_key=databento_key, mt5_enabled=providers_enabled,
        dxfeed_rest_url=dxfeed_url, dxfeed_username=dxfeed_user,
        dxfeed_password=dxfeed_password, dxfeed_token=dxfeed_token,
        dxfeed_symbol_map_json=dxfeed_symbol_map_json,
    )


def _stop_live_hub_for_keys(
    massive_key: str, databento_key: str, dxfeed_url: str = "", dxfeed_user: str = "",
    dxfeed_password: str = "", dxfeed_token: str = "", dxfeed_symbol_map_json: str = "",
) -> None:
    try:
        hub = get_live_hub(massive_key, databento_key, dxfeed_url, dxfeed_user, dxfeed_password, dxfeed_token, dxfeed_symbol_map_json, True)
        hub.stop()
    except Exception:
        pass
    try:
        get_live_hub.clear()
    except Exception:
        pass


def _available_provider_key(name: str) -> str:
    """Return the configured key regardless of the pause toggle; used for clean shutdown."""
    runtime = str(st.session_state.get(f"runtime_{name.lower()}", "") or "").strip()
    return runtime or _stored_secret(name)


def _resolved_provider_setting(name: str) -> str:
    if not bool(st.session_state.get("live_providers_enabled", True)):
        return ""
    runtime = str(st.session_state.get(f"runtime_{name.lower()}", "") or "").strip()
    return runtime or _stored_secret(name)


def _available_provider_setting(name: str) -> str:
    runtime = str(st.session_state.get(f"runtime_{name.lower()}", "") or "").strip()
    return runtime or _stored_secret(name)


def _provider_connect_callback() -> None:
    old = (
        _available_provider_key("MASSIVE_API_KEY"), _available_provider_key("DATABENTO_API_KEY"),
        _available_provider_setting("DXFEED_REST_URL"), _available_provider_setting("DXFEED_USERNAME"),
        _available_provider_setting("DXFEED_PASSWORD"), _available_provider_setting("DXFEED_TOKEN"),
        _available_provider_setting("DXFEED_SYMBOL_MAP_JSON"),
    )
    _stop_live_hub_for_keys(*old)
    for widget_key, runtime_name in [
        ("massive_key_entry", "MASSIVE_API_KEY"), ("databento_key_entry", "DATABENTO_API_KEY"),
        ("dxfeed_url_entry", "DXFEED_REST_URL"), ("dxfeed_user_entry", "DXFEED_USERNAME"),
        ("dxfeed_password_entry", "DXFEED_PASSWORD"), ("dxfeed_token_entry", "DXFEED_TOKEN"),
    ]:
        value = str(st.session_state.get(widget_key, "") or "").strip()
        if value:
            st.session_state[f"runtime_{runtime_name.lower()}"] = value
    st.session_state.live_providers_enabled = True
    for key in ["massive_key_entry", "databento_key_entry", "dxfeed_password_entry", "dxfeed_token_entry"]:
        st.session_state[key] = ""


def _provider_pause_callback() -> None:
    _stop_live_hub_for_keys(
        _available_provider_key("MASSIVE_API_KEY"), _available_provider_key("DATABENTO_API_KEY"),
        _available_provider_setting("DXFEED_REST_URL"), _available_provider_setting("DXFEED_USERNAME"),
        _available_provider_setting("DXFEED_PASSWORD"), _available_provider_setting("DXFEED_TOKEN"),
        _available_provider_setting("DXFEED_SYMBOL_MAP_JSON"),
    )
    st.session_state.live_providers_enabled = False


def _provider_enabled_changed() -> None:
    _stop_live_hub_for_keys(
        _available_provider_key("MASSIVE_API_KEY"), _available_provider_key("DATABENTO_API_KEY"),
        _available_provider_setting("DXFEED_REST_URL"), _available_provider_setting("DXFEED_USERNAME"),
        _available_provider_setting("DXFEED_PASSWORD"), _available_provider_setting("DXFEED_TOKEN"),
        _available_provider_setting("DXFEED_SYMBOL_MAP_JSON"),
    )


def market_state_for_symbol(sym: str, dt: datetime | None = None) -> str:
    dt = dt or now_et()
    wd = dt.weekday()
    minute = dt.hour * 60 + dt.minute
    if sym in {"BTC-USD", "ETH-USD"}:
        return "OPEN"
    if sym in {"EURUSD=X", "JPY=X", "CAD=X"}:
        if wd == 5 or (wd == 6 and minute < 17 * 60) or (wd == 4 and minute >= 17 * 60):
            return "CLOSED"
        return "OPEN"
    if sym.endswith("=F"):
        if wd == 5 or (wd == 6 and minute < 18 * 60) or (wd == 4 and minute >= 17 * 60):
            return "CLOSED"
        if 17 * 60 <= minute < 18 * 60:
            return "BREAK"
        return "OPEN"
    if sym.startswith("^") or sym in {"DX-Y.NYB"}:
        if wd >= 5:
            return "CLOSED"
        return "OPEN" if 9 * 60 + 30 <= minute < 16 * 60 else "CLOSED"
    if wd >= 5:
        return "CLOSED"
    if 9 * 60 + 30 <= minute < 16 * 60:
        return "OPEN"
    if 4 * 60 <= minute < 9 * 60 + 30 or 16 * 60 <= minute < 20 * 60:
        return "EXTENDED"
    return "CLOSED"


def _seconds_since(value: object) -> int:
    if value in (None, "", np.nan):
        return 999999
    try:
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return max(0, int((now_et() - dt.astimezone(TZ)).total_seconds()))
    except Exception:
        return 999999


def build_market_snapshot(symbols: tuple[str, ...]) -> tuple[pd.DataFrame, LiveMarketHub]:
    baseline = fetch_universe_snapshot(symbols).copy()
    massive_key = _resolved_provider_key("MASSIVE_API_KEY")
    databento_key = _resolved_provider_key("DATABENTO_API_KEY")
    dxfeed_url = _resolved_provider_setting("DXFEED_REST_URL")
    dxfeed_user = _resolved_provider_setting("DXFEED_USERNAME")
    dxfeed_password = _resolved_provider_setting("DXFEED_PASSWORD")
    dxfeed_token = _resolved_provider_setting("DXFEED_TOKEN")
    dxfeed_symbol_map_json = _resolved_provider_setting("DXFEED_SYMBOL_MAP_JSON")
    hub = get_live_hub(
        massive_key, databento_key, dxfeed_url, dxfeed_user, dxfeed_password, dxfeed_token,
        dxfeed_symbol_map_json, bool(st.session_state.get("live_providers_enabled", True)),
    )
    hub.ensure_started(list(symbols))
    live = hub.snapshot()

    if baseline.empty:
        baseline = pd.DataFrame([fallback_row(sym, now_et().isoformat()) for sym in symbols])
    # Preserve the last official/reference value before the universal live router
    # overlays an exchange or broker-active level. This prevents loss of auditability
    # when a 24h broker quote takes over a cash/reference instrument after hours.
    baseline["reference_price"] = pd.to_numeric(baseline.get("latest_close"), errors="coerce")
    baseline["reference_provider_ts"] = baseline.get("provider_ts")
    baseline["reference_source"] = baseline.get("source")
    baseline = baseline.set_index("symbol", drop=False)
    for sym, tick in live.items():
        if sym not in baseline.index:
            continue
        if str(tick.get("feed_mode", "") or "").upper() == "STREAM":
            live_event_age = _seconds_since(tick.get("provider_ts"))
            if live_event_age > MAX_DATA_AGE_SECONDS:
                continue
        for key, value in tick.items():
            if key == "symbol" or value is None:
                continue
            # A live stream should not erase a valid fallback-derived session metric
            # merely because the stream has not accumulated enough history yet.
            if isinstance(value, float) and math.isnan(value):
                continue
            baseline.at[sym, key] = value

    out = baseline.reset_index(drop=True)
    if "price_type" not in out.columns:
        out["price_type"] = "REFERENCE"
    else:
        out["price_type"] = out["price_type"].fillna("REFERENCE")
    if "active_provider_symbol" not in out.columns:
        out["active_provider_symbol"] = out["symbol"].astype(str)
    else:
        out["active_provider_symbol"] = out["active_provider_symbol"].fillna(out["symbol"]).astype(str)
    # Session schedule is context only. It never creates LIVE/EXTENDED.
    out["session_reference_state"] = out["symbol"].apply(market_state_for_symbol)
    out["market_age_sec"] = out.apply(lambda r: _seconds_since(r.get("provider_ts") or r.get("updated")), axis=1)
    out["event_age_sec"] = out["market_age_sec"]
    out["fetch_age_sec"] = out.apply(lambda r: _seconds_since(r.get("received_ts") or r.get("check_ts")), axis=1)
    out["collection_age_sec"] = out["fetch_age_sec"]
    if "route_accuracy" not in out.columns:
        out["route_accuracy"] = "REFERENCE"
    else:
        out["route_accuracy"] = out["route_accuracy"].fillna("REFERENCE")
    if "route_session" not in out.columns:
        out["route_session"] = ""
    else:
        out["route_session"] = out["route_session"].fillna("")
    out["extended_route_symbol"] = ""
    out["extended_route_price"] = np.nan
    out["extended_route_age_sec"] = np.nan
    out["extended_route_source"] = ""

    index = {str(r["symbol"]): r for _, r in out.iterrows()}
    for i, row in out.iterrows():
        sym = str(row["symbol"])
        own_age = int(row.get("market_age_sec", 999999)) if pd.notna(row.get("market_age_sec", np.nan)) else 999999
        own_stream = str(row.get("feed_mode", "")).upper() == "STREAM"
        own_fresh = own_stream and own_age <= MAX_DATA_AGE_SECONDS and pd.notna(row.get("latest_close", np.nan))
        if own_fresh:
            continue
        route_sym = LIVE_PROXY_MAP.get(sym, "")
        route = index.get(route_sym) if route_sym else None
        if route is None:
            continue
        route_age = int(route.get("market_age_sec", 999999)) if pd.notna(route.get("market_age_sec", np.nan)) else 999999
        route_stream = str(route.get("feed_mode", "")).upper() == "STREAM"
        route_price = route.get("latest_close", np.nan)
        if not route_stream or route_age > MAX_DATA_AGE_SECONDS or pd.isna(route_price):
            continue
        out.at[i, "extended_route_symbol"] = route_sym
        out.at[i, "extended_route_price"] = route_price
        out.at[i, "extended_route_age_sec"] = route_age
        out.at[i, "extended_route_source"] = str(route.get("source", "") or "")
        out.at[i, "latest_close"] = route_price
        out.at[i, "provider_ts"] = route.get("provider_ts")
        out.at[i, "received_ts"] = route.get("received_ts")
        out.at[i, "source"] = str(route.get("source", "") or "")
        out.at[i, "source_ok"] = bool(route.get("source_ok", True))
        out.at[i, "feed_mode"] = "STREAM"
        out.at[i, "price_type"] = f"EXTENDED REAL LEVEL · {route_sym}"
        out.at[i, "active_provider_symbol"] = route_sym
        out.at[i, "route_accuracy"] = "ECONOMIC EQUIVALENT"
        out.at[i, "route_session"] = "EXTENDED"
        for fld in ["bid", "ask", "bid_size", "ask_size", "spread", "book_imbalance", "orderflow_source", "volume_1s", "volume_1m", "session_volume", "volume"]:
            if fld in out.columns and fld in route.index and pd.notna(route.get(fld, np.nan)):
                out.at[i, fld] = route.get(fld)

    out["market_age_sec"] = out.apply(lambda r: _seconds_since(r.get("provider_ts") or r.get("updated")), axis=1)
    out["event_age_sec"] = out["market_age_sec"]
    out["fetch_age_sec"] = out.apply(lambda r: _seconds_since(r.get("received_ts") or r.get("check_ts")), axis=1)
    out["collection_age_sec"] = out["fetch_age_sec"]
    states = []
    collection_states = []
    for _, row in out.iterrows():
        event_age = int(row.get("market_age_sec", 999999)) if pd.notna(row.get("market_age_sec", np.nan)) else 999999
        check_age = int(row.get("fetch_age_sec", 999999)) if pd.notna(row.get("fetch_age_sec", np.nan)) else 999999
        mode = str(row.get("feed_mode", "") or "").upper()
        stream = mode == "STREAM"
        source_ok = bool(row.get("source_ok", False))
        price_ok = pd.notna(row.get("latest_close", np.nan))
        attempted = bool(row.get("check_attempted", True))
        if attempted and check_age <= MAX_DATA_AGE_SECONDS:
            collection_states.append("CHECKED" if source_ok else "CHECKED · DEGRADED")
        else:
            collection_states.append("CHECK STALE")

        if stream and source_ok and price_ok and event_age <= MAX_DATA_AGE_SECONDS:
            explicit = str(row.get("route_session", "") or "").upper()
            session_ref = str(row.get("session_reference_state", "") or "").upper()
            routed = str(row.get("route_accuracy", "") or "").upper() == "ECONOMIC EQUIVALENT"
            states.append("EXTENDED" if explicit == "EXTENDED" or routed or session_ref in {"CLOSED", "BREAK"} else "LIVE")
        elif mode == "POLL" and source_ok and price_ok and check_age <= MAX_DATA_AGE_SECONDS:
            # Fresh collection is not the same as a fresh market event. Keep both clocks visible.
            states.append("CURRENT" if event_age <= MAX_DATA_AGE_SECONDS else "CHECKED")
        elif price_ok and mode.startswith("HOLD"):
            states.append("DEGRADED")
        elif not price_ok:
            states.append("UNAVAILABLE")
        else:
            states.append("STALE")
    out["market_state"] = states
    out["collection_state"] = collection_states
    out["monitor_symbol"] = out["active_provider_symbol"].fillna(out["symbol"]).astype(str)
    out["monitor_price"] = pd.to_numeric(out["latest_close"], errors="coerce")
    out["monitor_age_sec"] = pd.to_numeric(out["collection_age_sec"], errors="coerce")
    out["monitor_source"] = out["source"].astype(str)
    out["monitor_mode"] = out["price_type"].fillna("REFERENCE").astype(str)
    out["monitor_status"] = out["market_state"].astype(str)
    out["live_proxy_symbol"] = out["extended_route_symbol"]
    out["live_proxy_price"] = out["extended_route_price"]
    out["live_proxy_age_sec"] = out["extended_route_age_sec"]
    out["live_proxy_source"] = out["extended_route_source"]
    return _apply_volume_proxies(out), hub


def score_for(sym: str, pct: float, category: str = "") -> float:
    sym = sym.upper()
    try:
        pct = float(pct)
    except Exception:
        pct = 0.0
    if not math.isfinite(pct):
        pct = 0.0
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
    out["change_pct"] = pd.to_numeric(out.get("change_pct"), errors="coerce")
    out["session_pct"] = pd.to_numeric(out.get("session_pct"), errors="coerce")
    out["score"] = out.apply(lambda r: score_for(r["symbol"], r["change_pct"], r["category"]), axis=1)
    out["state"] = out["score"].apply(state_for)
    out["quality"] = out["score"].apply(quality_for)
    if "market_state" not in out:
        out["market_state"] = out["symbol"].apply(market_state_for_symbol)
    if "market_age_sec" not in out:
        out["market_age_sec"] = out.apply(lambda r: _seconds_since(r.get("provider_ts") or r.get("updated")), axis=1)
    if "fetch_age_sec" not in out:
        out["fetch_age_sec"] = out.apply(lambda r: _seconds_since(r.get("received_ts")), axis=1)
    out["age_sec"] = out["market_age_sec"]

    def row_freshness(r: pd.Series) -> str:
        price_ok = pd.notna(r.get("latest_close", np.nan))
        mode = str(r.get("feed_mode", "") or "").upper()
        event_age = int(r.get("market_age_sec", 999999))
        check_age = int(r.get("fetch_age_sec", 999999))
        if not price_ok:
            return "NO QUOTE"
        if mode == "STREAM":
            if event_age <= 5:
                return "LIVE"
            if event_age <= MAX_DATA_AGE_SECONDS:
                return "CURRENT"
            return "STREAM STALE"
        if mode == "POLL" and check_age <= MAX_DATA_AGE_SECONDS:
            if event_age <= MAX_DATA_AGE_SECONDS:
                return "CURRENT · CHECKED"
            return f"CHECKED · EVENT {event_age}s"
        if mode.startswith("HOLD"):
            return "LAST VERIFIED"
        return "STALE"

    out["freshness"] = out.apply(row_freshness, axis=1)
    return out


def age_from_iso(value: str) -> int:
    return _seconds_since(value)


def health_state(age: int) -> tuple[str, str]:
    age = int(age)
    if age <= 5:
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
    pct = float(row["change_pct"]) if pd.notna(row.get("change_pct", np.nan)) else 0.0
    tone = "green" if pct > 0 else "red" if pct < 0 else "yellow"
    cls = "mini-inst selected" if selected else "mini-inst"
    try:
        intel = instrument_intelligence(row)
        fresh = f"{intel['status']} · C{intel['check_age_sec']}s / E{intel['event_age_sec']}s"
    except Exception:
        fresh = str(row.get("freshness", "—"))
    return (
        f"<div class='{cls}'><div class='mini-symbol'>{row['symbol']}</div>"
        f"<div class='mini-price'>{short_num(row['latest_close'])}</div>"
        f"<div class='mini-change {tone}'>{format_change(pct)}</div>"
        f"<div class='micro' style='margin-top:3px'>{fresh}</div></div>"
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
        elif low in {"age_sec", "age sec", "check age", "event age", "market age", "fetch age", "market_age_sec", "fetch_age_sec", "collection_age_sec", "event_age_sec", "check_age_sec", "monitor_age_sec", "live_proxy_age_sec", "observed_price_change_age_sec", "observed_route_change_age_sec", "observed_source_change_age_sec", "observed_state_change_age_sec"}:
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
    pct = float(row.get("change_pct", 0.0)) if pd.notna(row.get("change_pct", np.nan)) else 0.0
    freshness = str(row.get("freshness", "—"))
    market_state = str(row.get("market_state", ""))
    monitor_status = str(row.get("monitor_status", freshness) or freshness)
    monitor_symbol = str(row.get("monitor_symbol", row.get("symbol", "")) or "")
    own_symbol = str(row.get("symbol", "") or "")
    status = monitor_status if monitor_symbol == own_symbol else f"{monitor_status} · {monitor_symbol}"
    return (
        f"{row.get('symbol','—')}  ·  {row.get('name','—')}   |   "
        f"{short_num(row.get('latest_close'))}   {format_change(pct)}   ·   "
        f"{row.get('state','—')}   ·   {row.get('price_type','REFERENCE')}   ·   {status}"
    )


def render_strip_cards(view: pd.DataFrame, key_prefix: str, raw_columns: list[str] | None = None) -> None:
    """Persistent strip cards. Open state and display edits survive timed/manual refreshes."""
    if view.empty:
        st.info("No instruments match this filter.")
        return
    mode = st.radio(
        "View",
        ["Strip Cards", "Interactive Table", "Editable Table", "Raw Table"],
        index=0,
        horizontal=True,
        key=f"{key_prefix}_view_mode",
        label_visibility="collapsed",
    )
    cols = raw_columns or [c for c in view.columns if not str(c).startswith("_")]
    cols = [c for c in cols if c in view.columns]

    if mode == "Interactive Table":
        st.caption("Interactive display view · search, filter, sort, choose columns and click any row to focus it. Display overrides are applied.")
        effective = apply_df_display_overrides(view[cols].copy())
        render_interactive_table(effective, f"{key_prefix}_interactive", default_columns=cols[: min(14, len(cols))], height=420, select_symbol=True)
        return

    if mode == "Editable Table":
        st.caption("Editable display table · edits persist through refresh and immediately propagate back into the matching strip card. Live feed values remain untouched underneath.")
        render_editable_override_table(view[cols].copy(), f"{key_prefix}_editable_table", columns=cols)
        return

    if mode == "Raw Table":
        st.caption("Raw synchronized feed view · no display override is applied. Search, filter, sort and row focus remain available for audit.")
        render_interactive_table(view[cols].copy(), f"{key_prefix}_raw", default_columns=cols[: min(14, len(cols))], height=420, select_symbol=True)
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


def _collection_metrics(rows: pd.DataFrame) -> dict:
    """Collection health is based on source-check age, never route/session labels.

    Market-event age remains a separate diagnostic clock. A fresh POLL/REFERENCE
    collection is therefore CURRENT, not IDLE, even when the latest market event
    has not changed since the previous check.
    """
    if rows is None or rows.empty:
        return {"total": 0, "fresh": 0, "age": None, "status": "NO DATA", "tone": "red", "feed": "NONE"}

    age_col = "collection_age_sec" if "collection_age_sec" in rows.columns else "fetch_age_sec"
    ages = pd.to_numeric(rows.get(age_col, pd.Series(index=rows.index, dtype=float)), errors="coerce")
    valid_ages = ages[np.isfinite(ages)]
    total = int(len(rows))
    fresh_mask = ages.notna() & np.isfinite(ages) & (ages <= MAX_DATA_AGE_SECONDS)
    fresh = int(fresh_mask.sum())
    max_age = int(valid_ages.max()) if len(valid_ages) else None

    states = rows.get("collection_state", pd.Series([""] * total, index=rows.index)).fillna("").astype(str).str.upper()
    degraded = states.str.contains("DEGRADED", regex=False).any()

    if fresh == total and total > 0:
        status = "DEGRADED" if degraded else "CURRENT"
        tone = "yellow" if degraded else "green"
    elif fresh > 0:
        status = "PARTIAL"
        tone = "yellow"
    else:
        status = "STALE"
        tone = "red"

    modes = []
    if "feed_mode" in rows.columns:
        for value in rows["feed_mode"].dropna().astype(str).str.upper():
            value = value.strip()
            if not value or value == "UNAVAILABLE":
                continue
            if value.startswith("HOLD"):
                value = "HOLD"
            modes.append(value)
    unique_modes = sorted(set(modes))
    feed = unique_modes[0] if len(unique_modes) == 1 else ("MIXED" if unique_modes else "UNKNOWN")

    return {"total": total, "fresh": fresh, "age": max_age, "status": status, "tone": tone, "feed": feed}


def health_rows(df: pd.DataFrame, selected_symbol: str) -> list[dict]:
    groups: list[tuple[str, pd.DataFrame]] = [
        ("Core", df[df["symbol"].isin(CORE)]),
        ("Selected", df[df["symbol"] == selected_symbol]),
        ("Sectors", df[df["category"].isin(["Sectors", "AI / Tech", "Healthcare / Science", "Defense / Aero", "Real Estate"])]),
        ("Universe", df),
    ]
    output: list[dict] = []
    for name, subset in groups:
        metrics = _collection_metrics(subset)
        metrics["name"] = name
        output.append(metrics)
    return output


def option_underlying_for(symbol: str) -> str:
    symbol = str(symbol or "").upper()
    if symbol in OPTION_UNDERLYING_MAP:
        return OPTION_UNDERLYING_MAP[symbol]
    # Equities/ETFs in the universal instrument map are option-query candidates.
    if symbol and not symbol.startswith("^") and "=" not in symbol and not symbol.endswith("-USD"):
        return symbol
    return ""


def normalize_option_chain(rows: list[dict]) -> pd.DataFrame:
    out = []
    for item in rows or []:
        details = item.get("details") or {}
        day = item.get("day") or {}
        quote = item.get("last_quote") or {}
        trade = item.get("last_trade") or {}
        greeks = item.get("greeks") or {}
        underlying = item.get("underlying_asset") or {}
        bid = pd.to_numeric(quote.get("bid"), errors="coerce")
        ask = pd.to_numeric(quote.get("ask"), errors="coerce")
        midpoint = pd.to_numeric(quote.get("midpoint"), errors="coerce")
        if pd.isna(midpoint) and pd.notna(bid) and pd.notna(ask):
            midpoint = (float(bid) + float(ask)) / 2.0
        out.append({
            "contract": details.get("ticker"),
            "type": str(details.get("contract_type") or "").upper(),
            "expiration": details.get("expiration_date"),
            "strike": pd.to_numeric(details.get("strike_price"), errors="coerce"),
            "bid": bid, "ask": ask, "mid": midpoint,
            "last": pd.to_numeric(trade.get("price"), errors="coerce"),
            "volume": pd.to_numeric(day.get("volume"), errors="coerce"),
            "open_interest": pd.to_numeric(item.get("open_interest"), errors="coerce"),
            "iv": pd.to_numeric(item.get("implied_volatility"), errors="coerce"),
            "delta": pd.to_numeric(greeks.get("delta"), errors="coerce"),
            "gamma": pd.to_numeric(greeks.get("gamma"), errors="coerce"),
            "theta": pd.to_numeric(greeks.get("theta"), errors="coerce"),
            "vega": pd.to_numeric(greeks.get("vega"), errors="coerce"),
            "quote_timeframe": quote.get("timeframe"),
            "trade_timeframe": trade.get("timeframe"),
            "underlying_price": pd.to_numeric(underlying.get("price"), errors="coerce"),
            "underlying_timeframe": underlying.get("timeframe"),
        })
    return pd.DataFrame(out)


def option_chain_summary(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {"contracts": 0, "call_oi": np.nan, "put_oi": np.nan, "call_volume": np.nan, "put_volume": np.nan, "avg_iv": np.nan, "timeframe": "UNAVAILABLE"}
    calls = df[df["type"] == "CALL"]
    puts = df[df["type"] == "PUT"]
    frames = [str(x).upper() for x in pd.concat([df["quote_timeframe"], df["trade_timeframe"]]).dropna().unique().tolist()]
    timeframe = "REAL-TIME" if any("REAL" in x for x in frames) else "DELAYED" if frames else "UNKNOWN"
    return {
        "contracts": int(len(df)),
        "call_oi": float(pd.to_numeric(calls["open_interest"], errors="coerce").fillna(0).sum()),
        "put_oi": float(pd.to_numeric(puts["open_interest"], errors="coerce").fillna(0).sum()),
        "call_volume": float(pd.to_numeric(calls["volume"], errors="coerce").fillna(0).sum()),
        "put_volume": float(pd.to_numeric(puts["volume"], errors="coerce").fillna(0).sum()),
        "avg_iv": float(pd.to_numeric(df["iv"], errors="coerce").dropna().median()) if pd.to_numeric(df["iv"], errors="coerce").notna().any() else np.nan,
        "timeframe": timeframe,
    }


def health_card(df: pd.DataFrame, selected_symbol: str) -> str:
    pieces = ["<div class='card'><div class='section-title'>Active Market Collection Health · Max 25s</div><div class='health-grid'>"]
    for item in health_rows(df, selected_symbol):
        age_text = "—" if item["age"] is None else f"{item['age']:02d}s"
        coverage = f"{item['fresh']}/{item['total']}" if item["total"] else "0/0"
        pieces.append(
            f"<div>{item['name']}</div>"
            f"<div class='{item['tone']}'>{item['status']} · {coverage} · {age_text} · {item['feed']}</div>"
        )
    pieces.append("</div><div class='micro' style='margin-top:6px'>Collection health uses CHECK AGE. Provider EVENT AGE remains separate in Diagnostics/Data Health.</div></div>")
    return "".join(pieces)




def _safe_age(row: pd.Series, *keys: str, default: int = 999999) -> int:
    for key in keys:
        value = row.get(key, np.nan)
        try:
            if pd.notna(value) and np.isfinite(float(value)):
                return max(0, int(float(value)))
        except Exception:
            continue
    return default


def _real_route_expected(row: pd.Series) -> bool:
    feed_mode = str(row.get("feed_mode", "") or "").upper()
    price_type = str(row.get("price_type", "") or "").upper()
    market_state = str(row.get("market_state", "") or "").upper()
    source = str(row.get("source", "") or "").upper()
    return (
        any(token in feed_mode for token in ("STREAM", "BROKER", "DIRECT"))
        or any(token in price_type for token in ("BROKER", "DIRECT", "LIVE"))
        or market_state in {"LIVE", "EXTENDED"}
        or source.startswith("MT5")
    )


def instrument_intelligence(row: pd.Series) -> dict:
    """Decision-facing health summary for one instrument.

    The collection clock answers whether the engine is checking the route. The event
    clock answers whether the provider has actually published a new market event.
    They are deliberately not conflated.
    """
    symbol = str(row.get("symbol", "—") or "—")
    price = pd.to_numeric(row.get("latest_close", np.nan), errors="coerce")
    check_age = _safe_age(row, "collection_age_sec", "fetch_age_sec")
    event_age = _safe_age(row, "event_age_sec", "market_age_sec")
    monitor_age = _safe_age(row, "monitor_age_sec")
    collection_state = str(row.get("collection_state", "") or "").upper()
    market_state = str(row.get("market_state", "") or "").upper()
    feed_mode = str(row.get("feed_mode", "") or "").upper()
    source = str(row.get("source", "") or "")
    price_type = str(row.get("price_type", "REFERENCE") or "REFERENCE")
    source_ok = bool(row.get("source_ok", True))
    direct_expected = _real_route_expected(row)

    active_provider = str(row.get("active_provider_symbol", "") or "")
    monitor_symbol = str(row.get("monitor_symbol", "") or "")
    proxy_symbol = str(row.get("live_proxy_symbol", "") or "")
    best_route = active_provider or (monitor_symbol if monitor_symbol and monitor_symbol != symbol else "") or proxy_symbol or symbol

    if pd.isna(price) or market_state == "UNAVAILABLE" or not source_ok and check_age > MAX_DATA_AGE_SECONDS:
        status, tone, severity = "UNAVAILABLE", "red", 4
        issue = "NO VALID CURRENT LEVEL"
        action = "RECOVER LIVE ROUTE"
    elif check_age > MAX_DATA_AGE_SECONDS:
        status, tone, severity = "STALE", "red", 3
        issue = f"COLLECTION LATE · {check_age}s"
        action = "RETRY / FAILOVER"
    elif not source_ok:
        status, tone, severity = "DEGRADED", "yellow", 2
        issue = "SOURCE CHECK FAILED"
        action = "VERIFY FAILOVER"
    elif direct_expected and event_age > MAX_DATA_AGE_SECONDS:
        status, tone, severity = "WATCH", "yellow", 2
        issue = f"DIRECT EVENT LATE · {event_age}s"
        action = "CHECK LIVE ROUTE"
    elif "DEGRADED" in collection_state:
        status, tone, severity = "DEGRADED", "yellow", 2
        issue = "PRIMARY ROUTE DEGRADED"
        action = "VERIFY FAILOVER"
    elif ("POLL" in feed_mode or "FALLBACK" in feed_mode or "YFINANCE" in source.upper()) and event_age > 90:
        status, tone, severity = "WATCH", "yellow", 1
        issue = f"POLL EVENT AGE · {event_age}s"
        action = "PREFER DIRECT FEED"
    elif direct_expected:
        status, tone, severity = "LIVE", "green", 0
        issue = "NONE"
        action = "USE CURRENT LEVEL"
    else:
        status, tone, severity = "CURRENT", "green", 0
        if "POLL" in feed_mode or "FALLBACK" in feed_mode or "YFINANCE" in source.upper():
            issue = f"REFERENCE/POLL · EVENT {event_age}s"
            action = "DIRECT FEED FOR TICKS"
        else:
            issue = "NONE"
            action = "USE CURRENT CHECK"

    route_label = f"{best_route} · {price_type}"
    if source:
        route_label += f" · {source.split('·')[0].strip()}"

    return {
        "symbol": symbol,
        "status": status,
        "tone": tone,
        "severity": severity,
        "issue": issue,
        "action": action,
        "check_age_sec": check_age,
        "event_age_sec": event_age,
        "monitor_age_sec": monitor_age,
        "route": route_label,
        "best_route": best_route,
        "feed_mode": feed_mode or "—",
        "source": source or "—",
        "price_type": price_type,
        "market_state": market_state or "—",
    }


def update_observed_change_tracker(df: pd.DataFrame) -> pd.DataFrame:
    """Track what changed between dashboard observations without altering feed data."""
    out = df.copy()
    tracker = st.session_state.setdefault("_instrument_change_tracker", {})
    now_ts = time.time()
    price_ages: list[float] = []
    route_ages: list[float] = []
    source_ages: list[float] = []
    state_ages: list[float] = []

    for _, row in out.iterrows():
        symbol = str(row.get("symbol", ""))
        price = pd.to_numeric(row.get("latest_close", np.nan), errors="coerce")
        route = str(row.get("active_provider_symbol", "") or row.get("monitor_symbol", "") or symbol)
        source = str(row.get("source", "") or "")
        state = str(row.get("market_state", "") or row.get("freshness", "") or "")
        old = tracker.get(symbol)
        if old is None:
            tracker[symbol] = {
                "price": float(price) if pd.notna(price) else np.nan,
                "route": route,
                "source": source,
                "state": state,
                "price_changed_at": None,
                "route_changed_at": None,
                "source_changed_at": None,
                "state_changed_at": None,
                "first_seen_at": now_ts,
            }
            old = tracker[symbol]
        else:
            old_price = old.get("price", np.nan)
            if pd.notna(price) and (pd.isna(old_price) or not math.isclose(float(price), float(old_price), rel_tol=0.0, abs_tol=1e-12)):
                old["price_changed_at"] = now_ts
                old["price"] = float(price)
            if route != old.get("route"):
                old["route_changed_at"] = now_ts
                old["route"] = route
            if source != old.get("source"):
                old["source_changed_at"] = now_ts
                old["source"] = source
            if state != old.get("state"):
                old["state_changed_at"] = now_ts
                old["state"] = state

        def _age(field: str) -> float:
            stamp = old.get(field)
            return max(0.0, now_ts - float(stamp)) if stamp else np.nan

        price_ages.append(_age("price_changed_at"))
        route_ages.append(_age("route_changed_at"))
        source_ages.append(_age("source_changed_at"))
        state_ages.append(_age("state_changed_at"))

    out["observed_price_change_age_sec"] = price_ages
    out["observed_route_change_age_sec"] = route_ages
    out["observed_source_change_age_sec"] = source_ages
    out["observed_state_change_age_sec"] = state_ages
    return out


def _age_label(value) -> str:
    try:
        if pd.isna(value):
            return "not changed this session"
        sec = max(0, int(float(value)))
    except Exception:
        return "—"
    if sec < 60:
        return f"{sec}s ago"
    if sec < 3600:
        return f"{sec // 60}m {sec % 60:02d}s ago"
    return f"{sec // 3600}h {(sec % 3600) // 60:02d}m ago"


def immediate_action_html(row: pd.Series) -> str:
    info = instrument_intelligence(row)
    driver = str(row.get("driver", "—") or "—")
    price_change_age = _age_label(row.get("observed_price_change_age_sec", np.nan))
    check = info["check_age_sec"]
    event = info["event_age_sec"]
    return (
        "<div class='action-read'>"
        "<div class='headline'>"
        f"<b>Immediate read</b>{chip_html(info['status'], info['tone'])}"
        "</div><div class='action-grid'>"
        f"<div class='action-cell'><div class='k'>Active level</div><div class='v'>{short_num(row.get('latest_close'))}</div></div>"
        f"<div class='action-cell'><div class='k'>Best route</div><div class='v'>{info['best_route']}</div></div>"
        f"<div class='action-cell'><div class='k'>Check / event</div><div class='v'>{check}s / {event}s</div></div>"
        f"<div class='action-cell'><div class='k'>Driver</div><div class='v'>{driver}</div></div>"
        f"<div class='action-cell'><div class='k'>Issue</div><div class='v'>{info['issue']}</div></div>"
        f"<div class='action-cell'><div class='k'>Last observed move</div><div class='v'>{price_change_age}</div></div>"
        "</div></div>"
    )


def attention_frame(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for _, row in df.iterrows():
        info = instrument_intelligence(row)
        rows.append({
            "symbol": row.get("symbol"),
            "name": row.get("name"),
            "category": row.get("category"),
            "status": info["status"],
            "issue": info["issue"],
            "active_level": row.get("latest_close"),
            "change_pct": row.get("change_pct"),
            "check_age_sec": info["check_age_sec"],
            "event_age_sec": info["event_age_sec"],
            "best_route": info["best_route"],
            "feed_mode": row.get("feed_mode", "—"),
            "source": row.get("source", "—"),
            "driver": row.get("driver", "—"),
            "action": info["action"],
            "_severity": info["severity"],
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out = out.sort_values(["_severity", "check_age_sec", "event_age_sec"], ascending=[False, False, False])
    return out


def _health_counts(df: pd.DataFrame) -> dict[str, int]:
    counts = {"ALL": int(len(df)), "ATTENTION": 0, "LIVE": 0, "CURRENT": 0, "WATCH": 0, "DEGRADED": 0, "STALE": 0, "UNAVAILABLE": 0}
    for _, row in df.iterrows():
        status = instrument_intelligence(row)["status"]
        counts[status] = counts.get(status, 0) + 1
        if status in {"WATCH", "DEGRADED", "STALE", "UNAVAILABLE"}:
            counts["ATTENTION"] += 1
    return counts


def _set_health_focus(value: str) -> None:
    st.session_state["dashboard_health_focus"] = value


def render_health_quick_panel(df: pd.DataFrame) -> None:
    counts = _health_counts(df)
    focus = st.session_state.get("dashboard_health_focus", "ATTENTION")
    st.markdown("<div class='section-title'>Market Health · click to filter</div>", unsafe_allow_html=True)
    grid = [("ATTN", "ATTENTION"), ("ALL", "ALL"), ("LIVE", "LIVE"), ("CURRENT", "CURRENT"), ("WATCH", "WATCH"), ("DEGRADED", "DEGRADED"), ("STALE", "STALE"), ("UNAVAIL", "UNAVAILABLE")]
    for start in range(0, len(grid), 2):
        cols = st.columns(2, gap="small")
        for col, (label, value) in zip(cols, grid[start:start + 2]):
            with col:
                count = counts.get(value, 0)
                st.button(
                    f"{label} · {count}",
                    key=f"health_focus_{value}",
                    use_container_width=True,
                    on_click=_set_health_focus,
                    args=(value,),
                )
    st.caption(f"Active filter: {focus} · collection clock and provider-event clock remain separate.")


def _quick_filter_mask(df: pd.DataFrame, quick: str) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=bool, index=df.index)
    if "status" in df.columns and df["status"].astype(str).str.upper().isin(["LIVE", "CURRENT", "WATCH", "DEGRADED", "STALE", "UNAVAILABLE"]).any():
        statuses = df["status"].fillna("").astype(str).str.upper()
    else:
        statuses = df.apply(lambda r: instrument_intelligence(r)["status"], axis=1)
    if quick == "Attention":
        return statuses.isin(["WATCH", "DEGRADED", "STALE", "UNAVAILABLE"])
    if quick == "Live / Current":
        return statuses.isin(["LIVE", "CURRENT"])
    if quick == "Stale / Unavailable":
        return statuses.isin(["STALE", "UNAVAILABLE"])
    if quick == "Direct live":
        return df.apply(_real_route_expected, axis=1)
    if quick == "Poll / fallback":
        mode = df.get("feed_mode", pd.Series([""] * len(df), index=df.index)).fillna("").astype(str).str.upper()
        source = df.get("source", pd.Series([""] * len(df), index=df.index)).fillna("").astype(str).str.upper()
        return mode.str.contains("POLL|FALLBACK", regex=True) | source.str.contains("YFINANCE", regex=False)
    return pd.Series(True, index=df.index)


def render_interactive_table(
    df: pd.DataFrame,
    key: str,
    *,
    default_columns: list[str] | None = None,
    height: int = 330,
    select_symbol: bool = True,
    forced_status: str | None = None,
    max_rows: int | None = None,
) -> pd.DataFrame:
    """Native Streamlit table console: search, filters, sorting, column control and row focus."""
    work = df.copy()
    if work.empty:
        st.info("No rows match this view.")
        return work

    all_columns = [str(c) for c in work.columns if not str(c).startswith("_")]
    default_columns = [c for c in (default_columns or all_columns) if c in all_columns]
    if not default_columns:
        default_columns = all_columns[: min(12, len(all_columns))]

    t1, t2, t3 = st.columns([2.0, 1.2, 1.2], gap="small")
    with t1:
        search = st.text_input("Search table", key=f"{key}_search", placeholder="symbol, source, driver, issue…", label_visibility="collapsed")
    with t2:
        quick = st.selectbox(
            "Quick filter",
            ["All", "Attention", "Live / Current", "Stale / Unavailable", "Direct live", "Poll / fallback"],
            key=f"{key}_quick",
            label_visibility="collapsed",
        )
    with t3:
        sort_col = st.selectbox("Sort", ["Keep current order"] + all_columns, key=f"{key}_sort", label_visibility="collapsed")

    with st.popover("FILTERS / COLUMNS", use_container_width=True):
        categories = []
        if "category" in work.columns:
            categories = st.multiselect("Category", sorted(work["category"].dropna().astype(str).unique().tolist()), key=f"{key}_cats")
        sources = []
        if "source" in work.columns:
            sources = st.multiselect("Source", sorted(work["source"].dropna().astype(str).unique().tolist()), key=f"{key}_sources")
        feeds = []
        if "feed_mode" in work.columns:
            feeds = st.multiselect("Feed mode", sorted(work["feed_mode"].dropna().astype(str).unique().tolist()), key=f"{key}_feeds")
        visible = st.multiselect("Visible columns", all_columns, default=default_columns, key=f"{key}_visible")
        direction = st.radio("Sort direction", ["Descending", "Ascending"], horizontal=True, key=f"{key}_direction")
        csv_bytes = work[all_columns].to_csv(index=False).encode("utf-8")
        st.download_button("EXPORT CURRENT DATASET", csv_bytes, file_name=f"{key}.csv", mime="text/csv", use_container_width=True, key=f"{key}_download")

    mask = pd.Series(True, index=work.index)
    if search:
        needle = search.strip().upper()
        search_cols = [c for c in all_columns if work[c].dtype == object or c in {"symbol", "name", "source", "driver", "status", "issue"}]
        if search_cols:
            text = work[search_cols].fillna("").astype(str).agg(" ".join, axis=1).str.upper()
            mask &= text.str.contains(needle, regex=False)
    if quick != "All":
        mask &= _quick_filter_mask(work, quick)
    if "status" in work.columns and work["status"].astype(str).str.upper().isin(["LIVE", "CURRENT", "WATCH", "DEGRADED", "STALE", "UNAVAILABLE"]).any():
        health_statuses = work["status"].fillna("").astype(str).str.upper()
    else:
        health_statuses = work.apply(lambda r: instrument_intelligence(r)["status"], axis=1)
    if forced_status and forced_status not in {"ALL", "ATTENTION"}:
        mask &= health_statuses.eq(forced_status)
    elif forced_status == "ATTENTION":
        mask &= health_statuses.isin(["WATCH", "DEGRADED", "STALE", "UNAVAILABLE"])
    if "category" in work.columns and categories:
        mask &= work["category"].astype(str).isin(categories)
    if "source" in work.columns and sources:
        mask &= work["source"].astype(str).isin(sources)
    if "feed_mode" in work.columns and feeds:
        mask &= work["feed_mode"].astype(str).isin(feeds)

    filtered = work.loc[mask].copy()
    if sort_col != "Keep current order" and sort_col in filtered.columns:
        try:
            filtered = filtered.sort_values(sort_col, ascending=(direction == "Ascending"), na_position="last")
        except Exception:
            filtered = filtered.sort_values(sort_col, key=lambda s: s.astype(str), ascending=(direction == "Ascending"), na_position="last")
    if max_rows:
        filtered = filtered.head(max_rows)

    shown_cols = [c for c in visible if c in filtered.columns]
    symbol_col = "symbol" if "symbol" in filtered.columns else "SOURCE" if "SOURCE" in filtered.columns else None
    if select_symbol and symbol_col and symbol_col not in shown_cols:
        shown_cols = [symbol_col] + shown_cols
    if not shown_cols:
        shown_cols = all_columns[: min(8, len(all_columns))]

    table_df = filtered[shown_cols].copy()
    try:
        event = st.dataframe(
            table_df,
            use_container_width=True,
            hide_index=True,
            height=height,
            column_config=_table_column_config(shown_cols),
            key=f"{key}_grid",
            on_select="rerun",
            selection_mode="single-row",
        )
        rows = list(getattr(getattr(event, "selection", None), "rows", []) or [])
        if select_symbol and rows and symbol_col and symbol_col in table_df.columns:
            selected_row = int(rows[0])
            if 0 <= selected_row < len(table_df):
                symbol = str(table_df.iloc[selected_row][symbol_col])
                if symbol and st.session_state.get("selected_symbol") != symbol:
                    st.session_state.selected_symbol = symbol
                    st.rerun()
    except TypeError:
        # Backward-compatible rendering if an older Streamlit runtime lacks row-selection callbacks.
        st.dataframe(table_df, use_container_width=True, hide_index=True, height=height, column_config=_table_column_config(shown_cols))
    st.caption(f"Showing {len(table_df)}/{len(work)} rows · click a row to focus the instrument · column headers sort · toolbar search/download remain available.")
    return filtered


def render_editable_override_table(df: pd.DataFrame, key: str, *, columns: list[str] | None = None) -> pd.DataFrame:
    """Editable table that persists display overrides by symbol, independent of row order."""
    if df.empty:
        st.info("No rows match this view.")
        return df
    cols = [c for c in (columns or list(df.columns)) if c in df.columns]
    effective = apply_df_display_overrides(df[cols].copy())
    edited = render_editable_table(effective, key, disabled=["symbol"] if "symbol" in cols else [])
    any_change = False
    if "symbol" in effective.columns and "symbol" in edited.columns:
        baseline = effective.set_index("symbol", drop=False)
        for _, edited_row in edited.iterrows():
            symbol = str(edited_row.get("symbol", ""))
            if symbol in baseline.index:
                original = baseline.loc[symbol]
                if isinstance(original, pd.DataFrame):
                    original = original.iloc[0]
                if save_symbol_display_overrides(symbol, original, edited_row, cols):
                    any_change = True
    if any_change:
        st.rerun()
    return edited


def render_sidebar() -> tuple[str, bool, int]:
    with st.sidebar:
        st.markdown(f"<div class='mid'>🌐 MACRO REGIME ENGINE <span class='cyan'>{APP_VERSION}</span></div><div class='small'>IMMEDIATE INTELLIGENCE ROUTER · GEO + MARKET</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:5px'></div>", unsafe_allow_html=True)
        pages = [
            "Dashboard", "Instruments", "Flow Tracker", "Options / Pressure", "Sectors", "Defense / Aero",
            "Real Estate", "Healthcare / Science", "Geo / Global", "Global Sessions", "Events", "Data Health", "Raw Data",
        ]
        page = st.radio("", pages, index=0, label_visibility="collapsed")
        st.markdown("---")
        auto = st.toggle("Auto refresh", value=True)
        interval = st.selectbox("UI refresh", [1, 2, 5, 10, 15, 20, 25], index=1, format_func=lambda x: f"{x} sec")
        st.caption("Universal router runs continuously · actual provider/broker levels · UI redraw independent · SLA ≤25s")

        with st.expander("LIVE DATA CONNECTIONS", expanded=False):
            enabled = st.toggle("Live providers enabled", key="live_providers_enabled", on_change=_provider_enabled_changed)
            massive_origin = _credential_origin("MASSIVE_API_KEY")
            databento_origin = _credential_origin("DATABENTO_API_KEY")
            dxfeed_origin = "CONFIGURED" if (_stored_secret("DXFEED_REST_URL") or st.session_state.get("runtime_dxfeed_rest_url")) else "NOT CONFIGURED"
            mt5_origin = "AUTO-DETECT"
            st.caption(f"dxFeed: {dxfeed_origin} · MT5: {mt5_origin} · Massive: {massive_origin} · Databento: {databento_origin}")
            st.caption("Every LIVE/EXTENDED state requires an actual fresh provider quote/trade timestamp. dxFeed is the preferred U.S. overnight stock/ETF layer when entitled.")
            st.caption("Credentials entered here stay in this Streamlit session. Deployment Secrets remain persistent.")
            st.text_input("dxFeed REST events URL", key="dxfeed_url_entry", placeholder="Production .../webservice/rest/events.json")
            st.text_input("dxFeed username (optional)", key="dxfeed_user_entry", placeholder="Basic-auth username")
            st.text_input("dxFeed password (optional)", type="password", key="dxfeed_password_entry", placeholder="Basic-auth password")
            st.text_input("dxFeed bearer token (optional)", type="password", key="dxfeed_token_entry", placeholder="Bearer token")
            massive_entry = st.text_input("Massive API key", type="password", key="massive_key_entry", placeholder="Paste key or leave blank to use existing secret")
            databento_entry = st.text_input("Databento API key", type="password", key="databento_key_entry", placeholder="Paste key or leave blank to use existing secret")
            c1, c2 = st.columns(2)
            with c1:
                st.button("CONNECT / RESTART", key="provider_connect", use_container_width=True, on_click=_provider_connect_callback)
            with c2:
                st.button("PAUSE STREAMS", key="provider_pause", use_container_width=True, on_click=_provider_pause_callback)
            if not enabled:
                st.warning("Live providers are paused. The app will use timestamp-correct fallback checks only.")

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
st.session_state.setdefault("live_providers_enabled", True)
st.session_state.setdefault("runtime_massive_api_key", "")
st.session_state.setdefault("runtime_databento_api_key", "")
st.session_state.setdefault("runtime_dxfeed_rest_url", "")
st.session_state.setdefault("runtime_dxfeed_username", "")
st.session_state.setdefault("runtime_dxfeed_password", "")
st.session_state.setdefault("runtime_dxfeed_token", "")
st.session_state.setdefault("runtime_dxfeed_symbol_map_json", "")
st.session_state.setdefault("dashboard_health_focus", "ATTENTION")

page, auto_refresh, refresh_interval = render_sidebar()
if auto_refresh and st_autorefresh:
    st_autorefresh(interval=min(refresh_interval, MAX_DATA_AGE_SECONDS) * 1000, key="global_refresh_v103")

# One universe state, continuously overlaid by provider WebSockets. Stream ingestion is
# independent of Streamlit reruns; every page reads the same thread-safe live hub.
raw_universe, live_hub = build_market_snapshot(tuple(SYMBOLS))
universe_df = update_observed_change_tracker(enrich(raw_universe))
_active = universe_df[universe_df["market_state"].isin(["LIVE", "EXTENDED"])] if not universe_df.empty else universe_df
snapshot_age = int(_active["market_age_sec"].max()) if len(_active) else 0
snapshot_state, snapshot_tone = health_state(snapshot_age) if len(_active) else ("IDLE", "yellow")
_check_age = pd.to_numeric(universe_df.get("collection_age_sec", universe_df.get("fetch_age_sec", pd.Series(dtype=float))), errors="coerce")
check_total = int(len(universe_df))
check_fresh = int((_check_age <= MAX_DATA_AGE_SECONDS).sum()) if check_total else 0
check_stale = max(0, check_total - check_fresh)
active_total = int(len(_active))
active_fresh = int((pd.to_numeric(_active.get("market_age_sec", pd.Series(dtype=float)), errors="coerce") <= MAX_DATA_AGE_SECONDS).sum()) if active_total else 0
active_stale = max(0, active_total - active_fresh)
health_counts = _health_counts(universe_df)
check_tone = "green" if check_stale == 0 else "yellow" if check_fresh >= max(1, int(check_total * .85)) else "red"
provider_status = live_hub.provider_status()
provider_config = live_hub.configured_summary()

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
    st.markdown(f"<div class='micro'>Collection</div><div class='{check_tone}' style='font-weight:900'>{check_fresh}/{check_total} ≤25s</div>", unsafe_allow_html=True)
with h4:
    pstat_header = pd.DataFrame(provider_status)
    mt5_live = False
    massive_live = False
    databento_live = False
    dxfeed_live = False
    if not pstat_header.empty:
        live_mask = pstat_header["connected"].fillna(False) & pstat_header["authenticated"].fillna(False)
        mt5_live = bool(((pstat_header["provider"] == "mt5") & live_mask).any())
        massive_live = bool(((pstat_header["provider"] == "massive") & live_mask).any())
        databento_live = bool(((pstat_header["provider"] == "databento") & live_mask).any())
        dxfeed_live = bool(((pstat_header["provider"] == "dxfeed") & live_mask).any())
    live_count = int(mt5_live) + int(massive_live) + int(databento_live) + int(dxfeed_live)
    configured_count = sum(int(bool(provider_config.get(k))) for k in ("mt5", "massive", "databento", "dxfeed"))
    if live_count:
        engine_text = f"{live_count} SOURCE{'S' if live_count != 1 else ''} STREAMING · UI {refresh_interval}s"
    elif configured_count:
        engine_text = f"CONNECTING · UI {refresh_interval}s"
    else:
        engine_text = f"PUBLIC CHECK · UI {refresh_interval}s"
    st.markdown(f"<div class='micro'>Live Engine</div><div class='mid'>{engine_text}</div>", unsafe_allow_html=True)
with h5:
    if st.button("↻ UPDATE", key="global_update"):
        fetch_universe_snapshot.clear()
        st.session_state.last_manual_update = time.time()
        st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

selected_symbol = st.session_state.selected_symbol
selected = apply_row_display_overrides(get_row(universe_df, selected_symbol))
related = related_symbols(selected_symbol)
rel_df = apply_df_display_overrides(universe_df[universe_df["symbol"].isin(related)].copy())
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
            st.markdown(card_html("Live Checks", f"{check_fresh}/{check_total}", f"live {health_counts.get('LIVE',0)} · current {health_counts.get('CURRENT',0)} · attn {health_counts.get('ATTENTION',0)}", check_tone, "≤25s"), unsafe_allow_html=True)

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
            st.markdown(immediate_action_html(selected), unsafe_allow_html=True)
            with st.popover("Provider audit", use_container_width=True):
                intel = instrument_intelligence(selected)
                st.metric("Usability", intel["status"])
                st.caption(f"Active level: {short_num(selected.get('latest_close'))}")
                st.caption(f"Best route: {intel['route']}")
                st.caption(f"Check age: {intel['check_age_sec']} sec · provider event age: {intel['event_age_sec']} sec")
                st.caption(f"Issue: {intel['issue']} · action: {intel['action']}")
                st.caption(f"Category: {selected['category']} · driver: {selected['driver']}")
                st.caption(f"Market state: {selected.get('market_state','—')} · feed: {selected.get('feed_mode','—')}")
                st.caption(f"Last provider event: {selected.get('provider_ts') or '—'}")
                st.caption(f"Last observed price move: {_age_label(selected.get('observed_price_change_age_sec', np.nan))}")
                st.caption(f"Last observed route change: {_age_label(selected.get('observed_route_change_age_sec', np.nan))}")
                if pd.notna(selected.get("reference_price", np.nan)):
                    st.caption(f"Reference: {short_num(selected.get('reference_price'))} · {selected.get('reference_source','—')} · {selected.get('reference_provider_ts') or '—'}")
                if selected.get("live_proxy_symbol"):
                    st.caption(f"Live proxy: {selected.get('live_proxy_symbol')} @ {short_num(selected.get('live_proxy_price'))} · age {int(selected.get('live_proxy_age_sec',999999))}s")

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
            book_imb = float(selected.get("book_imbalance", np.nan)) if pd.notna(selected.get("book_imbalance", np.nan)) else np.nan
            if pd.notna(book_imb):
                pressure = "Bid-led" if book_imb > 0.12 else "Ask-led" if book_imb < -0.12 else "Balanced"
                absorption = "Two-sided" if abs(book_imb) < 0.12 else "Directional"
            else:
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
                    f"<div class='rowline'><span>L1 imbalance</span><b>{'N/A' if pd.isna(book_imb) else f'{book_imb:+.2f}'}</b></div>"
                    f"<div class='rowline'><span>Absorption</span><b>{absorption}</b></div></div>",
                    unsafe_allow_html=True,
                )
                with st.popover("Open flow", use_container_width=True):
                    st.write("Where live quote entitlement exists, bid/ask and L1 imbalance come directly from Massive NBBO or Databento MBP-1. Other instruments retain the synchronized proxy layer.")
                    mini_cols = [c for c in ["symbol", "change_pct", "bid", "ask", "bid_size", "ask_size", "book_imbalance", "spread", "orderflow_source", "volume_1m", "session_volume", "relative_volume", "volume_delta_pct", "volume_source", "score", "state"] if c in rel_df.columns]
                    render_interactive_table(rel_df[mini_cols].head(10), "dashboard_flow_table", default_columns=mini_cols, height=280, select_symbol=True)
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
                    render_interactive_table(drivers, "dashboard_driver_table", default_columns=list(drivers.columns), height=260, select_symbol=True)

        with right:
            render_health_quick_panel(universe_df)
            st.markdown("<div style='height:7px'></div>", unsafe_allow_html=True)
            selected_intel = instrument_intelligence(selected)
            alerts = [
                (selected["symbol"], selected_intel["status"]),
                ("Issue", selected_intel["issue"]),
                ("Driver", cause["cause"]),
                ("Checks", f"{check_fresh}/{check_total} ≤25s"),
            ]
            alert_html = "<div class='card compact'><div class='section-title'>Immediate Alerts</div>" + "".join(
                f"<div class='rowline'><span>{a}</span><b>{b}</b></div>" for a, b in alerts
            ) + "</div>"
            st.markdown(alert_html, unsafe_allow_html=True)
            with st.popover("Data audit", use_container_width=True):
                st.write("Collection health and provider-event health are tracked separately. A current check does not manufacture a current market event.")
                st.caption(f"Snapshot created: {universe_df['updated'].iloc[0] if len(universe_df) else '—'}")
                st.caption(f"Provider rows OK: {int(universe_df['source_ok'].sum())}/{len(universe_df)}")
                st.caption(f"Selected route: {selected_intel['route']}")

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        attention = attention_frame(universe_df)
        focus = st.session_state.get("dashboard_health_focus", "ATTENTION")
        if focus == "ATTENTION":
            focus_rows = attention[attention["status"].isin(["WATCH", "DEGRADED", "STALE", "UNAVAILABLE"])].copy()
            if focus_rows.empty:
                focus_rows = attention.head(12).copy()
                attention_note = "No critical attention rows right now · showing the slowest/current routes for verification."
            else:
                attention_note = "Problems first · click a row to focus that instrument."
        elif focus == "ALL":
            focus_rows = attention.copy()
            attention_note = "All instruments · problems remain sorted to the top."
        else:
            focus_rows = attention[attention["status"] == focus].copy()
            attention_note = f"Health filter: {focus}."
        st.markdown(f"<div class='shell'><div class='attention-head'><div class='section-title' style='margin:0'>Immediate Market Attention</div><div class='small'>{attention_note}</div></div>", unsafe_allow_html=True)
        attn_cols = [c for c in ["symbol", "status", "issue", "active_level", "change_pct", "check_age_sec", "event_age_sec", "best_route", "feed_mode", "driver", "action"] if c in focus_rows.columns]
        render_interactive_table(focus_rows, "dashboard_attention", default_columns=attn_cols, height=235, select_symbol=True, max_rows=40)
        st.markdown("</div>", unsafe_allow_html=True)

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
            render_interactive_table(cat_summary, "regime_category_table", default_columns=list(cat_summary.columns), height=330, select_symbol=False)

    with diag_tab:
        st.markdown("<div class='shell'><div class='section-title'>Selected Instrument · synchronized direct data</div>", unsafe_allow_html=True)
        diag_cols = [c for c in ["symbol", "name", "category", "latest_close", "change_pct", "score", "quality", "state", "market_state", "collection_state", "collection_age_sec", "event_age_sec", "market_age_sec", "freshness", "source", "feed_mode", "price_type", "active_provider_symbol", "reference_price", "reference_source", "provider_ts", "live_proxy_symbol", "live_proxy_price", "bid", "ask", "book_imbalance", "role"] if c in rel_df.columns]
        diag_mode = st.radio("Diagnostics mode", ["Inspect", "Edit display"], horizontal=True, key="dashboard_diag_mode", label_visibility="collapsed")
        if diag_mode == "Edit display":
            render_editable_override_table(rel_df[diag_cols].copy(), "dashboard_diagnostics_edit", columns=diag_cols)
        else:
            render_interactive_table(rel_df[diag_cols].copy(), "dashboard_diagnostics_table", default_columns=diag_cols, height=380, select_symbol=True)
        st.markdown("</div>", unsafe_allow_html=True)


elif page == "Instruments":
    st.markdown("<div class='shell'><div class='section-title'>Universal Instruments · Interactive Strip + Table Matrix</div><div class='small'>Strip Cards remain the primary presentation. Interactive Table adds search/filter/sort/row focus; Editable Table keeps display edits persistent; Raw Table stays auditable.</div>", unsafe_allow_html=True)
    f1, f2 = st.columns([1.1, 2.3])
    with f1:
        cat = st.selectbox("Filter", ["All"] + sorted(universe_df["category"].unique().tolist()))
    with f2:
        inst_search = st.text_input("Search instruments", placeholder="symbol, name, category, role, driver…", label_visibility="collapsed")
    view = universe_df if cat == "All" else universe_df[universe_df["category"] == cat]
    if inst_search:
        q = inst_search.upper()
        view = view[view.apply(lambda r: q in f"{r['symbol']} {r['name']} {r['category']} {r['role']} {r['driver']}".upper(), axis=1)]
    render_strip_cards(view, "instruments", [c for c in ["symbol", "name", "category", "latest_close", "change_pct", "session_pct", "bid", "ask", "bid_size", "ask_size", "spread", "book_imbalance", "orderflow_source", "volume", "volume_1s", "volume_1m", "session_volume", "relative_volume", "volume_delta_pct", "volume_source", "volume_proxy_symbol", "score", "quality", "state", "market_state", "market_age_sec", "fetch_age_sec", "freshness", "monitor_mode", "monitor_symbol", "monitor_price", "monitor_age_sec", "monitor_status", "monitor_source", "source", "feed_mode", "price_type", "active_provider_symbol", "reference_price", "reference_source", "reference_provider_ts", "source_ok", "live_proxy_symbol", "live_proxy_price", "live_proxy_age_sec", "live_proxy_source", "role", "driver", "provider_ts", "received_ts"] if c in view.columns])
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Flow Tracker":
    flow = universe_df.copy()
    flow["pressure"] = flow["score"].apply(lambda x: "Sellers" if x < -30 else "Buyers" if x > 30 else "Balanced")
    flow["absorption"] = flow["score"].apply(lambda x: "Weak" if x < -50 else "Strong" if x > 50 else "Mixed")
    flow["volume_activity"] = flow["relative_volume"].apply(
        lambda x: "N/A" if pd.isna(x) else "Elevated" if float(x) >= 1.35 else "Thin" if float(x) < 0.70 else "Normal"
    )
    if "book_imbalance" in flow.columns:
        flow["l1_pressure"] = flow["book_imbalance"].apply(lambda x: "N/A" if pd.isna(x) else "Bid-led" if float(x) > .12 else "Ask-led" if float(x) < -.12 else "Balanced")
    st.markdown("<div class='shell'><div class='section-title'>Order Flow Proxy Tracker · Interactive Strips</div><div class='small'>Live L1 when entitled: Databento MBP-1 for CME futures and Massive NBBO for equities/ETFs. Proxy logic remains only where direct quote depth is unavailable.</div>", unsafe_allow_html=True)
    scope = st.selectbox("Scope", ["Selected cluster", "All instruments"], label_visibility="collapsed")
    view = flow[flow["symbol"].isin(related)] if scope == "Selected cluster" else flow
    render_strip_cards(view, "flow")
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Options / Pressure":
    tmp = universe_df.copy()
    tmp["options_pressure"] = tmp["score"].apply(lambda x: "Put pressure" if x < -30 else "Call support" if x > 30 else "Neutral")
    tmp["iv_event_risk"] = tmp["score"].apply(lambda x: "Elevated" if abs(x) > 40 else "Normal")
    st.markdown("<div class='shell'><div class='section-title'>Options / Instrument Pressure · Live Chain + Interactive Strips</div><div class='small'>The selected instrument now queries actual Massive options-chain snapshots when the connected plan permits. Futures/cash references use a labeled liquid listed-options proxy; the universal live level remains the instrument's own routed level.</div>", unsafe_allow_html=True)

    opt_underlying = option_underlying_for(selected_symbol)
    chain_rows = live_hub.options_chain_snapshot(opt_underlying, max_age_seconds=20.0, limit=250) if opt_underlying else []
    chain_df = normalize_option_chain(chain_rows)
    chain_summary = option_chain_summary(chain_df)
    o1, o2, o3, o4, o5 = st.columns(5)
    o1.metric("Options underlying", opt_underlying or "N/A", help=f"Selected dashboard instrument: {selected_symbol}")
    o2.metric("Chain contracts", chain_summary["contracts"])
    o3.metric("Call OI", "—" if pd.isna(chain_summary["call_oi"]) else f"{chain_summary['call_oi']:,.0f}")
    o4.metric("Put OI", "—" if pd.isna(chain_summary["put_oi"]) else f"{chain_summary['put_oi']:,.0f}")
    o5.metric("Feed", chain_summary["timeframe"])
    if not chain_df.empty:
        cf1, cf2 = st.columns([1.0, 3.0])
        with cf1:
            expiries = [x for x in sorted(chain_df["expiration"].dropna().astype(str).unique().tolist())]
            expiry_pick = st.selectbox("Expiry", ["Nearest loaded"] + expiries, key="options_expiry_filter")
            type_pick = st.radio("Contract", ["All", "CALL", "PUT"], horizontal=True, key="options_type_filter")
            if pd.notna(chain_summary["avg_iv"]):
                st.metric("Median IV", f"{chain_summary['avg_iv']:.2%}")
            st.caption(f"Call vol {chain_summary['call_volume']:,.0f} · Put vol {chain_summary['put_volume']:,.0f}")
        with cf2:
            chain_view = chain_df.copy()
            if expiry_pick == "Nearest loaded" and expiries:
                chain_view = chain_view[chain_view["expiration"].astype(str) == expiries[0]]
            elif expiry_pick != "Nearest loaded":
                chain_view = chain_view[chain_view["expiration"].astype(str) == expiry_pick]
            if type_pick != "All":
                chain_view = chain_view[chain_view["type"] == type_pick]
            display_cols = ["contract", "type", "expiration", "strike", "bid", "ask", "mid", "last", "volume", "open_interest", "iv", "delta", "gamma", "theta", "vega", "quote_timeframe", "trade_timeframe"]
            render_interactive_table(chain_view[display_cols].head(250), "options_chain_table", default_columns=display_cols, height=420, select_symbol=False)
    else:
        if provider_config.get("massive") and opt_underlying:
            st.warning("No options chain returned for this underlying/entitlement. The instrument's live routed level continues independently.")
        else:
            st.info("Connect Massive to populate actual option-chain pricing/Greeks. The strip matrix below still tracks the complete instrument universe.")

    st.markdown("<div class='section-title' style='margin-top:10px'>Universal Instrument Pressure Matrix</div>", unsafe_allow_html=True)
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
    st.markdown("<div class='shell'><div class='section-title'>Data Health · Collection Integrity + Provider Clocks</div>", unsafe_allow_html=True)
    st.markdown(health_card(universe_df, selected_symbol), unsafe_allow_html=True)
    render_health_quick_panel(universe_df)

    cfg1, cfg2, cfg3, cfg4, cfg5 = st.columns(5)
    with cfg1:
        st.markdown(card_html("Universe Checks", f"{check_fresh}/{check_total}", f"stale {check_stale}", check_tone, "≤25s"), unsafe_allow_html=True)
    with cfg2:
        active_tone = "green" if active_stale == 0 else "red"
        st.markdown(card_html("Active Levels", f"{active_fresh}/{active_total}", f"stale {active_stale}", active_tone, "REAL"), unsafe_allow_html=True)
    with cfg3:
        st.markdown(card_html("MT5 Broker", "AUTO", "local real broker levels", "green" if provider_config.get("mt5") else "yellow", "SOURCE"), unsafe_allow_html=True)
    with cfg4:
        st.markdown(card_html("Massive Key", _credential_origin("MASSIVE_API_KEY"), "stocks · ETFs · indices · FX · crypto · futures", "green" if provider_config.get("massive") else "yellow", "SOURCE"), unsafe_allow_html=True)
    with cfg5:
        st.markdown(card_html("Databento Key", _credential_origin("DATABENTO_API_KEY"), "CME futures · L1", "green" if provider_config.get("databento") else "yellow", "SOURCE"), unsafe_allow_html=True)

    configured_count = sum(int(bool(provider_config.get(k))) for k in ("mt5", "massive", "databento", "dxfeed"))
    if configured_count < 1:
        st.warning("No dedicated live source is available. Install the optional MT5 connector on the local Windows machine or configure dxFeed, Massive, or Databento. Public collection remains timestamp-correct and is checked continuously; exchange-delayed data is never promoted to direct LIVE. Configure at least one direct provider for true real-time coverage.")

    pstat = pd.DataFrame(provider_status)
    if not pstat.empty:
        pstat["state"] = pstat.apply(lambda r: "STREAMING" if r.get("connected") and r.get("authenticated") else "NOT CONFIGURED" if not r.get("configured") else "CONNECTING / RETRY", axis=1)
        pstat["message_age_sec"] = pstat["last_message_at"].apply(_seconds_since)
        st.markdown("<div class='section-title' style='margin-top:8px'>Provider Connections</div>", unsafe_allow_html=True)
        provider_cols = ["provider", "channel", "state", "message_age_sec", "last_message_at", "reconnects", "last_error"]
        render_interactive_table(pstat[provider_cols], "provider_connections_table", default_columns=provider_cols, height=280, select_symbol=False)

    st.markdown("<div class='section-title' style='margin-top:8px'>Per-Instrument Collection + Market Clocks</div>", unsafe_allow_html=True)
    st.caption("DIRECT/BROKER LIVE = a real provider is publishing an actual level for this dashboard instrument now. OFFICIAL INDEX = the calculating index feed. REFERENCE/PROXY is used only when no direct real quote exists. The original official/reference value is always retained separately for audit.")
    health_cols = [c for c in ["symbol", "name", "category", "market_state", "latest_close", "price_type", "active_provider_symbol", "reference_price", "reference_source", "collection_age_sec", "event_age_sec", "market_age_sec", "fetch_age_sec", "collection_state", "monitor_mode", "monitor_symbol", "monitor_price", "monitor_age_sec", "monitor_status", "source", "feed_mode", "provider_ts", "received_ts", "source_ok"] if c in universe_df.columns]
    health_view = universe_df[health_cols].copy()
    health_view["status"] = health_view.apply(lambda r: instrument_intelligence(r)["status"], axis=1)
    health_view["issue"] = health_view.apply(lambda r: instrument_intelligence(r)["issue"], axis=1)
    health_view["action"] = health_view.apply(lambda r: instrument_intelligence(r)["action"], axis=1)
    if "monitor_age_sec" in health_view.columns:
        health_view = health_view.sort_values(["monitor_age_sec", "symbol"], ascending=[False, True], na_position="first")
    health_default = [c for c in ["symbol", "status", "issue", "latest_close", "collection_age_sec", "event_age_sec", "active_provider_symbol", "source", "feed_mode", "action", "category"] if c in health_view.columns]
    health_focus = st.session_state.get("dashboard_health_focus", "ATTENTION")
    health_forced = health_focus if health_focus != "ATTENTION" or health_counts.get("ATTENTION", 0) > 0 else None
    render_interactive_table(health_view, "data_health_instruments", default_columns=health_default, height=520, select_symbol=True, forced_status=health_forced)
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
    raw_base = raw_view.copy()
    raw_view = raw_view.rename(columns={
        "symbol": "SOURCE", "category": "DOMAIN", "latest_close": "VALUE", "change_pct": "Δ %",
        "collection_age_sec": "CHECK AGE", "event_age_sec": "EVENT AGE", "market_age_sec": "MARKET AGE", "fetch_age_sec": "FETCH AGE", "freshness": "STATUS", "source": "FEED",
    })
    raw_cols = [c for c in ["SOURCE", "name", "DOMAIN", "VALUE", "Δ %", "score", "quality", "state", "market_state", "CHECK AGE", "EVENT AGE", "MARKET AGE", "FETCH AGE", "STATUS", "FEED", "feed_mode", "provider_ts", "received_ts", "bid", "ask", "bid_size", "ask_size", "spread", "book_imbalance", "orderflow_source", "volume", "volume_1s", "volume_1m", "session_volume", "relative_volume", "volume_delta_pct", "volume_source", "volume_proxy_symbol", "live_proxy_symbol", "live_proxy_price", "live_proxy_age_sec", "monitor_mode", "monitor_symbol", "monitor_price", "monitor_age_sec", "monitor_status", "monitor_source", "price_type", "active_provider_symbol", "reference_price", "reference_source", "reference_provider_ts", "source_ok"] if c in raw_view.columns]
    raw_mode = st.radio("Raw console mode", ["Inspect", "Edit display"], horizontal=True, key="raw_console_mode", label_visibility="collapsed")
    if raw_mode == "Edit display":
        editable_cols = [c for c in ["symbol", "name", "category", "latest_close", "change_pct", "score", "quality", "state", "role", "driver", "market_state", "source", "feed_mode", "price_type"] if c in raw_base.columns]
        render_editable_override_table(raw_base[editable_cols].copy(), "raw_data_edit", columns=editable_cols)
    else:
        render_interactive_table(raw_view[raw_cols].copy(), "raw_data_table", default_columns=raw_cols[: min(18, len(raw_cols))], height=560, select_symbol=True)
    with st.expander("Selected raw payload", expanded=False):
        r = selected.to_dict()
        st.json({k: (float(v) if isinstance(v, np.floating) else int(v) if isinstance(v, np.integer) else v) for k, v in r.items()})
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    f"<div class='footerbar'>Macro Regime Engine {APP_VERSION} · always-on provider hub · UI redraw {refresh_interval}s · collection SLA {MAX_DATA_AGE_SECONDS}s</div>",
    unsafe_allow_html=True,
)
