import os
import asyncio
import logging
import re

from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from MCP_agent.agent_setup import shutdown_mcp
from MCP_agent.mcp_manager import ensure_mcp

from Agents.resume_agent import run_resume_agent
from Agents.job_search_agent import run_job_search_agent
from Agents.orchestrator import run_orchestrator
from tools.pdf_ingester import ingest_pdf_hybrid

# =========================================================
# ENV
# =========================================================
load_dotenv()

# Safe HuggingFace login (non-blocking)
from huggingface_hub import login
hf_token = os.getenv("HF_TOKEN")
if hf_token:
    try:
        login(token=hf_token)
    except Exception as e:
        print("HF login skipped:", e)

# =========================================================
# APP INIT (FAST START ONLY)
# =========================================================
app = FastAPI()

logging.basicConfig(level=logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# =========================================================
# DEBUG (IMPORTANT FOR RENDER TROUBLESHOOTING)
# =========================================================
print("🔥 API MODULE LOADED")

@app.on_event("startup")
async def startup_event():
    print("🚀 FastAPI STARTED (port should bind soon)")

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 FastAPI shutting down")
    await shutdown_mcp()

# =========================================================
# HEALTH CHECK (REQUIRED FOR RENDER)
# =========================================================
@app.get("/")
def root():
    return {"status": "running"}

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
    ext = Path(filename).suffix or ".pdf"
    stem = Path(filename).stem

    stem = re.sub(r"[^a-z0-9\s_-]", "", stem.lower())
    stem = re.sub(r"\s+", "_", stem.strip())

    return f"{stem}{ext}"

# =========================================================
# MCP LAZY LOADER (CRITICAL FIX)
# =========================================================
async def safe_mcp():
    try:
        await ensure_mcp()
    except Exception as e:
        print("⚠ MCP failed but API continues:", e)

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
            "message": "uploaded successfully",
            "filename": file_path.name,
            "result": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/query")
async def query_rag(payload: RagQueryRequest):
    await safe_mcp()

    response = await run_orchestrator(payload.question, payload.top_k)

    return response


@app.post("/api/jobs/search")
async def search_jobs_api(request: JobSearchRequest):
    await safe_mcp()

    return await run_job_search_agent(
        keyword=request.keyword,
        location=request.location,
        per_page=request.per_page,
    )


@app.post("/api/jobs/resume")
async def search_resume_api(request: ResumeSearchRequest):
    await safe_mcp()

    return await run_resume_agent(
        question=request.question,
        top_k=request.top_k
    )