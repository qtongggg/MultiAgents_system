from Agents.Base_agent import BaseAgent, AgentInfo
from MCP_agent.agent_setup import get_mcp_tools
import asyncio
import logging

from Agents.email_agent import EmailAgent
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


    async def run_background_task(self, coro, logger, task_name="task"):
        try:

            result = await coro


        except Exception as e:
            logger.error(f"[{task_name}] FAILED: {e}", exc_info=True)

    async def run(self, user_input: str, location: str, per_page: int, page: int):

        try:
            #####################
            # 1. SEARCH JOBS
            #####################
            mcp_tools = await self.get_tools()
            search_jobs_tool = mcp_tools["search_jobs_tool"]

            search_result = await self.execute_tool(
                search_jobs_tool,
                {
                    "keyword": user_input,
                    "location": location or "malaysia",
                    "per_page": per_page,
                    "page": page 
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

            tasks = [
                self.execute_tool(
                    match_jobs_tool,
                    {
                        "jobs": [job.model_dump()]
                    }
                )
                for job in cleaned_jobs
            ]

            results = await asyncio.gather(*tasks)

            matched_jobs = []

            for match_result in results:
                for j in match_result.get("jobs", []):
                    matched_jobs.append(
                        MatchJobInfo.model_validate(j).model_dump()
                    )

            #####################
            # 3. INGEST (BACKGROUND SAFE)
            #####################
            ingest_jobs_tool = mcp_tools["ingest_jobs_tool"]

            asyncio.create_task(
                self.run_background_task(
                    self.execute_tool(
                        ingest_jobs_tool,
                        {"jobs": matched_jobs}
                    ),
                    logger,
                    task_name="ingest_jobs"
                )
            )

            # #####################
            # # 4. Email agent 
            # #####################            
            # email_agent = EmailAgent(
            #     AgentInfo(
            #         name="EmailAgent",
            #         description="An agent that generates email content based on job search results."
            #     )
            # )
            # await email_agent.run(
            #     context=matched_jobs,
            #     user_email="smartqingtong@gmail.com"
            # )
            

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
        
