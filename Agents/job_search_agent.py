import os
import json
import logging
import asyncio
from marshmallow import pprint
from openai import AsyncOpenAI
from dotenv import load_dotenv
from MCP_agent.agent_setup import get_mcp_tools
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue




logger = logging.getLogger(__name__)


load_dotenv()

qdrant = QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# MAX_ITERATIONS = 8


# # ---------------------------------------------------------------------------
# # Resume helper
# # ---------------------------------------------------------------------------

def get_resume_source_id() -> str | None:
    env_id = os.getenv("RESUME_SOURCE_ID")
    if env_id:
        return env_id

    filters = [
        Filter(must=[FieldCondition(key="source_type", match=MatchValue(value="resume"))]),
        None,
    ]

    for f in filters:
        try:
            kwargs = dict(
                collection_name="pdf_chunks_hybrid",
                limit=1,
                with_payload=True,
                with_vectors=False,
            )
            if f:
                kwargs["scroll_filter"] = f

            results, _ = qdrant.scroll(**kwargs)
            if results:
                payload = results[0].payload or {}
                return payload.get("source_id") or payload.get("source")
        except Exception:
            logger.exception("Failed while looking up resume_source_id")

    return None


# # ---------------------------------------------------------------------------
# # MCP standardized result helpers
# # ---------------------------------------------------------------------------

def normalize_tool_result(result, tool_name: str) -> dict:
    """
    Normalize MCP / LangChain tool output into:
    {
        "ok": bool,
        "tool": str,
        "jobs": list,
        "error": str | None,
        "meta": dict
    }
    """

    # Case 0: raw JSON string
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except Exception:
            return {
                "ok": False,
                "tool": tool_name,
                "jobs": [],
                "error": "Failed to parse string tool result as JSON",
                "meta": {"raw_text": result[:500]},
            }

    # Case 1: already standardized dict
    if isinstance(result, dict):
        jobs = result.get("jobs", [])
        if not isinstance(jobs, list):
            jobs = []

        meta = result.get("meta", {})
        if not isinstance(meta, dict):
            meta = {}

        return {
            "ok": bool(result.get("ok", False)),
            "tool": result.get("tool", tool_name),
            "jobs": jobs,
            "error": result.get("error"),
            "meta": meta,
        }

    # Case 2: MCP/LangChain text block list
    if isinstance(result, list) and result:
        first = result[0]

        if isinstance(first, dict) and first.get("type") == "text":
            text = first.get("text", "")
            if isinstance(text, str):
                try:
                    parsed = json.loads(text)

                    if isinstance(parsed, dict):
                        jobs = parsed.get("jobs", [])
                        if not isinstance(jobs, list):
                            jobs = []

                        meta = parsed.get("meta", {})
                        if not isinstance(meta, dict):
                            meta = {}

                        return {
                            "ok": bool(parsed.get("ok", False)),
                            "tool": parsed.get("tool", tool_name),
                            "jobs": jobs,
                            "error": parsed.get("error"),
                            "meta": meta,
                        }
                except Exception:
                    return {
                        "ok": False,
                        "tool": tool_name,
                        "jobs": [],
                        "error": "Failed to parse JSON from text tool result",
                        "meta": {"raw_text": text[:500]},
                    }

        # Case 3: legacy bare job list
        if isinstance(first, dict) and "title" in first:
            return {
                "ok": True,
                "tool": tool_name,
                "jobs": result,
                "error": None,
                "meta": {"legacy_format": True},
            }

    # Case 4: unsupported format
    return {
        "ok": False,
        "tool": tool_name,
        "jobs": [],
        "error": f"Invalid tool output type: {type(result).__name__}",
        "meta": {},
    }


# def serialize_result(result: dict, tool_name: str = "unknown") -> str:
#     normalized = normalize_tool_result(result, tool_name)
#     return json.dumps(normalized, ensure_ascii=False)



# # ---------------------------------------------------------------------------
# # Tool registry
# # ---------------------------------------------------------------------------

