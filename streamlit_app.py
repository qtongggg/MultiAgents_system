# import asyncio
# from pathlib import Path
# import time
# import json
# import streamlit as st
# import inngest
# from dotenv import load_dotenv
# import os
# import requests

# load_dotenv()

# st.set_page_config(page_title="RAG PDF & Job Agent", page_icon="📄", layout="centered")

# # ----------------- Inngest Client -----------------
# @st.cache_resource
# def get_inngest_client() -> inngest.Inngest:
#     return inngest.Inngest(app_id="rag_app", is_production=False)

# # ----------------- PDF Upload & RAG -----------------
# def save_uploaded_pdf(file) -> Path:
#     uploads_dir = Path("uploads")
#     uploads_dir.mkdir(parents=True, exist_ok=True)
#     file_path = uploads_dir / file.name
#     file_path.write_bytes(file.getbuffer())
#     return file_path

# async def send_rag_ingest_event(pdf_path: Path) -> None:
#     client = get_inngest_client()
#     await client.send(
#         inngest.Event(
#             name="rag/ingest_pdf",
#             data={"pdf_path": str(pdf_path.resolve()), "source_id": pdf_path.name},
#         )
#     )

# st.title("Upload a PDF to Ingest")
# uploaded = st.file_uploader("Choose a PDF", type=["pdf"], accept_multiple_files=False)
# if uploaded is not None:
#     with st.spinner("Uploading and triggering ingestion..."):
#         path = save_uploaded_pdf(uploaded)
#         asyncio.run(send_rag_ingest_event(path))
#         time.sleep(0.3)
#     st.success(f"Triggered ingestion for: {path.name}")

# st.divider()
# st.title("Ask a question about your PDFs")

# async def send_rag_query_event(question: str, top_k: int) -> str:
#     client = get_inngest_client()
#     result = await client.send(
#         inngest.Event(name="rag/query_pdf_ai", data={"question": question, "top_k": top_k})
#     )
#     return result[0]

# def _inngest_api_base() -> str:
#     return os.getenv("INNGEST_API_BASE", "http://127.0.0.1:8288/v1")

# def fetch_runs(event_id: str) -> list[dict]:
#     url = f"{_inngest_api_base()}/events/{event_id}/runs"
#     resp = requests.get(url)
#     resp.raise_for_status()
#     return resp.json().get("data", [])

# def wait_for_run_output(event_id: str, timeout_s: float = 300.0, poll_interval_s: float = 0.5) -> dict:
#     start = time.time()
#     last_status = None
#     while True:
#         runs = fetch_runs(event_id)
#         if runs:
#             run = runs[0]
#             status = run.get("status")
#             last_status = status or last_status
#             if status in ("Completed", "Succeeded", "Success", "Finished"):
#                 return run.get("output") or {}
#             if status in ("Failed", "Cancelled"):
#                 raise RuntimeError(f"Function run {status}")
#         if time.time() - start > timeout_s:
#             raise TimeoutError(f"Timed out (last status: {last_status})")
#         time.sleep(poll_interval_s)

# with st.form("rag_query_form"):
#     question = st.text_input("Your question")
#     top_k = st.number_input("How many chunks to retrieve", min_value=1, max_value=20, value=5, step=1)
#     submitted = st.form_submit_button("Ask")
#     if submitted and question.strip():
#         with st.spinner("Generating answer..."):
#             event_id = asyncio.run(send_rag_query_event(question.strip(), int(top_k)))
#             output = wait_for_run_output(event_id)
#         st.subheader("Answer")
#         st.write(output.get("answer", "(No answer)"))
#         if output.get("sources"):
#             st.caption("Sources")
#             for s in output["sources"]:
#                 st.write(f"- {s}")

# # ----------------- Job Search Agent -----------------
# st.divider()
# st.title("Job Search Agent")


# async def send_job_search_event(keyword: str, location: str, per_page: int) -> str:
#     client = get_inngest_client()
#     result = await client.send(
#         inngest.Event(
#             name="rag/orchestrator",
#             data={
#                 "intent": "job_search",
#                 "payload": {
#                     "keyword":  keyword,
#                     "location": location,
#                     "per_page": per_page,
#                 }
#             }
#         )
#     )
#     return result[0]


# def render_job_card(job: dict):
#     """Render a single job card with summary + resume match info."""
#     fit_score       = job.get("fit_score", 0.0) or 0.0
#     matching_skills = job.get("matching_skills", []) or []
#     missing_skills  = job.get("missing_skills", [])  or []
#     reason          = job.get("reason", "")          or ""

