import streamlit as st
from components.api_client import search_jobs
from components.job_card import render_job

st.title("💼 AI Job Search Engine")

# -------------------------
# Search Inputs
# -------------------------
keyword = st.text_input("Job Keyword", "AI Engineer")
location = st.text_input("Location", "Malaysia")

col1, col2 = st.columns(2)

with col1:
    per_page = st.slider("Results per page", 1, 10, 5)

with col2:
    page = st.number_input("Page", 1, 10, 1)

# -------------------------
# Search Button
# -------------------------
if st.button("Search Jobs"):
    with st.spinner("Searching jobs..."):
        result = search_jobs(keyword, location, per_page, page)

    if result.get("status") != "success":
        st.error(result.get("error", "Unknown error"))
    else:
        jobs = result["data"].get("jobs", [])

        st.success(f"Found {len(jobs)} jobs")

        for job in jobs:
            render_job(job)