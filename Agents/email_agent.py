import sys
from pathlib import Path
import logging
from dotenv import load_dotenv

# --------------------------------------------------
# Project path setup
# --------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

load_dotenv()
logger = logging.getLogger(__name__)

# --------------------------------------------------
# Imports
# --------------------------------------------------
from LLM.llm import llm
from langchain_community.agent_toolkits import GmailToolkit
from langchain_community.tools.gmail.utils import (
    build_resource_service,
    get_gmail_credentials,
)
from langchain.agents import create_agent

# --------------------------------------------------
# Gmail setup
# --------------------------------------------------
def get_gmail_tools():
    credentials = get_gmail_credentials(
        token_file=str(PROJECT_ROOT / "token.json"),
        scopes=["https://mail.google.com/"],
        client_secrets_file=str(PROJECT_ROOT / "credentials.json"),
    )

    api_resource = build_resource_service(credentials=credentials)
    toolkit = GmailToolkit(api_resource=api_resource)
    return toolkit.get_tools()


# --------------------------------------------------
# System prompt
# --------------------------------------------------
SYSTEM_PROMPT = """
You are a professional Gmail assistant.

Your job is to help the user draft, search, read, reply to, and send emails using the available Gmail tools.

Available tools may include:
- create_gmail_draft
- send_gmail_message
- search_gmail
- get_gmail_message
- get_gmail_thread

Rules:
1. If the user says "draft", "write", "compose", or "prepare", use create_gmail_draft.
2. If the user says "send", use send_gmail_message.
3. Never create a draft when the user explicitly asked to send.
4. If the user wants to reply to an existing email:
   - search for the relevant email first
   - fetch the full message or thread if needed
   - then draft or send the reply
5. If the user asks to summarize, inspect, or find an email, use search_gmail first and then get_gmail_message or get_gmail_thread if needed.
6. Do not invent email addresses, thread details, message IDs, or message content.
7. Keep emails clear, professional, and natural unless the user asks for another tone.
8. When finished, return a concise final response describing what action was completed.
"""


# --------------------------------------------------
# Build agent
# --------------------------------------------------
def build_email_agent():
    tools = get_gmail_tools()

    logger.info("Loaded Gmail tools:")
    for tool in tools:
        logger.info("%s - %s", tool.name, tool.description)

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )
    return agent


# --------------------------------------------------
# Public runner
# --------------------------------------------------
async def run_email_agent(instruction: str):
    try:
        agent = build_email_agent()

        result = await agent.ainvoke(
            {
                "messages": [
                    {"role": "user", "content": instruction}
                ]
            }
        )

        return {
            "ok": True,
            "tool": "run_email_agent",
            "instruction": instruction,
            "result": result,
            "error": None,
        }

    except Exception as exc:
        logger.exception("Email agent failed")
        return {
            "ok": False,
            "tool": "run_email_agent",
            "instruction": instruction,
            "result": None,
            "error": str(exc),
        }


