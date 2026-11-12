"""Step 2. The assistant as an agent with memory: create_agent + checkpointer.

There are no tools yet, so each question is a single model call. What step 2 adds:
- InMemorySaver keeps the messages of each conversation, separated by thread_id.
- keep_last_messages trims the stored conversation to the last MAX_MESSAGES messages.
"""

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import before_model
from langchain_core.messages import RemoveMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.runtime import Runtime

from common.config import OPENAI_API_KEY, OPENAI_MODEL
from step2.prompts import system_prompt

MAX_MESSAGES = 10

llm = ChatOpenAI(
    model=OPENAI_MODEL,
    api_key=OPENAI_API_KEY,
    reasoning_effort="low",
    timeout=30,
    max_retries=1,
)


@before_model
def keep_last_messages(state: AgentState, runtime: Runtime) -> dict | None:
    """Before each model call, keeps only the last MAX_MESSAGES messages of the conversation.

    It runs after the new question has been added, so the question is always among them.
    The removal is saved by the checkpointer: the old messages are deleted, not just hidden.
    """
    messages = state["messages"]
    if len(messages) <= MAX_MESSAGES:
        return None
    return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *messages[-MAX_MESSAGES:]]}


def create_assistant():
    return create_agent(
        model=llm,
        tools=[],
        system_prompt=system_prompt,
        middleware=[keep_last_messages],
        checkpointer=InMemorySaver(),
    )
