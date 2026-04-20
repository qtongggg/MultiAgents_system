import os
import json
import logging
from openai import AsyncOpenAI
from dotenv import load_dotenv
from MCP_agent.agent_setup import get_mcp_tools

logger = logging.getLogger(__name__)
load_dotenv()

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MAX_ITERATIONS = 10


# ---------------------------------------------------------------------------
# Output builder — single source of truth for the response shape
# ---------------------------------------------------------------------------

def make_result(
    analysis: dict,
    summary: str,
    iterations: int,
    done: bool,
    error: str | None = None,
    warning: str | None = None,
) -> dict:
    return {
        "ok": error is None,
        "tool": "run_resume_agent",
        "intent": analysis.get("intent", "qa"),
        "company_name": analysis.get("company_name"),
        "location": analysis.get("location"),
        "candidate_name": analysis.get("candidate_name"),
        "rewritten_query": analysis.get("rewritten_query", ""),
        "result": {"answer": summary},
        "mode": analysis.get("mode", "resume"),
        "error": error,
        "iterations": iterations,
        "done": done,
        **({"warning": warning} if warning else {}),
    }


# ---------------------------------------------------------------------------
# System prompt — persona + workflow only, no conflicting JSON instruction
# ---------------------------------------------------------------------------

def build_system_prompt(question: str, top_k: int) -> str:
    return f"""You are an HR orchestration agent.

User question: "{question}"
Top K: {top_k}

Your workflow (follow in order):
1. Call analyze_query with the user's question
2. If intent == "resume" → call search_resume with rewritten_query, top_k, and candidate_name (if present)
3. After search_resume completes → call summarize_tool with the retrieved context and the original question
4. Once summarize_tool responds, you are done — stop calling tools

Rules:
- Only call the tools listed above
- Do not skip steps or reorder them
- Do not invent facts
- Pass candidate_name into search_resume only if analyze_query returned one
- Use top_k={top_k} for search_resume
- After all tools complete, output a single valid JSON object with no markdown fences:
{{
  "ok": true,
  "intent": "<intent>",
  "company_name": null,
  "location": null,
  "candidate_name": null,
  "rewritten_query": "<rewritten_query>",
  "result": {{"answer": "<summary>"}},
  "mode": "<mode>",
  "error": null,
  "done": true
}}"""


# ---------------------------------------------------------------------------
# MCP response normalizer — handles all the weird shapes MCP tools return
# ---------------------------------------------------------------------------

async def _call_mcp(tool, payload: dict) -> dict:
    raw = await tool.ainvoke(payload)

    if isinstance(raw, dict):
        return raw

    if isinstance(raw, list) and raw:
        first = raw[0]
        if isinstance(first, dict) and first.get("type") == "text":
            text = first.get("text", "")
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return parsed
                raise TypeError(f"Parsed MCP text is not a dict: {type(parsed).__name__}")
            except json.JSONDecodeError as exc:
                raise TypeError(f"MCP returned non-JSON text: {text}") from exc

    if hasattr(raw, "content"):
        content = raw.content
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError as exc:
                raise TypeError(f"Tool .content is not valid JSON: {content}") from exc

    raise TypeError(f"Unexpected MCP result type {type(raw).__name__}: {raw!r}")


# ---------------------------------------------------------------------------
# Input preparation — all argument normalization in one place
# ---------------------------------------------------------------------------

def prepare_input(tool_name: str, raw_input: dict, analysis: dict, resume_results: list, question: str, top_k: int) -> dict:
    if tool_name == "analyze_query":
        return {"question": raw_input.get("question") or question}

    if tool_name == "search_resume":
        payload = {
            "question": raw_input.get("question") or analysis.get("rewritten_query") or question,
            "top_k": raw_input.get("top_k") or top_k,
        }
        candidate_name = raw_input.get("candidate_name") or analysis.get("candidate_name")
        if candidate_name:
            payload["candidate_name"] = candidate_name
        return payload

    if tool_name == "summarize_tool":
        context = _build_context(resume_results)
        if not context:
            raise ValueError("summarize_tool called with empty resume context")
        return {
            "context": context,
            "question": raw_input.get("question") or question,
        }

    raise ValueError(f"Unknown tool: {tool_name}")


def _build_context(results: list[dict]) -> str:
    chunks = []
    for item in results:
        if not isinstance(item, dict):
            continue
        text = (
            item.get("text")
            or item.get("payload", {}).get("text")
            or item.get("page_content")
            or item.get("content")
            or item.get("chunk_text")
            or ""
        )
        if isinstance(text, str) and text.strip():
            chunks.append(text.strip())
    return "\n\n".join(chunks)


# ---------------------------------------------------------------------------
# Tool registry — OpenAI schema + dispatcher
# ---------------------------------------------------------------------------

def build_tool_registry(tools: dict) -> tuple[list, dict]:
    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": "analyze_query",
                "description": "Analyze the user's question. Returns rewritten_query, intent, company_name, location, and candidate_name.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "The user's original question."}
                    },
                    "required": ["question"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_resume",
                "description": "Search the resume database. Use only when intent is 'resume'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "Rewritten query for retrieval."},
                        "top_k": {"type": "integer", "description": "Number of resume chunks to return."},
                        "candidate_name": {"type": "string", "description": "Optional candidate name in lowercase_with_underscores."},
                    },
                    "required": ["question", "top_k"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "summarize_tool",
                "description": "Summarize retrieved resume context.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "context": {"type": "string", "description": "Resume text to summarize."},
                        "question": {"type": "string", "description": "The original user question."},
                    },
                    "required": ["context", "question"],
                },
            },
        },
    ]

    tool_map = {
        "analyze_query":  lambda payload: _call_mcp(tools["analyze_query_with_llm"], payload),
        "search_resume":  lambda payload: _call_mcp(tools["search_resume"], payload),
        "summarize_tool": lambda payload: _call_mcp(tools["summarize_tool"], payload),
    }

    return openai_tools, tool_map


