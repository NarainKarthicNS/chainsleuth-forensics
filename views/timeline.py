import streamlit as st
from engine import V_OK, V_INFERRED

timeline_df = st.session_state["case"]["timeline_df"]

col_filter, _ = st.columns([1, 2])
with col_filter:
    filter_status = st.selectbox(
        "Verification Filter",
        options=["All Events", "Verified On-Chain Only", "Unverified / Failed Ledger Records", "Inferred Off-Chain Only"],
        key="timeline_filter"
    )

if timeline_df.empty:
    st.info("No events to show.")
    st.stop()

if filter_status == "Verified On-Chain Only":
    filtered_tl = timeline_df[timeline_df["verification_status"] == V_OK]
elif filter_status == "Unverified / Failed Ledger Records":
    filtered_tl = timeline_df[~timeline_df["verification_status"].isin([V_OK, V_INFERRED])]
elif filter_status == "Inferred Off-Chain Only":
    filtered_tl = timeline_df[timeline_df["verification_status"] == V_INFERRED]
else:
    filtered_tl = timeline_df

st.dataframe(filtered_tl, use_container_width=True, height=420, hide_index=True)
