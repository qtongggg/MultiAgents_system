from Agents.Base_agent import BaseAgent, AgentInfo
from Agents.Agent_Registry import AgentRegistry
import logging

from custom.custom_types import (
    AgentResult
)

logger = logging.getLogger(__name__)

class ClarificationAgent(BaseAgent):

    def __init__(self, info: AgentInfo):
        super().__init__(info)

        

    async def run(self, user_input: str):
        mcp_tools = await self.get_tools()


        clarification_tool = mcp_tools['clarification_tool']

        clarification_result = await self.execute_tool(
            clarification_tool,
            {
                "user_input": user_input
            }
        )

        return clarification_result
        

