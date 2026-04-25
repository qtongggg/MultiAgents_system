from custom.custom_types import JobSearchRequest   
from Agents.new_job_search_agent import JobSearchAgent, AgentInfo
from Agents.new_resume_agent import ResumeAgent

import asyncio



import asyncio
from MCP_agent.agent_setup import shutdown_mcp

async def main():


    agent = ResumeAgent(
        AgentInfo(
            name="resume_agent",
            description="search the vector database and summarize the result to the user."
        )
    )

    result = await agent.run(
        user_input = "show me about the details from the resume mah qing tong",
        top_k = 5
    )

    print(result)

    await shutdown_mcp()   # 👈 IMPORTANT FIX

if __name__ == "__main__":
    asyncio.run(main())