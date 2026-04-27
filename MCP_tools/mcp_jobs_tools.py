# MCP_tools/mcp_jobs_tools.py

from mcp.server.fastmcp import FastMCP
import json
import traceback
import random
import os

from qdrant_client import QdrantClient, models
from typing import Any
from tools.data_loader import search_jobs_from_qd, embed_dense, rerank_results, embed_sparse, hybrid_search_jobs
from tools.job_searcher import search_jobs, clean_job_results
from tools.job_cleanning_chunk import ingest_jobs_to_qdrant, make_cache_key, make_job_id
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from langchain_core.prompts import ChatPromptTemplate
from LLM.llm import llm
from custom.custom_types import MatchResult, MCPToolResult
import logging
from pathlib import Path
import logging
import os

def get_qdrant():
    return QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))


RESUME_COLLECTION_HYBRID = "pdf_chunks_hybrid"
# ============================================================================
# Logging Configuration
# ============================================================================

LOG_DIR = Path("MCP_tools")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logging.basicConfig(level=logging.INFO)
if not logger.handlers:
    file_handler = logging.FileHandler(LOG_DIR / "mcp_debug.log")
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# ============================================================================
# Response Helpers
# ============================================================================

def ok_response(tool: str, jobs: list | None = None, meta: dict | None = None) -> dict:
    """Build successful tool response"""
    return {
        "ok": True,
        "tool": tool,
        "jobs": jobs or [],
        "error": None,
        "meta": meta or {},
    }


def error_response(tool: str, error: str, jobs: list | None = None, meta: dict | None = None) -> dict:
    """Build error tool response"""
    return {
        "ok": False,
        "tool": tool,
        "jobs": jobs or [],
        "error": error,
        "meta": meta or {},
    }

def get_resume_source_id() -> str | None:
    env_id = os.getenv("RESUME_SOURCE_ID")
    if env_id:
        return env_id

    filters = [
        Filter(must=[FieldCondition(key="source_type", match=MatchValue(value="resume"))]),
        None,
    ]

    for f in filters:
        try:
            kwargs = dict(
                collection_name="pdf_chunks_hybrid",
                limit=1,
                with_payload=True,
                with_vectors=False,
            )
            if f:
                kwargs["scroll_filter"] = f

            results, _ = get_qdrant().scroll(**kwargs)
            if results:
                payload = results[0].payload or {}
                return payload.get("source_id") or payload.get("source")
        except Exception:
            logger.exception("Failed while looking up resume_source_id")

    return None

# ============================================================================
# Qdrant Client Configuration
# ============================================================================

RESUME_COLLECTION = "pdf_chunks_hybrid"


