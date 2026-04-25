import logging
from symtable import Class
import asyncio
from typing import Any, Callable, Dict, Awaitable
from Agents.router_agent import rewrite_query_with_llm, detect_intent_with_llm
from Agents.Agent_Registry import AgentRegistry
# from Agents.email_agent import run_email_agent

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




import asyncio
import logging
from typing import Optional, List
from pydantic import BaseModel, Field

from Agents.Agent_Registry import AgentRegistry
from Agents.router_agent import detect_intent_with_llm
from custom.custom_types import AgentResult
logger = logging.getLogger(__name__)



# =========================================================
# ORCHESTRATOR AGENT
# =========================================================

class OrchestratorAgent:
    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    # -----------------------------------------------------
    # SAFE AGENT EXECUTION
    # -----------------------------------------------------
    async def run(self, name: str, **kwargs):
        try:
            agent = self.registry.get_agent(name)
            result = await agent.run(**kwargs)

            if isinstance(result, AgentResult):
                return result.model_dump()

            return result

        except Exception as e:
            logger.exception(f"[Orchestrator] Agent failed: {name}")

            return AgentResult(
                status="error",
                data={},
                error=str(e),
                meta={"agent": name}
            ).model_dump()

    # -----------------------------------------------------
    # INTENT → AGENT MAPPING
    # -----------------------------------------------------
    def get_agent_by_intent(self, intent: str) -> str:
        mapping = {
            "job_search": "job_search_agent",
            "resume": "resume_agent",
            "qa": "qa_agent",
            "email": "email_agent",
        }

        return mapping.get(intent, "qa_agent")

    # -----------------------------------------------------
    # POST ACTIONS (EMAIL AFTER JOB SEARCH)
    # -----------------------------------------------------
    async def handle_post_actions(self, intent: str, jobs: list):
        if intent == "job_search" and jobs:
            logger.info("📧 Triggering EmailAgent in background...")

            asyncio.create_task(
                self.run(
                    name="email_agent",
                    context=jobs,
                    user_email="smartqingtong@gmail.com"
                )
            )

    # -----------------------------------------------------
    # SAFE EXTRACT ANSWER
    # -----------------------------------------------------
    def _extract_answer(self, result: dict) -> str:
        if not isinstance(result, dict):
            return ""

        # Case 1: direct answer
        if isinstance(result.get("answer"), str):
            return result["answer"]

        # Case 2: AgentResult style -> data.answer
        data = result.get("data")
        if isinstance(data, dict):
            if isinstance(data.get("answer"), str):
                return data["answer"]

        # Case 3: legacy result.answer
        nested = result.get("result")
        if isinstance(nested, dict):
            if isinstance(nested.get("answer"), str):
                return nested["answer"]

        return ""

    # -----------------------------------------------------
    # SAFE EXTRACT JOBS
    # -----------------------------------------------------
    def _extract_jobs(self, result: dict) -> list:
        if not isinstance(result, dict):
            return []

        # Case 1: direct jobs
        if isinstance(result.get("jobs"), list):
            return result["jobs"]

        # Case 2: AgentResult style -> data.jobs
        data = result.get("data")
        if isinstance(data, dict):
            if isinstance(data.get("jobs"), list):
                return data["jobs"]

        # Case 3: legacy result.jobs
        nested = result.get("result")
        if isinstance(nested, dict):
            if isinstance(nested.get("jobs"), list):
                return nested["jobs"]

        return []

    # -----------------------------------------------------
    # MAIN PIPELINE
    # -----------------------------------------------------
    async def run_pipeline(self, question: str, location: str = "Malaysia", top_k: int = 5):
        logger.info("====================================")
        logger.info("🔥 START ORCHESTRATOR PIPELINE")
        logger.info("====================================")

        try:
            # ---------------------------------
            # STEP 1: Detect intent using LLM
            # ---------------------------------
            intent_data = await detect_intent_with_llm(question)

            intent = intent_data.get("intent", "qa")
            location = intent_data.get("location") or "Malaysia"
            number = intent_data.get("number") or top_k
            candidate_name = intent_data.get("candidate_name")

            if candidate_name:
                candidate_name = candidate_name.strip().lower().replace(" ", "_")

            logger.info(f"Detected intent: {intent}")
            logger.info(f"Candidate name: {candidate_name}")
            # ---------------------------------
            # STEP 2: Select agent
            # ---------------------------------
            agent_name = self.get_agent_by_intent(intent)

            kwargs = {}

            if intent == "job_search":
                kwargs = {
                    "user_input": question,
                    "location": location,
                    "per_page": number,
                    "page": 1,
                }

            elif intent == "resume":
                kwargs = {
                    "user_input": question,
                    "top_k": number
                }

            else:
                kwargs = {
                    "user_input": question
                }

            # ---------------------------------
            # STEP 3: Run selected agent
            # ---------------------------------
            raw_result = await self.run(
                name=agent_name,
                **kwargs
            )

            logger.info(raw_result)

            # ---------------------------------
            # STEP 4: Normalize output
            # ---------------------------------
            answer = self._extract_answer(raw_result)
            jobs = self._extract_jobs(raw_result)

            if not answer and jobs:
                answer = f"Found {len(jobs)} relevant jobs"

            # ---------------------------------
            # STEP 5: Trigger post actions
            # ---------------------------------
            await self.handle_post_actions(intent, jobs)

            # ---------------------------------
            # STEP 6: Final standardized response
            # ---------------------------------
            final_response = AgentResult(
                status = "success",
                data = {
                    "mode": intent,
                    "answer": answer,
                    "jobs": jobs
                },
                meta=raw_result.get("meta", {})
            )
            logger.info(final_response)
            return final_response.model_dump()

        except Exception as e:
            logger.exception("[Orchestrator] Pipeline failed")

            return AgentResult(
                status = "error",
                data = {},
                error=str(e),
                meta={"stage": "run_pipeline"}
            ).model_dump()