#     # ---- Job header ----
#     st.markdown(f"### {job.get('title')} at *{job.get('company')}*")
#     st.markdown(f"📍 {job.get('location')}")
#     st.markdown(f"{job.get('brief_summary')}")


#     # ---- Resume match section (only show if fit_score > 0) ----
#     if fit_score > 0:
#         score_pct = int(fit_score * 100)

#         # Color based on score
#         if fit_score >= 0.7:
#             color = "green"
#         elif fit_score >= 0.4:
#             color = "orange"
#         else:
#             color = "red"

#         st.markdown(
#             f"**Resume Match:** :{color}[{score_pct}% fit]"
#         )
#         st.progress(fit_score)

#         if matching_skills:
#             st.markdown(f"✅ **Matching:** {', '.join(matching_skills)}")
#         if missing_skills:
#             st.markdown(f"❌ **Missing:** {', '.join(missing_skills)}")
#         if reason:
#             st.caption(f"💬 {reason}")

#     st.markdown(f"[Apply here]({job.get('link')})")
#     st.markdown("---")


# with st.form("job_search_form"):
#     job_keyword  = st.text_input("Job title or keyword", value="AI Engineer")
#     job_location = st.text_input("Location", value="Malaysia")
#     per_page     = st.number_input("Number of results", min_value=1, max_value=10, value=5, step=1)
#     submitted_jobs = st.form_submit_button("Search Jobs")

#     if submitted_jobs and job_keyword.strip():
#         with st.spinner("Searching for jobs..."):
#             event_id = asyncio.run(send_job_search_event(
#                 job_keyword.strip(), job_location.strip(), int(per_page)
#             ))
#             output = wait_for_run_output(event_id, timeout_s=300.0)

#             if isinstance(output, dict) and "raw_output" in output:
#                 raw = output["raw_output"].strip()
#                 if raw.startswith("```json"):
#                     raw = raw[len("```json"):].strip()
#                 if raw.endswith("```"):
#                     raw = raw[:-3].strip()
#                 try:
#                     output = json.loads(raw)
#                 except json.JSONDecodeError:
#                     st.error("Failed to parse job results")
#                     st.write(raw)
#                     output = {}

#             job_results = output.get("jobs", [])

#         st.subheader(f"Found {len(job_results)} Jobs")

#         if job_results:
#             # Sort by fit_score descending if available
#             job_results.sort(key=lambda x: x.get("fit_score", 0.0) or 0.0, reverse=True)
#             for job in job_results:
#                 render_job_card(job)
#         else:
#             st.write("No jobs found.")
import asyncio
import time
import requests
import os
import streamlit as st
import streamlit.components.v1 as components
import inngest
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Career Intelligence Chat",
    page_icon="🎯",
    layout="centered",
)

# ─── Font import via components.html (avoids Streamlit stripping <link> tags) -
components.html("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
""", height=0)

# ─── Global CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"] { background: #0b0e14 !important; }
[data-testid="stHeader"]                { background: transparent !important; }
[data-testid="stToolbar"]               { display: none !important; }
[data-testid="stDecoration"]            { display: none !important; }

/* chat messages */
[data-testid="stChatMessage"]           { background: transparent !important; border: none !important; }

/* markdown text inside chat */
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li        { color: #9aa3c2 !important; font-size: 14px !important; line-height: 1.7 !important; }
[data-testid="stChatMessage"] em        { color: #7aafff !important; font-style: normal !important; }

/* chat input box */
[data-testid="stChatInput"] > div       { background: #12161f !important; border: 1px solid #252a40 !important; border-radius: 14px !important; }
[data-testid="stChatInput"] textarea    { background: transparent !important; color: #e0e3ef !important; font-size: 14px !important; }
[data-testid="stChatInput"] textarea::placeholder { color: #3a4060 !important; }
[data-testid="stChatInput"] button      { background: linear-gradient(135deg,#4f8bff,#7c5cff) !important; border-radius: 8px !important; border: none !important; }

/* expander */
[data-testid="stExpander"]              { background: #12161f !important; border: 1px solid #1e2238 !important; border-radius: 12px !important; }
[data-testid="stExpander"] summary      { color: #4e5574 !important; font-size: 13px !important; }

/* slider fill */
[data-testid="stSlider"] [class*="thumb"] { background: #4f8bff !important; }
[data-testid="stSlider"] [class*="track"]:first-child { background: linear-gradient(90deg,#4f8bff,#7c5cff) !important; }

/* clear button */
button[kind="secondary"]                { background: #1a1f2e !important; border: 1px solid #252a40 !important; color: #8892b0 !important; border-radius: 8px !important; font-size: 13px !important; }
button[kind="secondary"]:hover          { border-color: #4f8bff !important; color: #e0e3ef !important; }

/* spinner */
[data-testid="stSpinner"] p             { color: #4e5574 !important; font-size: 13px !important; }
</style>
""", unsafe_allow_html=True)


