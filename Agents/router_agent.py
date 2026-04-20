import json
from langchain_core.prompts import ChatPromptTemplate
from LLM.llm import llm


async def detect_intent_with_llm(question: str) -> dict:
    prompt = ChatPromptTemplate.from_template("""
    You are an intent router for an HR assistant.

    Your task:
    1. Classify the user's question into exactly ONE intent
    2. Extract the company name if clearly mentioned
    3. Extract the location if clearly mentioned
    4. Extract the candidate name if clearly mentioned and in lowercase with underscores instead of spaces

    Allowed intents:
    - resume
    - job_details
    - job_search
    - qa

    Intent meaning:
    - resume: questions about candidate profile, resume, skills, education, experience, qualifications, fit
    - job_details: questions asking to summarize a company or summarize jobs from a specific company
    - job_search: questions asking to list, find, show, or retrieve jobs
    - qa: all other general questions

    Rules:
    - Return ONLY valid JSON
    - Do not explain
    - If no company is mentioned, use null
    - If no location is mentioned, use null
    - If no candidate name is mentioned, use null
    - If the question is about jobs at a company, prefer "job_search"
    - If the question is about summarizing a company or its roles, prefer "job_details"
    - If the question is about a candidate or resume, prefer "resume"

    Return this exact JSON format:
    {{
    "intent": "resume|job_details|job_search|qa",
    "company_name": "string or null",
    "location": "string or null",
    "candidate_name": "string or null"
    "number": "int or null"
    }}

    Examples:

    User: Show me 5 jobs from Grab in Malaysia
    Output:
    {{"intent": "job_search", "company_name": "Grab", "location": "Malaysia", "candidate_name": null, "number": 5}}

    User: Summarize the company Grab
    Output:
    {{"intent": "job_details", "company_name": "Grab", "location": null, "candidate_name": null, "number": null}}

    User: Give me the resume of Hoo Vi Ying
    Output:
    {{"intent": "resume", "company_name": null, "location": null, "candidate_name": "hoo_vi_ying", "number": null}}

    User: Summarize Mah Qing Tong's profile
    Output:
    {{"intent": "resume", "company_name": null, "location": null, "candidate_name": "mah_qing_tong", "number": null}}

    User: What skills does this candidate have?
    Output:
    {{"intent": "resume", "company_name": null, "location": null, "candidate_name": null, "number": null}}

    User: What is RAG?
    Output:
    {{"intent": "qa", "company_name": null, "location": null, "candidate_name": null, "number": null}}

    User question:
    {question}
    """)

    chain = prompt | llm
    response = await chain.ainvoke({"question": question})

    content = response.content.strip()

    try:
        parsed = json.loads(content)

        intent = parsed.get("intent", "qa")
        company_name = parsed.get("company_name", None)
        location = parsed.get("location", None)
        candidate_name = parsed.get("candidate_name", None)
        number = parsed.get("number", None)

        allowed_intents = {"resume", "job_details", "job_search", "qa"}
        if intent not in allowed_intents:
            intent = "qa"

        return {
            "intent": intent,
            "company_name": company_name,
            "location": location,
            "candidate_name": candidate_name,
            "number": number
        }

    except json.JSONDecodeError:
        return {
            "intent": "qa",
            "company_name": None,
            "location": None,
            "candidate_name": None,
            "number": None
        }




async def rewrite_query_with_llm(question: str) -> dict:
    prompt = ChatPromptTemplate.from_template("""
You are a search query optimizer for vector database searches.

Your task is to rewrite the user's query into a more effective retrieval query.

Goals:
1. Preserve the original meaning
2. Remove filler words and conversational phrasing
3. Add useful related search terms when they improve retrieval
4. Make the query concise, keyword-rich, and searchable
5. Keep focus on the main concepts

Rules:
- Return ONLY valid JSON
- Do not explain
- Do not add markdown
- Do not invent facts not implied by the query
- Output should be optimized for search, not conversation

Return this exact JSON format:
{{
  "rewritten_query": "string"
}}

Examples:

User query: give me the resume of hoo vi ying
Output:
{{"rewritten_query": "hoo vi ying resume candidate profile education skills experience projects contact information"}}
                                              
user query: what is the projects that mah qing tong has done
Output:
{{"rewritten_query": "mah qing tong projects experience candidate profile resume"}}

User query: what skills does this candidate have
Output:
{{"rewritten_query": "candidate resume skills technical skills qualifications tools experience"}}

User query: summarize this applicant background
Output:
{{"rewritten_query": "applicant profile summary background education skills experience qualifications"}}

User query: show me jobs from grab in malaysia
Output:
{{"rewritten_query": "grab jobs openings roles positions malaysia hiring"}}

User query: what is rag
Output:
{{"rewritten_query": "RAG retrieval augmented generation explanation"}}

User query:
{question}
""")

    chain = prompt | llm
    response = await chain.ainvoke({"question": question})

    content = response.content.strip()

    try:
        parsed = json.loads(content)
        rewritten_query = parsed.get("rewritten_query", question)

        if not rewritten_query or not isinstance(rewritten_query, str):
            rewritten_query = question

        return {
            "rewritten_query": rewritten_query.strip()
        }

    except json.JSONDecodeError:
        return {
            "rewritten_query": question
        }