import sys
from pathlib import Path
import logging
from Agents.Base_agent import BaseAgent, AgentInfo
from custom.custom_types import AgentResult
from dotenv import load_dotenv
from email.mime.text import MIMEText
import base64

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
# HTML Body
# --------------------------------------------------
html_body = """
<p>Dear User,</p>

<p>I hope this message finds you well. I wanted to share a job opportunity that may be of interest to you:</p>

<p><b>Job Title:</b> Senior Data Science Manager<br>
<b>Company:</b> Hays<br>
<b>Location:</b> Malaysia<br>
<b>Fit Score:</b> 0.1</p>

<p><b>Summary:</b><br>
The Senior Data Science Manager at Hays is responsible for gathering requirements, designing methodologies for problem-solving, conducting statistical analyses, and developing credit risk models.
</p>

<p><b>Why it matches / does not match:</b><br>
The candidate has limited experience and does not meet the 5~7 years requirement.
</p>

<p><b>Key Skills:</b></p>
<ul>
<li><b>Matching:</b> Python, Tableau</li>
<li><b>Missing:</b> credit modeling, Cloud, data modeling</li>
</ul>

<p><b>Job Link:</b><br>
<a href="https://my.expertini.com/job/senior-data-science-manager-malaysia-hays-ba0b5f7a95a1/">
View Job Posting
</a>
</p>

<p>Best regards,<br>Your Assistant</p>
"""
# --------------------------------------------------
# System prompt
# --------------------------------------------------
SYSTEM_PROMPT = """
You are a professional Gmail assistant.

Your job is to generate email content based on user instructions and provided context.

IMPORTANT:
- You MUST return output in STRICT JSON format.
- Do NOT return plain text.
- Do NOT include explanations.

Output format:
{
  "subject": "string",
  "body_html": "string"
}

Rules:
1. The email body MUST be valid HTML.
2. Use proper HTML tags:
   - <p> for paragraphs
   - <b> for labels
   - <ul><li> for lists
   - <a href=""> for links
3. Do NOT use Markdown (**, -, etc).
4. Keep formatting clean and professional.

5. If job data is provided:
   - Include title, company, location, fit score
   - Include summary
   - Include matching vs missing skills
   - Include job link

6. If no jobs are provided:
   - Return a polite email saying no jobs were found.

7. If more than 1 jobs are provided, space them out clearly in the email.

Return ONLY JSON.
"""

user_email = "smartqingtong@gmail.com"

# --------------------------------------------------
# Create Message
# --------------------------------------------------
def create_html_message(to, subject, html_body):
    message = MIMEText(html_body, "html")  # 👈 THIS enables rendering
    message["to"] = to
    message["subject"] = subject

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw_message}

def send_email(service, to, subject, html_body):
    message = create_html_message(to, subject, html_body)

    sent = service.users().messages().send(
        userId="me",
        body=message
    ).execute()

    return sent
# --------------------------------------------------
# Build agent
# --------------------------------------------------
def build_email_agent(context: list[dict]):
    tools = get_gmail_tools()

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT + f"\n\nAvailable context:\n{context}"
    )
    return agent


# --------------------------------------------------
# Public runner
# --------------------------------------------------
async def generate_email_content(agent, context):
    result = await agent.ainvoke({
        "messages": [
            {
                "role": "user",
                "content": "Generate an email for these job results."
            }
        ]
    })

    # Extract raw text
    raw_output = result["messages"][-1].content

    import json
    parsed = json.loads(raw_output)

    return parsed["subject"], parsed["body_html"]



class EmailAgent(BaseAgent):
    def __init__(self, info: AgentInfo):
        super().__init__(info)

    async def run(self, context, user_email):
        try:
            agent = build_email_agent(context)
            
            subject, body_html = await generate_email_content(
                agent, 
                context
                )  
            
            service = build_resource_service(
                credentials=get_gmail_credentials(
                    token_file=str(PROJECT_ROOT / "token.json"),
                    scopes=["https://mail.google.com/"],
                    client_secrets_file=str(PROJECT_ROOT / "credentials.json"),
                )
            )

            send_email(
                service=service,
                to=user_email,
                subject=subject,
                html_body=body_html
            )

            return AgentResult(
                status="success",
                data={
                    "email_sent_to": user_email,
                    "subject": subject
                }
            )

        except Exception as e:
            logger.error(f"EmailAgent failed: {e}", exc_info=True)

            return AgentResult(
                status="error",
                data={},
                error=str(e)
            )