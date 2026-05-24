import csv
import html
import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

INTENT_TO_TOOL: dict[str, str] = {
    "REALTIME": "get_live_flights",
    "KNOWLEDGE": "search_aviation_docs",
    "ANALYTICS": "get_traffic_analytics",
    "ANOMALY": "detect_anomalies",
    "HYBRID": "get_live_flights + search_aviation_docs",
    "OUT_OF_SCOPE": "checking scope",
}

SUGGESTIONS = [
    "How many flights over France right now?",
    "EU 261 delay compensation rules?",
    "Any anomalous flights in Europe?",
]

_REGION_CODE = {"FRANCE": "FR", "EUROPE": "EU", "WORLD": "WORLD"}

_REGION_VIEW = {
    "FRANCE": pdk.ViewState(latitude=46.5, longitude=2.3, zoom=5.0),
    "EUROPE": pdk.ViewState(latitude=50.0, longitude=10.0, zoom=3.5),
    "WORLD":  pdk.ViewState(latitude=20.0, longitude=0.0,  zoom=1.5),
}


def _check_api() -> bool:
    try:
        return requests.get(f"{API_URL}/health", timeout=3).status_code == 200
    except Exception:
        return False


def _fetch_flights(region: str) -> tuple[list[dict], str]:
    code = _REGION_CODE.get(region, "EU")
    try:
        r = requests.get(f"{API_URL}/flights/live", params={"country": code}, timeout=20)
        r.raise_for_status()
        return r.json(), ""
    except requests.exceptions.ConnectionError:
        return [], "Live data is currently unavailable. Please try refreshing."
    except requests.exceptions.Timeout:
        return [], "Live data is taking too long to load. Please try refreshing."
    except Exception:
        return [], "Unable to load live flights. Please try refreshing."


def _fetch_analytics(region: str) -> tuple[dict | None, str]:
    code = _REGION_CODE.get(region, "EU")
    try:
        r = requests.get(f"{API_URL}/analytics/overview", params={"country": code}, timeout=20)
        r.raise_for_status()
        return r.json(), ""
    except requests.exceptions.ConnectionError:
        return None, "Analytics are currently unavailable. Please try refreshing."
    except requests.exceptions.Timeout:
        return None, "Analytics are taking too long to load. Please try refreshing."
    except Exception:
        return None, "Unable to load analytics. Please try refreshing."


def _error_banner(msg: str) -> None:
    st.markdown(
        f'<div class="error-banner">⚠ {html.escape(msg)}</div>',
        unsafe_allow_html=True,
    )


def _safe_render(fn) -> None:
    """Run a tab render fn; swallow any uncaught error so users never see a traceback."""
    try:
        fn()
    except Exception as e:
        # Log to stderr for debugging; show a generic banner to the user.
        print(f"[Aether] render error in {fn.__name__}: {e}", flush=True)
        _error_banner("Couldn't load this view. Please refresh the page.")


@st.cache_data(ttl=3600)
def _load_airline_names() -> dict[str, str]:
    """ICAO 3-letter airline code → airline name, loaded once per session."""
    path = Path(__file__).parent.parent / "app" / "data" / "airlines.dat"
    result: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for row in csv.reader(fh):
                if len(row) < 8:
                    continue
                icao = row[4].strip()
                name = row[1].strip()
                active = row[7].strip()
                if icao and icao not in (r"\N", "-") and name and active == "Y":
                    result[icao.upper()] = name
    except FileNotFoundError:
        pass
    return result


def _infer_type(speed_kmh: int, alt_m: int, on_ground: bool) -> str:
    if on_ground:
        return "Ground vehicle"
    if speed_kmh < 100:
        return "Helicopter / UAV"
    if speed_kmh < 350:
        return "Turboprop / Light"
    if speed_kmh < 600:
        return "Regional Jet"
    if alt_m > 9000:
        return "Long-haul Jet"
    return "Commercial Jet"


def _speed_color(speed_kmh: int, on_ground: bool) -> list:
    if on_ground:
        return [245, 158, 11, 170]
    if speed_kmh < 200:
        return [74, 222, 128, 200]
    if speed_kmh < 600:
        return [56, 189, 248, 200]
    if speed_kmh < 800:
        return [167, 139, 250, 200]
    return [248, 113, 113, 200]


# ── CSS ────────────────────────────────────────────────────────────────────────

def inject_css() -> None:
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600&family=JetBrains+Mono:wght@400;600&family=Inter:wght@400&display=swap');

