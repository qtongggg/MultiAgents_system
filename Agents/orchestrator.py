
import asyncio
import logging
from typing import Optional, List
from pydantic import BaseModel, Field

from Agents.Agent_Registry import AgentRegistry
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

        
    async def run_pipeline(self, question: str):

        logger.info("🔥 START PLANNER PIPELINE")

        try:
            

            # ---------------------------------
            # 1. PLAN
            # ---------------------------------
            plan = await self.run(
                "planner_agent",
                user_input=question
            )

            steps = plan.get("result", {}).get("steps", [])

            if not steps:
                return AgentResult(
                    status="error",
                    data={},
                    error="No execution steps generated",
                    meta={"stage": "planner"}
                ).model_dump()

            # ---------------------------------
            # 2. MEMORY
            # ---------------------------------
            job_results = []
            final_result = None
            final_mode = None

            # ---------------------------------
            # 3. EXECUTE STEPS
            # ---------------------------------
            for step in steps:

                agent_name = step.get("agent")
                params = dict(step.get("params", {}))

                if not agent_name:
                    continue

                # ---------------------------------
                # EMAIL AGENT → BACKGROUND ONLY
                # ---------------------------------
                if agent_name == "email_agent":

                    params["context"] = job_results

                    logger.info(f"📧 Running EmailAgent in background: {params}")

                    asyncio.create_task(
                        self.run(
                            name="email_agent",
                            **params
                        )
                    )

                    # IMPORTANT:
                    # skip overwrite final_result
                    continue

                # ---------------------------------
                # NORMAL AGENT EXECUTION
                # ---------------------------------
                logger.info(f"Running agent: {agent_name}")
                logger.info(f"Params: {params}")

                result = await self.run(
                    name=agent_name,
                    **params
                )

                logger.info(f"Result from {agent_name}: {result}")

                final_mode = agent_name
                final_result = result

                # capture jobs
                if agent_name == "job_search_agent":
                    job_results = result.get("data", {}).get("jobs", [])

            # ---------------------------------
            # 4. NORMALIZE RESPONSE
            # ---------------------------------
            answer = self._extract_answer(final_result)
            jobs = self._extract_jobs(final_result)

            if not answer and jobs:
                answer = f"Found {len(jobs)} relevant jobs"

            if not answer and final_result:
                answer = str(final_result.get("data", {}))

            # ---------------------------------
            # 5. FINAL RESPONSE
            # ---------------------------------
            return AgentResult(
                status="success",
                data={
                    "mode": final_mode,
                    "answer": answer,
                    "jobs": jobs
                },
                meta={
                    "total_steps": len(steps),
                    "pipeline": "planner_orchestrator"
                }
            ).model_dump()

        except Exception as e:
            logger.exception("Pipeline failed")

            return AgentResult(
                status="error",
                data={},
                error=str(e),
                meta={"stage": "run_pipeline"}
            ).model_dump()