# def build_tool_registry(tools: dict, resume_source_id: str | None) -> tuple[list, dict]:
#     """
#     Returns:
#       openai_tools — tool schemas passed to OpenAI
#       tool_map     — name → async callable that accepts OpenAI's input dict
#     """
#     openai_tools = [
#         {
#             "type": "function",
#             "function": {
#                 "name": "search_jobs",
#                 "description": (
#                     "Search for live job listings by keyword and location. "
#                     "Always call this first."
#                 ),
#                 "parameters": {
#                     "type": "object",
#                     "properties": {
#                         "keyword": {
#                             "type": "string",
#                             "description": "Job title or skill, e.g. 'Python Developer'"
#                         },
#                         "location": {
#                             "type": "string",
#                             "description": "City or country, e.g. 'Malaysia'"
#                         },
#                         "per_page": {
#                             "type": "integer",
#                             "description": "Number of results (default 5)"
#                         },
#                     },
#                     "required": ["keyword", "location"],
#                 },
#             },
#         },
#         {
#             "type": "function",
#             "function": {
#                 "name": "match_jobs",
#                 "description": (
#                     "Score each job against the candidate's resume. "
#                     + (
#                         "Resume IS available — call after search_jobs. "
#                         "You MUST pass the full jobs array returned by search_jobs."
#                         if resume_source_id
#                         else "Resume NOT available — do NOT call this tool."
#                     )
#                 ),
#                 "parameters": {
#                     "type": "object",
#                     "properties": {
#                         "jobs": {
#                             "type": "array",
#                             "items": {"type": "object"},
#                             "description": "REQUIRED. Pass the full jobs array from search_jobs. Do not omit this.",
#                         },
#                     },
#                     "required": ["jobs"],
#                 },
#             },
#         },
#         {
#             "type": "function",
#             "function": {
#                 "name": "ingest_jobs",
#                 "description": (
#                     "Persist jobs into the vector database. Always call before summarize_jobs. "
#                     "You MUST pass the full jobs array from match_jobs or search_jobs."
#                 ),
#                 "parameters": {
#                     "type": "object",
#                     "properties": {
#                         "jobs": {
#                             "type": "array",
#                             "items": {"type": "object"},
#                             "description": "REQUIRED. Pass the full jobs array from match_jobs or search_jobs. Do not omit this.",
#                         },
#                     },
#                     "required": ["jobs"],
#                 },
#             },
#         },
#         {
#             "type": "function",
#             "function": {
#                 "name": "summarize_jobs",
#                 "description": (
#                     "Generate clean UI-ready summaries. Always call last, after ingest_jobs. "
#                     "Preserves fit_score and resume match fields. "
#                     "You MUST pass the full jobs array returned by ingest_jobs."
#                 ),
#                 "parameters": {
#                     "type": "object",
#                     "properties": {
#                         "jobs": {
#                             "type": "array",
#                             "items": {"type": "object"},
#                             "description": "REQUIRED. Pass the full jobs array from ingest_jobs. Do not omit this.",
#                         },
#                     },
#                     "required": ["jobs"],
#                 },
#             },
#         },
#     ]

#     def require_jobs(tool_name: str, p: dict) -> dict:
#         jobs = p.get("jobs")
#         if not isinstance(jobs, list) or len(jobs) == 0:
#             raise ValueError(
#                 f"'{tool_name}' requires a non-empty 'jobs' list but got: {p}. "
#                 "Pass the jobs array from the previous tool result."
#             )
#         return p

#     async def call(tool, payload: dict):
#         return await tool.ainvoke(payload)

#     tool_map: dict = {
#         "search_jobs": lambda p: call(tools["search_jobs_tool"], p),
#         "ingest_jobs": lambda p: call(tools["ingest_jobs_tool"], require_jobs("ingest_jobs", p)),
#         "summarize_jobs": lambda p: call(tools["summarize_jobs_tool"], require_jobs("summarize_jobs", p)),
#     }

#     if tools.get("match_jobs_tool") and resume_source_id:
#         _rid = resume_source_id
#         tool_map["match_jobs"] = lambda p: call(
#             tools["match_jobs_tool"],
#             {
#                 "resume_source_id": _rid,
#                 "jobs": require_jobs("match_jobs", p).get("jobs", []),
#             },
#         )

#     return openai_tools, tool_map


