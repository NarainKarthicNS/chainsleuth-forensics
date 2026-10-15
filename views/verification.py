import streamlit as st
from engine import verify_ledger_on_chain, V_OK

case = st.session_state["case"]
traced_df = case["traced_df"]

st.caption("Each ledger transfer is re-fetched from Ethereum Mainnet (Blockscout) and compared on sender, receiver, "
           "ETH value and time (±10 min, UTC). Only native ETH transfers are checked.")

if traced_df.empty:
    st.info("No traced transfers to verify.")
    st.stop()

if case["ledger_source"] == "simulated":
    st.info("The sample ledger is simulated, so its hashes will not exist on Mainnet. Verification will honestly report "
            "'Not Found On-Chain' for them. Switch to the live source (sidebar, step 3) to trace real transactions.")

if st.button("Verify all transfers against Ethereum Mainnet", key="verify_btn"):
    with st.spinner(f"Checking {len(traced_df)} transactions..."):
        results = verify_ledger_on_chain(traced_df)
    st.session_state["verification_results"] = {**st.session_state.get("verification_results", {}), **results}
    st.rerun()

results = st.session_state.get("verification_results", {})
c1, c2, c3 = st.columns(3)
c1.metric("Verified On-Chain", int((traced_df["verification"] == V_OK).sum()))
c2.metric("Total Transfers", len(traced_df))
c3.metric("Checked This Session", sum(1 for h in traced_df["tx_hash"] if h.lower() in results))

view = traced_df[["timestamp", "tx_hash", "from_label", "to_label", "amount_eth", "verification"]].copy()
view["detail"] = [results.get(h.lower(), {}).get("detail", "Not yet checked") for h in traced_df["tx_hash"]]
st.dataframe(view, use_container_width=True, hide_index=True)
