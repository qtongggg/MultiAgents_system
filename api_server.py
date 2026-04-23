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
orchestrator = OrchestratorAgent()

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
# REQUEST MODELS
# =========================================================
class JobSearchRequest(BaseModel):
    keyword: str
    location: str
    per_page: int = 5


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
from Agents.job_search_agent import run_job_search_agent
from Agents.resume_agent import run_resume_agent
from Agents.qa_agent import run_qa_agent
from Agents.email_agent import run_email_agent

orchestrator.register("job_search_agent", run_job_search_agent)
orchestrator.register("resume_agent", run_resume_agent)
orchestrator.register("qa_agent", run_qa_agent)  # optional, can be used for general questions without job/resume intent
orchestrator.register("email_agent", run_email_agent)  # optional, can be used to trigger email generation from any agent


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
async def search_jobs_api(request: JobSearchRequest):

    result = await orchestrator.run(
        "job_search_agent",
        request.keyword,
        location=request.location,
        per_page=request.per_page
    )

    return result


@app.post("/api/jobs/resume")
async def search_resume_api(request: ResumeSearchRequest):

    result = await orchestrator.run(
        "resume_agent",
        request.question,
        top_k=request.top_k
    )

    return result

@app.post("/api/rag/query")
async def query_rag(payload: RagQueryRequest):
    try:
        response = await orchestrator.run_pipeline(
            payload.question,
            payload.top_k
        )

        return {
            "ok": response.get("ok", True),
            "answer": response.get("answer", ""),
            "sources": response.get("sources", []),
            "mode": response.get("mode", "qa"),
            "jobs": response.get("jobs", []),
            "error": response.get("error"),
        }

    except Exception as e:
        logging.exception("query_rag failed")

        return {
            "ok": False,
            "answer": "",
            "sources": [],
            "mode": "qa",
            "jobs": [],
            "error": str(e),
        }