# # ---------------------------------------------------------------------------
# # System prompt
# # ---------------------------------------------------------------------------

# def build_system_prompt(keyword: str, location: str, resume_source_id: str | None) -> str:
#     resume_line = (
#         "Resume IS available — call match_jobs after search_jobs."
#         if resume_source_id
#         else "No resume available — skip match_jobs entirely."
#     )

#     return f"""You are a job search agent. Complete the task by calling tools in the correct order.

# Task: Find "{keyword}" jobs in "{location}".
# Resume: {resume_line}

# Required tool order:
# 1. search_jobs          — always first
# 2. match_jobs           — only if resume is available
# 3. ingest_jobs          — always, pass the best job list you have
# 4. summarize_jobs       — always last

# CRITICAL — passing data between tools:
# - Every tool except search_jobs requires a "jobs" argument.
# - Always use the latest jobs array returned by the previous successful tool.
# - Flow with resume: search_jobs → jobs → match_jobs → jobs → ingest_jobs → jobs → summarize_jobs
# - Flow without resume: search_jobs → jobs → ingest_jobs → jobs → summarize_jobs

# CRITICAL — tool result format:
# - Every tool returns JSON with keys: ok, tool, jobs, error, meta
# - Always read the jobs array from the previous tool result
# - If a tool returns ok=false, inspect the error field and recover if possible

# Retry rule:
# - If search_jobs returns fewer than 3 jobs, retry once with a broader keyword

# Final output rules:
# - Return ONLY one valid JSON object
# - Do NOT wrap the JSON in markdown fences
# - Do NOT output ```json
# - Do NOT output ```
# - Do NOT include any explanation, heading, notes, or extra text
# - Do NOT add text before or after the JSON

# When done, output exactly this structure:
# {{"jobs": [...final summarized job list...], "done": true}}"""


# # ---------------------------------------------------------------------------
# # Agent loop — OpenAI tool-calling format
# # ---------------------------------------------------------------------------

# # ---------------------------------------------------------------------------
# # Agent loop — OpenAI tool-calling format
# # ---------------------------------------------------------------------------

# async def run_agent_loop(
#     keyword: str,
#     location: str,
#     per_page: int,
#     openai_tools: list,
#     tool_map: dict,
#     system_prompt: str,
# ) -> dict:
#     messages = [
#         {"role": "system", "content": system_prompt},
#         {
#             "role": "user",
#             "content": (
#                 f"Find '{keyword}' jobs in '{location}', up to {per_page} results. "
#                 "Complete all required steps and return the final job list."
#             ),
#         },
#     ]

#     iterations = 0
#     last_jobs: list = []

#     while iterations < MAX_ITERATIONS:
#         iterations += 1
#         logger.info("[Agent Loop] Iteration %s/%s", iterations, MAX_ITERATIONS)

#         response = await openai_client.chat.completions.create(
#             model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
#             tools=openai_tools,
#             messages=messages,
#             max_tokens=4096,
#         )

#         choice = response.choices[0]
#         finish_reason = choice.finish_reason
#         message = choice.message

#         logger.info("[Agent Loop] finish_reason=%s", finish_reason)

#         messages.append(message)

#         # -------------------------------------------------------------------
#         # ✅ FINAL OUTPUT (FIXED)
#         # -------------------------------------------------------------------
#         if finish_reason == "stop":
#             logger.info(
#                 "[Agent Loop] STOP reached — returning last_jobs (%s jobs)",
#                 len(last_jobs),
#             )

#             # 🔥 Always trust pipeline state
#             return {
#                 "jobs": last_jobs,
#                 "iterations": iterations,
#             }

#         # -------------------------------------------------------------------
#         # Tool calls
#         # -------------------------------------------------------------------
#         if finish_reason == "tool_calls":
#             tool_calls = message.tool_calls or []

#             for tc in tool_calls:
#                 tool_name = tc.function.name
#                 tool_use_id = tc.id

#                 try:
#                     tool_input = json.loads(tc.function.arguments)
#                 except json.JSONDecodeError:
#                     tool_input = {}

#                 if not isinstance(tool_input, dict):
#                     tool_input = {}

