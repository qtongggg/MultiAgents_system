import logging
from typing import Any, Dict, List

from MCP_agent.agent_setup import get_mcp_tools
from Agents.resume_agent import run_resume_agent
from Agents.job_search_agent import run_job_search_agent
from Agents.company_summary_agent import job_details_agent
from Agents.qa_agent import run_qa_agent
from Agents.router_agent import rewrite_query_with_llm, detect_intent_with_llm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper: safe extractors
# ---------------------------------------------------------------------------

def _extract_answer(result: dict) -> str:
    if not isinstance(result, dict):
        return ""
    # look inside `result` if present
    if "result" in result and isinstance(result["result"], dict):
        return result["result"].get("answer", "")
    return result.get("answer", "")

def _extract_jobs(result: dict) -> list:
    if not isinstance(result, dict):
        return []
    if "result" in result and isinstance(result["result"], dict):
        return result["result"].get("jobs", [])
    return result.get("jobs", [])

# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

async def run_orchestrator(question: str, top_k: int = 5) -> Dict[str, Any]:
    try:
        # ------------------------
        # Step 1: intent + rewrite
        # ------------------------

        rewrite_resp = await rewrite_query_with_llm(question)
    

        logger.info(f"[Orchestrator] rewrite response: {rewrite_resp}")
        intent_resp = await detect_intent_with_llm(question)

        query_intent = intent_resp.get("intent", "qa")
        company_name = intent_resp.get("company_name")
        location = intent_resp.get("location")
        number = intent_resp.get("number") if intent_resp.get("number") is not None else top_k

        rewritten_query = rewrite_resp.get("rewritten_query", question)

        logger.info(f"[Orchestrator] intent={query_intent}")

        # ------------------------
        # Step 2: route to agent
        # ------------------------
        if query_intent == "resume":
            raw_result = await run_resume_agent(rewritten_query, top_k=number)

        elif query_intent == "job_details":
            raw_result = await job_details_agent(
                question=question,
                company_name=company_name,
                location=location,
                top_k=top_k

            )
                    
        elif query_intent == "job_search":
            raw_result = await run_job_search_agent(
                keyword=rewritten_query,
                location=location or "Malaysia",
                per_page= number
            )
        else:
            raw_result = await run_qa_agent(rewritten_query)

        logger.info(f"Raw result: {raw_result}")

        # ------------------------
        # Step 3: normalize output
        # ------------------------
        # Orchestrator normalization
        answer = _extract_answer(raw_result)
        jobs = _extract_jobs(raw_result)

        # fallback string for job search summary
        if not answer and jobs:
            answer = f"Found {len(jobs)} relevant jobs"  # optional

        return {
            "ok": True,
            "mode": query_intent,
            "answer": answer,       # always string
            "jobs": jobs,           # always array
            "meta": { ... }
        }

    except Exception as e:
        logger.exception("[Orchestrator] FAILED")

        return {
            "ok": False,
            "mode": "error",
            "answer": "Something went wrong while processing your request.",
            "jobs": [],
            "error": str(e),
            "meta": {}
        }
