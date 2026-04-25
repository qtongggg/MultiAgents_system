import os
import re
import logging
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from MCP_agent.agent_setup import startup_mcp, shutdown_mcp
from Agents.Base_agent import AgentInfo
from custom.custom_types import JobSearchRequest, AgentResult
from tools.pdf_ingester import ingest_pdf_hybrid

from Agents.orchestrator import OrchestratorAgent

# =========================================================
# LOAD ENV
# =========================================================
load_dotenv()
logging.basicConfig(level=logging.INFO)

# =========================================================
# ORCHESTRATOR (GLOBAL SINGLE INSTANCE)
# =========================================================
from Agents.Agent_Registry import AgentRegistry
registry = AgentRegistry()
orchestrator = OrchestratorAgent(registry=registry)

# =========================================================
# SCHEDULER
# =========================================================
scheduler = AsyncIOScheduler()


async def run_scheduled_job():
    try:
        print("🚀 [SCHEDULER] Running job search via orchestrator...")

        result = await orchestrator.run(
            "job_search_agent",
            "AI Engineer",
            location="Malaysia",
            per_page=5
        )

        print("✅ [SCHEDULER DONE]", result)

    except Exception as e:
        print("❌ [SCHEDULER ERROR]", str(e))


def start_scheduler():
    scheduler.add_job(
        run_scheduled_job,
        trigger="cron",
        hour=11,  # every day at 11am
        minute=9,
    )
    scheduler.start()
    print("⏰ Scheduler started")


# =========================================================
# FASTAPI LIFESPAN (ONLY ONE - FIXED)
# =========================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting system...")

    await startup_mcp()
    start_scheduler()

    yield

    print("🛑 Shutting down system...")

    scheduler.shutdown()
    await shutdown_mcp()


# =========================================================
# APP INIT
# =========================================================
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://192.168.0.234:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# =========================================================
# REQUEST MODELS can be removed afterward 
# =========================================================

class ResumeSearchRequest(BaseModel):
    question: str
    top_k: int = 5

class RagQueryRequest(BaseModel):
    question: str
    top_k: int = 5

# =========================================================
# UTIL
# =========================================================
def normalize_resume_filename(filename: str) -> str:
    ext = Path(filename).suffix.lower() or ".pdf"
    stem = Path(filename).stem.lower()

    stem = re.sub(r"[^a-z0-9\s_-]", "", stem)
    stem = re.sub(r"\s+", " ", stem).strip()

    if "resume" not in stem:
        stem = f"{stem} resume"

    return f"{stem.replace(' ', '_')}{ext}"


# =========================================================
# REGISTER AGENTS (IMPORTANT STEP)
# =========================================================

from Agents.new_job_search_agent import JobSearchAgent as JobSearchAgentClass

job_search_agent  = JobSearchAgentClass(AgentInfo(
    name="job_search_agent",
    description="An agent that searches for jobs based on a keyword and location. It uses the search_jobs_tool to fetch job data, and then formats that data into a structured email content. The email content includes job title, company, location, fit score, summary, matching vs missing skills, and job link. If no jobs are found, it returns a polite message indicating that."
))

registry.register('job_search_agent', job_search_agent)

from Agents.email_agent import EmailAgent as EmailAgentClass

email_agent = EmailAgentClass(AgentInfo(
    name="email_agent",
    description="An agent that make use of the google email api to sent, draft or check the email for the user "
))

registry.register('email_agent', email_agent)

from Agents.new_resume_agent import ResumeAgent as ResumeAgentClass

resume_agent = ResumeAgentClass(AgentInfo(
    name = "resume_agent",
    description= "An Agent that we summarize the information about this candidate and ensure that we can retrive the accurate information for the user."
))

registry.register('resume_agent', resume_agent)
# =========================================================
# API ROUTES (NOW CLEAN)
# =========================================================

@app.post("/api/rag/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        file_path = UPLOAD_DIR / normalize_resume_filename(file.filename)

        with open(file_path, "wb") as f:
            f.write(await file.read())

        result = ingest_pdf_hybrid(str(file_path), file_path.name)

        return {
            "message": "Uploaded + ingested",
            "file": file_path.name,
            "result": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jobs/search")
async def search_jobs_api(payload: JobSearchRequest):
    try:
        result = await orchestrator.run(
            name="job_search_agent",
            user_input=payload.keyword,
            location=payload.location,
            per_page=payload.per_page,
            page=1
        )

        return result

    except Exception as e:
        logging.exception("search_jobs_api failed")

        return AgentResult(
            status="error",
            data={},
            error=str(e)
        ).model_dump()

# @app.post("/api/jobs/resume")
# async def search_resume_api(request: ResumeSearchRequest):

#     result = await orchestrator.run(
#         "resume_agent",
#         request.question,
#         top_k=request.top_k
#     )

#     return result

@app.post("/api/rag/query")
async def query_rag(payload: RagQueryRequest):
    try:
        return await orchestrator.run_pipeline(
            payload.question,
            payload.top_k
        )

    except Exception as e:
        logging.exception("query_rag failed")

        return AgentResult(
            status="error",
            data={},
            error=str(e)
        ).model_dump()