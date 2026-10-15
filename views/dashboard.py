# views/dashboard.py
import streamlit as st

case = st.session_state["case"]
extracted, traced_df, risk_df, m = case["extracted"], case["traced_df"], case["risk_df"], case["metrics"]

# ---------------- Cyberpunk Glitch Hero Banner ----------------
st.markdown("""
<div class="cyber-hero-box">
    <div class="cyber-sys-tag">// FORENSIC ENGINE v2.4 // ON-CHAIN &amp; OFF-CHAIN CORRELATION UNIT</div>
    <h1 class="cyber-hero-title">CHAINSLEUTH</h1>
    <p class="cyber-hero-sub">
        &gt; Automated cryptocurrency scam investigation, multi-hop laundering topology &amp; CEX asset-freeze warrant dispatch<span class="cyber-cursor">_</span>
    </p>
</div>
""", unsafe_allow_html=True)

# ---------------- Terminal "How to Use" Section ----------------
st.markdown("""
<div class="terminal-card">
    <div class="terminal-header">
        <span class="dot dot-r"></span>
        <span class="dot dot-y"></span>
        <span class="dot dot-g"></span>
        <span>CHAINSLEUTH:how to use</span>
    </div>
    <div class="terminal-body">
        <div class="cmd-line">
            <span class="cmd-prefix">&gt;</span>
            <span class="cmd-step">[STEP 01 // INGEST EVIDENCE]</span> :
            Use the left <b>Case Workspace</b> sidebar to inspect the pre-loaded <i>ApexQuant</i> case or switch to <b>Custom Evidence Import</b> to upload WhatsApp/Telegram chat exports (<code>.txt</code>) and deceptive platform screenshots.
        </div>
        <div class="cmd-line">
            <span class="cmd-prefix">&gt;</span>
            <span class="cmd-step">[STEP 02 // TRACE &amp; CORRELATE]</span> :
            Open <b>[01] Fund Flow Graph</b> and <b>[03] Evidence Parser</b> to map multi-hop peel chains, calculate explainable wallet risk scores, and flag discrepancies between fake UI balance claims and real blockchain drains.
        </div>
        <div class="cmd-line">
            <span class="cmd-prefix">&gt;</span>
            <span class="cmd-step">[STEP 03 // VERIFY ON MAINNET]</span> :
            Launch <b>[04] Verification</b> or toggle <i>Live Ethereum Mainnet (Blockscout)</i> in the sidebar to validate every transaction hash, sender, receiver, and timestamp against live Mainnet blocks.
        </div>
        <div class="cmd-line">
            <span class="cmd-prefix">&gt;</span>
            <span class="cmd-step">[STEP 04 // DISPATCH WARRANT]</span> :
            Navigate to <b>[05] Freeze Warrant</b> to compile and download a law-enforcement compliance report and emergency CEX asset-freeze request (<code>.md</code>) with <span class="cmd-magenta">zero hallucinated hashes</span>.
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------- Case Overview Metrics ----------------
st.markdown("#### // TELEMETRY & CASE OVERVIEW")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Victim Transfers", f"{m['total_loss_eth']:.2f} ETH")
c2.metric("Traced to CEX", f"{m['cex_eth']:.2f} ETH")
c3.metric("Platform UI Claim", f"USD {m['claimed_usd']:,.0f}" if m["claimed_usd"] else "None found")
c4.metric("Fastest Peel Hop", f"{m['fastest_hop_min']:.1f} mins" if m["fastest_hop_min"] is not None else "N/A")

st.write("")
s1, s2, s3, s4 = st.columns(4)
s1.metric("Wallets Identified", len(extracted["extracted_wallets"]))
s2.metric("Tx Hashes Extracted", len(extracted["extracted_tx_hashes"]))
s3.metric("Verified On-Chain", f"{m['n_verified']} / {m['n_transfers']}")
s4.metric("Off-Chain Chat Events", len(extracted["chat_events"]))

st.write("")
st.markdown("#### // INVESTIGATION MODULES")

cards = [
    ("[01]", "FUND FLOW GRAPH", "views/fund_flow.py", "Interactive wallet topology, explainable risk matrix and raw hop ledger."),
    ("[02]", "INCIDENT TIMELINE", "views/timeline.py", "Chat evidence and on-chain transfers merged chronologically with cross-links."),
    ("[03]", "EVIDENCE PARSER", "views/evidence.py", "Extracted wallets, hashes, UI balance claims, chat-to-chain linking and logs."),
    ("[04]", "VERIFICATION", "views/verification.py", "Re-check every ledger transfer against live Ethereum Mainnet via Blockscout."),
    ("[05]", "FREEZE WARRANT", "views/warrant.py", "Evidence-backed forensic summary and downloadable CEX asset-freeze request."),
    ("[06]", "LIVE ETH LOOKUP", "views/live_lookup.py", "Query live Mainnet balance, contract labels and ENS for any address."),
]
for start in range(0, len(cards), 3):
    cols = st.columns(3)
    for slot, (tag, title, path, desc) in zip(cols, cards[start:start + 3]):
        with slot:
            with st.container(border=True):
                st.markdown(f"**`{tag}` {title}**")
                st.caption(desc)
                st.page_link(path, label=f"EXECUTE // {title}", use_container_width=True)

st.write("")
st.markdown("#### // HIGHEST-RISK WALLETS")
if risk_df.empty:
    st.info("No wallets to score yet.")
else:
    st.dataframe(
        risk_df[["Wallet Address", "Role / Classification", "Risk Score", "Explainable Evidence Basis"]].head(5),
        use_container_width=True, hide_index=True,
        column_config={"Risk Score": st.column_config.ProgressColumn("Risk Score", min_value=0, max_value=100, format="%d")},
    )
    st.page_link("views/fund_flow.py", label="OPEN FULL RISK ASSESSMENT MATRIX ->")