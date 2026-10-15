import streamlit as st
from reporter import generate_freeze_report

case = st.session_state["case"]

report_md = generate_freeze_report(case["victim_report"], case["extracted"], case["traced_df"], case["api_key"])
st.download_button(
    label="Download Freeze Warrant (.md)",
    data=report_md,
    file_name="Asset_Freeze_Request_Case_01.md",
    mime="text/markdown",
    key="download_warrant_btn"
)
st.markdown("---")
st.markdown(report_md)
