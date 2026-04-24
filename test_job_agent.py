from custom.custom_types import JobSearchRequest   
from Agents.new_job_search_agent import JobSearchAgent, AgentInfo

import asyncio



import asyncio
from MCP_agent.agent_setup import shutdown_mcp

async def main():


    agent = JobSearchAgent(
        AgentInfo(
            name="job_search_agent",
            description="An agent that searches for jobs based on a keyword and location. It uses the search_jobs_tool to fetch job data, and then formats that data into a structured email content. The email content includes job title, company, location, fit score, summary, matching vs missing skills, and job link. If no jobs are found, it returns a polite message indicating that."
        )
    )

    result = await agent.run({
        "keyword": "data scientist",
        "location": "Malaysia",
        "per_page": 1,
        "page": 1
    })
    print(result)

    await shutdown_mcp()   # 👈 IMPORTANT FIX

if __name__ == "__main__":
    asyncio.run(main())