#                 # 🔥 Auto-fill jobs chaining
#                 chained_tools = {"match_jobs", "ingest_jobs", "summarize_jobs"}
#                 if tool_name in chained_tools:
#                     jobs_in_input = tool_input.get("jobs")
#                     if (not isinstance(jobs_in_input, list) or len(jobs_in_input) == 0) and last_jobs:
#                         tool_input["jobs"] = last_jobs
#                         logger.info(
#                             "[Agent Loop] auto-filled jobs for %s from last_jobs (%s jobs)",
#                             tool_name,
#                             len(last_jobs),
#                         )

#                 logger.info("[Agent Loop] calling tool=%s keys=%s", tool_name, list(tool_input.keys()))

#                 callable_fn = tool_map.get(tool_name)

#                 if callable_fn is None:
#                     raw = {
#                         "ok": False,
#                         "tool": tool_name,
#                         "jobs": [],
#                         "error": f"Tool '{tool_name}' not available.",
#                         "meta": {},
#                     }
#                     result_str = json.dumps(raw, ensure_ascii=False)
#                     logger.error("[Agent Loop] tool not available: %s", tool_name)

#                 else:
#                     try:
#                         raw = await callable_fn(tool_input)

#                         logger.info("[Agent Loop] %s raw type=%s", tool_name, type(raw).__name__)
#                         logger.debug("[Agent Loop] %s raw preview=%s", tool_name, str(raw)[:500])

#                         raw = normalize_tool_result(raw, tool_name)
#                         result_str = json.dumps(raw, ensure_ascii=False)

#                         jobs = raw.get("jobs", [])

#                         if jobs:
#                             last_jobs = jobs  # ✅ SOURCE OF TRUTH
#                             logger.info(
#                                 "[Agent Loop] %s returned %s jobs (updated last_jobs)",
#                                 tool_name,
#                                 len(jobs),
#                             )
#                         else:
#                             logger.warning("[Agent Loop] %s returned no jobs", tool_name)

#                         if not raw.get("ok", False):
#                             logger.warning("[Agent Loop] %s error: %s", tool_name, raw.get("error"))

#                     except ValueError as exc:
#                         raw = {
#                             "ok": False,
#                             "tool": tool_name,
#                             "jobs": [],
#                             "error": str(exc),
#                             "meta": {
#                                 "hint": (
#                                     f"You called '{tool_name}' without a jobs array. "
#                                     "Re-call this tool and pass the full jobs list from the previous tool result."
#                                 )
#                             },
#                         }
#                         result_str = json.dumps(raw, ensure_ascii=False)
#                         logger.warning("[Agent Loop] %s missing jobs", tool_name)

#                     except Exception as exc:
#                         raw = {
#                             "ok": False,
#                             "tool": tool_name,
#                             "jobs": [],
#                             "error": str(exc),
#                             "meta": {},
#                         }
#                         result_str = json.dumps(raw, ensure_ascii=False)
#                         logger.exception("[Agent Loop] %s FAILED", tool_name)

#                 messages.append({
#                     "role": "tool",
#                     "tool_call_id": tool_use_id,
#                     "content": result_str,
#                 })

#             continue

#         logger.warning("[Agent Loop] Unexpected finish_reason='%s' — stopping.", finish_reason)
#         break

#     logger.warning("[Agent Loop] Hit MAX_ITERATIONS (%s)", MAX_ITERATIONS)

#     # 🔥 Fallback also uses last_jobs
#     return {
#         "jobs": last_jobs,
#         "iterations": iterations,
#         "warning": "max iterations reached",
#     }


# # ---------------------------------------------------------------------------
# # entry point
# # ---------------------------------------------------------------------------

# async def run_job_search_agent(keyword: str, location: str = "Malaysia", per_page: int = 5):
#     try:
#         resume_source_id = get_resume_source_id()

#         tools = await get_mcp_tools()

#         logger.info("[Agent] MCP tools loaded: %s", list(tools.keys()))
        

#         openai_tools, tool_map = build_tool_registry(tools, resume_source_id)
#         system_prompt = build_system_prompt(keyword, location, resume_source_id)

