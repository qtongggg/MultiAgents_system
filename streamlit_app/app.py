import streamlit as st

st.set_page_config(
    page_title="AI Career Copilot",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI Career Copilot Platform")
st.markdown("""
Welcome to your AI-powered job intelligence system.

Use the sidebar to navigate:
- 📄 Resume Intelligence (Upload + RAG)
- 💼 AI Job Search
""")

st.info("Select a page from the sidebar to begin.")