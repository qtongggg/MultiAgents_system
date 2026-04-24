from pydantic import BaseModel
from Agents.Base_agent import BaseAgent, AgentInfo
from custom.custom_types import JobSearchRequest, JobSearchInfo, MatchJobInfo, AgentResult


class AgentRegistry:

    def __init__(self):
        self._agents = {}

    def register(self, name: str, agent:BaseAgent):

        if name in self._agents:
            raise ValueError(f"Agent with name '{name}' is already registered.")
        
        self._agents[name] = agent
        print(f"✅ Registered agent: {name}")
        

    def get_agent(self, name: str):

        agent = self._agents.get(name)

        if not agent:
            raise ValueError(f"No agent found with name '{name}'.")
        
        return agent