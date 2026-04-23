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





from pydantic import BaseModel, Field
from typing import Dict, Callable, Awaitable, Any, List, Optional
import asyncio


# =========================================================
# STANDARD RESPONSE MODEL
# =========================================================

class AgentResponse(BaseModel):
    ok: bool = True
    mode: str = "qa"
    answer: str = ""
    jobs: List[dict] = Field(default_factory=list)
    error: Optional[str] = None
    meta: dict = Field(default_factory=dict)


# =========================================================
# ORCHESTRATOR AGENT
# =========================================================

class OrchestratorAgent:
    def __init__(self):
        self.agents: Dict[str, Callable[..., Awaitable[Any]]] = {}

    # -----------------------------------------------------
    # REGISTER AGENT
    # -----------------------------------------------------
    def register(self, name: str, func: Callable[..., Any]):
        self.agents[name] = func
        print(f"✅ Registered agent: {name}")

    # -----------------------------------------------------
    # RUN AGENT SAFELY
    # -----------------------------------------------------
    async def run(self, name: str, user_input: str = "", **kwargs):
        if name not in self.agents:
            raise ValueError(f"Agent '{name}' not found")

        print(f"🚀 Running agent: {name}")

        try:
            agent = self.agents[name]
            result = agent(user_input, **kwargs)

            if asyncio.iscoroutine(result):
                result = await result

            return result

        except Exception as e:
            print(f"❌ Agent failed: {name} -> {str(e)}")

            return {
                "ok": False,
                "answer": "",
                "jobs": [],
                "error": str(e),
                "meta": {"failed_agent": name}
            }

    # -----------------------------------------------------
    # INTENT MAPPING
    # -----------------------------------------------------
    def get_agent_by_intent(self, intent: str) -> str:
        return {
            "job_search": "job_search_agent",
            "resume": "resume_agent",
            "qa": "qa_agent",
            "email": "email_agent",
        }.get(intent, "qa_agent")

    # -----------------------------------------------------
    # POST ACTIONS
    # -----------------------------------------------------
    async def handle_post_actions(self, intent: str, jobs: list):
        if intent == "job_search" and jobs:
            print("📧 Triggering email agent...")
            await self.run("email_agent", user_input=str(jobs))

    # -----------------------------------------------------
    # SAFE EXTRACTORS (CRITICAL FIX)
    # -----------------------------------------------------
    def _extract_answer(self, result: dict) -> str:
        if not isinstance(result, dict):
            return ""

        # Case 1: direct answer
        if isinstance(result.get("answer"), str):
            return result["answer"]

        # Case 2: nested result.answer
        nested = result.get("result")
        if isinstance(nested, dict):
            if isinstance(nested.get("answer"), str):
                return nested["answer"]

        return ""

    def _extract_jobs(self, result: dict) -> list:
        if not isinstance(result, dict):
            return []

        # Case 1: direct jobs
        if isinstance(result.get("jobs"), list):
            return result["jobs"]

        # Case 2: nested result.jobs
        nested = result.get("result")
        if isinstance(nested, dict):
            if isinstance(nested.get("jobs"), list):
                return nested["jobs"]

        return []

    # -----------------------------------------------------
    # MAIN PIPELINE
    # -----------------------------------------------------
    async def run_pipeline(self, question: str, top_k: int = 5) -> dict:

        print("======================================")
        print("🔥 START ORCHESTRATOR PIPELINE")
        print("======================================")

        try:
            # -------------------------
            # Step 1: intent detection
            # -------------------------
            intent_data = await detect_intent_with_llm(question)

            intent = intent_data.get("intent", "qa")
            location = intent_data.get("location") or "Malaysia"
            number = intent_data.get("number") or top_k

            print(f"Detected intent: {intent}")

            # -------------------------
            # Step 2: select agent
            # -------------------------
            agent_name = self.get_agent_by_intent(intent)

            kwargs = {}

            if intent == "job_search":
                kwargs = {
                    "location": location,
                    "per_page": number,
                }

            elif intent == "resume":
                kwargs = {
                    "top_k": number,
                }

            # -------------------------
            # Step 3: run agent
            # -------------------------
            raw_result = await self.run(
                name=agent_name,
                user_input=question,
                **kwargs
            )

            # -------------------------
            # Step 4: normalize output
            # -------------------------
            answer = self._extract_answer(raw_result)
            jobs = self._extract_jobs(raw_result)

            if not answer and jobs:
                answer = f"Found {len(jobs)} relevant jobs"

            # -------------------------
            # Step 5: post actions
            # -------------------------
            await self.handle_post_actions(intent, jobs)

            # -------------------------
            # Step 6: final response
            # -------------------------
            final_response = AgentResponse(
                ok=raw_result.get("ok", True),
                mode=intent,
                answer=answer,
                jobs=jobs,
                error=raw_result.get("error"),
                meta=raw_result.get("meta", {})
            )

            return final_response.model_dump()

        except Exception as e:
            print(f"❌ Pipeline failed: {str(e)}")

            return AgentResponse(
                ok=False,
                mode="qa",
                answer="",
                jobs=[],
                error=str(e),
                meta={"stage": "run_pipeline"}
            ).model_dump()