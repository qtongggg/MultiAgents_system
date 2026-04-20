import asyncio
import logging
from MCP_agent.agent_setup import startup_mcp

logger = logging.getLogger(__name__)

_mcp_ready = False
_lock = asyncio.Lock()

async def ensure_mcp():
    global _mcp_ready

    if _mcp_ready:
        return

    async with _lock:
        if _mcp_ready:
            return

        try:
            logger.info("🔧 Initializing MCP lazily...")
            await startup_mcp()
            _mcp_ready = True
            logger.info("✅ MCP ready")
        except Exception as e:
            logger.error(f"❌ MCP failed: {e}")
            _mcp_ready = False