"""Step 3. The agent with memory and tools: create_agent + checkpointer + tools.

What step 3 adds to step 2:
- The tools search_events and get_order. The model decides when to call them; the agent
  runs them and gives the result back to the model, which then writes the answer.
- The trim keeps whole turns: it never separates a tool call from its result.
"""

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import before_model
from langchain_core.messages import AnyMessage, HumanMessage, RemoveMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.runtime import Runtime

from common.config import OPENAI_API_KEY, OPENAI_MODEL
from step3.prompts import system_prompt
from step3.tools import get_order, search_events

MAX_MESSAGES = 10

llm = ChatOpenAI(
    model=OPENAI_MODEL,
    api_key=OPENAI_API_KEY,
    reasoning_effort="low",
    timeout=30,
    max_retries=1,
)


def trim_start(messages: list[AnyMessage]) -> int:
    """Index of the first message to keep: at most MAX_MESSAGES, starting on a question.

    A tool call (AIMessage with tool_calls) and its result (ToolMessage) must stay together:
    the API rejects a tool result without its call. Starting the kept messages on a
    question (HumanMessage) guarantees it, because a turn is never cut in half.
    If the current turn alone is longer than MAX_MESSAGES, the whole turn is kept.
    """
    start = max(len(messages) - MAX_MESSAGES, 0)
    questions = [i for i, message in enumerate(messages) if isinstance(message, HumanMessage)]
    later = [i for i in questions if i >= start]
    if later:
        return later[0]
    return questions[-1] if questions else start


@before_model
def keep_last_messages(state: AgentState, runtime: Runtime) -> dict | None:
    """Before each model call, keeps only the last turns that fit in MAX_MESSAGES messages.

    It also runs between a tool result and the next model call, so the trim may happen in
    the middle of a turn; trim_start never cuts that turn.
    The removal is saved by the checkpointer: the old messages are deleted, not just hidden.
    """
    messages = state["messages"]
    start = trim_start(messages)
    if start == 0:
        return None
    return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *messages[start:]]}


def create_assistant():
    return create_agent(
        model=llm,
        tools=[search_events, get_order],
        system_prompt=system_prompt,
        middleware=[keep_last_messages],
        checkpointer=InMemorySaver(),
    )