/* ── Base ── */
html, body, .stApp { background-color: #0B1120 !important; color: #E2E8F0; }
.stApp { font-family: 'Space Grotesk', system-ui, sans-serif; }

/* Header + toolbar: match dark background — do NOT hide, native toggle stays functional */
header[data-testid="stHeader"] {
    background-color: #0B1120 !important;
    border-bottom: 1px solid #1E2D47 !important;
}
[data-testid="stToolbar"] {
    background-color: #0B1120 !important;
}
/* Hide decorative chrome we don't need */
[data-testid="stDecoration"] { display: none !important; }
#MainMenu                     { display: none !important; }
footer                        { display: none !important; }
/* Style both sidebar toggle buttons */
[data-testid="stExpandSidebarButton"] button,
[data-testid="stSidebarCollapseButton"] button {
    background: transparent !important;
    border: 1px solid #1E2D47 !important;
    border-radius: 4px !important;
}
[data-testid="stExpandSidebarButton"] svg,
[data-testid="stSidebarCollapseButton"] svg {
    fill: #38BDF8 !important;
}

/* ── Main block container ── */
.main .block-container {
    padding-top: 12px !important;
    padding-bottom: 80px !important;
    max-width: 100% !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background-color: #141D2F !important;
    border-right: 1px solid #1E2D47 !important;
}
section[data-testid="stSidebar"] > div:first-child { padding-top: 24px !important; }
[data-testid="stSidebarNav"]            { display: none !important; }

/* Sidebar labels */
.sidebar-label {
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 0.75rem;
    font-weight: 500;
    letter-spacing: 0.01em;
    color: #6B7B92;
    margin: 18px 0 8px 0;
    display: block;
}
.sidebar-wordmark {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.05rem;
    font-weight: 400;
    letter-spacing: -0.01em;
    color: #E2E8F0;
    margin-bottom: 16px;
}
.sidebar-footer {
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 0.7rem;
    color: #4A5E78;
    line-height: 1.7;
    margin-top: 28px;
}

/* ── Dividers ── */
hr { border-color: #1E2D47 !important; margin: 12px 0 !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background-color: transparent !important;
    border-bottom: 1px solid #1E2D47 !important;
    gap: 0 !important;
    padding: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    background-color: transparent !important;
    color: #8899AA !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    letter-spacing: 0 !important;
    text-transform: none !important;
    border-radius: 0 !important;
    padding: 10px 18px !important;
    border: none !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #E2E8F0 !important; }
.stTabs [data-baseweb="tab"][aria-selected="true"] { color: #E2E8F0 !important; }
.stTabs [data-baseweb="tab-highlight"] {
    background-color: #38BDF8 !important;
    height: 2px !important;
}
.stTabs [data-baseweb="tab-border"] { display: none !important; }
.stTabs [data-baseweb="tab-panel"] { padding: 24px 0 0 0 !important; }

/* ── Keyframes ── */
@keyframes fade-up {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes msg-enter {
    from { opacity: 0; transform: translateY(10px); filter: blur(1px); }
    to   { opacity: 1; transform: translateY(0);    filter: blur(0);   }
}
@keyframes cursor-blink {
    0%, 49%   { opacity: 1; }
    50%, 100% { opacity: 0; }
}
@keyframes live-pulse {
    0%, 100% { transform: scale(1);   opacity: 1; }
    50%      { transform: scale(1.6); opacity: 0.5; }
}
@keyframes scan-bar {
    0%   { width: 0%;   opacity: 0;   }
    30%  { opacity: 1;               }
    100% { width: 100%; opacity: 0;   }
}

/* ── Chat messages ── */
/* Layout note: chat history renders newest-first, so the assistant answer
   appears ABOVE its user question. Keep the gap between A→Q (same pair)
   tight, and the gap below the Q (separating pairs) wider. */
.msg-user {
    background: rgba(56, 189, 248, 0.04);
    border: 1px solid rgba(56, 189, 248, 0.12);
    border-radius: 10px;
    padding: 12px 18px;
    margin-bottom: 28px;
    margin-left: 88px;
    animation: msg-enter 360ms cubic-bezier(0.22, 1, 0.36, 1);
}
.msg-assistant {
    background: transparent;
    border: none;
    padding: 4px 0 4px 0;
    margin-bottom: 6px;
    margin-right: 32px;
    animation: msg-enter 400ms cubic-bezier(0.22, 1, 0.36, 1);
}
.msg-error {
    border-left: 2px solid #F59E0B;
    padding: 10px 16px 10px 18px;
    margin-bottom: 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: #F59E0B;
    letter-spacing: 0.02em;
    animation: msg-enter 360ms cubic-bezier(0.22, 1, 0.36, 1);
}
.streaming-cursor {
    display: inline-block;
    width: 7px;
    margin-left: 2px;
    color: #38BDF8;
    animation: cursor-blink 0.9s steps(1) infinite;
}
@media (prefers-reduced-motion: reduce) {
    .msg-user, .msg-assistant, .msg-error, .tool-call,
    .empty-hero__wordmark, .empty-hero__sub, .empty-chips {
        animation: none !important; opacity: 1 !important;
    }
    .streaming-cursor { animation: none !important; opacity: 1; }
}
.msg-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
}
.msg-header:empty { display: none; }
.msg-intent {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.5625rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #38BDF8;
    background: rgba(56, 189, 248, 0.08);
    border: 1px solid rgba(56, 189, 248, 0.25);
    padding: 2px 7px;
    border-radius: 2px;
    line-height: 1.2;
}
.msg-intent-anomaly {
    color: #F59E0B;
    background: rgba(245, 158, 11, 0.08);
    border-color: rgba(245, 158, 11, 0.3);
}
.msg-body {
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 0.9rem;
    line-height: 1.7;
    color: #E2E8F0;
    max-width: 70ch;
}
.msg-body p:first-child { margin-top: 0; }
.msg-body p:last-child  { margin-bottom: 0; }
.msg-body p             { margin: 0 0 12px 0; }
.msg-body strong        { font-weight: 600; color: #FFFFFF; }
.msg-body em            { font-style: italic; color: #C0CAD8; }
.msg-body h1, .msg-body h2, .msg-body h3 {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 500;
    color: #E2E8F0;
    margin: 18px 0 8px 0;
    line-height: 1.3;
}
.msg-body h1 { font-size: 1.0625rem; }
.msg-body h2 { font-size: 0.9375rem; letter-spacing: 0.01em; }
.msg-body h3 {
    font-size: 0.6875rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #8899AA;
}
.msg-body ul, .msg-body ol {
    margin: 6px 0 14px 0;
    padding-left: 22px;
}
.msg-body li {
    margin: 4px 0;
}
.msg-body ul li::marker {
    color: #38BDF8;
}
.msg-body ol li::marker {
    color: #8899AA;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8em;
}
.msg-body code {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8125rem;
    background: #1A2540;
    color: #62CCFA;
    padding: 1px 6px;
    border-radius: 2px;
}
.msg-body pre {
    background: #0E1828;
    border: 1px solid #1E2D47;
    border-radius: 4px;
    padding: 12px 14px;
    margin: 10px 0;
    overflow-x: auto;
}
.msg-body pre code {
    background: transparent;
    color: #E2E8F0;
    padding: 0;
    font-size: 0.8125rem;
    line-height: 1.55;
}
.msg-body a {
    color: #38BDF8;
    text-decoration: none;
    border-bottom: 1px solid rgba(56, 189, 248, 0.3);
    transition: border-color 150ms;
}
.msg-body a:hover {
    border-bottom-color: #38BDF8;
}
.msg-body hr {
    border: none;
    border-top: 1px solid #1E2D47 !important;
    margin: 16px 0 !important;
}

/* ── Response tables ── */
.msg-body table {
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0 18px 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
}
.msg-body thead tr {
    background: rgba(56, 189, 248, 0.08);
    border-bottom: 1px solid rgba(56, 189, 248, 0.35);
}
.msg-body th {
    color: #38BDF8;
    font-weight: 600;
    font-size: 0.5625rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 8px 14px;
    text-align: left;
    white-space: nowrap;
}
.msg-body td {
    padding: 7px 14px;
    border-bottom: 1px solid #1A2540;
    color: #C0CAD8;
    vertical-align: middle;
}
.msg-body tbody tr:hover td { background: rgba(56, 189, 248, 0.04); }
.msg-body tbody tr:last-child td { border-bottom: none; }
/* First column = identifier (callsign etc) */
.msg-body td:first-child {
    color: #E2E8F0;
    font-weight: 600;
    letter-spacing: 0.04em;
}
/* Numeric columns */
.msg-body td.num { color: #38BDF8; font-variant-numeric: tabular-nums; }
/* Status / badge cells */
.msg-body .badge {
    display: inline-block;
    background: rgba(56, 189, 248, 0.1);
    border: 1px solid rgba(56, 189, 248, 0.25);
    color: #38BDF8;
    font-size: 0.5625rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 2px 7px;
    border-radius: 2px;
}

/* ── Tool call indicator ── */
.tool-call {
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.5625rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #38BDF8;
    padding: 12px 2px 8px 2px;
    margin-bottom: 6px;
    opacity: 0;
    animation: fade-up 220ms 60ms cubic-bezier(0.22, 1, 0.36, 1) forwards;
}
.tool-call .dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: #38BDF8;
    flex-shrink: 0;
    box-shadow: 0 0 8px rgba(56,189,248,0.8);
    animation: cursor-blink 1.1s steps(1) infinite;
}
.tool-call__bar {
    flex: 1;
    max-width: 100px;
    height: 1px;
    background: linear-gradient(90deg, #38BDF8, rgba(56,189,248,0));
    animation: scan-bar 1.5s ease-out infinite;
    overflow: hidden;
}

/* ── Empty state hero ── */
.empty-hero {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 64px 0 28px 0;
    text-align: center;
}
.empty-hero__wordmark {
    font-family: 'Space Grotesk', sans-serif;
    font-size: clamp(2.25rem, 4.5vw, 3.25rem);
    font-weight: 300;
    letter-spacing: -0.025em;
    line-height: 1;
    color: #E2E8F0;
    margin-bottom: 14px;
    opacity: 0;
    animation: fade-up 500ms 80ms cubic-bezier(0.22, 1, 0.36, 1) forwards;
}
.empty-hero__sub {
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 0.875rem;
    color: #8899AA;
    margin-bottom: 0;
    opacity: 0;
    animation: fade-up 500ms 180ms cubic-bezier(0.22, 1, 0.36, 1) forwards;
}
.empty-chips {
    display: flex;
    justify-content: center;
    gap: 0;
    margin-top: 36px;
    opacity: 0;
    animation: fade-up 500ms 280ms cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

/* ── Buttons (primary) ── */
[data-testid="baseButton-primary"] {
    background: #38BDF8 !important;
    color: #0B1120 !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    font-size: 0.8125rem !important;
    font-weight: 600 !important;
    letter-spacing: 0 !important;
    text-transform: none !important;
    padding: 9px 18px !important;
    transition: background 200ms !important;
}
[data-testid="baseButton-primary"]:hover {
    background: #62CCFA !important;
    color: #0B1120 !important;
}

/* ── Buttons (secondary — suggestion chips) ── */
[data-testid="baseButton-secondary"] {
    background: transparent !important;
    color: #3A5068 !important;
    border: 1px solid #1A2840 !important;
    border-radius: 100px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.6875rem !important;
    font-weight: 400 !important;
    letter-spacing: 0.03em !important;
    text-transform: none !important;
    padding: 10px 22px !important;
    white-space: nowrap !important;
    height: auto !important;
    transition: color 180ms, border-color 180ms, background 180ms !important;
}
[data-testid="baseButton-secondary"]:hover {
    background: rgba(56,189,248,0.05) !important;
    color: #C0CAD8 !important;
    border-color: rgba(56,189,248,0.3) !important;
}

/* ── Radio buttons ── */
.stRadio > label {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    color: #8899AA !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
.stRadio [data-testid="stMarkdownContainer"] p {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    color: #8899AA !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
[data-testid="stRadio"] > div { gap: 4px !important; }

/* ── Text input (sidebar filter) ── */
.stTextInput input {
    background-color: #0B1120 !important;
    color: #E2E8F0 !important;
    border: 1px solid #1E2D47 !important;
    border-radius: 4px !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    font-size: 0.8125rem !important;
}
.stTextInput input:focus { border-color: #38BDF8 !important; box-shadow: none !important; }
.stTextInput input::placeholder { color: #4A5E78 !important; }
.stTextInput label { display: none !important; }

/* ── Chat input ── */
[data-testid="stChatInput"] {
    background-color: #0D1626 !important;
    border: 1px solid #1A2840 !important;
    border-radius: 12px !important;
    transition: border-color 220ms, box-shadow 220ms !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: rgba(56,189,248,0.4) !important;
    box-shadow: 0 0 0 3px rgba(56,189,248,0.07), 0 0 28px rgba(56,189,248,0.05) !important;
}
[data-testid="stChatInput"] textarea {
    background-color: #0D1626 !important;
    color: #E2E8F0 !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    font-size: 0.9rem !important;
    line-height: 1.6 !important;
    caret-color: #38BDF8 !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: #243246 !important;
    font-style: italic !important;
}
[data-testid="stChatInputSubmitButton"] svg { fill: #38BDF8 !important; }
[data-testid="stChatInputSubmitButton"]:hover svg { fill: #7DD3FC !important; }

/* ── Metric cards (map + analytics) ── */
.metrics-row {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}
.metric-card {
    background: #141D2F;
    border: 1px solid #1E2D47;
    border-radius: 4px;
    padding: 14px 18px;
    flex: 1;
    min-width: 110px;
}
.metric-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.5625rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #4A5E78;
    margin-bottom: 6px;
}
.metric-value {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.5rem;
    font-weight: 300;
    color: #E2E8F0;
    line-height: 1;
}
.metric-value--sky   { color: #38BDF8; }
.metric-value--amber { color: #F59E0B; }
.metric-unit {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.625rem;
    color: #4A5E78;
    margin-left: 4px;
    letter-spacing: 0.06em;
}
.map-info {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.625rem;
    color: #4A5E78;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 16px;
}

/* ── Error banner ── */
.error-banner {
    background: rgba(245, 158, 11, 0.06);
    border: 1px solid rgba(245, 158, 11, 0.3);
    border-radius: 4px;
    padding: 14px 18px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: #F59E0B;
    letter-spacing: 0.02em;
    margin-bottom: 16px;
}

/* ── API status (sidebar) ── */
.api-status {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.625rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-top: 4px;
}
.api-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
}
.api-dot--ok   { background: #4ADE80; }
.api-dot--fail { background: #F59E0B; }
.api-label--ok   { color: #4ADE80; }
.api-label--fail { color: #F59E0B; }

/* ── Stub page ── */
.stub-page {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 400px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.6875rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #4A5E78;
}

/* ── Page header ── */
.page-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    padding-bottom: 0;
    margin-bottom: 16px;
}
.page-wordmark {
    font-family: 'Space Grotesk', sans-serif;
    font-size: clamp(1.25rem, 1.8vw, 1.5rem);
    font-weight: 400;
    letter-spacing: -0.015em;
    color: #E2E8F0;
}
.page-version {
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 0.7rem;
    color: #4A5E78;
    letter-spacing: 0;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

_NUM_RE = re.compile(r"^[\d,.\s%+\-/kmhftknts↑↓⬤]+$", re.IGNORECASE)


def _is_table_row(line: str) -> bool:
    return line.strip().startswith("|") and line.strip().endswith("|")


def _is_separator_row(line: str) -> bool:
    return _is_table_row(line) and re.match(r"^[\|\s\-:]+$", line.strip()) is not None


def _render_table(raw_rows: list[str]) -> str:
    """Convert raw markdown table lines into a styled HTML table."""
    rows = [r.strip().strip("|").split("|") for r in raw_rows]
    rows = [[html.escape(c.strip()) for c in row] for row in rows]

    if len(rows) < 2:
        return ""

    header = rows[0]
    body = [r for r in rows[2:] if r]  # skip separator row

    thead = "<thead><tr>" + "".join(f"<th>{c}</th>" for c in header) + "</tr></thead>"

    tbody_rows = []
    for row in body:
        cells = []
        for i, c in enumerate(row):
            # Detect numeric / unit cells → add .num class
            plain = re.sub(r"<[^>]+>", "", c)
            cls = ' class="num"' if i > 0 and _NUM_RE.match(plain.strip()) else ""
            cells.append(f"<td{cls}>{c}</td>")
        tbody_rows.append("<tr>" + "".join(cells) + "</tr>")

    tbody = "<tbody>" + "".join(tbody_rows) + "</tbody>"
    return f'<table>{thead}{tbody}</table>'


def _inline(text: str) -> str:
    """Apply inline markdown (bold, italic, code) to already-escaped text."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text, flags=re.DOTALL)
    text = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"`([^`\n]+?)`", r"<code>\1</code>", text)
    return text


def md_to_html(text: str) -> str:
    """Convert markdown to styled HTML for the chat message renderer."""
    # 1. Stash fenced code blocks
    code_blocks: list[str] = []

    def _stash_code(m: re.Match) -> str:
        code_blocks.append(html.escape(m.group(1)))
        return f"\x00CODEBLOCK{len(code_blocks) - 1}\x00"

    text = re.sub(r"```[a-zA-Z]*\n?(.*?)```", _stash_code, text, flags=re.DOTALL)

    # 2. Stash markdown tables (before html.escape)
    tables: list[str] = []
    lines_raw = text.split("\n")
    processed: list[str] = []
    i = 0
    while i < len(lines_raw):
        line = lines_raw[i]
        if _is_table_row(line):
            table_lines = []
            while i < len(lines_raw) and (_is_table_row(lines_raw[i]) or _is_separator_row(lines_raw[i])):
                table_lines.append(lines_raw[i])
                i += 1
            tables.append(_render_table(table_lines))
            processed.append(f"\x00TABLE{len(tables) - 1}\x00")
        else:
            processed.append(line)
            i += 1
    text = "\n".join(processed)

    # 3. Escape HTML, then apply inline formatting
    text = html.escape(text)
    text = _inline(text)

    # 4. Line-by-line: headings, lists, paragraphs
    lines = text.split("\n")
    out: list[str] = []
    in_ul = False
    in_ol = False
    para: list[str] = []

    def _flush_para() -> None:
        if para:
            out.append(f"<p>{' '.join(para).strip()}</p>")
            para.clear()

    def _close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    for line in lines:
        stripped = line.strip()

        if not stripped:
            _flush_para()
            _close_lists()
            continue

        if "\x00TABLE" in stripped or "\x00CODEBLOCK" in stripped:
            _flush_para()
            _close_lists()
            out.append(stripped)
            continue

        h_match = re.match(r"^(#{1,3})\s+(.*)$", stripped)
        if h_match:
            _flush_para()
            _close_lists()
            level = len(h_match.group(1))
            out.append(f"<h{level}>{h_match.group(2)}</h{level}>")
            continue

        if stripped.startswith(("- ", "* ")):
            _flush_para()
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{stripped[2:]}</li>")
            continue

        ol_match = re.match(r"^\d+[.)]\s+(.*)", stripped)
        if ol_match:
            _flush_para()
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{ol_match.group(1)}</li>")
            continue

        _close_lists()
        para.append(stripped)

    _flush_para()
    _close_lists()

    result = "\n".join(out)

    # 5. Restore tables
    for idx, table_html in enumerate(tables):
        result = result.replace(f"\x00TABLE{idx}\x00", table_html)

    # 6. Restore code blocks
    for idx, code in enumerate(code_blocks):
        result = result.replace(
            f"\x00CODEBLOCK{idx}\x00",
            f"<pre><code>{code.strip()}</code></pre>",
        )

    return result


def intent_badge(intent: str) -> str:
    cls = "msg-intent-anomaly" if intent == "ANOMALY" else "msg-intent"
    return f'<span class="{cls}">{intent}</span>' if intent else ""


def init_session() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "region" not in st.session_state:
        st.session_state.region = "EUROPE"


# ── Streaming ─────────────────────────────────────────────────────────────────

def stream_response(message: str, resp_ph, tool_ph) -> tuple[str, str, str]:
    """Call /chat/stream, render tokens live into supplied placeholders.

    Returns (full_text, intent, error).
    """
    full_text = ""
    intent = ""
    error = ""

    tool_ph.markdown(
        '<div class="tool-call"><span class="dot"></span>'
        '<span>Classifying intent</span>'
        '<span class="tool-call__bar"></span></div>',
        unsafe_allow_html=True,
    )

    try:
        with requests.post(
            f"{API_URL}/chat/stream",
            json={"message": message},
            stream=True,
            timeout=90,
        ) as response:
            response.raise_for_status()

            for raw_line in response.iter_lines():
                if not raw_line:
                    continue
                if isinstance(raw_line, bytes):
                    raw_line = raw_line.decode("utf-8")
                if not raw_line.startswith("data: "):
                    continue

                payload: dict = json.loads(raw_line[6:])
                event_type = payload.get("type")

                if event_type == "intent":
                    intent = payload.get("value", "")
                    tool = INTENT_TO_TOOL.get(intent, intent.lower())
                    tool_ph.markdown(
                        f'<div class="tool-call"><span class="dot"></span>'
                        f'<span>Calling {tool}</span>'
                        f'<span class="tool-call__bar"></span></div>',
                        unsafe_allow_html=True,
                    )

                elif event_type == "token":
                    full_text += payload.get("content", "")
                    badge = intent_badge(intent)
                    header = f'<div class="msg-header">{badge}</div>' if badge else ""
                    resp_ph.markdown(
                        f'<div class="msg-assistant">{header}'
                        f'<div class="msg-body">{md_to_html(full_text)}'
                        f'<span class="streaming-cursor">▍</span></div></div>',
                        unsafe_allow_html=True,
                    )

                elif event_type == "error":
                    error = "Aether ran into a problem answering. Please try again."
                    break

                elif event_type == "done":
                    break

    except requests.exceptions.ConnectionError:
        error = "Couldn't reach Aether. Please check your connection and try again."
    except requests.exceptions.Timeout:
        error = "Aether is taking too long to respond. Please try again."
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else 0
        if status == 429:
            error = "Too many requests. Please wait a moment before trying again."
        elif status == 422:
            error = "Your message couldn't be processed. Please rephrase and try again."
        else:
            error = "Aether is having trouble responding right now. Please try again."
    except Exception:
        error = "Something went wrong. Please try again."

    # Stream ended cleanly but produced nothing — treat as a soft failure.
    if not error and not full_text:
        error = "Aether didn't return an answer. Please try again."

    if error:
        tool_ph.empty()
        resp_ph.empty()
        return "", "", error

    tool_ph.empty()

    if full_text:
        badge = intent_badge(intent)
        header = f'<div class="msg-header">{badge}</div>' if badge else ""
        resp_ph.markdown(
            f'<div class="msg-assistant">{header}'
            f'<div class="msg-body">{md_to_html(full_text)}</div></div>',
            unsafe_allow_html=True,
        )

    return full_text, intent, ""


# ── Message rendering ─────────────────────────────────────────────────────────

def render_message(msg: dict) -> None:
    role = msg["role"]

    if role == "user":
        body = html.escape(msg["content"])
        st.markdown(
            f'<div class="msg-user"><div class="msg-body">{body}</div></div>',
            unsafe_allow_html=True,
        )

    elif role == "assistant":
        badge = intent_badge(msg.get("intent", ""))
        header = f'<div class="msg-header">{badge}</div>' if badge else ""
        body = md_to_html(msg["content"])
        st.markdown(
            f'<div class="msg-assistant">{header}<div class="msg-body">{body}</div></div>',
            unsafe_allow_html=True,
        )

    elif role == "error":
        st.markdown(
            f'<div class="msg-error">{html.escape(msg["content"])}</div>',
            unsafe_allow_html=True,
        )


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            '<div class="sidebar-wordmark">Aether</div>',
            unsafe_allow_html=True,
        )
        st.divider()

        # ── Region selector ──────────────────────────────────────────────────
        # Controls the data scope for Map, Analytics, and Chat tabs.
        st.markdown('<span class="sidebar-label">Region</span>', unsafe_allow_html=True)
        region = st.radio(
            label="region",
            options=["FRANCE", "EUROPE", "WORLD"],
            index=["FRANCE", "EUROPE", "WORLD"].index(st.session_state.region),
            label_visibility="collapsed",
        )
        if region != st.session_state.region:
            # Clear cached map/analytics data when region changes so the next
            # tab load fetches fresh data for the new scope.
            for key in list(st.session_state.keys()):
                if key.startswith("map_") or key.startswith("analytics_"):
                    del st.session_state[key]
        st.session_state.region = region

        # ── Airline filter ───────────────────────────────────────────────────
        # Filters flights shown on the Map tab only. Does not affect Chat.
        st.markdown('<span class="sidebar-label">Airline filter</span>', unsafe_allow_html=True)
        airline_filter = st.text_input(
            "airline",
            placeholder="e.g. Air France",
            key="airline_filter",
            label_visibility="collapsed",
        )

        # Show match count against cached map data if available
        if airline_filter.strip():
            cache_key = f"map_{region}"
            cached_flights = st.session_state.get(cache_key, [])
            airline_names = _load_airline_names()
            filter_lower = airline_filter.strip().lower()
            matches = sum(
                1 for f in cached_flights
                if not f.get("on_ground")
                and filter_lower in airline_names.get(
                    (f.get("callsign") or "")[:3].upper(), ""
                ).lower()
            )
            if cached_flights:
                st.markdown(
                    f'<div style="font-family:JetBrains Mono,monospace;font-size:0.5625rem;'
                    f'color:#38BDF8;letter-spacing:.08em;margin-top:4px">'
                    f'{matches} flights matched</div>',
                    unsafe_allow_html=True,
                )

        st.divider()

        if st.button("Clear chat", type="primary", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        st.markdown(
            '<div class="sidebar-footer">Data: OpenSky Network · Non-commercial use<br><br>Aether v0.3</div>',
            unsafe_allow_html=True,
        )


# ── Tabs ──────────────────────────────────────────────────────────────────────

def render_chat_tab() -> None:
    prompt = st.chat_input("Ask about any flight, regulation, or anomaly...")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

    if not st.session_state.messages:
        st.markdown(
            '<div class="empty-hero">'
            '<div class="empty-hero__wordmark">Aether</div>'
            '<div class="empty-hero__sub">Live air traffic · EU regulations · Anomaly detection</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="empty-chips">', unsafe_allow_html=True)
        _, c1, c2, c3, _ = st.columns([0.5, 2, 2, 2, 0.5])
        for col, sug, idx in zip([c1, c2, c3], SUGGESTIONS, range(len(SUGGESTIONS))):
            with col:
                if st.button(sug, key=f"sug_{idx}", type="secondary", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": sug})
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        return

    needs_stream = st.session_state.messages[-1]["role"] == "user"

    if needs_stream:
        # Reserve top slots: streaming response goes ABOVE the user question.
        # Order during stream: [tool-call] → [streaming AETHER response] → [latest YOU] → history (reversed).
        tool_ph = st.empty()
        resp_ph = st.empty()

        # Latest YOU message just below the streaming target
        render_message(st.session_state.messages[-1])

        # History (excluding the in-flight question) in reverse — newest first
        for msg in reversed(st.session_state.messages[:-1]):
            render_message(msg)

        last_msg = st.session_state.messages[-1]["content"]
        region = st.session_state.get("region", "EUROPE")
        # Region is a coarse, user-selected scope (radio button) → safe to inject.
        # Airline filter is intentionally NOT injected here: it's a Map-tab visibility
        # filter, and silently prepending it to chat caused false-negative answers.
        enriched = f"[Focus region: {region}] {last_msg}" if region and region != "WORLD" else last_msg

        full_text, intent, error = stream_response(enriched, resp_ph, tool_ph)

        if full_text:
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_text,
                "intent": intent,
            })
        elif error:
            st.session_state.messages.append({
                "role": "error",
                "content": error,
            })
        st.rerun()
    else:
        # No pending stream — render entire history newest-first.
        for msg in reversed(st.session_state.messages):
            render_message(msg)


def render_map_tab() -> None:
    region = st.session_state.get("region", "EUROPE")

    col_info, col_btn = st.columns([6, 1])
    with col_btn:
        do_refresh = st.button("Refresh", type="primary", use_container_width=True, key="map_refresh")

    cache_key = f"map_{region}"
    if do_refresh or cache_key not in st.session_state:
        with st.spinner("Fetching live flights..."):
            flights, fetch_err = _fetch_flights(region)
        st.session_state[cache_key] = flights
        st.session_state[f"{cache_key}_err"] = fetch_err
        st.session_state[f"{cache_key}_ts"] = datetime.utcnow().strftime("%H:%M:%S UTC")

    flights = st.session_state.get(cache_key, [])
    fetch_err = st.session_state.get(f"{cache_key}_err", "")
    ts = st.session_state.get(f"{cache_key}_ts", "—")

    if fetch_err:
        _error_banner(fetch_err)

    valid = [f for f in flights if f.get("latitude") and f.get("longitude")]
    total = len(flights)
    airborne = sum(1 for f in valid if not f.get("on_ground"))

    # Apply airline filter if set
    airline_filter = st.session_state.get("airline_filter", "").strip().lower()
    airline_names = _load_airline_names()
    if airline_filter:
        valid = [
            f for f in valid
            if airline_filter in airline_names.get(
                (f.get("callsign") or "")[:3].upper(), ""
            ).lower()
        ]
        filter_label = f"Filtered: {airline_filter.title()}"
    else:
        filter_label = region

    last_card_label = "FILTER MATCHES" if airline_filter else "REGION"
    last_card_value = f"{len(valid):,}" if airline_filter else filter_label

    st.markdown(
        f'<div class="metrics-row">'
        f'<div class="metric-card"><div class="metric-label">TOTAL FLIGHTS</div>'
        f'<div class="metric-value">{total:,}</div></div>'
        f'<div class="metric-card"><div class="metric-label">AIRBORNE</div>'
        f'<div class="metric-value metric-value--sky">{airborne:,}</div></div>'
        f'<div class="metric-card"><div class="metric-label">ON GROUND</div>'
        f'<div class="metric-value metric-value--amber">{total - airborne:,}</div></div>'
        f'<div class="metric-card"><div class="metric-label">{last_card_label}</div>'
        f'<div class="metric-value" style="font-size:1rem;letter-spacing:0.04em">{last_card_value}</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    with col_info:
        st.markdown(
            f'<div class="map-info">Last updated: {ts} · {len(valid)} positioned flights</div>',
            unsafe_allow_html=True,
        )

    if not valid:
        if not fetch_err:
            _error_banner("No flights to display for this region right now. Try refreshing in a moment.")
        return

    def _heading(deg) -> str:
        if deg is None:
            return "N/A"
        dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        return f"{int(deg)}° {dirs[round(deg / 45) % 8]}"

    def _vrate_status(vr, on_ground: bool) -> str:
        if on_ground:
            return "⬤ On ground"
        if vr is None or abs(vr) < 0.5:
            return "→ Level"
        return "↑ Climbing" if vr > 0 else "↓ Descending"

    airline_names = _load_airline_names()

    df = pd.DataFrame([
        {
            "lat": f["latitude"],
            "lon": f["longitude"],
            "callsign": (f.get("callsign") or "").strip() or f["icao24"],
            "icao24": f["icao24"],
            "country": f.get("origin_country", ""),
            "altitude_m": int(f.get("baro_altitude") or 0),
            "altitude_ft": int((f.get("baro_altitude") or 0) * 3.281),
            "speed_kmh": int((f.get("velocity") or 0) * 3.6),
            "heading": _heading(f.get("true_track")),
            "v_status": _vrate_status(f.get("vertical_rate"), f.get("on_ground", False)),
            "on_ground": f.get("on_ground", False),
        }
        for f in valid
    ])

    df["airline"] = df["callsign"].apply(
        lambda cs: airline_names.get(cs[:3].upper(), "–") if len(cs) >= 3 else "–"
    )
    df["ac_type"] = df.apply(
        lambda r: _infer_type(r["speed_kmh"], r["altitude_m"], r["on_ground"]), axis=1
    )
    df["color"] = df.apply(
        lambda r: _speed_color(r["speed_kmh"], r["on_ground"]), axis=1
    )
    df["radius"] = df["on_ground"].apply(lambda g: 2800 if g else 5000)
    df["color_glow"] = df["on_ground"].apply(
        lambda g: [0, 0, 0, 0] if g else [56, 189, 248, 18]
    )
    df["radius_glow"] = df["on_ground"].apply(lambda g: 0 if g else 11000)

    # Dots color-coded by speed
    solid_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["lon", "lat"],
        get_radius="radius",
        get_fill_color="color",
        pickable=True,
        auto_highlight=True,
        highlight_color=[255, 255, 255, 100],
        stroked=True,
        get_line_color=[255, 255, 255, 30],
        line_width_min_pixels=1,
        transitions={
            "getFillColor": {"duration": 600},
            "getRadius": {"duration": 400},
        },
    )

    tooltip_html = (
        "<div style='font-family:JetBrains Mono,monospace;font-size:12px;line-height:1.8;min-width:220px'>"
        "<div style='color:#38BDF8;font-weight:700;font-size:13px;letter-spacing:.04em;margin-bottom:2px'>✈ {callsign}</div>"
        "<div style='color:#E2E8F0;font-size:12px;margin-bottom:1px'>{airline}</div>"
        "<div style='color:#8899AA;font-size:10px;letter-spacing:.06em;text-transform:uppercase;margin-bottom:8px'>{ac_type} · {country}</div>"
        "<div style='border-top:1px solid #1E2D47;margin:4px 0 8px 0'></div>"
        "<div style='display:grid;grid-template-columns:52px 1fr;row-gap:4px;column-gap:10px'>"
        "<span style='color:#4A5E78;font-size:10px;text-transform:uppercase;align-self:start'>Alt</span>"
        "<span style='color:#E2E8F0'>{altitude_m} m <span style='color:#4A5E78'>/ {altitude_ft} ft</span></span>"
        "<span style='color:#4A5E78;font-size:10px;text-transform:uppercase'>Speed</span>"
        "<span style='color:#E2E8F0'>{speed_kmh} km/h</span>"
        "<span style='color:#4A5E78;font-size:10px;text-transform:uppercase'>Heading</span>"
        "<span style='color:#E2E8F0'>{heading}</span>"
        "<span style='color:#4A5E78;font-size:10px;text-transform:uppercase'>Status</span>"
        "<span style='color:#F59E0B'>{v_status}</span>"
        "</div>"
        "<div style='margin-top:8px;color:#2A3A52;font-size:10px;letter-spacing:.04em'>{icao24}</div>"
        "</div>"
    )

    # Color legend
    st.markdown(
        "<div style='font-family:JetBrains Mono,monospace;font-size:10px;color:#4A5E78;"
        "letter-spacing:.06em;margin-bottom:8px;display:flex;gap:18px;flex-wrap:wrap'>"
        "<span><span style='color:#4ADE80'>●</span> &lt;200 km/h</span>"
        "<span><span style='color:#38BDF8'>●</span> 200–600 km/h</span>"
        "<span><span style='color:#A78BFA'>●</span> 600–800 km/h</span>"
        "<span><span style='color:#F87171'>●</span> 800+ km/h</span>"
        "<span><span style='color:#F59E0B'>●</span> Ground</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    deck = pdk.Deck(
        layers=[solid_layer],
        initial_view_state=_REGION_VIEW.get(region, _REGION_VIEW["EUROPE"]),
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        tooltip={
            "html": tooltip_html,
            "style": {
                "backgroundColor": "#0E1828",
                "border": "1px solid #1E2D47",
                "borderRadius": "8px",
                "padding": "14px 18px",
                "boxShadow": "0 8px 32px rgba(0,0,0,0.65)",
                "maxWidth": "280px",
            },
        },
    )

    st.pydeck_chart(deck, width="stretch")


def render_analytics_tab() -> None:
    region = st.session_state.get("region", "EUROPE")

    col_info, col_btn = st.columns([6, 1])
    with col_btn:
        do_refresh = st.button("Refresh", type="primary", use_container_width=True, key="analytics_refresh")

    cache_key = f"analytics_{region}"
    if do_refresh or cache_key not in st.session_state:
        with st.spinner("Computing analytics..."):
            data, fetch_err = _fetch_analytics(region)
        if data:
            st.session_state[cache_key] = data
        st.session_state[f"{cache_key}_err"] = fetch_err
        st.session_state[f"{cache_key}_ts"] = datetime.utcnow().strftime("%H:%M:%S UTC")

    data = st.session_state.get(cache_key)
    fetch_err = st.session_state.get(f"{cache_key}_err", "")
    ts = st.session_state.get(f"{cache_key}_ts", "—")

    if not data:
        _error_banner(fetch_err or "No analytics data returned.")
        return

    with col_info:
        st.markdown(
            f'<div class="map-info">Last updated: {ts} · {region}</div>',
            unsafe_allow_html=True,
        )

    avg_spd = f"{data['avg_speed_kmh']:,.0f}" if data["avg_speed_kmh"] else "—"
    avg_alt = f"{data['avg_altitude_m']:,.0f}" if data["avg_altitude_m"] else "—"

    fastest = data.get("fastest") or {}
    highest = data.get("highest") or {}
    fastest_cs = fastest.get("callsign", "–") if fastest else "–"
    fastest_spd = f"{fastest.get('value', 0):,.0f}" if fastest else "—"
    highest_cs = highest.get("callsign", "–") if highest else "–"
    highest_alt = f"{highest.get('value', 0):,.0f}" if highest else "—"

    st.markdown(
        f'<div class="metrics-row">'
        f'<div class="metric-card"><div class="metric-label">TOTAL FLIGHTS</div>'
        f'<div class="metric-value">{data["total"]:,}</div></div>'
        f'<div class="metric-card"><div class="metric-label">AIRBORNE</div>'
        f'<div class="metric-value metric-value--sky">{data["airborne"]:,}</div></div>'
        f'<div class="metric-card"><div class="metric-label">ON GROUND</div>'
        f'<div class="metric-value metric-value--amber">{data["on_ground"]:,}</div></div>'
        f'<div class="metric-card"><div class="metric-label">AVG SPEED</div>'
        f'<div class="metric-value">{avg_spd}<span class="metric-unit">km/h</span></div></div>'
        f'<div class="metric-card"><div class="metric-label">AVG ALTITUDE</div>'
        f'<div class="metric-value">{avg_alt}<span class="metric-unit">m</span></div></div>'
        f'<div class="metric-card"><div class="metric-label">FASTEST FLIGHT</div>'
        f'<div class="metric-value" style="font-size:1rem;letter-spacing:.03em">{fastest_cs}</div>'
        f'<div class="metric-unit" style="margin-top:2px">{fastest_spd} km/h</div></div>'
        f'<div class="metric-card"><div class="metric-label">HIGHEST FLIGHT</div>'
        f'<div class="metric-value" style="font-size:1rem;letter-spacing:.03em">{highest_cs}</div>'
        f'<div class="metric-unit" style="margin-top:2px">{highest_alt} m</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Shared Plotly theme ──
    _CARD  = "#141D2F"
    _GRID  = "#1E2D47"
    _TEXT  = "#8899AA"
    _SKY   = "#38BDF8"
    _AMBER = "#F59E0B"
    _GREEN = "#4ADE80"
    _VIOLET = "#A78BFA"

    def _base_layout(**overrides) -> dict:
        return {
            "paper_bgcolor": _CARD,
            "plot_bgcolor": _CARD,
            "font": {"family": "JetBrains Mono, monospace", "size": 11, "color": _TEXT},
            "margin": {"l": 8, "r": 8, "t": 36, "b": 8},
            "showlegend": False,
            **overrides,
        }

    # ── Row 1: Top countries | Airborne donut | Vertical rate ──
    col1, col2, col3 = st.columns([3, 1.8, 1.8])

    with col1:
        countries = data.get("top_countries", [])
        if countries:
            fig = go.Figure(go.Bar(
                x=[c["count"] for c in countries],
                y=[c["country"] for c in countries],
                orientation="h",
                marker_color=[
                    _AMBER if i == 0 else f"rgba(56,189,248,{max(0.3, 0.75 - i * 0.06):.2f})"
                    for i in range(len(countries))
                ],
                text=[f"{c['count']:,}" for c in countries],
                textposition="outside",
                textfont={"size": 9, "color": _TEXT},
                hovertemplate="%{y}: %{x:,} flights<extra></extra>",
            ))
            fig.update_layout(
                **_base_layout(
                    title={"text": "TOP COUNTRIES BY FLIGHT COUNT", "font": {"size": 10, "color": _TEXT}, "x": 0},
                    height=360,
                ),
                xaxis={"gridcolor": _GRID, "linecolor": _GRID, "title": None, "showticklabels": False},
                yaxis={"gridcolor": _GRID, "linecolor": _GRID, "title": None, "autorange": "reversed"},
            )
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    with col2:
        airborne_pct = data.get("airborne_pct", 0)
        fig = go.Figure(go.Pie(
            values=[data["airborne"], data["on_ground"]],
            labels=["Airborne", "On Ground"],
            hole=0.65,
            marker_colors=[_SKY, _AMBER],
            marker_line={"color": _CARD, "width": 2},
            textinfo="percent",
            textfont={"size": 10},
            hovertemplate="%{label}: %{value:,} (%{percent})<extra></extra>",
        ))
        fig.update_layout(
            **_base_layout(
                title={"text": "AIRBORNE VS GROUND", "font": {"size": 10, "color": _TEXT}, "x": 0},
                height=360,
                showlegend=True,
                legend={"font": {"size": 10}, "orientation": "h", "y": -0.05},
                margin={"l": 8, "r": 8, "t": 36, "b": 30},
                annotations=[{
                    "text": f"{airborne_pct:.1f}%",
                    "x": 0.5, "y": 0.5,
                    "font": {"size": 18, "color": _SKY},
                    "showarrow": False,
                }],
            ),
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    with col3:
        climbing = data.get("climbing", 0)
        level = data.get("level", 0)
        descending = data.get("descending", 0)
        fig = go.Figure(go.Bar(
            x=["↑ Climbing", "→ Level", "↓ Descending"],
            y=[climbing, level, descending],
            marker_color=[_GREEN, _SKY, _AMBER],
            marker_opacity=0.85,
            text=[f"{v:,}" for v in [climbing, level, descending]],
            textposition="outside",
            textfont={"size": 9, "color": _TEXT},
            hovertemplate="%{x}: %{y:,} flights<extra></extra>",
        ))
        fig.update_layout(
            **_base_layout(
                title={"text": "VERTICAL RATE", "font": {"size": 10, "color": _TEXT}, "x": 0},
                height=360,
            ),
            xaxis={"gridcolor": _GRID, "linecolor": _GRID, "title": None, "tickfont": {"size": 9}},
            yaxis={"gridcolor": _GRID, "linecolor": _GRID, "title": None},
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    # ── Row 2: Altitude & Speed distributions ──
    col4, col5 = st.columns(2)

    with col4:
        alt_bins = data.get("altitude_dist", [])
        if alt_bins:
            fig = go.Figure(go.Bar(
                x=[b["label"] for b in alt_bins],
                y=[b["count"] for b in alt_bins],
                marker_color=_SKY,
                marker_opacity=0.75,
                text=[f"{b['count']:,}" for b in alt_bins],
                textposition="outside",
                textfont={"size": 9, "color": _TEXT},
                hovertemplate="%{x}: %{y:,} flights<extra></extra>",
            ))
            fig.update_layout(
                **_base_layout(
                    title={"text": "ALTITUDE DISTRIBUTION", "font": {"size": 10, "color": _TEXT}, "x": 0},
                    height=240,
                ),
                xaxis={"gridcolor": _GRID, "linecolor": _GRID, "title": None, "tickfont": {"size": 9}},
                yaxis={"gridcolor": _GRID, "linecolor": _GRID, "title": None},
            )
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    with col5:
        spd_bins = data.get("speed_dist", [])
        if spd_bins:
            fig = go.Figure(go.Bar(
                x=[b["label"] for b in spd_bins],
                y=[b["count"] for b in spd_bins],
                marker_color=[_GREEN, _SKY, _SKY, _VIOLET, "#F87171"],
                marker_opacity=0.85,
                text=[f"{b['count']:,}" for b in spd_bins],
                textposition="outside",
                textfont={"size": 9, "color": _TEXT},
                hovertemplate="%{x}: %{y:,} flights<extra></extra>",
            ))
            fig.update_layout(
                **_base_layout(
                    title={"text": "SPEED DISTRIBUTION", "font": {"size": 10, "color": _TEXT}, "x": 0},
                    height=240,
                ),
                xaxis={"gridcolor": _GRID, "linecolor": _GRID, "title": None, "tickfont": {"size": 9}},
                yaxis={"gridcolor": _GRID, "linecolor": _GRID, "title": None},
            )
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="Aether",
        page_icon="✈",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    inject_css()
    init_session()
    render_sidebar()

    st.markdown(
        '<div class="page-header">'
        '<span class="page-wordmark">Aether</span>'
        '<span class="page-version">v0.3 · aviation intelligence</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    chat_tab, map_tab, analytics_tab = st.tabs(["Chat", "Map", "Analytics"])

    with chat_tab:
        _safe_render(render_chat_tab)
    with map_tab:
        _safe_render(render_map_tab)
    with analytics_tab:
        _safe_render(render_analytics_tab)


if __name__ == "__main__":
    main()
