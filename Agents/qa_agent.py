from langchain_core.prompts import ChatPromptTemplate
from LLM.llm import llm


async def run_qa_agent(question: str):

    prompt = ChatPromptTemplate.from_template("""
    You are a helpful AI assistant.

    You can:
    - Greet the user
    - Answer simple questions
    - Solve basic math problems
    - Respond naturally and briefly

    If the user says something like "good morning", respond politely.

    Question:
    {question}

    Answer:
    """)

    chain = prompt | llm

    response = await chain.ainvoke({
        "question": question
    })

    return {
        "answer": response.content.strip(),
        "mode": "chat"
    }