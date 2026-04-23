from Agents.Base_agent import BaseAgent, AgentInfo
from MCP_agent.agent_setup import get_mcp_tools
import asyncio
import logging

from custom.custom_types import (
    AgentResult,
    JobSearchRequest,
    JobSearchInfo,
    MatchJobInfo
)

logger = logging.getLogger(__name__)


class JobSearchAgent(BaseAgent):

    def __init__(self, info: AgentInfo):
        super().__init__(info)
        self._tools = None

    async def get_tools(self):
        if self._tools is None:
            self._tools = await get_mcp_tools()
        return self._tools

    async def run_background_task(self, coro, logger, task_name="task"):
        try:
            logger.info(f"[{task_name}] START")

            result = await coro

            logger.info(f"[{task_name}] SUCCESS RESULT: {result}")

        except Exception as e:
            logger.error(f"[{task_name}] FAILED: {e}", exc_info=True)

    async def run(self, user_request: JobSearchRequest):

        try:
            #####################
            # 1. SEARCH JOBS
            #####################
            mcp_tools = await self.get_tools()
            search_jobs_tool = mcp_tools["search_jobs_tool"]

            search_result = await self.execute_tool(
                search_jobs_tool,
                {
                    "keyword": user_request.get("keyword", ""),
                    "location": user_request.get("location", "Malaysia"),
                    "per_page": user_request.get("per_page", 1),
                    "page": user_request.get("page", 1)
                }
            )

            raw_jobs = search_result.get("jobs", [])

            cleaned_jobs = [
                JobSearchInfo.model_validate(job)
                for job in raw_jobs
                if isinstance(job, dict)
            ]

            #####################
            # 2. MATCH JOBS
            #####################
            match_jobs_tool = mcp_tools["match_jobs_tool"]

            matched_jobs = []

            for job in cleaned_jobs:
                match_result = await self.execute_tool(
                    match_jobs_tool,
                    {
                        "jobs": [job.model_dump()]
                    }
                )

                for j in match_result["jobs"]:
                    matched_jobs.append(
                        MatchJobInfo.model_validate(j).model_dump()
                    )

            #####################
            # 3. INGEST (BACKGROUND SAFE)
            #####################
            ingest_jobs_tool = mcp_tools["ingest_jobs_tool"]

            await self.execute_tool(
                ingest_jobs_tool,
                {"jobs": matched_jobs}
            )

            

            #####################
            # 4. FINAL RESPONSE
            #####################
            return AgentResult(
                status="success",
                data={
                    "jobs": matched_jobs
                },
                meta={
                    "count": len(matched_jobs)
                }
            )

        except Exception as e:
            logger.error(f"JobSearchAgent failed: {e}", exc_info=True)

            return AgentResult(
                status="error",
                data={},
                error=str(e)
            )
        
