from custom.custom_types import JobSearchRequest   
from Agents.new_job_search_agent import JobSearchAgent, AgentInfo
from Agents.new_resume_agent import ResumeAgent

from Agents.planner_agent import PlannerAgent
from Agents.Agent_Registry import AgentRegistry
import asyncio



import asyncio
from MCP_agent.agent_setup import shutdown_mcp
registry = AgentRegistry()
async def main():

    from Agents.new_job_search_agent import JobSearchAgent as JobSearchAgentClass


    job_search_agent  = JobSearchAgentClass(AgentInfo(
    name="job_search_agent",
    description="An agent that searches for jobs based on a keyword and location. It uses the search_jobs_tool to fetch job data, and then formats that data into a structured email content. The email content includes job title, company, location, fit score, summary, matching vs missing skills, and job link. If no jobs are found, it returns a polite message indicating that."
    ))

    registry.register('job_search_agent', job_search_agent)

    from Agents.email_agent import EmailAgent as EmailAgentClass

    email_agent = EmailAgentClass(AgentInfo(
        name="email_agent",
        description="An agent that make use of the google email api to sent, draft or check the email for the user "
    ))

    registry.register('email_agent', email_agent)

    from Agents.new_resume_agent import ResumeAgent as ResumeAgentClass

    resume_agent = ResumeAgentClass(AgentInfo(
        name = "resume_agent",
        description= "An Agent that we summarize the information about this candidate and ensure that we can retrive the accurate information for the user."
    ))

    registry.register('resume_agent', resume_agent)

    agent = PlannerAgent(
        AgentInfo(
            name="planner_agent",
            description="plan the agent that we need to use by using llm decision"
        ),
        registry

    )

    result = await agent.run(
        user_input = "Send Mah Qing Tong personal information and email it to smartqingtong@gmail.com"  
    )

    print(result)

    await shutdown_mcp()   # 👈 IMPORTANT FIX

if __name__ == "__main__":
    asyncio.run(main())