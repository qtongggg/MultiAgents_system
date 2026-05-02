import os
import json
from typing import List, Dict, Any

from dotenv import load_dotenv
from docling.document_converter import DocumentConverter
from langchain_openai import ChatOpenAI

# =========================
# INIT
# =========================

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)

# =========================
# PROMPT (FIXED STRUCTURE)
# =========================

RESUME_SYSTEM_PROMPT = """
You are an expert resume parsing system.

RULES:
- Extract ALL information accurately
- Do NOT hallucinate
- Preserve structure strictly
- Always attach dates if inferable
- Group related items properly (DO NOT SPLIT LISTS)

IMPORTANT GROUPING RULES:
1. Leadership programs MUST be grouped into ONE object with multiple items
2. Experience MUST include dates when available (even if only year)
3. Do NOT split competitions, awards, or leadership into multiple chunks

Return ONLY valid JSON.

OUTPUT FORMAT:

{
  "personal_details": {
    "name": "",
    "phone": "",
    "email": "",
    "location": "",
    "linkedin": "",
    "github": ""
  },
  "career_objective": [
    {"information": ""}
  ],
  "education": [
    {
      "school": "",
      "degree": "",
      "date": "",
      "information": ""
    }
  ],
  "experience": [
    {
      "company": "",
      "role": "",
      "date": "",
      "information": ""
    }
  ],
  "skills": [
    {"information": ""}
  ],
  "projects": [
    {"information": ""}
  ],
  "certifications": [
    {"information": ""}
  ],
  "awards": [
    {"information": ""}
  ],
  "extracurricular_activity": [
    {"information": ""}
  ],
  "leadership_program": {
    "items": [
      {
        "name": "",
        "date": "",
        "information": ""
      }
    ]
  }
}
"""

# =========================
# PDF EXTRACTION
# =========================

def extract_resume_text(path: str) -> str:
    converter = DocumentConverter()
    result = converter.convert(source=path)
    doc = result.document

    return doc.export_to_markdown() if hasattr(doc, "export_to_markdown") else str(doc)

# =========================
# HEADER DETECTION
# =========================

POSSIBLE_HEADERS = [
    "personal",
    "education",
    "experience",
    "skills",
    "projects",
    "certifications",
    "awards",
    "career objective",
    "summary",
    "leadership",
    "competition"
]

def extract_known_headers(text: str) -> List[str]:
    text = text.lower()
    return [h for h in POSSIBLE_HEADERS if h in text]

# =========================
# PROMPT BUILDER
# =========================

def build_prompt(resume_text: str, headers: List[str]) -> str:
    return f"""
You are parsing a resume for a job-matching system.

Detected sections:
{headers}

RULES:
- Infer missing structure if needed
- Attach dates whenever possible
- Do NOT split grouped sections (especially leadership & competitions)
- Preserve ALL information

Resume:
{resume_text}
"""

# =========================
# JSON PARSER
# =========================

def safe_json_parse(text: str):
    text = text.strip()

    if text.startswith("```"):
        text = text.split("```")[1]
        text = text.replace("json", "").strip()

    return json.loads(text)

# =========================
# LLM PARSER
# =========================

def parse_resume_with_llm(resume_text: str, headers: List[str]):
    prompt = build_prompt(resume_text, headers)

    response = llm.invoke([
        ("system", RESUME_SYSTEM_PROMPT),
        ("user", prompt)
    ])

    return safe_json_parse(response.content)

# =========================
# MAIN PIPELINE
# =========================

def process_resume(path: str):
    text = extract_resume_text(path)
    headers = extract_known_headers(text)
    return parse_resume_with_llm(text, headers)

# =========================
# CHUNK BUILDER (FIXED)
# =========================

def build_resume_chunks(structured: Dict[str, Any]) -> List[str]:
    chunks = []

    # =========================
    # PERSONAL DETAILS (ONE CHUNK ONLY)
    # =========================
    pd = structured.get("personal_details", {})

    chunks.append(
        "Personal Details:\n"
        f"Name: {pd.get('name','')}\n"
        f"Phone: {pd.get('phone','')}\n"
        f"Email: {pd.get('email','')}\n"
        f"Location: {pd.get('location','')}\n"
        f"LinkedIn: {pd.get('linkedin','')}\n"
        f"GitHub: {pd.get('github','')}"
    )

    # =========================
    # CAREER OBJECTIVE
    # =========================
    for obj in structured.get("career_objective", []):
        chunks.append("Career Objective:\n" + obj.get("information", ""))

    # =========================
    # EDUCATION
    # =========================
    for edu in structured.get("education", []):
        chunks.append(
            "Education:\n"
            f"{edu.get('school','')}\n"
            f"{edu.get('degree','')}\n"
            f"{edu.get('date','')}\n"
            f"{edu.get('information','')}"
        )

    # =========================
    # EXPERIENCE
    # =========================
    for exp in structured.get("experience", []):
        chunks.append(
            "Experience:\n"
            f"{exp.get('company','')}\n"
            f"{exp.get('role','')}\n"
            f"{exp.get('date','')}\n"
            f"{exp.get('information','')}"
        )

    # =========================
    # PROJECTS
    # =========================
    for proj in structured.get("projects", []):
        chunks.append("Project:\n" + proj.get("information", ""))

    # =========================
    # SKILLS
    # =========================
    skills = "\n".join(
        s.get("information", "")
        for s in structured.get("skills", [])
    )

    if skills:
        chunks.append("Skills:\n" + skills)

    # =========================
    # LEADERSHIP (FIXED GROUPING)
    # =========================
    lp = structured.get("leadership_program", {}).get("items", [])

    if lp:
        text = "Leadership & Competitions:\n"
        for item in lp:
            text += f"- {item.get('name','')} ({item.get('date','')})\n"
        chunks.append(text.strip())

    # =========================
    # OTHER SECTIONS
    # =========================
    for section in [
        "extracurricular_activity",
        "certifications",
        "awards"
    ]:
        for item in structured.get(section, []):
            chunks.append(f"{section.title()}:\n{item.get('information','')}")

    return chunks

# =========================
# RUN
# =========================

if __name__ == "__main__":
    path = r"C:\Users\User\OneDrive\Documents\Wish you have a nice job\MAH QING TONG Resume.pdf"

    structured = process_resume(path)
    chunks = build_resume_chunks(structured)

    for i, c in enumerate(chunks):
        print(f"\n--- CHUNK {i} ---\n")
        print(c)