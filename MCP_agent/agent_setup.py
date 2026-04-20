from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

server_params = StdioServerParameters(
    command=sys.executable,
    args=["-u", "-m", "MCP_tools.mcp_jobs_tools"],
    cwd=str(PROJECT_ROOT),
    env={
        **os.environ,
        "PYTHONPATH": str(PROJECT_ROOT),
        "PYTHONUNBUFFERED": "1",
    },
)


_stdio_cm = None
_session_cm = None
_session = None
_tool_map = None


async def startup_mcp():
    global _stdio_cm, _session_cm, _session, _tool_map

    if _tool_map is not None:
        logger.info("[MCP] already started")
        return _tool_map

    _stdio_cm = stdio_client(server_params)
    read, write = await _stdio_cm.__aenter__()

    _session_cm = ClientSession(read, write)
    _session = await _session_cm.__aenter__()
    await _session.initialize()

    tools_list = await load_mcp_tools(_session)
    _tool_map = {tool.name: tool for tool in tools_list}

    logger.info("[MCP] persistent session ready")
    logger.info("[MCP] loaded tools: %s", list(_tool_map.keys()))
    return _tool_map


async def shutdown_mcp():
    global _stdio_cm, _session_cm, _session, _tool_map

    logger.info("[MCP] shutting down persistent session")

    try:
        if _session_cm is not None:
            await _session_cm.__aexit__(None, None, None)
    finally:
        _session_cm = None
        _session = None

    try:
        if _stdio_cm is not None:
            await _stdio_cm.__aexit__(None, None, None)
    finally:
        _stdio_cm = None
        _tool_map = None


async def get_mcp_tools():
    if _tool_map is None:
        logger.info("[MCP] no cached session, starting MCP")
        return await startup_mcp()

    logger.info("[MCP] using cached MCP tools: %s", list(_tool_map.keys()))
    return _tool_map