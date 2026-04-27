import streamlit as st
from components.api_client import upload_resume, rag_query

st.set_page_config(
    page_title="AI Career Copilot",
    page_icon="✨",
    layout="wide"
)

# --------------------------------------------------
# CLEAN MODERN UI CONFIG
# --------------------------------------------------

st.markdown("""
<style>
.block-container {
    padding-top: 3rem;
    max-width: 950px;
}

h1 {
    font-size: 4rem !important;
    font-weight: 700 !important;
}

[data-testid="stChatInput"] {
    margin-top: 1rem;
}

.stButton > button {
    border-radius: 999px !important;
    padding: 0.6rem 1.2rem !important;
    border: 1px solid #e5e7eb !important;
    background: white !important;
}

.small-muted {
    color: #6b7280;
    font-size: 0.95rem;
}
</style>
""", unsafe_allow_html=True)

SUGGESTIONS = {
    "🎯 Find matching jobs": "Find AI Engineer jobs for me",
    "📈 Skill gap analysis": "What skills am I missing for AI roles?",
    "🛠 Improve my resume": "How can I improve my resume for AI Engineer roles?",
    "☁️ Cloud AI roles": "Should I apply for cloud AI roles?",
    "💪 Strongest skills": "What are my strongest skills?"
}

WELCOME_MESSAGE = "Hi! I'm your AI Career Copilot. Upload your resume first so I can personalize recommendations for you."

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "resume_uploaded" not in st.session_state:
    st.session_state.resume_uploaded = False

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.header("📄 Resume Upload")

    uploaded_file = st.file_uploader(
        "Upload your resume (PDF)",
        type=["pdf"]
    )

    if uploaded_file:
        if st.button("Process Resume", use_container_width=True):
            with st.spinner("Analyzing your resume..."):
                upload_resume(uploaded_file)

            st.session_state.resume_uploaded = True
            st.success("Resume processed successfully")


# --------------------------------------------------
# CUSTOM CHAT INPUT WITH FILE UPLOAD (OPTION 1)
# --------------------------------------------------

def chat_input_with_upload():
    st.markdown("<br>", unsafe_allow_html=True)

    with st.container():
        uploaded_resume = st.file_uploader(
            "Upload Resume",
            type=["pdf"],
            label_visibility="collapsed",
            key="chat_resume_upload"
        )

        user_prompt = st.text_input(
            "Ask a question",
            placeholder="Upload resume + ask your career question...",
            label_visibility="collapsed",
            key="chat_prompt_input"
        )

        send_clicked = st.button(
            "Send",
            use_container_width=True
        )

        if uploaded_resume and not st.session_state.resume_uploaded:
            with st.spinner("Analyzing your resume..."):
                upload_resume(uploaded_resume)

            st.session_state.resume_uploaded = True
            st.success("Resume processed successfully")

        if send_clicked and user_prompt:
            return user_prompt

    return None


# --------------------------------------------------
# LANDING PAGE (CLEAN LIKE YOUR REFERENCE)
# --------------------------------------------------

if len(st.session_state.messages) == 0:
    st.markdown("# AI Career Copilot")

    prompt = chat_input_with_upload()

    selected = st.pills(
        label="Suggestions",
        label_visibility="collapsed",
        options=list(SUGGESTIONS.keys())
    )

    if selected:
        st.session_state.pending_prompt = SUGGESTIONS[selected]

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        "<p class='small-muted'>⚖ Legal disclaimer</p>",
        unsafe_allow_html=True
    )

else:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = chat_input_with_upload()


# --------------------------------------------------
# PROMPT PROCESSING
# --------------------------------------------------

if st.session_state.pending_prompt:
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if prompt:
    if not st.session_state.resume_uploaded:
        st.warning("Please upload your resume first for personalized career guidance.")

    else:
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = rag_query(prompt)
                    data = response.get("data", {})
                    answer = data.get("answer", "I couldn't generate a response.")

                    st.markdown(answer)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer
                    })

                except Exception as e:
                    error_message = f"Something went wrong: {str(e)}"
                    st.error(error_message)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_message
                    })
