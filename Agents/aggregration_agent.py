from Agents.Base_agent import BaseAgent, AgentInfo
import logging

from custom.custom_types import (
    AgentResult,
    ResumeResult
)

logger = logging.getLogger(__name__)


class AggregrationAgent(BaseAgent):

    def __init__(self, info: AgentInfo):
        super().__init__(info)

    def run(self, input: list[dict]):
        pass