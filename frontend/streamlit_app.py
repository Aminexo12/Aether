import html
import json
import re
from datetime import datetime

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


def _fetch_flights(region: str) -> list[dict]:
    code = _REGION_CODE.get(region, "EU")
    try:
        r = requests.get(f"{API_URL}/flights/live", params={"country": code}, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def _fetch_analytics(region: str) -> dict | None:
    code = _REGION_CODE.get(region, "EU")
    try:
        r = requests.get(f"{API_URL}/analytics/overview", params={"country": code}, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


# ── CSS ────────────────────────────────────────────────────────────────────────

def inject_css() -> None:
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600&family=JetBrains+Mono:wght@400;600&family=Inter:wght@400&display=swap');

/* ── Base ── */
html, body, .stApp { background-color: #0B1120 !important; color: #E2E8F0; }
.stApp { font-family: 'Space Grotesk', system-ui, sans-serif; }

/* Hide Streamlit chrome */
header[data-testid="stHeader"]          { display: none !important; }
footer                                   { display: none !important; }
#MainMenu                                { display: none !important; }
[data-testid="stToolbar"]               { display: none !important; }
[data-testid="stDecoration"]            { display: none !important; }

/* ── Main block container ── */
.main .block-container {
    padding-top: 24px !important;
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
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #4A5E78;
    margin: 16px 0 8px 0;
    display: block;
}
.sidebar-wordmark {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.1rem;
    font-weight: 300;
    letter-spacing: -0.01em;
    color: #E2E8F0;
    margin-bottom: 4px;
}
.sidebar-tagline {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.625rem;
    color: #4A5E78;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.sidebar-footer {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.625rem;
    color: #4A5E78;
    letter-spacing: 0.05em;
    line-height: 1.7;
    text-transform: uppercase;
    margin-top: 24px;
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
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.6875rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    border-radius: 0 !important;
    padding: 10px 20px !important;
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

/* ── Chat messages ── */
@keyframes msg-enter {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes tool-enter {
    from { opacity: 0; transform: translateY(-4px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes cursor-blink {
    0%, 49%   { opacity: 1; }
    50%, 100% { opacity: 0; }
}

.msg-user {
    background: #1A2540;
    border-radius: 4px;
    padding: 16px 18px;
    margin-bottom: 12px;
    animation: msg-enter 380ms cubic-bezier(0.25, 0, 0, 1);
}
.msg-assistant {
    background: #0B1120;
    border-left: 2px solid #38BDF8;
    padding: 16px 18px 18px 20px;
    margin-bottom: 12px;
    animation: msg-enter 420ms cubic-bezier(0.25, 0, 0, 1);
}
.msg-error {
    border-left: 2px solid #F59E0B;
    padding: 10px 16px 10px 18px;
    margin-bottom: 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: #F59E0B;
    letter-spacing: 0.02em;
    animation: msg-enter 380ms cubic-bezier(0.25, 0, 0, 1);
}
.streaming-cursor {
    display: inline-block;
    width: 7px;
    margin-left: 2px;
    color: #38BDF8;
    animation: cursor-blink 0.9s steps(1) infinite;
}
@media (prefers-reduced-motion: reduce) {
    .msg-user, .msg-assistant, .msg-error, .tool-call { animation: none !important; }
    .streaming-cursor { animation: none !important; opacity: 1; }
}
.msg-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
}
.msg-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.625rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #8899AA;
    line-height: 1;
}
.msg-label-aether {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.625rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #38BDF8;
    line-height: 1;
}
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

/* ── Tool call indicator ── */
.tool-call {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: #4A5E78;
    letter-spacing: 0.02em;
    padding: 8px 0 4px 20px;
    margin-bottom: 4px;
    animation: tool-enter 240ms cubic-bezier(0.25, 0, 0, 1);
}
.tool-call .dot {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #38BDF8;
    margin-right: 8px;
    margin-bottom: 1px;
    vertical-align: middle;
    animation: cursor-blink 1.2s steps(1) infinite;
}

/* ── Empty state ── */
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 72px 40px 40px 40px;
    text-align: center;
}
.empty-headline {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.6875rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #4A5E78;
    margin-bottom: 28px;
}

/* ── Buttons (primary) ── */
[data-testid="baseButton-primary"] {
    background: #38BDF8 !important;
    color: #0B1120 !important;
    border: none !important;
    border-radius: 4px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.6875rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    padding: 10px 20px !important;
    transition: background 200ms !important;
}
[data-testid="baseButton-primary"]:hover {
    background: #62CCFA !important;
    color: #0B1120 !important;
}

/* ── Buttons (secondary — suggestion chips) ── */
[data-testid="baseButton-secondary"] {
    background: #141D2F !important;
    color: #8899AA !important;
    border: 1px solid #1E2D47 !important;
    border-radius: 4px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.75rem !important;
    font-weight: 400 !important;
    letter-spacing: 0 !important;
    text-transform: none !important;
    padding: 8px 14px !important;
    white-space: normal !important;
    height: auto !important;
    transition: border-color 150ms, color 150ms !important;
}
[data-testid="baseButton-secondary"]:hover {
    background: #141D2F !important;
    color: #E2E8F0 !important;
    border-color: #38BDF8 !important;
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
    background-color: #141D2F !important;
    border: 1px solid #1E2D47 !important;
    border-radius: 4px !important;
}
[data-testid="stChatInput"]:focus-within { border-color: #38BDF8 !important; }
[data-testid="stChatInput"] textarea {
    background-color: #141D2F !important;
    color: #E2E8F0 !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    font-size: 0.875rem !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: #4A5E78 !important; }
[data-testid="stChatInputSubmitButton"] svg { fill: #38BDF8 !important; }

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
    margin-bottom: 20px;
}
.page-wordmark {
    font-family: 'Space Grotesk', sans-serif;
    font-size: clamp(1.5rem, 2.5vw, 2rem);
    font-weight: 300;
    letter-spacing: -0.02em;
    color: #E2E8F0;
}
.page-version {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.625rem;
    color: #4A5E78;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def md_to_html(text: str) -> str:
    """Convert a subset of markdown to HTML for safe inline rendering."""
    # Extract fenced code blocks first to protect them from other replacements
    code_blocks: list[str] = []

    def _stash_code(m: re.Match) -> str:
        code_blocks.append(html.escape(m.group(1)))
        return f"\x00CODEBLOCK{len(code_blocks) - 1}\x00"

    text = re.sub(r"```[a-zA-Z]*\n?(.*?)```", _stash_code, text, flags=re.DOTALL)

    text = html.escape(text)

    # Bold + italic
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text, flags=re.DOTALL)
    text = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<em>\1</em>", text)
    # Inline code
    text = re.sub(r"`([^`\n]+?)`", r"<code>\1</code>", text)

    # Process line by line for headings, lists, paragraphs
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

        # Headings
        h_match = re.match(r"^(#{1,3})\s+(.*)$", stripped)
        if h_match:
            _flush_para()
            _close_lists()
            level = len(h_match.group(1))
            out.append(f"<h{level}>{h_match.group(2)}</h{level}>")
            continue

        # Unordered list
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

        # Ordered list
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

        # Code block placeholder line
        if "\x00CODEBLOCK" in line:
            _flush_para()
            _close_lists()
            out.append(line)
            continue

        # Paragraph text
        _close_lists()
        para.append(stripped)

    _flush_para()
    _close_lists()

    result = "\n".join(out)

    # Restore code blocks
    for i, code in enumerate(code_blocks):
        result = result.replace(
            f"\x00CODEBLOCK{i}\x00",
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
        '<div class="tool-call"><span class="dot"></span>classifying intent...</div>',
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
                        f'<div class="tool-call"><span class="dot"></span>calling {tool}...</div>',
                        unsafe_allow_html=True,
                    )

                elif event_type == "token":
                    full_text += payload.get("content", "")
                    badge = intent_badge(intent)
                    resp_ph.markdown(
                        f"""<div class="msg-assistant">
<div class="msg-header"><span class="msg-label-aether">AETHER</span>{badge}</div>
<div class="msg-body">{md_to_html(full_text)}<span class="streaming-cursor">▍</span></div>
</div>""",
                        unsafe_allow_html=True,
                    )

                elif event_type == "done":
                    break

    except requests.exceptions.ConnectionError as exc:
        error = f"ConnectionError: {exc}"
    except requests.exceptions.HTTPError as exc:
        error = f"HTTP {exc.response.status_code} — {exc.request.url}"
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    if error:
        tool_ph.empty()
        resp_ph.empty()
        return "", "", error

    tool_ph.empty()

    if full_text:
        badge = intent_badge(intent)
        resp_ph.markdown(
            f"""<div class="msg-assistant">
<div class="msg-header"><span class="msg-label-aether">AETHER</span>{badge}</div>
<div class="msg-body">{md_to_html(full_text)}</div>
</div>""",
            unsafe_allow_html=True,
        )

    return full_text, intent, ""


# ── Message rendering ─────────────────────────────────────────────────────────

def render_message(msg: dict) -> None:
    role = msg["role"]

    if role == "user":
        body = html.escape(msg["content"])
        st.markdown(
            f'<div class="msg-user">'
            f'<div class="msg-header"><span class="msg-label">YOU</span></div>'
            f'<div class="msg-body">{body}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    elif role == "assistant":
        badge = intent_badge(msg.get("intent", ""))
        body = md_to_html(msg["content"])
        st.markdown(
            f"""<div class="msg-assistant">
<div class="msg-header"><span class="msg-label-aether">AETHER</span>{badge}</div>
<div class="msg-body">{body}</div>
</div>""",
            unsafe_allow_html=True,
        )

    elif role == "error":
        st.markdown(
            f'<div class="msg-error">› {html.escape(msg["content"])}</div>',
            unsafe_allow_html=True,
        )


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            '<div class="sidebar-wordmark">AETHER</div>'
            '<div class="sidebar-tagline">Aviation Intelligence</div>',
            unsafe_allow_html=True,
        )
        st.divider()

        st.markdown('<span class="sidebar-label">REGION</span>', unsafe_allow_html=True)
        region = st.radio(
            label="region",
            options=["FRANCE", "EUROPE", "WORLD"],
            index=["FRANCE", "EUROPE", "WORLD"].index(st.session_state.region),
            label_visibility="collapsed",
        )
        st.session_state.region = region

        st.markdown('<span class="sidebar-label">AIRLINE FILTER</span>', unsafe_allow_html=True)
        st.text_input("airline", placeholder="e.g. Air France", key="airline_filter", label_visibility="collapsed")

        st.divider()

        if st.button("CLEAR CHAT", type="primary", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        if st.button("TEST API", type="primary", use_container_width=True):
            try:
                r = requests.get(f"{API_URL}/health", timeout=5)
                st.success(f"API OK — {r.json()}")
            except Exception as e:
                st.error(f"API FAIL — {type(e).__name__}: {e}")

        st.markdown(
            '<div class="sidebar-footer">Data: OpenSky Network<br>Non-commercial use<br><br>Aether v0.2</div>',
            unsafe_allow_html=True,
        )


# ── Tabs ──────────────────────────────────────────────────────────────────────

def render_chat_tab() -> None:
    prompt = st.chat_input("Ask about any flight, regulation, or anomaly...")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

    if not st.session_state.messages:
        st.markdown(
            '<div class="empty-state"><div class="empty-headline">Ask anything about aviation</div></div>',
            unsafe_allow_html=True,
        )
        cols = st.columns(3)
        for i, suggestion in enumerate(SUGGESTIONS):
            with cols[i]:
                if st.button(suggestion, key=f"sug_{i}", type="secondary", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": suggestion})
                    st.rerun()
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
        do_refresh = st.button("REFRESH", type="primary", use_container_width=True, key="map_refresh")

    cache_key = f"map_{region}"
    if do_refresh or cache_key not in st.session_state:
        with st.spinner("Fetching live flights..."):
            flights = _fetch_flights(region)
        st.session_state[cache_key] = flights
        st.session_state[f"{cache_key}_ts"] = datetime.utcnow().strftime("%H:%M:%S UTC")

    flights = st.session_state.get(cache_key, [])
    ts = st.session_state.get(f"{cache_key}_ts", "—")

    valid = [f for f in flights if f.get("latitude") and f.get("longitude")]
    total = len(flights)
    airborne = sum(1 for f in valid if not f.get("on_ground"))

    st.markdown(
        f'<div class="metrics-row">'
        f'<div class="metric-card"><div class="metric-label">TOTAL FLIGHTS</div>'
        f'<div class="metric-value">{total:,}</div></div>'
        f'<div class="metric-card"><div class="metric-label">AIRBORNE</div>'
        f'<div class="metric-value metric-value--sky">{airborne:,}</div></div>'
        f'<div class="metric-card"><div class="metric-label">ON GROUND</div>'
        f'<div class="metric-value metric-value--amber">{total - airborne:,}</div></div>'
        f'<div class="metric-card"><div class="metric-label">REGION</div>'
        f'<div class="metric-value" style="font-size:1rem;letter-spacing:0.04em">{region}</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    with col_info:
        st.markdown(
            f'<div class="map-info">Last updated: {ts} · {len(valid)} positioned flights</div>',
            unsafe_allow_html=True,
        )

    if not valid:
        st.markdown(
            '<div class="stub-page">No flight data — check API connection</div>',
            unsafe_allow_html=True,
        )
        return

    df = pd.DataFrame([
        {
            "lat": f["latitude"],
            "lon": f["longitude"],
            "callsign": (f.get("callsign") or "").strip() or f["icao24"],
            "country": f.get("origin_country", ""),
            "altitude_m": int(f.get("baro_altitude") or 0),
            "speed_kmh": int((f.get("velocity") or 0) * 3.6),
            "on_ground": f.get("on_ground", False),
            "color": [245, 158, 11, 160] if f.get("on_ground") else [56, 189, 248, 180],
            "radius": 3000 if f.get("on_ground") else 5500,
        }
        for f in valid
    ])

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["lon", "lat"],
        get_radius="radius",
        get_fill_color="color",
        pickable=True,
        auto_highlight=True,
        highlight_color=[255, 255, 255, 60],
    )

    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=_REGION_VIEW.get(region, _REGION_VIEW["EUROPE"]),
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        tooltip={
            "html": "<b>{callsign}</b><br/>Country: {country}<br/>Alt: {altitude_m} m · Speed: {speed_kmh} km/h",
            "style": {
                "backgroundColor": "#141D2F",
                "color": "#E2E8F0",
                "fontFamily": "'JetBrains Mono', monospace",
                "fontSize": "12px",
                "border": "1px solid #1E2D47",
                "borderRadius": "4px",
                "padding": "8px 12px",
            },
        },
    )

    st.pydeck_chart(deck, use_container_width=True)


def render_analytics_tab() -> None:
    region = st.session_state.get("region", "EUROPE")

    col_info, col_btn = st.columns([6, 1])
    with col_btn:
        do_refresh = st.button("REFRESH", type="primary", use_container_width=True, key="analytics_refresh")

    cache_key = f"analytics_{region}"
    if do_refresh or cache_key not in st.session_state:
        with st.spinner("Computing analytics..."):
            data = _fetch_analytics(region)
        if data:
            st.session_state[cache_key] = data
            st.session_state[f"{cache_key}_ts"] = datetime.utcnow().strftime("%H:%M:%S UTC")

    data = st.session_state.get(cache_key)
    ts = st.session_state.get(f"{cache_key}_ts", "—")

    if not data:
        st.markdown(
            '<div class="stub-page">Analytics unavailable — check API connection</div>',
            unsafe_allow_html=True,
        )
        return

    with col_info:
        st.markdown(
            f'<div class="map-info">Last updated: {ts} · {region}</div>',
            unsafe_allow_html=True,
        )

    avg_spd = f"{data['avg_speed_kmh']:,.0f}" if data["avg_speed_kmh"] else "—"
    avg_alt = f"{data['avg_altitude_m']:,.0f}" if data["avg_altitude_m"] else "—"

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
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Shared Plotly theme ──
    _CARD = "#141D2F"
    _GRID = "#1E2D47"
    _TEXT = "#8899AA"
    _SKY  = "#38BDF8"
    _AMBER = "#F59E0B"

    def _base_layout(**overrides) -> dict:
        return {
            "paper_bgcolor": _CARD,
            "plot_bgcolor": _CARD,
            "font": {"family": "JetBrains Mono, monospace", "size": 11, "color": _TEXT},
            "margin": {"l": 8, "r": 8, "t": 36, "b": 8},
            "showlegend": False,
            **overrides,
        }

    col1, col2 = st.columns([3, 2])

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
                hovertemplate="%{y}: %{x} flights<extra></extra>",
            ))
            fig.update_layout(
                **_base_layout(
                    title={"text": "TOP COUNTRIES", "font": {"size": 10, "color": _TEXT}, "x": 0},
                    height=320,
                ),
                xaxis={"gridcolor": _GRID, "linecolor": _GRID, "title": None},
                yaxis={"gridcolor": _GRID, "linecolor": _GRID, "title": None, "autorange": "reversed"},
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col2:
        alt_bins = data.get("altitude_dist", [])
        if alt_bins:
            fig = go.Figure(go.Bar(
                x=[b["label"] for b in alt_bins],
                y=[b["count"] for b in alt_bins],
                marker_color=_SKY,
                marker_opacity=0.75,
                hovertemplate="%{x}: %{y} flights<extra></extra>",
            ))
            fig.update_layout(
                **_base_layout(
                    title={"text": "ALTITUDE DISTRIBUTION", "font": {"size": 10, "color": _TEXT}, "x": 0},
                    height=200,
                ),
                xaxis={"gridcolor": _GRID, "linecolor": _GRID, "title": None, "tickfont": {"size": 9}},
                yaxis={"gridcolor": _GRID, "linecolor": _GRID, "title": None},
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        spd_bins = data.get("speed_dist", [])
        if spd_bins:
            fig = go.Figure(go.Bar(
                x=[b["label"] for b in spd_bins],
                y=[b["count"] for b in spd_bins],
                marker_color=_AMBER,
                marker_opacity=0.75,
                hovertemplate="%{x}: %{y} flights<extra></extra>",
            ))
            fig.update_layout(
                **_base_layout(
                    title={"text": "SPEED DISTRIBUTION", "font": {"size": 10, "color": _TEXT}, "x": 0},
                    height=200,
                ),
                xaxis={"gridcolor": _GRID, "linecolor": _GRID, "title": None, "tickfont": {"size": 9}},
                yaxis={"gridcolor": _GRID, "linecolor": _GRID, "title": None},
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


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
        '<span class="page-wordmark">AETHER</span>'
        '<span class="page-version">v0.2-agent · aviation intelligence</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    chat_tab, map_tab, analytics_tab = st.tabs(["CHAT", "MAP", "ANALYTICS"])

    with chat_tab:
        render_chat_tab()
    with map_tab:
        render_map_tab()
    with analytics_tab:
        render_analytics_tab()


if __name__ == "__main__":
    main()
