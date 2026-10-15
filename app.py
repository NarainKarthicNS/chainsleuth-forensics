# app.py
import streamlit as st
import streamlit.components.v1 as components
from mock_data import SAMPLE_VICTIM_REPORT, SAMPLE_CHAT_LOG, BLOCKCHAIN_LEDGER
from engine import (
    extract_offchain_evidence,
    trace_onchain_funds,
    correlate_timeline,
    score_wallet_risks,
    fetch_live_eth_address
)
from reporter import build_interactive_graph_html, generate_freeze_report

st.set_page_config(page_title="ChainSleuth | Cyber Forensics", layout="wide", initial_sidebar_state="expanded")

# Professional Obsidian & Dark Forest Green Theme (Targeting Streamlit internal active tab underline)
st.markdown("""
<style>
    .stApp { background-color: #090d0a; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1240px; }
    
    div[data-testid="stMetric"] {
        background-color: #0d1510;
        border: 1px solid #14281a;
        border-top: 2px solid #10b981;
        padding: 16px 20px;
        border-radius: 6px;
    }
    div[data-testid="stMetricLabel"] { color: #94a3b8 !important; font-size: 0.85rem !important; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }
    div[data-testid="stMetricValue"] { color: #f8fafc !important; font-size: 1.6rem !important; font-weight: 600; }
    
    /* Clean Tab Styling & Overriding Streamlit Active Tab Underline with Dark Forest Green */
    .stTabs [data-baseweb="tab-list"] { gap: 20px; border-bottom: 1px solid #14281a; padding-bottom: 4px; }
    .stTabs [data-baseweb="tab"] { background-color: transparent; color: #94a3b8; font-weight: 500; border-radius: 4px; padding: 8px 16px; }
    .stTabs [data-baseweb="tab"]:hover { color: #10b981; }
    .stTabs [aria-selected="true"] { background-color: #0d1510 !important; color: #10b981 !important; font-weight: 600; border-bottom: 2px solid #064e3b !important; }
    
    /* Force Streamlit tab indicator bar to dark forest green */
    div[data-baseweb="tab-highlight"] { background-color: #064e3b !important; }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.markdown("### ChainSleuth // Forensics & Compliance Terminal")
st.caption("SEC-01: Cross-Domain Evidence Correlation & Automated On-Chain Asset Tracing")

with st.sidebar:
    st.markdown("#### Case Workspace")
    data_mode = st.radio(
        "Mode",
        ["ApexQuant Pig-Butchering Case", "Custom Evidence Import"],
        key="evidence_source_radio",
        label_visibility="collapsed"
    )

    with st.expander("1. Evidence & Chat Logs", expanded=False):
        if data_mode == "ApexQuant Pig-Butchering Case":
            victim_report = st.text_area("Victim Statement", SAMPLE_VICTIM_REPORT.strip(), height=100, key="victim_sample")
            chat_log = st.text_area("Chat Export (.txt)", SAMPLE_CHAT_LOG.strip(), height=160, key="chat_sample")
        else:
            victim_report = st.text_area("Victim Statement", height=100, key="victim_custom")
            uploaded_chat = st.file_uploader("Upload Chat (.txt)", type=["txt"], key="chat_custom")
            chat_log = uploaded_chat.read().decode("utf-8") if uploaded_chat else ""

    with st.expander("2. Screenshot Evidence", expanded=False):
        uploaded_img = st.file_uploader("Platform Screenshot", type=["png", "jpg", "jpeg"], key="img_uploader")
        default_ocr = "ApexQuant VIP Dashboard — Status: LOCKED | Balance: USD 14,800.00 | Unlock Tax: 3.2 ETH"
        screenshot_ocr = st.text_area("Extracted Text", value=default_ocr, height=80, key="ocr_text_area")

    with st.expander("3. API Integration", expanded=False):
        api_key = st.text_input("Gemini API Key", type="password", key="api_key_input")

    st.markdown("---")
    st.caption("**Node Classification Legend**")
    st.caption("■ Blue: Origin Victim\n■ Red: Scammer Deposit Node\n■ Deep Emerald: Mule Transit Hop\n■ Emerald: CEX Target Endpoint\n■ Purple: Inferred Off-Chain")

if not chat_log.strip():
    st.info("Select or load case evidence in the sidebar workspace to initialize the pipeline.")
    st.stop()

# Run Forensic Pipeline
extracted = extract_offchain_evidence(chat_log, victim_report, screenshot_ocr)
traced_df = trace_onchain_funds(extracted["extracted_wallets"], BLOCKCHAIN_LEDGER)
risk_df = score_wallet_risks(traced_df, extracted["extracted_wallets"])
timeline_df = correlate_timeline(extracted["chat_events"], traced_df)

total_stolen = traced_df[traced_df["from_label"].str.contains("Victim")]["amount_eth"].sum() if not traced_df.empty else 0
cex_traced = traced_df[traced_df["to_label"].str.contains("CEX|Binance")]["amount_eth"].sum() if not traced_df.empty else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Verified Loss", f"{total_stolen:.2f} ETH")
c2.metric("Traced to CEX", f"{cex_traced:.2f} ETH")
c3.metric("Platform UI Claim", "USD 14,800")
c4.metric("Fastest Peel Hop", "3.9 mins")

st.write("")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Fund Flow Graph",
    "Incident Timeline",
    "Evidence Parser",
    "Freeze Warrant",
    "Live ETH Lookup"
])

with tab1:
    st.caption("Spacious left-to-right laundering path with structured hub routing. Solid lines = Verified on-chain transfers; dashed lines = Unfulfilled off-chain demands.")
    graph_html = build_interactive_graph_html(traced_df, extracted["extracted_wallets"])
    components.html(graph_html, height=480)

    st.markdown("##### Wallet Risk Assessment Matrix")
    st.dataframe(risk_df, use_container_width=True, hide_index=True)

    with st.expander("View Raw On-Chain Hop Ledger"):
        st.dataframe(
            traced_df[["timestamp", "hop_stage", "from_label", "to_label", "amount_eth", "hop_velocity", "suspicious_indicator"]],
            use_container_width=True,
            hide_index=True
        )

with tab2:
    col_filter, _ = st.columns([1, 2])
    with col_filter:
        filter_status = st.selectbox(
            "Verification Filter",
            options=["All Events", "Verified On-Chain Only", "Inferred Off-Chain Only"],
            key="timeline_filter"
        )

    if filter_status == "Verified On-Chain Only":
        filtered_tl = timeline_df[timeline_df["verification_status"] == "Verified On-Chain"]
    elif filter_status == "Inferred Off-Chain Only":
        filtered_tl = timeline_df[timeline_df["verification_status"] == "Inferred Association (Off-Chain)"]
    else:
        filtered_tl = timeline_df

    st.dataframe(filtered_tl, use_container_width=True, height=400, hide_index=True)

with tab3:
    if extracted["claimed_usd_amounts"]:
        clean_claims = [c.replace("$", "USD ") for c in sorted(list(set(extracted["claimed_usd_amounts"])))]
        st.warning(
            f"**Forensic Discrepancy Flag:** Platform dashboard reports **{', '.join(clean_claims)}**, "
            f"whereas blockchain ledger proves **99.7% of funds** were siphoned out within minutes."
        )

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("##### Extracted Wallet Addresses")
        for w in extracted["extracted_wallets"]:
            st.code(w, language=None)
    with col_b:
        st.markdown("##### Extracted Transaction Hashes")
        for h in extracted["extracted_tx_hashes"]:
            st.code(h, language=None)

    if uploaded_img:
        st.image(uploaded_img, caption="Uploaded Screenshot Artifact", width=300)

    with st.expander("View Parsed Chat Transcripts", expanded=True):
        st.dataframe(extracted["chat_events"], use_container_width=True, hide_index=True)

with tab4:
    report_md = generate_freeze_report(victim_report, extracted, traced_df, api_key)
    st.download_button(
        label="Download Freeze Warrant (.md)",
        data=report_md,
        file_name="Asset_Freeze_Request_Case_01.md",
        mime="text/markdown",
        key="download_warrant_btn"
    )
    st.markdown("---")
    st.markdown(report_md)

with tab5:
    st.caption("Query live Ethereum Mainnet state via public RPC inspection.")
    col_in, col_btn = st.columns([3, 1])
    with col_in:
        live_addr = st.text_input(
            "Ethereum Address",
            value="0x28C6c06298d514Db089934071355E5743bf21d60",
            key="live_eth_input",
            label_visibility="collapsed"
        )
    with col_btn:
        run_query = st.button("Inspect Wallet", key="live_eth_btn", use_container_width=True)

    if run_query:
        with st.spinner("Querying Mainnet Node..."):
            res = fetch_live_eth_address(live_addr)
            if res["success"]:
                m1, m2, m3 = st.columns(3)
                m1.metric("Live Balance", f"{res['eth_balance']:,.4f} ETH")
                m2.metric("Label", res["implementation_name"])
                m3.metric("ENS", res["ens_domain"])
            else:
                st.warning(f"RPC connection unavailable: {res['error']}")