

# # # main.py
# # import logging
# # from contextlib import asynccontextmanager
# # from fastapi import FastAPI
# # import inngest.fast_api
# # from dotenv import load_dotenv

# # from tools.pdf_ingester import rag_ingest_pdf
# # from Agents.query_agent import rag_query_pdf_agent
# # from Agents.resume_ranking_agent import rag_rank_resume_agent
# # from Agents.job_search_agent import rag_job_search_agent
# # from Agents.orchestrator_agent import rag_orchestrator_agent
# # from client import inngest_client
# # from MCP_agent.agent_setup import startup_mcp, shutdown_mcp

# # load_dotenv()
# # logging.basicConfig(level=logging.INFO)

# # @asynccontextmanager
# # async def lifespan(app: FastAPI):
# #     await startup_mcp()
# #     yield
# #     await shutdown_mcp()

# # app = FastAPI(lifespan=lifespan)

# # inngest.fast_api.serve(
# #     app,
# #     inngest_client,
# #     [
# #         rag_ingest_pdf,
# #         rag_query_pdf_agent,
# #         rag_orchestrator_agent,
# #         rag_job_search_agent,
# #         rag_rank_resume_agent,
# #     ]
# # )

# # main.py
# import logging
# from contextlib import asynccontextmanager
# from fastapi import FastAPI
# import inngest.fast_api
# from dotenv import load_dotenv

# from tools.pdf_ingester import rag_ingest_pdf
# from Agents.query_agent import rag_query_pdf_agent
# from Agents.job_search_agent import rag_job_search_agent
# from Agents.orchestrator_agent import rag_orchestrator_agent
# from client import inngest_client
# from MCP_agent.agent_setup import startup_mcp, shutdown_mcp
# from routes.rag import router as rag_router   # add this

# load_dotenv()
# logging.basicConfig(level=logging.INFO)

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     await startup_mcp()
#     yield
#     await shutdown_mcp()

# app = FastAPI(lifespan=lifespan)

# app.include_router(rag_router)   # add this

# inngest.fast_api.serve(
#     app,
#     inngest_client,
#     [
#         rag_ingest_pdf,
#         rag_query_pdf_agent,
#         rag_orchestrator_agent,
#         rag_job_search_agent,
#     ]
# )

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import os

app = FastAPI()
load_dotenv()
# Load API key from environment (IMPORTANT for production)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# -------------------------
# Request schema (validation)
# -------------------------
class ChatRequest(BaseModel):
    prompt: str


# -------------------------
# API endpoint
# -------------------------
@app.post("/api/v1/chat")
async def chat(request: ChatRequest):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",   # or GPT-5 if available in your setup
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": request.prompt}
            ],
            temperature=0.7
        )

        return {
            "response": response.choices[0].message.content
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/")
def root():
    return {"message": "API is running"}