from MCP_agent.agent_setup import get_mcp_tools
from MCP_tools.mcp_jobs_tools import search_jobs_tool, match_jobs_tool, summarize_jobs_tool

def run_job_search():
    print("🚀 Running scheduled job search...")

    jobs = search_jobs_tool("AI Engineer", "Malaysia")
    matched = match_jobs_tool("mah_qing_tong_resume.pdf", jobs["jobs"])
    summarized = summarize_jobs_tool(matched["jobs"])

    print("Done:", summarized)

if __name__ == "__main__":
    run_job_search()