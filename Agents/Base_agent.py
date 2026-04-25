from pydantic import BaseModel, Field
from abc import ABC, abstractmethod

import json
from MCP_agent.agent_setup import get_mcp_tools

class AgentInfo(BaseModel):
    name: str = Field(description="The name of the agent")
    description: str = Field(description="A brief description of the agent's purpose and capabilities")



class BaseAgent(ABC):

    def __init__(self, info: AgentInfo):
        self.info = info
        self._tools = None

    @abstractmethod
    async def run(self, *args, **kwargs):
        pass

    async def execute_tool(self, tool, payload: dict):
        """
        Standardized MCP tool execution
        Handles LangChain MCP wrapped output
        """

        raw_result = await tool.ainvoke(payload)

        # MCP adapter returns:
        # [ {"type": "text", "text": "{json}"} ]

        if isinstance(raw_result, list) and len(raw_result) > 0:
            first = raw_result[0]

            if isinstance(first, dict) and "text" in first:
                try:
                    return json.loads(first["text"])
                except Exception as e:
                    raise Exception(f"Failed to parse MCP JSON: {e}")

        if isinstance(raw_result, dict):
            return raw_result

        raise Exception(f"Unsupported tool output format: {type(raw_result)}")
    
    async def get_tools(self):
        if self._tools is None:
            self._tools = await get_mcp_tools()
        return self._tools





        




    
    
    