def fetch_resume_text(resume_source_id: str, limit: int = 30) -> str:
    """
    Fetch resume chunks from Qdrant.
    
    Args:
        resume_source_id: Source ID of the resume document
        limit: Maximum number of chunks to fetch
        
    Returns:
        Concatenated resume text from all chunks
    """
    for key in ["source_id", "source"]:
        try:
            results, _ = get_qdrant().scroll(
                collection_name=RESUME_COLLECTION,
                scroll_filter=Filter(
                    must=[FieldCondition(key=key, match=MatchValue(value=resume_source_id))]
                ),
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
            if results:
                chunks = [hit.payload.get("text", "") for hit in results if hit.payload.get("text")]
                logger.info(f"Fetched resume with key={key}: {len(chunks)} chunks")
                return "\n\n".join(chunks)
        except Exception as e:
            logger.warning(f"Failed to fetch resume with key={key}: {e}")
    
    logger.error(f"No resume found for source_id: {resume_source_id}")
    return ""


# ============================================================================
# Query Parsing and Filtering
# ============================================================================

PLATFORM_WORDS = [
    "via linkedin", "on linkedin", "from linkedin", "linkedin",
    "via indeed", "on indeed", "from indeed", "indeed",
    "via jobstreet", "jobstreet", "via glassdoor", "glassdoor",
    "via google", "on google",
]

LEVEL_PATTERNS = {
    "junior": ["junior", "entry level", "entry-level", "fresh grad", "fresh graduate", "0-2 years", "intern"],
    "mid": ["mid level", "mid-level", "intermediate", "2-5 years", "3+ years"],
    "senior": ["senior", "sr.", "lead", "principal", "staff", "head of", "5+ years", "7+ years"],
}

LEVEL_EXCLUDES = {
    "junior": ["senior", "sr ", "lead", "principal", "staff", "manager", "director", "head", "vp"],
    "mid": ["junior", "entry", "intern", "senior", "principal", "director"],
    "senior": ["junior", "entry", "intern", "fresh grad"],
    "any": [],
}

KNOWN_SKILLS = [
    "python", "javascript", "typescript", "java", "golang", "rust", "c++", "c#",
    "react", "vue", "angular", "node", "fastapi", "django", "flask", "spring",
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
    "langchain", "llm", "openai", "pytorch", "tensorflow", "mlops",
    "machine learning", "deep learning", "nlp", "computer vision",
]


def parse_job_query(keyword: str, location: str) -> dict:
    """
    Parse and extract information from a job search query.
    
    Args:
        keyword: Job search keyword
        location: Job location
        
    Returns:
        Dictionary with parsed query information including experience level and skills
    """
    clean = keyword.lower()
    
    # Remove platform references
    for pw in PLATFORM_WORDS:
        clean = clean.replace(pw, "").strip()

    # Detect experience level
    experience_level = "any"
    for level, patterns in LEVEL_PATTERNS.items():
        if any(p in clean for p in patterns):
            experience_level = level
            break

    # Extract known skills
    required_skills = [s for s in KNOWN_SKILLS if s in clean]

    # Clean keyword by removing level words
    level_words = [p for patterns in LEVEL_PATTERNS.values() for p in patterns]
    clean_keyword = clean
    for lw in level_words:
        clean_keyword = clean_keyword.replace(lw, "").strip()

    clean_keyword = " ".join(w.capitalize() for w in clean_keyword.split() if w)
    if len(clean_keyword) < 3:
        clean_keyword = keyword

    exclude_keywords = LEVEL_EXCLUDES.get(experience_level, [])

    result = {
        "keyword": clean_keyword,
        "location": location,
        "experience_level": experience_level,
        "required_skills": required_skills,
        "exclude_keywords": exclude_keywords,
    }
    
    logger.debug(f"Parsed query: {json.dumps(result)}")
    return result


def post_filter_jobs(jobs: list, parsed: dict) -> list:
    """
    Filter jobs based on parsed query parameters.
    
    Args:
        jobs: List of jobs to filter
        parsed: Parsed query parameters
        
    Returns:
        Filtered list of jobs
    """
    exclude = [w.lower() for w in parsed.get("exclude_keywords", [])]
    filtered = []
    
    for job in jobs:
        title = (job.get("title") or "").lower()
        
        # Skip if matches exclude keywords
        if any(ex in title for ex in exclude):
            logger.debug(f"Filtered out: {job.get('title')} (matched exclude keyword)")
            continue

        filtered.append(job)

    logger.info(f"Job filtering: {len(jobs)} → {len(filtered)} jobs")
    return filtered


# ============================================================================
# Module-level Cache
# ============================================================================

_last_jobs: list = []
_raw_jobs_cache: dict = {}

mcp = FastMCP("job-tools")


# ============================================================================
# Tool 1: Search Jobs
# ============================================================================

@mcp.tool()
def search_jobs_tool(keyword: str, location: str = "Malaysia", per_page: int = 5) -> dict:
    """
    Search for jobs matching the given criteria.
    
    Args:
        keyword: Job title or skill keywords
        location: Job location (default: Malaysia)
        per_page: Number of results to return (default: 5)
        
    Returns:
        Dictionary with search results and metadata
    """
    tool_name = "search_jobs_tool"
    
    try:
        random_page = random.randint(1, 3)
        parsed = parse_job_query(keyword, location)
        clean_keyword = parsed.get("keyword", keyword)
        clean_location = parsed.get("location", location)


        # Fetch jobs from API
        jobs = search_jobs(
            clean_keyword,
            clean_location,
            page=random_page,
            per_page=per_page + 3
        )
        

        # Clean and filter results
        results = clean_job_results(jobs)
        # results = post_filter_jobs(results, parsed)
        results = results[:per_page]


        # Cache raw job data
        global _raw_jobs_cache, _last_jobs
        for job in results:
            job_id = make_job_id(job)
            _raw_jobs_cache[job_id] = job

        _last_jobs = results


        return ok_response(
            tool=tool_name,
            jobs=results,
            meta={
                "parsed_query": parsed,
                "count": len(results),
                "page_used": random_page,
            },
        )

    except Exception as e:
        logger.error(f"search_jobs_tool failed: {str(e)}", exc_info=True)
        return error_response(tool=tool_name, error=str(e))


# ============================================================================
# Tool 2: Match Jobs with Resume
# ============================================================================



@mcp.tool()
def match_jobs_tool(jobs: list[dict]) -> dict:
    tool_name = "match_jobs_tool"

    try:
        if not isinstance(jobs, list):
            return error_response(tool_name, "jobs must be a list")
        
        resume_source_id = get_resume_source_id()
        
        resume_text = fetch_resume_text(resume_source_id)
        if not resume_text:
            return error_response(tool_name, f"No resume found for qdrant'")

        prompt = ChatPromptTemplate.from_template("""
        You are a resume-job matching assistant.

        Your task is to evaluate how well a candidate's resume matches a job.

        Resume:
        {resume}

        Job:
        Title: {title}
        Company: {company}
        Location: {location}
        Description: {job_description}

        Return ONLY one valid JSON object in exactly this format:
        {{
        "fit_score": 0.0,
        "matching_skills": [],
        "missing_skills": [],
        "reason": ""
        }}

        Strict output rules:
        - Return ONLY the JSON object
        - Do NOT wrap the JSON in markdown fences
        - Do NOT output ```json
        - Do NOT output ```
        - Do NOT include any explanation, heading, notes, or extra text
        - Do NOT add text before or after the JSON
        - fit_score must be a float from 0.0 to 1.0 and fit_score should not be none

        Scoring rules:
        - Working experience is one of the MOST IMPORTANT factors in scoring
        - Pay very close attention to explicit experience requirements in the job description
        - Compare the candidate's resume experience against the required years/level in the job
        - If the resume does NOT clearly meet the required years of experience, reduce the fit_score significantly
        - If the role is for fresh graduates / junior / entry-level and the resume matches, increase the fit_score
        - matching_skills: short skill/tool names found in BOTH resume and job; may include matched experience level phrases
        - missing_skills: short skill names, tool names, and important missing experience requirements; max 10 items
        - reason: 4~5 sentences explicitly mentioning whether the candidate meets, partially meets, or does not meet the required experience level
        """)

        # ✅ Structured LLM (KEY CHANGE)
        structured_llm = llm.with_structured_output(MatchResult)

        logger.info(f"structured llm {structured_llm}")
        
        chain = prompt | structured_llm

        matched_jobs = []

        for job in jobs:
            try:
                parsed: MatchResult = chain.invoke({
                    "resume": resume_text,
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    "location": job.get("location", ""),
                    "job_description": job.get("job_description", "")
                })

                enriched = {
                    **job,
                    "fit_score": float(parsed.fit_score),
                    "matching_skills": parsed.matching_skills,
                    "missing_skills": parsed.missing_skills,
                    "reason": parsed.reason,
                }

                matched_jobs.append(enriched)

            except Exception as e:
                logger.warning(f"[MATCH FAILED] {job.get('title')} → {str(e)}")

                matched_jobs.append({
                    **job,
                    "fit_score": 0.0,
                    "matching_skills": [],
                    "missing_skills": [],
                    "reason": f"Scoring failed: {str(e)}",
                })

        global _last_jobs
        _last_jobs = matched_jobs

        return ok_response(
            tool=tool_name,
            jobs=matched_jobs,
            meta={"count": len(matched_jobs)}
        )

    except Exception as e:
        logger.error(f"match_jobs_tool failed: {str(e)}", exc_info=True)
        return error_response(tool_name, str(e))


# ============================================================================
# Tool 3: Ingest Jobs into Vector Database
# ============================================================================
@mcp.tool()
def ingest_jobs_tool(jobs: list[dict]) -> dict:
    tool_name = "ingest_jobs_tool"

    try:
        if not isinstance(jobs, list):
            return error_response(tool=tool_name, error="jobs must be list[dict]")

        enriched = []

        for job in jobs:
            if not isinstance(job, dict):
                continue

            job_id = job.get("id") or job.get("job_id") or make_job_id(job)

            # SAFE float conversion
            try:
                fit_score = float(job.get("fit_score", 0.0))
            except Exception:
                fit_score = 0.0

            merged = {
                "id": job_id,
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "location": job.get("location", ""),
                "job_description": job.get("job_description", ""),
                "link": job.get("link", ""),

                "fit_score": fit_score,

                "matching_skills": job.get("matching_skills") or [],
                "missing_skills": job.get("missing_skills") or [],
                "reason": job.get("reason") or ""
            }

            # ⚠️ ONLY merge raw AFTER cleaning (or remove this entirely)
            raw = _raw_jobs_cache.get(job_id)
            if isinstance(raw, dict):
                # prevent overwrite of clean fields
                raw.pop("fit_score", None)
                merged.update(raw)

            enriched.append(merged)

        ingest_jobs_to_qdrant(enriched)

        global _last_jobs
        _last_jobs = enriched

        return ok_response(
            tool=tool_name,
            jobs=enriched,
            meta={"count": len(enriched), "ingested": True}
        )

    except Exception as e:
        logger.error(f"ingest_jobs_tool failed: {e}", exc_info=True)
        return error_response(tool=tool_name, error=str(e))



def make_agent_state():
    return {
        "ok": True,
        "tool": None,
        "intent": None,
        "company_name": None,
        "location": None,
        "candidate_name": None,
        "rewritten_query": None,
        "result": None,
        "mode": None,
        "error": None,
    }


# ============================================================================
# Tool 4: Summarize Jobs
# ============================================================================
@mcp.tool()
def summarize_jobs_tool(jobs: list[dict], resume: str) -> dict:
    tool_name = "summarize_jobs_tool"
    

    try:
        # ✅ Proper validation
        if not isinstance(jobs, list) or not all(isinstance(j, dict) for j in jobs):
            logger.error(f"Invalid input: jobs must be a list of dicts, got {type(jobs)}")
            return error_response(tool=tool_name, error="Invalid input: jobs must be a list of dicts")

        if not jobs:
            logger.info("No jobs to summarize")
            return ok_response(tool=tool_name, jobs=[], meta={"count": 0})

        logger.info(f"Summarizing {len(jobs)} jobs (per-job mode)")

        # ✅ Per-job prompt (NO LIST → no dropping)
        prompt = ChatPromptTemplate.from_template("""
            You are a professional HR assistant and job summarization expert.

            Job:
            {job}

            Candidate Resume:
            {resume}

            Task:
            - Write a clean 5~7 sentence professional summary for this job.
            - Highlight the main responsibilities, required skills/tech stack, and the type of candidate who would excel.
            - Optionally provide a short HR-style insight or second opinion on the candidate fit based on the resume.

            Return ONLY JSON:
            {{
            "brief_summary": "",
            "hr_insight": ""
            }}

            Rules:
            - Do NOT include any extra text.
            - Do NOT wrap in markdown.
            - Keep it concise, professional, and actionable.
            - Focus on providing both a summary of the role and a human-like assessment.
            """)

        chain = prompt | llm

        summarized_jobs = []

        for idx, job in enumerate(jobs):
            try:
                response = chain.invoke({
                    "job": json.dumps(job, ensure_ascii=False),
                    "resume": resume

                })

                raw = response.content if hasattr(response, "content") else str(response)
                parsed = json.loads(raw)

                brief_summary = parsed.get("brief_summary", "")
                hr_insight = parsed.get("hr_insight", "")

                # ✅ Merge safely (NO DATA LOSS)
                enriched = {
                    **job,
                    "brief_summary": brief_summary or job.get("brief_summary", ""),
                    "fit_score": float(job.get("fit_score", 0.0) or 0.0),
                    "matching_skills": job.get("matching_skills", []) or [],
                    "missing_skills": job.get("missing_skills", []) or [],
                    "reason": job.get("reason", "") or "",
                }
                


                summarized_jobs.append(enriched)

                logger.debug(f"[Summarize] {idx+1}/{len(jobs)} OK: {job.get('title')}")

            except Exception as e:
                logger.warning(f"[Summarize] Failed for job '{job.get('title', '')}': {str(e)}")

                # ✅ FAIL-SAFE → never drop job
                summarized_jobs.append({
                    **job,
                    "brief_summary": job.get("brief_summary", ""),
                    "fit_score": float(job.get("fit_score", 0.0) or 0.0),
                    "matching_skills": job.get("matching_skills", []) or [],
                    "missing_skills": job.get("missing_skills", []) or [],
                    "reason": job.get("reason", f"Summarization failed: {str(e)}"),
                })

        global _last_jobs
        _last_jobs = summarized_jobs

        logger.info(f"Summarization completed: {len(summarized_jobs)} jobs")

        return ok_response(
            tool=tool_name,
            jobs=summarized_jobs,
            meta={"count": len(summarized_jobs)},
        )

    except Exception as e:
        logger.error(f"summarize_jobs_tool failed: {str(e)}", exc_info=True)
        return error_response(tool=tool_name, error=str(e))
        
# ============================================================================
# Tool 5: analyze_query_with_llm
# ============================================================================

@mcp.tool()
def analyze_query_with_llm(question: str) -> dict:
    state = make_agent_state()
    state["tool"] = "analyze_query_with_llm"

    prompt = ChatPromptTemplate.from_template("""
    You are a query analysis assistant for an HR AI system.

    Your task:
    1. Detect the user's primary intent
    2. Extract company_name if clearly mentioned
    3. Extract location if clearly mentioned
    4. Extract candidate_name if clearly mentioned
    5. Rewrite the query into a concise retrieval-friendly query

    Allowed intents:
    - resume
    - job_details
    - job_search
    - qa

    Intent meaning:
    - resume: questions about candidate profile, resume, skills, education, experience, qualifications, projects, fit
    - job_details: questions asking to summarize a company or summarize jobs from a company
    - job_search: questions asking to list, find, show, or retrieve jobs
    - qa: all other general questions

    Rules:
    - Return ONLY valid JSON
    - Do not explain
    - Do not add markdown
    - If no company is mentioned, use null
    - If no location is mentioned, use null
    - If no candidate name is mentioned, use null
    - candidate_name must be lowercase_with_underscores if present
    - rewritten_query must preserve the original meaning
    - rewritten_query should remove conversational filler and be optimized for retrieval/search
    - Do not invent facts not implied by the question

    Return this exact JSON format:
    {{
      "rewritten_query": "string",
      "intent": "resume|job_details|job_search|qa",
      "company_name": null,
      "location": null,
      "candidate_name": null
    }}

    Examples:

    User: Show me jobs from Grab in Malaysia
    Output:
    {{"rewritten_query":"grab jobs openings roles positions malaysia hiring","intent":"job_search","company_name":"Grab","location":"Malaysia","candidate_name":null}}

    User: Summarize the company Grab
    Output:
    {{"rewritten_query":"grab company summary overview roles hiring","intent":"job_details","company_name":"Grab","location":null,"candidate_name":null}}

    User: Give me the resume of Hoo Vi Ying
    Output:
    {{"rewritten_query":"hoo vi ying resume profile education skills experience projects contact information","intent":"resume","company_name":null,"location":null,"candidate_name":"hoo_vi_ying"}}

    User: What skills does this candidate have?
    Output:
    {{"rewritten_query":"candidate resume skills technical skills qualifications tools experience","intent":"resume","company_name":null,"location":null,"candidate_name":null}}

    User: What is RAG?
    Output:
    {{"rewritten_query":"RAG retrieval augmented generation explanation","intent":"qa","company_name":null,"location":null,"candidate_name":null}}

    User question:
    {question}
    """)

    try:
        chain = prompt | llm
        response = chain.invoke({"question": question})
        content = response.content.strip()

        parsed = json.loads(content)

        rewritten_query = parsed.get("rewritten_query", question)
        intent = parsed.get("intent", "qa")
        company_name = parsed.get("company_name")
        location = parsed.get("location")
        candidate_name = parsed.get("candidate_name")       

        allowed_intents = {"resume", "job_details", "job_search", "qa"}
        if intent not in allowed_intents:
            intent = "qa"

        if not isinstance(rewritten_query, str) or not rewritten_query.strip():
            rewritten_query = question

        logger.info(f"Query analysis result: intent={intent}, company_name={company_name}, location={location}, candidate_name={candidate_name}, rewritten_query={rewritten_query}")

        state.update({
            "intent": intent,
            "company_name": company_name,
            "location": location,
            "candidate_name": candidate_name,
            "rewritten_query": rewritten_query.strip(),
            "result": None,
            "mode": "resume" if intent == "resume" else intent,
            "error": None,
            "ok": True,
        })
        return state

    except Exception as e:
        state.update({
            "ok": False,
            "intent": "qa",
            "company_name": None,
            "location": None,
            "candidate_name": None,
            "rewritten_query": question,
            "result": None,
            "mode": "qa",
            "error": str(e),
        })
        return state

# ============================================================================
# Tool 7: Intent detection
# ============================================================================
@mcp.tool()
def search_resume(
    question: str,
    top_k: int = 5,
    candidate_name: str | None = None
) -> dict:

    state = make_agent_state()

    state["tool"] = "search_resume"
    state["intent"] = "resume"
    state["rewritten_query"] = question
    state["candidate_name"] = candidate_name
    state["mode"] = "resume"

    try:
        # -----------------------------
        # EMBEDDINGS
        # -----------------------------
        dense_query = embed_dense(question)
        sparse_indices, sparse_values = embed_sparse(question)

        # -----------------------------
        # BUILD FILTER
        # -----------------------------
        query_filter = None
        target_source_id = None

        if candidate_name:
            normalized = candidate_name.strip().lower().replace(" ", "_")
            target_source_id = f"{normalized}_resume.pdf"

            logger.info(f"[search_resume] filter source_id = {target_source_id}")

            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="source_id",
                        match=models.MatchValue(value=target_source_id)
                    )
                ]
            )

        # -----------------------------
        # QUERY QDRANT
        # -----------------------------
        response = get_qdrant().query_points(
            collection_name=RESUME_COLLECTION_HYBRID,
            prefetch=[
                models.Prefetch(query=dense_query, using="dense"),
                models.Prefetch(
                    query=models.SparseVector(
                        indices=sparse_indices,
                        values=sparse_values,
                    ),
                    using="sparse"
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=top_k,
            with_payload=True,
            with_vectors=False,
            query_filter=query_filter,
        )

        # -----------------------------
        # DEBUG (IMPORTANT)
        # -----------------------------
        logger.info(f"[search_resume] points returned = {len(response.points)}")

        chunks = []
        scores = []

        for point in response.points:
            payload = point.payload or {}

            logger.debug(f"PAYLOAD: {payload}")

            # support BOTH flat and nested formats
            text = payload.get("text") or payload.get("payload", {}).get("text", "")
            source_id = payload.get("source_id") or payload.get("payload", {}).get("source_id", "")

            chunks.append({
                "text": text,
                "source_id": source_id,
            })

            scores.append(float(point.score or 0.0))

        # -----------------------------
        # FALLBACK 1: filter returned nothing
        # -----------------------------
        if not chunks and query_filter is not None:
            logger.warning("[search_resume] filter returned 0 results → retrying without filter")

            response = get_qdrant().query_points(
                collection_name=RESUME_COLLECTION_HYBRID,
                prefetch=[
                    models.Prefetch(query=dense_query, using="dense"),
                    models.Prefetch(
                        query=models.SparseVector(
                            indices=sparse_indices,
                            values=sparse_values,
                        ),
                        using="sparse"
                    ),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=top_k,
                with_payload=True,
                with_vectors=False,
            )

            chunks = []
            scores = []

            for point in response.points:
                payload = point.payload or {}

                text = payload.get("text") or payload.get("payload", {}).get("text", "")
                source_id = payload.get("source_id") or payload.get("payload", {}).get("source_id", "")

                chunks.append({
                    "text": text,
                    "source_id": source_id,
                })

                scores.append(float(point.score or 0.0))

        # -----------------------------
        # EMPTY RESULT HANDLING
        # -----------------------------
        if not chunks:
            return {
                "ok": True,
                "data": {
                    "chunks": [],
                    "count": 0
                },
                "error": None,
                "meta": {
                    "message": "no resume chunks found"
                }
            }

        # -----------------------------
        # RERANK
        # -----------------------------
        search_results = {
            "payloads": chunks,
            "scores": scores,
        }

        reranked = rerank_results(question, search_results, top_k)

        if not reranked:
            reranked = chunks[:top_k]

        # -----------------------------
        # FINAL RESPONSE
        # -----------------------------
        state.update({
            "ok": True,
            "result": reranked,
            "error": None,
        })

        return {
            "ok": True,
            "data": {
                "chunks": reranked,
                "count": len(reranked)
            },
            "error": None,
            "meta": {
                "tool": "search_resume",
                "filtered": candidate_name is not None
            }
        }

    except Exception as e:
        logger.exception("[search_resume] failed")

        return {
            "ok": False,
            "data": {
                "chunks": [],
                "count": 0
            },
            "error": str(e),
            "meta": {}
        }


# ============================================================================
# Tool 8: Summarize tool
# ============================================================================
@mcp.tool()
def summarize_tool(context: str, question: str) -> dict:
    state = make_agent_state()
    state["tool"] = "summarize_tool"
    state["intent"] = "resume"
    state["rewritten_query"] = question
    state["mode"] = "resume"

    try:
        if not isinstance(context, str) or not context.strip():
            state.update({
                "ok": False,
                "result": {
                    "answer": "No resume data found."
                },
                "error": "Empty context",
            })
            return state

        prompt = ChatPromptTemplate.from_template("""
        You are a professional HR resume assistant.

        Your task is to answer the question using ONLY the provided resume context.

        Rules:
        - Use only the context provided
        - Do not make up facts
        - Do not mix details from multiple candidates
        - If the candidate's identity is unclear, say that the retrieved context is ambiguous
        - If a requested detail is missing, state that it is not available in the context

        Response Style Rules (VERY IMPORTANT):
        - If the question is specific (e.g., projects, skills, experience), give a **direct and concise answer**
        - If the question is broad (e.g., "summarize the candidate", "tell me about him"), give a **structured summary**
        - Do NOT force full resume format unless necessary
        - Keep answers clear, relevant, and easy to scan

        Examples:
        - Question: "What projects did he do?"
        → Return only projects in bullet points

        - Question: "Summarize this candidate"
        → Return full structured format

        Context:
        {context}

        Question:
        {question}

        Answer:
        """)

        chain = prompt | llm
        response = chain.invoke({
            "context": context,
            "question": question
        })

        logger.info(f"Summarization response: {response.content.strip()}")

        state.update({
            "ok": True,
            "result": {
                "answer": response.content.strip()
            },
            "error": None,
        })
        return state

    except Exception as e:
        state.update({
            "ok": False,
            "result": None,
            "error": str(e),
        })
        return state

# ============================================================================
# Tool 9: planner tool (LLM)
# ============================================================================
import json
import logging
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@mcp.tool()
def planner_tool(user_input, available_agents ):
    tool_name = "planner_tool"

    prompt = ChatPromptTemplate.from_template(
    """
    You are a STRICT AI PLANNER.

    Convert the user request into a JSON execution plan.

    You MUST output ONLY valid JSON.
    No explanation.
    No markdown.
    No extra text.

    -------------------------------------------------
    AVAILABLE AGENTS
    -------------------------------------------------

    {available_agents}

    -------------------------------------------------
    AGENT RULES
    -------------------------------------------------

    resume_agent:
    - Use for personal information / profile / resume
    - Params:
    - {user_input}
    - top_k

    job_search_agent:
    - Use for job search / job listings
    - Params:
    - user_input
    - location
    - per_page
    - page

    email_agent:
    - Use for sending emails / forwarding
    - Params:
    - context
    - user_email

    -------------------------------------------------
    STRICT RULES
    -------------------------------------------------

    1. ONLY use listed agents
    2. NEVER invent parameters or values
    3. ONLY extract values from user input
    4. If missing value → set null
    5. ALWAYS preserve execution order logically:
    - fetch data first
    - email last if needed
    6. top_k always 5
    7. DO NOT use:
    - use_previous_output
    - context chaining
    - dependencies between steps

    Each step must be INDEPENDENT.

    -------------------------------------------------
    OUTPUT FORMAT
    -------------------------------------------------

    {{
    "steps": [
        {{
        "agent": "agent_name",
        "params": {{
            "key": "value"
        }}
        }}
    ]
    }}

    -------------------------------------------------
    EXAMPLE 1
    -------------------------------------------------

    User:
    Send John Smith personal information to john@gmail.com

    Output:
    {{
    "steps": [
        {{
        "agent": "resume_agent",
        "params": {{
            "user_input": {user_input},
            "top_k": 5
        }}
        }},
        {{
        "agent": "email_agent",
        "params": {{
            "recipient": "john@gmail.com",
            "context": "John Smith personal information"
        }}
        }}
    ]
    }}

    -------------------------------------------------
    EXAMPLE 2
    -------------------------------------------------

    User:
    Search me a job about AI Engineer in Malaysia

    Output:
    {{
    "steps": [
        {{
        "agent": "job_search_agent",
        "params": {{
            "user_input": "AI Engineer",
            "location": "Malaysia",
            "per_page": 1,
            "page": 1
        }}
        }}
    ]
    }}

    -------------------------------------------------
    EXAMPLE 3
    -------------------------------------------------

    User:
    Find me one AI Engineer job and send it to smartqingtong@gmail.com

    Output:
    {{
    "steps": [
        {{
        "agent": "job_search_agent",
        "params": {{
            "user_input": "AI Engineer",
            "location": "Malaysia",
            "per_page": 1,
            "page": 1
        }}
        }},
        {{
        "agent": "email_agent",
        "params": {{
            "recipient": "smartqingtong@gmail.com",
            "context": "AI Engineer job information"
        }}
        }}
    ]
    }}

    -------------------------------------------------
    EXAMPLE 4
    -------------------------------------------------

    User:
    Find John Smith profile and send it to john@gmail.com

    Output:
    {{
    "steps": [
        {{
        "agent": "resume_agent",
        "params": {{
            "user_input": "John Smith",
            "top_k": 5
        }}
        }},
        {{
        "agent": "email_agent",
        "params": {{
            "recipient": "john@gmail.com",
            "context": "John Smith personal information"
        }}
        }}
    ]
    }}
    -------------------------------------------------
    USER INPUT
    -------------------------------------------------

    {user_input}
    """
    )

    try:
        chain = prompt | llm

        response = chain.invoke({
            "user_input": user_input,
            "available_agents": available_agents
        })

        logger.info(response.content)

        parsed = json.loads(response.content)

        result = MCPToolResult(
            success=True,
            tool_name=tool_name,
            result={
                "steps": parsed["steps"]
            },
            message="Execution plan created successfully"
        )

        logger.info(result)

        return result.model_dump()

    except Exception as e:
        logger.exception("Planner tool failed")

        return MCPToolResult(
            success=False,
            tool_name=tool_name,
            result={},
            error=str(e),
            message="Failed to generate execution plan"
        ).model_dump()



    



# ============================================================================
# Server Entry Point
# ============================================================================

if __name__ == "__main__":
    logger.info("Starting MCP job tools server")
    mcp.run(transport="stdio")




# @app.post("/api/rag/query")
# async def query_rag(payload: RagQueryRequest):
#     response = await run_orchestrator(payload.question, payload.top_k)

#     return {
#         "answer": response.get("answer"),
#         "sources": response.get("sources", []),
#         "mode": response.get("mode"),
#         "jobs": response.get("jobs", []),
#     }