import streamlit as st

case = st.session_state["case"]
extracted, uploaded_img, m, link_df = case["extracted"], case["uploaded_img"], case["metrics"], case["link_df"]

if extracted["claimed_usd_amounts"]:
    text = f"**Forensic Discrepancy Flag:** the evidence claims a balance of **{', '.join(extracted['claimed_usd_amounts'])}**"
    if m["pct_siphoned"] is not None:
        text += f", whereas the traced ledger shows **{m['pct_siphoned']:.1f}%** of deposited funds were forwarded out of the deposit wallet(s)"
        if m["peel_minutes"]:
            text += f" (first hop {m['peel_minutes'][0]:.1f} min after receipt)"
        text += "."
    else:
        text += ", but no on-chain transfers were traced to compare against."
    st.warning(text)

col_a, col_b = st.columns(2)
with col_a:
    st.markdown("##### Extracted Wallet Addresses")
    for w in extracted["extracted_wallets"]:
        st.code(w, language=None)
    if not extracted["extracted_wallets"]:
        st.caption("None found.")
with col_b:
    st.markdown("##### Extracted Transaction Hashes")
    for h in extracted["extracted_tx_hashes"]:
        st.code(h, language=None)
    if not extracted["extracted_tx_hashes"]:
        st.caption("None found.")

st.markdown("##### Chat ↔ Chain Linking")
if link_df.empty:
    st.caption("No transaction hashes in the evidence to link.")
else:
    st.dataframe(link_df, use_container_width=True, hide_index=True)

if uploaded_img:
    st.image(uploaded_img, caption="Uploaded Screenshot Artifact", width=300)

with st.expander("View Parsed Chat Transcripts", expanded=True):
    if extracted.get("chat_formats"):
        st.caption("Detected format: " + ", ".join(extracted["chat_formats"]))
    elif extracted["chat_events"] == []:
        st.warning("No chat lines could be parsed. Check the export format.")
    st.dataframe(extracted["chat_events"], use_container_width=True, hide_index=True)
