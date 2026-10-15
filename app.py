# app.py
import streamlit as st
from mock_data import SAMPLE_VICTIM_REPORT, SAMPLE_CHAT_LOG, BLOCKCHAIN_LEDGER
from engine import (
    extract_offchain_evidence,
    trace_onchain_funds,
    apply_verification,
    link_chat_to_chain,
    correlate_timeline,
    score_wallet_risks,
    compute_case_metrics,
    build_live_ledger,
)

st.set_page_config(page_title="ChainSleuth", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Orbitron:wght@600;800;900&family=Share+Tech+Mono&display=swap');

    :root {
        --bg-void: #000000;
        --fg-primary: #e0e0e0;
        --bg-card: #08080c;
        --bg-muted: #101018;
        --fg-muted: #6b7280;
        --neon-green: #00ff88;
        --neon-magenta: #ff00ff;
        --neon-cyan: #00d4ff;
        --border-dim: #1f1f2e;
        --danger: #ff3366;
        --shadow-neon: 0 0 5px #00ff88, 0 0 10px #00ff8840;
        --chamfer: polygon(
            0 10px, 10px 0,
            calc(100% - 10px) 0, 100% 10px,
            100% calc(100% - 10px), calc(100% - 10px) 100%,
            10px 100%, 0 calc(100% - 10px)
        );
        --chamfer-sm: polygon(
            0 6px, 6px 0,
            calc(100% - 6px) 0, 100% 6px,
            100% calc(100% - 6px), calc(100% - 6px) 100%,
            6px 100%, 0 calc(100% - 6px)
        );
    }

    /* Pure Obsidian Black Background */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #000000 !important;
        background-image: none !important;
        color: var(--fg-primary);
        font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
    }

    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2.5rem;
        max-width: 1280px;
    }

    /* Splash Screen Smooth Fade-In Animation */
    @keyframes splashEntry {
        from {
            opacity: 0;
            transform: translateY(12px) scale(0.98);
        }
        to {
            opacity: 1;
            transform: translateY(0) scale(1);
        }
    }
    .splash-container {
        animation: splashEntry 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    /* Headings Typography */
    h1, h2, h3, h4, h5 {
        font-family: "Orbitron", "Share Tech Mono", monospace !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--fg-primary) !important;
    }

    /* Sidebar Chrome & Navigation */
    [data-testid="stSidebar"] {
        background-color: #050508 !important;
        border-right: 1px solid var(--border-dim) !important;
    }
    [data-testid="stSidebarNav"] span {
        font-family: "Share Tech Mono", monospace !important;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }
    [data-testid="stSidebarNav"] a[aria-current="page"] {
        background-color: rgba(0, 255, 136, 0.12) !important;
        border-left: 3px solid var(--neon-green) !important;
    }

    /* Chamfered Metric Cards */
    div[data-testid="stMetric"] {
        background-color: var(--bg-card);
        border: 1px solid var(--border-dim);
        border-left: 3px solid var(--neon-green);
        padding: 16px 20px;
        border-radius: 0px;
        clip-path: var(--chamfer);
        transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1);
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: var(--neon-green);
        filter: drop-shadow(0 0 6px rgba(0, 255, 136, 0.35));
    }
    div[data-testid="stMetricLabel"] {
        font-family: "Share Tech Mono", monospace !important;
        color: var(--neon-cyan) !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.15em;
    }
    div[data-testid="stMetricValue"] {
        font-family: "Orbitron", monospace !important;
        color: var(--fg-primary) !important;
        font-size: 1.65rem !important;
        font-weight: 800;
        text-shadow: 0 0 10px rgba(0, 255, 136, 0.3);
    }

    /* Chamfered Bordered Containers (Module Cards) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border-dim) !important;
        border-radius: 0px !important;
        clip-path: var(--chamfer);
        transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1);
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: var(--neon-green) !important;
        transform: translateY(-2px);
        filter: drop-shadow(0 0 8px rgba(0, 255, 136, 0.25));
    }

    /* Buttons, Download Buttons & Page Links (Black Text on Hover) */
    .stButton > button, .stDownloadButton > button, [data-testid="stPageLink-NavLink"] {
        font-family: "Share Tech Mono", monospace !important;
        text-transform: uppercase !important;
        letter-spacing: 0.14em !important;
        background-color: rgba(0, 255, 136, 0.05) !important;
        border: 1px solid var(--neon-green) !important;
        border-radius: 0px !important;
        color: var(--neon-green) !important;
        clip-path: var(--chamfer-sm);
        transition: all 150ms cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    .stButton > button *, .stDownloadButton > button *, [data-testid="stPageLink-NavLink"] * {
        color: var(--neon-green) !important;
        transition: color 150ms cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    .stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stPageLink-NavLink"]:hover {
        background-color: var(--neon-green) !important;
        color: #000000 !important;
        box-shadow: var(--shadow-neon) !important;
    }
    .stButton > button:hover *, .stDownloadButton > button:hover *, [data-testid="stPageLink-NavLink"]:hover * {
        color: #000000 !important;
        font-weight: 700 !important;
    }

    /* Inputs & Expanders */
    .stTextInput input, .stTextArea textarea, div[data-baseweb="select"] > div {
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border-dim) !important;
        border-radius: 2px !important;
        color: var(--neon-green) !important;
        font-family: "JetBrains Mono", monospace !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: var(--neon-green) !important;
        box-shadow: var(--shadow-neon) !important;
    }

    /* Glitch Animations (Restricted to Dashboard Title) */
    @keyframes rgbShift {
        0%, 100% { text-shadow: -2px 0 var(--neon-magenta), 2px 0 var(--neon-cyan), 0 0 12px rgba(0, 255, 136, 0.45); }
        50% { text-shadow: 2px 0 var(--neon-magenta), -2px 0 var(--neon-cyan), 0 0 20px rgba(0, 255, 136, 0.7); }
    }
    @keyframes glitchSnap {
        0%, 92%, 100% { transform: translate(0); }
        94% { transform: translate(-2px, 1px) skewX(-2deg); }
        96% { transform: translate(2px, -1px) skewX(2deg); }
        98% { transform: translate(-1px, 0); }
    }

    .cyber-hero-box {
        background-color: var(--bg-card);
        border: 1px solid var(--border-dim);
        border-left: 4px solid var(--neon-green);
        clip-path: var(--chamfer);
        padding: 22px 26px;
        margin-bottom: 18px;
    }
    .cyber-hero-title {
        font-family: "Orbitron", monospace !important;
        font-size: clamp(2.2rem, 4.2vw, 3.5rem) !important;
        font-weight: 900 !important;
        text-transform: uppercase;
        letter-spacing: 0.16em !important;
        color: var(--fg-primary) !important;
        animation: rgbShift 4s infinite, glitchSnap 6s infinite;
        margin: 0 0 6px 0 !important;
        line-height: 1.1 !important;
    }
    .cyber-hero-sub {
        font-family: "JetBrains Mono", monospace;
        font-size: 0.9rem;
        color: #9ca3af;
        margin: 0;
    }

    /* Clean How-To-Use Box */
    .terminal-card {
        background-color: var(--bg-card);
        border: 1px solid var(--border-dim);
        clip-path: var(--chamfer);
        margin: 0.5rem 0 1.6rem 0;
    }
    .terminal-header {
        background-color: var(--bg-muted);
        padding: 8px 18px;
        border-bottom: 1px solid var(--border-dim);
        font-family: "Share Tech Mono", monospace;
        font-size: 0.82rem;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--neon-green);
    }
    .terminal-body {
        padding: 16px 22px;
        font-size: 0.86rem;
        line-height: 1.75;
        color: var(--fg-primary);
    }
    .cmd-line { margin-bottom: 6px; }
    .cmd-step { color: var(--neon-cyan); font-family: "Share Tech Mono", monospace; font-weight: 600; }

    @media (prefers-reduced-motion: reduce) {
        .cyber-hero-title {
            animation: none;
            text-shadow: -2px 0 var(--neon-magenta), 2px 0 var(--neon-cyan);
        }
        .splash-container {
            animation: none;
        }
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

SIM_LEDGER = "Simulated sample ledger"
LIVE_LEDGER = "Live Ethereum Mainnet (Blockscout)"

@st.cache_data(ttl=900, show_spinner="Tracing funds on Ethereum Mainnet...")
def cached_live_ledger(wallets: tuple, hashes: tuple, max_hops: int):
    return build_live_ledger(list(wallets), list(hashes), max_hops=max_hops)

# ---------------- Splash Screen Gateway State ----------------
if "mode_selected" not in st.session_state:
    st.session_state["mode_selected"] = False

if not st.session_state["mode_selected"]:
    st.markdown("""
    <div class="splash-container" style="max-width: 700px; margin: 4rem auto; text-align: center; padding: 2rem;">
        <h1 style="font-family: 'Orbitron', monospace; font-size: 2.8rem; color: #e0e0e0; letter-spacing: 0.15em; margin-bottom: 0.5rem;">CHAINSLEUTH</h1>
        <p style="color: #6b7280; font-family: 'JetBrains Mono', monospace; font-size: 0.95rem; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 2.5rem;">
            Cross-Domain Evidence Correlation &amp; On-Chain Asset Tracing Terminal
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_a, col_b = st.columns(2, gap="large")
    with col_a:
        with st.container(border=True):
            st.markdown("#### Demo Investigation")
            st.caption("Load the pre-configured **ApexQuant Pig-Butchering Case**, complete with victim statements, multi-hop chat transcripts, and platform screenshots.")
            if st.button("Launch Demo Case", use_container_width=True):
                st.session_state["mode_selected"] = True
                st.session_state["selected_mode_type"] = "sample"
                st.rerun()

    with col_b:
        with st.container(border=True):
            st.markdown("#### Custom Investigation")
            st.caption("Import raw victim statements, upload WhatsApp/Telegram chat exports (`.txt`), and attach platform screenshots to trace live Mainnet funds.")
            if st.button("New Custom Workspace", use_container_width=True):
                st.session_state["mode_selected"] = True
                st.session_state["selected_mode_type"] = "custom"
                st.rerun()
    st.stop()

# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("#### Case Workspace")
    default_index = 0 if st.session_state.get("selected_mode_type") == "sample" else 1
    data_mode = st.radio(
        "Mode",
        ["ApexQuant Pig-Butchering Case", "Custom Evidence Import"],
        index=default_index,
        key="evidence_source_radio",
        label_visibility="collapsed"
    )
    sample_mode = data_mode == "ApexQuant Pig-Butchering Case"

    with st.expander("1. Evidence & Chat Logs", expanded=False):
        if sample_mode:
            victim_report = st.text_area("Victim Statement", SAMPLE_VICTIM_REPORT.strip(), height=100, key="victim_sample")
            chat_log = st.text_area("Chat Export (.txt)", SAMPLE_CHAT_LOG.strip(), height=160, key="chat_sample")
        else:
            victim_report = st.text_area("Victim Statement", height=100, key="victim_custom")
            uploaded_chat = st.file_uploader("Upload Chat (.txt)", type=["txt"], key="chat_custom")
            chat_log = uploaded_chat.getvalue().decode("utf-8-sig", errors="replace") if uploaded_chat else ""
        st.caption("Supported chat formats: `[YYYY-MM-DD HH:MM:SS] Sender: msg`, WhatsApp (Android/iOS), Telegram text export.")

    with st.expander("2. Screenshot Evidence", expanded=False):
        uploaded_img = st.file_uploader("Platform Screenshot", type=["png", "jpg", "jpeg"], key="img_uploader")
        if sample_mode:
            default_ocr = "ApexQuant VIP Dashboard — Status: LOCKED | Balance: USD 14,800.00 | Unlock Tax: 3.2 ETH"
            screenshot_ocr = st.text_area("Extracted Text", value=default_ocr, height=80, key="ocr_sample")
            screenshot_time = st.text_input("Screenshot capture time (optional)", value="2026-10-13 19:00:00", key="shot_time_sample")
        else:
            screenshot_ocr = st.text_area("Extracted Text", value="", height=80, key="ocr_custom")
            screenshot_time = st.text_input("Screenshot capture time (optional)", value="", key="shot_time_custom")

    with st.expander("3. Blockchain Data Source", expanded=False):
        if sample_mode:
            ledger_mode = st.radio("Source", [SIM_LEDGER, LIVE_LEDGER], key="ledger_sample", label_visibility="collapsed")
        else:
            ledger_mode = LIVE_LEDGER
            st.caption("Custom imports are traced live on Ethereum Mainnet via Blockscout.")
        max_hops = 2
        if ledger_mode == LIVE_LEDGER:
            max_hops = st.slider("Max hops to follow", 1, 3, 2, key="max_hops")

    with st.expander("4. API Integration", expanded=False):
        api_key = st.text_input("Gemini API Key", type="password", key="api_key_input")

    st.markdown("---")
    if st.button("← Back to Gateway", use_container_width=True):
        st.session_state["mode_selected"] = False
        st.rerun()

    st.markdown("---")
    st.caption("**Node Classification Legend**")
    st.caption("■ Cyan: Origin Victim\n■ Crimson: Scammer Deposit Node\n■ Matrix Green: Mule Transit Hop\n■ Electric Green: CEX Endpoint\n■ Magenta: Inferred Off-Chain")
    st.caption("**Edge Legend**")
    st.caption("— Electric Green: Verified Mainnet\n- - Cyan Dashed: Unverified Ledger\n- - Crimson Dashed: Failed Check\n- - Magenta Dashed: Inferred Demand")

if not chat_log.strip():
    st.info("Select or load case evidence in the sidebar workspace to initialize the pipeline.")
    st.stop()

# ---------------- Forensic pipeline ----------------
extracted = extract_offchain_evidence(chat_log, victim_report, screenshot_ocr, screenshot_time)

ledger_warnings = []
if ledger_mode == LIVE_LEDGER:
    ledger_rows, ledger_warnings = cached_live_ledger(
        tuple(extracted["extracted_wallets"]), tuple(extracted["extracted_tx_hashes"]), max_hops
    )
    ledger_source = "live"
else:
    ledger_rows, ledger_source = BLOCKCHAIN_LEDGER, "simulated"

traced_df = trace_onchain_funds(extracted["extracted_wallets"], ledger_rows, ledger_source=ledger_source)
traced_df = apply_verification(traced_df, st.session_state.get("verification_results", {}))
link_df = link_chat_to_chain(extracted, traced_df)
extracted["chain_links"] = link_df.to_dict("records")
risk_df = score_wallet_risks(traced_df, extracted["extracted_wallets"])
timeline_df = correlate_timeline(extracted["chat_events"], traced_df, link_df)
metrics = compute_case_metrics(traced_df, extracted)

st.session_state["case"] = {
    "victim_report": victim_report,
    "extracted": extracted,
    "traced_df": traced_df,
    "risk_df": risk_df,
    "timeline_df": timeline_df,
    "link_df": link_df,
    "metrics": metrics,
    "ledger_source": ledger_source,
    "uploaded_img": uploaded_img,
    "api_key": api_key,
}

if ledger_source == "simulated":
    st.caption("Data source: **simulated demo ledger**.")
if not extracted["extracted_wallets"]:
    st.warning("No wallet addresses were found in the supplied evidence, so nothing can be traced.")
elif traced_df.empty:
    st.warning("No on-chain transfers could be traced from the supplied wallets/hashes.")
if ledger_warnings:
    with st.expander(f"Live trace notices ({len(ledger_warnings)})"):
        for w in ledger_warnings:
            st.write(f"- {w}")

# ---------------- Navigation ----------------
pg = st.navigation([
    st.Page("views/dashboard.py",    title="Dashboard",         default=True),
    st.Page("views/fund_flow.py",    title="Fund Flow Graph"),
    st.Page("views/timeline.py",     title="Incident Timeline"),
    st.Page("views/evidence.py",     title="Evidence Parser"),
    st.Page("views/verification.py", title="Verification"),
    st.Page("views/warrant.py",      title="Freeze Warrant"),
    st.Page("views/live_lookup.py",  title="Live ETH Lookup"),
])
pg.run()