#         result = await run_agent_loop(
#             keyword=keyword,
#             location=location,
#             per_page=per_page,
#             openai_tools=openai_tools,
#             tool_map=tool_map,
#             system_prompt=system_prompt,
#         )


#         return {
#             "result": {
#                 "jobs": result.get("jobs", []),
#                 "iterations": result.get("iterations", 1),
#             },
#             "mode": "job_search"  # optional: helps orchestrator route
#         }

#     except Exception as e:
#         return {"error": str(e)}



# ---------------------------------------------------------------------------
# FAST PIPELINE (NO AGENT LOOP)
# ---------------------------------------------------------------------------

import asyncio
import logging

logger = logging.getLogger(__name__)


async def run_job_search_agent(
    keyword: str,
    location: str = "Malaysia",
    per_page: int = 5
):
    try:
        resume_source_id = get_resume_source_id()
        tools = await get_mcp_tools()

        logger.info("[FAST PIPELINE] tools loaded: %s", list(tools.keys()))
        logger.info("[FAST PIPELINE] INPUT keyword=%s location=%s", keyword, location)

        # -------------------------
        # 1. SEARCH JOBS
        # -------------------------
        logger.info("[FAST PIPELINE] Step 1: search_jobs_tool")

        raw_search_result = await tools["search_jobs_tool"].ainvoke({
            "keyword": keyword,
            "location": location,
            "per_page": per_page,
        })

        logger.info("[RAW TOOL OUTPUT] search_jobs_tool: %s", raw_search_result)

        search_result = normalize_tool_result(raw_search_result, "search_jobs")

        # Safe extraction (handles multiple schemas)
        jobs = (
            search_result.get("jobs")
            or search_result.get("data")
            or search_result.get("result", {}).get("jobs")
            or []
        )

        # Safety check
        if not isinstance(jobs, list):
            logger.error("[FAST PIPELINE] Invalid jobs type: %s", type(jobs))
            jobs = []

        logger.info("[FAST PIPELINE] search_jobs extracted %d jobs", len(jobs))

        if not jobs:
            return {
                "result": {"jobs": [], "iterations": 1},
                "mode": "job_search"
            }

        # -------------------------
        # 2. MATCH JOBS (if resume exists)
        # -------------------------
        if resume_source_id and tools.get("match_jobs_tool"):
            logger.info("[FAST PIPELINE] Step 2: match_jobs_tool")

            raw_match_result = await tools["match_jobs_tool"].ainvoke({
                "resume_source_id": resume_source_id,
                "jobs": jobs
            })

            logger.info("[RAW TOOL OUTPUT] match_jobs_tool: %s", raw_match_result)

            match_result = normalize_tool_result(raw_match_result, "match_jobs")

            jobs = (
                match_result.get("jobs")
                or jobs
            )

        # -------------------------
        # 3. PARALLEL: INGEST (non-blocking)
        # -------------------------
        logger.info("[FAST PIPELINE] Step 3: ingest_jobs_tool (async)")

        ingest_task = asyncio.create_task(
            tools["ingest_jobs_tool"].ainvoke({"jobs": jobs})
        )

        # -------------------------
        # 4. SUMMARIZE
        # -------------------------
        logger.info("[FAST PIPELINE] Step 4: summarize_jobs_tool")

        raw_summarize_result = await tools["summarize_jobs_tool"].ainvoke({
            "jobs": jobs,
            "resume": resume_source_id
        })

        logger.info("[RAW TOOL OUTPUT] summarize_jobs_tool: %s", raw_summarize_result)

        summarize_result = normalize_tool_result(raw_summarize_result, "summarize_jobs")

        final_jobs = (
            summarize_result.get("jobs")
            or jobs
        )

        # ensure ingestion completes in background
        try:
            await ingest_task
        except Exception as e:
            logger.warning("[FAST PIPELINE] ingest_jobs failed (non-blocking): %s", str(e))

        # -------------------------
        # DONE
        # -------------------------

        

        return {
            "result": {
                "jobs": final_jobs,
                "iterations": 1
            },
            "mode": "job_search"
        }

    except Exception as e:
        logger.exception("[FAST PIPELINE] FAILED")
        return {"error": str(e)}