# ─── Inngest helpers ──────────────────────────────────────────────────────────

@st.cache_resource
def get_inngest_client() -> inngest.Inngest:
    return inngest.Inngest(app_id="rag_app", is_production=False)

def _inngest_api_base() -> str:
    return os.getenv("INNGEST_API_BASE", "http://127.0.0.1:8288/v1")

def fetch_runs(event_id: str) -> list[dict]:
    url = f"{_inngest_api_base()}/events/{event_id}/runs"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json().get("data", [])

def wait_for_run_output(event_id: str, timeout_s: float = 300.0, poll_interval_s: float = 0.5) -> dict:
    start = time.time()
    last_status = None
    while True:
        runs = fetch_runs(event_id)
        if runs:
            run = runs[0]
            status = run.get("status")
            last_status = status or last_status
            if status in ("Completed", "Succeeded", "Success", "Finished"):
                return run.get("output") or {}
            if status in ("Failed", "Cancelled"):
                raise RuntimeError(f"Function run {status}")
        if time.time() - start > timeout_s:
            raise TimeoutError(f"Timed out (last status: {last_status})")
        time.sleep(poll_interval_s)

async def send_rag_query_event(question: str, top_k: int) -> str:
    client = get_inngest_client()
    result = await client.send(
        inngest.Event(name="rag/query_pdf_ai", data={"question": question, "top_k": top_k})
    )
    return result[0]


# ─── Job card HTML builder ────────────────────────────────────────────────────

def _score_color(score: float) -> str:
    if score >= 0.7: return "#22d3a0"
    if score >= 0.4: return "#f5c542"
    return "#ff5c7a"

def render_job_card_html(job: dict) -> str:
    fit_score       = job.get("fit_score", 0.0) or 0.0
    matching_skills = job.get("matching_skills", []) or []
    missing_skills  = job.get("missing_skills",  []) or []
    reason          = job.get("reason", "")          or ""
    link            = job.get("link", "#")            or "#"
    score_pct       = int(fit_score * 100)
    color           = _score_color(fit_score)

    match_chips = "".join(
        f'<span style="background:rgba(34,211,160,.12);color:#22d3a0;border:1px solid rgba(34,211,160,.25);'
        f'padding:2px 9px;border-radius:5px;font-size:11px;font-family:monospace;display:inline-block;margin:2px">{s}</span>'
        for s in matching_skills
    ) or '<span style="color:#3a4060;font-size:11px">None</span>'

    miss_chips = "".join(
        f'<span style="background:rgba(255,92,122,.09);color:#ff5c7a;border:1px solid rgba(255,92,122,.22);'
        f'padding:2px 9px;border-radius:5px;font-size:11px;font-family:monospace;display:inline-block;margin:2px">{s}</span>'
        for s in missing_skills
    ) or '<span style="color:#3a4060;font-size:11px">None</span>'

    reason_html = (
        f'<div style="background:#0d1017;border-left:3px solid #2e3560;border-radius:0 8px 8px 0;'
        f'padding:9px 13px;font-size:12px;color:#6b7494;line-height:1.6;margin:12px 0 8px">{reason}</div>'
    ) if reason else ""

    score_block = ""
    if fit_score > 0:
        score_block = f"""
        <div style="background:#1a1f2e;border:1px solid #252a40;border-radius:10px;
                    padding:9px 13px;text-align:center;flex-shrink:0;min-width:64px">
            <div style="font-size:19px;font-weight:800;color:{color};line-height:1">{score_pct}%</div>
            <div style="font-size:9px;color:#4e5574;font-family:monospace;letter-spacing:.08em;margin-top:2px">FIT</div>
        </div>"""

    return f"""
    <div style="background:#12161f;border:1px solid #1e2238;border-radius:14px;
                padding:18px 20px;margin:8px 0 12px">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:14px">
            <div style="flex:1;min-width:0">
                <div style="font-size:16px;font-weight:800;color:#e8eaf2;line-height:1.25">
                    {job.get('title','Unknown Role')}
                </div>
                <div style="color:#4f8bff;font-size:13px;font-weight:500;margin-top:3px">
                    {job.get('company','')}
                </div>
                <div style="color:#4e5574;font-size:11px;font-family:monospace;margin-top:3px">
                    📍 {job.get('location','')} &nbsp;·&nbsp; {job.get('employment_type','')}
                </div>
            </div>
            {score_block}
        </div>
        <div style="margin-top:14px">
            <div style="font-size:10px;color:#22d3a0;font-family:monospace;letter-spacing:.1em;
                        text-transform:uppercase;margin-bottom:6px">✓ Matching</div>
            <div>{match_chips}</div>
        </div>
        <div style="margin-top:10px">
            <div style="font-size:10px;color:#ff5c7a;font-family:monospace;letter-spacing:.1em;
                        text-transform:uppercase;margin-bottom:6px">✕ Missing</div>
            <div>{miss_chips}</div>
        </div>
        {reason_html}
        <a href="{link}" target="_blank"
           style="display:inline-flex;align-items:center;gap:5px;margin-top:8px;
                  background:rgba(79,139,255,.1);border:1px solid rgba(79,139,255,.25);
                  color:#7aafff;font-family:monospace;font-size:11px;
                  padding:5px 13px;border-radius:7px;text-decoration:none">
            Apply Now ↗
        </a>
    </div>
    """


