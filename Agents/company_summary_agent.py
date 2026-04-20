from tools.data_loader import search_jobs_from_qd
from utils.filters import filter_jobs_by_company
from utils.formatters import format_jobs_context

from langchain_core.prompts import ChatPromptTemplate
from LLM.llm import llm
import logging

logger = logging.getLogger(__name__)


async def job_details_agent(question: str, top_k: int = 5, company_name: str | None = None, location: str | None = None):
    result = search_jobs_from_qd(question, top_k)

    payloads = result.get("payloads", [])

    for job in payloads:
        logger.info(job)
        logger.info("-" * 50)

    if company_name:
        payloads = filter_jobs_by_company(payloads, company_name)

    if not payloads:
        return {
            "result": {
                "answer": f"No jobs found for {company_name}.",
                "sources": [],
                "jobs": []
            }
        }

    context = format_jobs_context(payloads)

    prompt = ChatPromptTemplate.from_template("""
        You are a Senior HR Analyst.

        Summarize the jobs for the company.

        Focus on:
        - types of roles
        - common skills
        - overall hiring pattern

        Context:
        {context}

        Question:
        {question}

        Answer:
    """)

    chain = prompt | llm

    response = await chain.ainvoke({
        "context": context,
        "question": question
    })

    logger.info(f"Generated company summary for {response.content.strip()}")

    return {
        "result": {
            "answer": response.content.strip(),
            "sources": payloads,
            "jobs": payloads
        }
    }