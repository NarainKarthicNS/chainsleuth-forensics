import streamlit as st
import streamlit.components.v1 as components
from reporter import build_interactive_graph_html

case = st.session_state["case"]
extracted, traced_df, risk_df = case["extracted"], case["traced_df"], case["risk_df"]

st.caption("Left-to-right laundering path. Green solid = verified on Mainnet; amber dashed = unverified ledger record; "
           "red dashed = failed verification; purple dashed = inferred off-chain demand.")

if traced_df.empty:
    st.info("No on-chain transfers were traced, so there is no fund-flow graph to draw.")
else:
    graph_html = build_interactive_graph_html(traced_df, extracted["extracted_wallets"], extracted.get("wallet_demands"))
    components.html(graph_html, height=480)

st.markdown("##### Wallet Risk Assessment Matrix")
st.dataframe(risk_df, use_container_width=True, hide_index=True)

if not traced_df.empty:
    with st.expander("View Raw On-Chain Hop Ledger"):
        st.dataframe(
            traced_df[["timestamp", "hop_stage", "from_label", "to_label", "amount_eth", "hop_velocity", "verification", "suspicious_indicator"]],
            use_container_width=True, hide_index=True
        )