# ─── Chat state ───────────────────────────────────────────────────────────────

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {
            "role": "assistant",
            "content": (
                "👋 Hi! Ask me about your resume, job matches, or anything in the indexed jobs.\n\n"
                "Try:\n"
                "- *What are my top 3 matching jobs?*\n"
                "- *Tell me about my background*\n"
                "- *Which jobs require Python?*"
            ),
            "type": "text",
        }
    ]

if "chat_top_k" not in st.session_state:
    st.session_state.chat_top_k = 5


# ─── Page header ──────────────────────────────────────────────────────────────

st.markdown("""
<div style="padding:12px 0 8px">
    <div style="font-size:24px;font-weight:800;color:#e8eaf2;margin-bottom:3px;letter-spacing:-0.01em">
        🎯 Career Intelligence Chat
    </div>
    <div style="font-size:11px;color:#3a4060;font-family:monospace;letter-spacing:.08em;text-transform:uppercase">
        Jobs · Resume · Skill Gap Analysis
    </div>
</div>
""", unsafe_allow_html=True)

with st.expander("⚙️ Settings", expanded=False):
    st.session_state.chat_top_k = st.slider(
        "Chunks to retrieve (top_k)",
        min_value=1, max_value=20,
        value=st.session_state.chat_top_k,
        help="Higher = more context retrieved per query"
    )
    if st.button("🗑️ Clear chat history"):
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "Chat cleared! Ask me anything 👇", "type": "text"}
        ]
        st.rerun()

st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)


# ─── Render history ───────────────────────────────────────────────────────────

for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        if msg.get("type") == "cards":
            if msg.get("answer"):
                st.markdown(msg["answer"])
            for job in msg.get("jobs", []):
                st.markdown(render_job_card_html(job), unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])


# ─── Chat input ───────────────────────────────────────────────────────────────

if user_input := st.chat_input("Ask about jobs, your resume, or skill gaps…"):

    st.session_state.chat_messages.append({"role": "user", "content": user_input, "type": "text"})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            event_id = asyncio.run(send_rag_query_event(user_input.strip(), st.session_state.chat_top_k))
            output   = wait_for_run_output(event_id)

        mode   = output.get("mode", "qa")
        answer = output.get("answer", "")
        jobs   = output.get("jobs", [])

        if jobs:
            if answer:
                st.markdown(answer)
            for job in jobs:
                st.markdown(render_job_card_html(job), unsafe_allow_html=True)
            st.session_state.chat_messages.append({
                "role": "assistant", "type": "cards", "answer": answer, "jobs": jobs,
            })
        else:
            placeholder = st.empty()
            displayed = ""
            for word in answer.split():
                displayed += word + " "
                time.sleep(0.02)
                placeholder.markdown(displayed + "▌")
            placeholder.markdown(displayed.strip())
            st.session_state.chat_messages.append({
                "role": "assistant", "content": displayed.strip(), "type": "text",
            })