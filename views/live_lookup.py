import streamlit as st
from engine import fetch_live_eth_address

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
