from Agents.Base_agent import BaseAgent, AgentInfo
from Agents.Agent_Registry import AgentRegistry
import logging

from custom.custom_types import (
    AgentResult
)

logger = logging.getLogger(__name__)

class PlannerAgent(BaseAgent):

    def __init__(self, info:AgentInfo, registry:AgentRegistry):
        super().__init__(info)
        self.registry = registry
    
    async def get_agents(self):

        return self.registry.list_agents()
        


    async def run(self, user_input: str):
        mcp_tools = await self.get_tools()
        available_agents = await self.get_agents()

        

        planner_tool = mcp_tools['planner_tool']

        planner_result = await self.execute_tool(
            planner_tool,
            {
                "user_input": user_input,
                "available_agents": available_agents 
            }

        )

        


        return planner_result
