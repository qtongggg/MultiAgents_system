
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

# =========================================================
# ORCHESTRATOR AGENT (FIXED)
# =========================================================

class OrchestratorAgent:
    def __init__(self, registry: AgentRegistry):
        self.registry = registry

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
    # EXTRACT ANSWER
    # -----------------------------------------------------
    def _extract_answer(self, result: dict) -> str:
        if not isinstance(result, dict):
            return ""

        if isinstance(result.get("answer"), str):
            return result["answer"]

        data = result.get("data")
        if isinstance(data, dict):
            if isinstance(data.get("answer"), str):
                return data["answer"]

        nested = result.get("result")
        if isinstance(nested, dict):
            if isinstance(nested.get("answer"), str):
                return nested["answer"]

        return ""

    # -----------------------------------------------------
    # EXTRACT JOBS
    # -----------------------------------------------------
    def _extract_jobs(self, result: dict) -> list:
        if not isinstance(result, dict):
            return []

        if isinstance(result.get("jobs"), list):
            return result["jobs"]

        data = result.get("data")
        if isinstance(data, dict):
            if isinstance(data.get("jobs"), list):
                return data["jobs"]

        nested = result.get("result")
        if isinstance(nested, dict):
            if isinstance(nested.get("jobs"), list):
                return nested["jobs"]

        return []

    # -----------------------------------------------------
    # MERGE ANSWERS (FIXED)
    # -----------------------------------------------------
    def _merge_answers(self, answers: List[str]) -> str:
        clean = [
            a.strip()
            for a in answers
            if a and a.strip() and a != "Not available in the provided resume context."
        ]

        if not clean:
            return "No relevant information found."

        # remove duplicates
        unique = list(dict.fromkeys(clean))

        return "\n".join(f"- {a}" for a in unique)

    # -----------------------------------------------------
    # PIPELINE
    # -----------------------------------------------------
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

            logger.info(plan)

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
            final_mode = None
            answer_list: List[str] = []

            # ---------------------------------
            # 3. EXECUTE STEPS
            # ---------------------------------
            for step in steps:

                agent_name = step.get("agent")
                params = dict(step.get("params", {}))

                if not agent_name:
                    continue

                # EMAIL → background
                if agent_name == "email_agent":
                    params["context"] = job_results

                    asyncio.create_task(
                        self.run(name="email_agent", **params)
                    )
                    continue

                logger.info(f"Running agent: {agent_name}")
                logger.info(f"Params: {params}")

                result = await self.run(
                    name=agent_name,
                    **params
                )

                logger.info(f"Result from {agent_name}: {result}")

                final_mode = agent_name

                # -------------------------
                # COLLECT ANSWERS
                # -------------------------
                answer = self._extract_answer(result)
                if answer:
                    answer_list.append(answer)

                # -------------------------
                # COLLECT JOBS
                # -------------------------
                if agent_name == "job_search_agent":
                    jobs = self._extract_jobs(result)
                    if jobs:
                        job_results.extend(jobs)

            # ---------------------------------
            # 4. FINAL MERGE
            # ---------------------------------
            final_answer = self._merge_answers(answer_list)

            if not final_answer and job_results:
                final_answer = f"Found {len(job_results)} relevant jobs."

            # ---------------------------------
            # 5. RESPONSE
            # ---------------------------------
            return AgentResult(
                status="success",
                data={
                    "mode": final_mode,
                    "answer": final_answer,   # ✅ STRING now
                    "jobs": job_results       # ✅ merged jobs
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