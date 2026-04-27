import streamlit as st

def render_job(job):
    with st.container():
        st.markdown("----")

        st.subheader(job.get("title", "No Title"))
        st.write(f"🏢 **Company:** {job.get('company')}")
        st.write(f"📍 **Location:** {job.get('location')}")

        st.progress(job.get("fit_score", 0))

        st.caption(f"Fit Score: {job.get('fit_score')}")

        col1, col2 = st.columns(2)

        with col1:
            st.success("Matching Skills")
            st.write(job.get("matching_skills", []))

        with col2:
            st.error("Missing Skills")
            st.write(job.get("missing_skills", []))

        st.write(job.get("reason", ""))

        st.link_button("Apply Now", job.get("link", "#"))