# ---------------------------------------------------------------------------
# Agent loop — LLM stays in control, Python only tracks state
# ---------------------------------------------------------------------------

async def _run_loop(
    question: str,
    top_k: int,
    openai_tools: list,
    tool_map: dict,
    system_prompt: str,
) -> dict:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Process this question: '{question}'"},
    ]

    # Mutable state — updated as tools return results
    analysis: dict = {}
    resume_results: list = []
    summary_text: str = ""
    iterations = 0

    while iterations < MAX_ITERATIONS:
        iterations += 1
        logger.info("[ResumeAgent] iteration %s/%s", iterations, MAX_ITERATIONS)

        response = await openai_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            tools=openai_tools,
            messages=messages,
            max_tokens=2048,
        )

        choice = response.choices[0]
        message = choice.message
        messages.append(message)

        logger.info("[ResumeAgent] finish_reason=%s", choice.finish_reason)

        # ── LLM finished — parse its final JSON response ──────────────────
        if choice.finish_reason == "stop":
            text = (message.content or "").strip()

            # Strip accidental markdown fences defensively
            if text.startswith("```"):
                parts = text.split("```")
                text = parts[1].removeprefix("json").strip() if len(parts) > 1 else text

            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    # Merge LLM output with our tracked state as fallback
                    analysis_fallback = analysis or {}
                    return {
                        "ok": data.get("ok", True),
                        "tool": "run_resume_agent",
                        "intent": data.get("intent") or analysis_fallback.get("intent", "qa"),
                        "company_name": data.get("company_name") or analysis_fallback.get("company_name"),
                        "location": data.get("location") or analysis_fallback.get("location"),
                        "candidate_name": data.get("candidate_name") or analysis_fallback.get("candidate_name"),
                        "rewritten_query": data.get("rewritten_query") or analysis_fallback.get("rewritten_query", question),
                        "result": data.get("result") or {"answer": summary_text},
                        "mode": data.get("mode") or analysis_fallback.get("mode", "resume"),
                        "error": data.get("error"),
                        "iterations": iterations,
                        "done": data.get("done", True),
                    }
            except (json.JSONDecodeError, Exception):
                logger.warning("[ResumeAgent] Final LLM output was not valid JSON, using tracked state")

            # Fallback: build result from what we tracked
            return make_result(analysis, summary_text, iterations, done=True,
                               warning="LLM final output was not valid JSON")


        if choice.finish_reason == "tool_calls":
            for tc in message.tool_calls or []:
                tool_name = tc.function.name
                tool_call_id = tc.id

                try:
                    raw_input = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    raw_input = {}

                logger.info("[ResumeAgent] tool=%s input=%s", tool_name, list(raw_input.keys()))

                # Normalize inputs, filling in missing fields from tracked state
                try:
                    tool_input = prepare_input(tool_name, raw_input, analysis, resume_results, question, top_k)
                except ValueError as exc:
                    # summarize_tool with empty context — tell the LLM and let it recover
                    logger.warning("[ResumeAgent] prepare_input failed: %s", exc)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": json.dumps({"ok": False, "error": str(exc)}),
                    })
                    continue

                # Dispatch to MCP tool
                callable_fn = tool_map.get(tool_name)
                if callable_fn is None:
                    tool_result = {"ok": False, "error": f"Tool '{tool_name}' not found"}
                else:
                    try:
                        tool_result = await callable_fn(tool_input)

                        # Update tracked state
                        if tool_name == "analyze_query":
                            analysis = tool_result
                            logger.info("[ResumeAgent] analysis done: intent=%s", analysis.get("intent"))

                        elif tool_name == "search_resume":
                            raw_result = tool_result.get("result")
                            resume_results = raw_result if isinstance(raw_result, list) else []
                            logger.info("[ResumeAgent] search_resume returned %s chunks", len(resume_results))

                        elif tool_name == "summarize_tool":
                            result_data = tool_result.get("result") or {}
                            summary_text = result_data.get("answer", "") if isinstance(result_data, dict) else ""
                            logger.info("[ResumeAgent] summary length=%s", len(summary_text))

                    except Exception as exc:
                        logger.exception("[ResumeAgent] tool %s failed", tool_name)
                        tool_result = {"ok": False, "error": str(exc)}

                # Feed result back to LLM — it decides what to do next
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })

            continue  # Go back to LLM with all tool results appended

        logger.warning("[ResumeAgent] Unexpected finish_reason='%s', stopping", choice.finish_reason)
        break

    # Hit iteration limit
    return make_result(analysis, summary_text, iterations, done=False,
                       warning="Max iterations reached without completion")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_resume_agent(question: str, top_k: int = 5) -> dict:
    try:
        tools = await get_mcp_tools()
        openai_tools, tool_map = build_tool_registry(tools)
        system_prompt = build_system_prompt(question, top_k)

        result = await _run_loop(
            question=question,
            top_k=top_k,
            openai_tools=openai_tools,
            tool_map=tool_map,
            system_prompt=system_prompt,
        )

        logger.info("[ResumeAgent] Final result:\n%s", json.dumps(result, indent=2, ensure_ascii=False))
        return result

    except Exception as exc:
        logger.exception("[ResumeAgent] Fatal error")
        return make_result(
            analysis={},
            summary="",
            iterations=0,
            done=False,
            error=str(exc),
        )