import os
import asyncio
import logging
import re

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from MCP_agent.agent_setup import startup_mcp, shutdown_mcp
from Agents.resume_agent import run_resume_agent
from Agents.job_search_agent import run_job_search_agent
from Agents.orchestrator import run_orchestrator
from tools.pdf_ingester import ingest_pdf_hybrid

# =========================================================
# LOAD ENV
# =========================================================
load_dotenv()

# Safe HF login (no crash if missing)
from huggingface_hub import login
hf_token = os.getenv("HF_TOKEN")
if hf_token:
    login(token=hf_token)

# =========================================================
# SCHEDULER
# =========================================================
scheduler = AsyncIOScheduler()

async def run_scheduled_job():
    try:
        print("🚀 [SCHEDULER] Running job search agent...")

        result = await run_job_search_agent(
            keyword="AI Engineer",
            location="Malaysia",
            per_page=5
        )

        print("✅ [SCHEDULER] Completed:", result)

    except Exception as e:
        print("❌ [SCHEDULER] Failed:", str(e))


def start_scheduler():
    scheduler.add_job(
        run_scheduled_job,
        trigger="cron",
        hour=17,
        minute=45
    )
    scheduler.start()
    print("⏰ Scheduler started")

# =========================================================
# LIFESPAN (NON-BLOCKING STARTUP)
# =========================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 App starting...")

    # MCP still background (non-blocking)
    asyncio.create_task(startup_mcp())

    # ✅ scheduler runs in main loop (NOT thread)
    start_scheduler()

    yield

    print("🛑 App shutting down...")
    scheduler.shutdown()
    await shutdown_mcp()

# =========================================================
# APP INIT
# =========================================================
app = FastAPI(lifespan=lifespan)

logging.basicConfig(level=logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all for now (simplify deployment)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# =========================================================
# TEST ROUTE (IMPORTANT)
# =========================================================
@app.get("/")
def root():
    return {"status": "running"}

# =========================================================
# REQUEST MODELS
# =========================================================
class RagQueryRequest(BaseModel):
    question: str
    top_k: int = 5

class JobSearchRequest(BaseModel):
    keyword: str
    location: str
    per_page: int = 5

class ResumeSearchRequest(BaseModel):
    question: str
    top_k: int = 5

# =========================================================
# UTIL
# =========================================================
def normalize_resume_filename(filename: str) -> str:
    ext = Path(filename).suffix.lower() or ".pdf"
    stem = Path(filename).stem.lower().strip()

    stem = re.sub(r"[^a-z0-9\s_-]", "", stem)
    stem = stem.replace("-", " ").replace("_", " ")
    stem = re.sub(r"\s+", " ", stem).strip()

    if "resume" not in stem:
        stem = f"{stem} resume"

    stem = stem.replace(" ", "_")
    return f"{stem}{ext}"

# =========================================================
# ROUTES
# =========================================================
@app.post("/api/rag/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        file_path = UPLOAD_DIR / normalize_resume_filename(file.filename)

        with open(file_path, "wb") as f:
            f.write(await file.read())

        result = ingest_pdf_hybrid(str(file_path), file_path.name)

        return {
            "message": "PDF uploaded and ingested successfully",
            "filename": file_path.name,
            "result": result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/query")
async def query_rag(payload: RagQueryRequest):
    response = await run_orchestrator(payload.question, payload.top_k)

    return {
        "answer": response.get("answer"),
        "sources": response.get("sources", []),
        "mode": response.get("mode"),
        "jobs": response.get("jobs", []),
    }


@app.post("/api/jobs/search")
async def search_jobs_api(request: JobSearchRequest):
    return await run_job_search_agent(
        keyword=request.keyword,
        location=request.location,
        per_page=request.per_page,
    )


@app.post("/api/jobs/resume")
async def search_resume_api(request: ResumeSearchRequest):
    return await run_resume_agent(
        question=request.question,
        top_k=request.top_k
    )