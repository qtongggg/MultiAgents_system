from Agents.Base_agent import BaseAgent, AgentInfo
import logging

from custom.custom_types import (
    AgentResult,
    ResumeResult
)

logger = logging.getLogger(__name__)


class ResumeAgent(BaseAgent):

    def __init__(self, info: AgentInfo):
        super().__init__(info)

    async def run(
        self,
        user_input: str,
        top_k: int = 5
    ):
        try:
            mcp_tools = await self.get_tools()

            # -------------------------------
            # 1. SEARCH RESUME
            # -------------------------------
            search_resume_tool = mcp_tools["search_resume"]

            search_result = await self.execute_tool(
                search_resume_tool,
                {
                    "question": user_input,
                    "top_k": top_k
                }
            )
            

            retrieved_chunks = search_result.get("data", [])  # list[dict]

            # -------------------------------
            # 2. SAFE VALIDATION
            # ------------------------------
            

            cleaned_chunks = [
                ResumeResult.model_validate(item)
                for item in retrieved_chunks.get("chunks")
                if isinstance(item, dict)
            ]
            

            
            # -------------------------------
            # 3. BUILD CONTEXT
            # -------------------------------
            context = "\n\n".join(
                chunk.text for chunk in cleaned_chunks if chunk.text
            )

            if not context.strip():
                return AgentResult(
                    status="success",
                    data={
                        "answer": "No resume information found.",
                        "chunks": []
                    },
                    meta={}
                ).model_dump()

            # -------------------------------
            # 4. SUMMARIZE
            # -------------------------------
            summarize_tool = mcp_tools["summarize_tool"]

            summary_result = await self.execute_tool(
                summarize_tool,
                {
                    "context": context,
                    "question": user_input
                }
            )

            final_answer = (
                summary_result
                .get("result", {})
                .get("answer", "")
            )

            logger.info(f"resume final result: {final_answer}")

            # -------------------------------
            # 5. RETURN STANDARD FORMAT
            # -------------------------------
            return AgentResult(
                status="success",
                data={
                    "answer": final_answer,
                    "chunks": [c.model_dump() for c in cleaned_chunks]
                },
                meta={}
            ).model_dump()

        except Exception as e:
            logger.exception("ResumeAgent failed")

            return AgentResult(
                status="error",
                data={},
                error=str(e),
                meta={"agent": "resume"}
            ).model_dump()