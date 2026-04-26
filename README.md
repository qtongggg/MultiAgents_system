# RAGProductionAPP

## Project Introduction

RAGProductionAPP is an AI-powered multi-agent job assistant system designed to automate job searching, candidate profile retrieval, resume understanding, and email delivery using an orchestration-based architecture.

The system combines Retrieval-Augmented Generation (RAG), MCP tools, and LLM-driven planning to create a workflow where user requests are automatically analyzed, planned, and executed by specialized agents.

Instead of relying on a single intent router, this project uses a Planner Agent that dynamically decides which agents should run and in what sequence.

---

## Core Objective

The goal of this project is to simulate a production-level intelligent assistant that can handle requests such as:

* Find AI Engineer jobs in Malaysia
* Search 3 Software Engineer jobs and email them to me
* Retrieve Mah Qing Tong's personal information
* Send candidate profile details to a recruiter
* Match candidate resumes against job requirements

This creates a more realistic enterprise-grade AI workflow compared to a single chatbot response.

---

## System Architecture

```text
User Query
   ↓
Planner Agent (LLM Decision Layer)
   ↓
Execution Plan (JSON Steps)
   ↓
Orchestrator Agent
   ↓
Specialized Agents
   ├── Resume Agent
   ├── Job Search Agent
   ├── QA Agent
   └── Email Agent
   ↓
MCP Tools + Vector DB + External APIs
   ↓
Final Standardized Response
```

---

## Main Components

## 1. Orchestrator Agent

The Orchestrator Agent is responsible for:

* calling the Planner Agent
* executing agents sequentially
* injecting runtime context when needed
* handling background tasks (such as email sending)
* normalizing final output into a standard response format

It acts as the central controller of the entire system.

---

## 2. Planner Agent

The Planner Agent replaces traditional intent detection.

Instead of classifying only one intent, it generates a structured execution plan like this:

```json
{
  "steps": [
    {
      "agent": "job_search_agent",
      "params": {
        "user_input": "AI Engineer jobs",
        "location": "Malaysia",
        "per_page": 3,
        "page": 1
      }
    },
    {
      "agent": "email_agent",
      "params": {
        "user_email": "example@gmail.com"
      }
    }
  ]
}
```

This makes the system scalable and flexible for multi-step workflows.

---

## 3. Resume Agent

Responsible for:

* retrieving candidate personal information
* resume search
* candidate profile summarization
* answering resume-related queries

This agent uses resume retrieval tools and summarization logic.

---

## 4. Job Search Agent

Responsible for:

* searching jobs from external job platforms
* matching jobs against candidate profiles
* scoring job fit
* identifying missing skills
* background ingestion into vector database

This creates a job recommendation pipeline instead of simple job listing retrieval.

---

## 5. Email Agent

Responsible for:

* generating professional email content
* sending emails automatically
* forwarding job opportunities to users

This agent runs as a background task and does not overwrite the main frontend response.

---

## MCP Tools Used

The system uses MCP tools for structured tool execution:

* `search_jobs_tool`
* `match_jobs_tool`
* `ingest_jobs_tool`
* `summarize_jobs_tool`
* `search_resume`
* `summarize_tool`
* `planner_tool`
* `analyze_query_with_llm`

These tools provide modular and production-friendly architecture.

---

## Response Standardization

All agents return a unified schema using `AgentResult`:

```python
class AgentResult(BaseModel):
    status: str
    data: dict
    error: Optional[str] = None
    meta: dict = {}
```

This ensures:

* consistent frontend integration
* stable API contracts
* easier debugging
* better observability

---

## Key Engineering Improvements

### From Intent Router → Planner Architecture

Old approach:

```text
detect_intent() → run one agent
```

New approach:

```text
planner_agent → generate multi-step execution plan
```

This significantly improves:

* scalability
* flexibility
* production readiness
* enterprise workflow simulation

---

## Technologies Used

* Python
* FastAPI
* AsyncIO
* Pydantic
* LangChain
* OpenAI API
* MCP Architecture
* Qdrant Vector Database
* Docker
* Git + GitHub

---

## Example Use Cases

### Example 1

```text
Search 2 AI Engineer jobs and send them to me
```

System flow:

```text
Planner → Job Search Agent → Email Agent (background)
```

---

### Example 2

```text
Send Mah Qing Tong personal information to recruiter@gmail.com
```

System flow:

```text
Planner → Resume Agent → Email Agent
```

---

## Future Improvements

Potential next upgrades:

* A2A architecture (Agent-to-Agent communication)
* autonomous retry handling
* approval workflow before sending emails
* recruiter-facing dashboard
* scheduling and follow-up automation
* interview preparation recommendations
* cover letter generation

---

## Conclusion

This project demonstrates how to move from a basic RAG chatbot into a production-style AI orchestration system using multi-agent workflows.

It focuses on:

* real business workflow automation
* structured execution planning
* reliable agent communication
* clean software architecture
* scalable system design

This makes it highly suitable for portfolio presentation, technical interviews, and production-oriented AI engineering showcases.
