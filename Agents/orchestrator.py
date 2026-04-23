import logging
from symtable import Class
import asyncio
from typing import Any, Callable, Dict, Awaitable
from MCP_agent.agent_setup import get_mcp_tools
from Agents.resume_agent import run_resume_agent
from Agents.job_search_agent import run_job_search_agent
from Agents.company_summary_agent import job_details_agent
from Agents.qa_agent import run_qa_agent
from Agents.router_agent import rewrite_query_with_llm, detect_intent_with_llm
from Agents.email_agent import run_email_agent

logger = logging.getLogger(__name__)

# # ---------------------------------------------------------------------------
# # Helper: safe extractors
# # ---------------------------------------------------------------------------

# def _extract_answer(result: dict) -> str:
#     if not isinstance(result, dict):
#         return ""
#     # look inside `result` if present
#     if "result" in result and isinstance(result["result"], dict):
#         return result["result"].get("answer", "")
#     return result.get("answer", "")

# def _extract_jobs(result: dict) -> list:
#     if not isinstance(result, dict):
#         return []
#     if "result" in result and isinstance(result["result"], dict):
#         return result["result"].get("jobs", [])
#     return result.get("jobs", [])

# # ---------------------------------------------------------------------------
# # Orchestrator
# # ---------------------------------------------------------------------------

# async def run_orchestrator(question: str, top_k: int = 5) -> Dict[str, Any]:
#     try:
#         # ------------------------
#         # Step 1: intent + rewrite
#         # ------------------------

#         rewrite_resp = await rewrite_query_with_llm(question)
#         intent_resp = await detect_intent_with_llm(question)

#         query_intent = intent_resp.get("intent", "qa")
#         company_name = intent_resp.get("company_name")
#         location = intent_resp.get("location")
#         number = intent_resp.get("number") if intent_resp.get("number") is not None else top_k


#         rewritten_query = rewrite_resp.get("rewritten_query", question)


#         # ------------------------
#         # Step 2: route to agent
#         # ------------------------
#         if query_intent == "resume":
#             raw_result = await run_resume_agent(rewritten_query, top_k=number)

#         elif query_intent == "job_details":
#             raw_result = await job_details_agent(
#                 question=question,
#                 company_name=company_name,
#                 location=location,
#                 top_k=top_k

#             )
                    
#         elif query_intent == "job_search":
#             raw_result = await run_job_search_agent(
#                 keyword=rewritten_query,
#                 location=location or "Malaysia",
#                 per_page= number
#             )

#             await run_email_agent(context=str(raw_result['result'].get('jobs', []))) # we can also move this inside the job search agent 


#         else:
#             raw_result = await run_qa_agent(rewritten_query) 


#         # ------------------------
#         # Step 3: normalize output
#         # ------------------------
#         # Orchestrator normalization
#         answer = _extract_answer(raw_result)
#         jobs = _extract_jobs(raw_result)

#         # fallback string for job search summary
#         if not answer and jobs:
#             answer = f"Found {len(jobs)} relevant jobs"  # optional

#         return {
#             "ok": True,
#             "mode": query_intent,
#             "answer": answer,       # always string
#             "jobs": jobs,           # always array
#             "meta": { ... }
#         }

#     except Exception as e:
#         logger.exception("[Orchestrator] FAILED")

#         return {
#             "ok": False,
#             "mode": "error",
#             "answer": "Something went wrong while processing your request.",
#             "jobs": [],
#             "error": str(e),
#             "meta": {}
#         }





class OrchestratorAgent:
    def __init__(self):
        self.agents: Dict[str, Callable[..., Awaitable[Any]]] = {}

    # -----------------------------
    # Register
    # -----------------------------
    def register(self, name: str, func: Callable[..., Any]):
        self.agents[name] = func
        print(f"Registered agent: {name}")

    # -----------------------------
    # Run agent
    # -----------------------------
    async def run(self, name: str, user_input: str = "", **kwargs):
        if name not in self.agents:
            raise ValueError(f"Agent '{name}' not found")

        print(f"Running agent: {name}")

        agent = self.agents[name]
        result = agent(user_input, **kwargs)

        if asyncio.iscoroutine(result):
            result = await result

        return result

    # =========================================================
    # 🔥 CLEAN HELPER METHODS (moved out)
    # =========================================================
    def _extract_answer(self, result: dict) -> str:
        if not isinstance(result, dict):
            return ""

        if "result" in result and isinstance(result["result"], dict):
            return result["result"].get("answer", "")

        return result.get("answer", "")

    def _extract_jobs(self, result: dict) -> list:
        if not isinstance(result, dict):
            return []

        if "result" in result and isinstance(result["result"], dict):
            return result["result"].get("jobs", [])

        return result.get("jobs", [])

    # Optional: combined extractor (cleaner usage)
    def _normalize_output(self, raw_result: dict) -> dict:
        answer = self._extract_answer(raw_result)
        jobs = self._extract_jobs(raw_result)

        if not answer and jobs:
            answer = f"Found {len(jobs)} relevant jobs"

        return {
            "answer": answer,
            "jobs": jobs
        }

    # =========================================================
    # PIPELINE
    # =========================================================
    async def run_pipeline(self, question: str, top_k: int = 5) -> dict:
        print("Starting orchestrator pipeline")

        intent = await detect_intent_with_llm(question)

        query_type = intent.get("intent", "qa")
        location = intent.get("location") or "Malaysia"
        number = intent.get("number") or top_k

        print(f"Intent: {query_type}")

        # -----------------------------
        # Routing
        # -----------------------------
        if query_type == "job_search":
            raw_result = await self.run(
                "job_search_agent",
                question,
                location=location,
                per_page=number
            )

            jobs = self._extract_jobs(raw_result)

            if jobs:
                await self.run("email_agent",str(jobs))

        elif query_type == "resume":
            raw_result = await self.run(
                "resume_agent",
                question,
                top_k=number
            )

        else:
            raw_result = await self.run("qa_agent", question)

        # -----------------------------
        # Normalize output
        # -----------------------------
        normalized = self._normalize_output(raw_result)

        return {
            "ok": True,
            "mode": query_type,
            "answer": normalized["answer"],
            "jobs": normalized["jobs"]
        }