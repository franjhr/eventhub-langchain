"""Extra step. The step 3 agent that can also reserve tickets.

Run:  .venv/bin/uvicorn step4_extra.app:app --port 8004

On start, the data is copied to data/runtime/: the reservations are written there and are
lost when the server restarts.
"""

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, ToolMessage

from common.server import ChatResponse, ToolCall, create_app
from step4_extra.agent import create_assistant
from step4_extra.tools import reset_runtime_data

reset_runtime_data()
assistant = create_assistant()


def tools_used(turn: list[AnyMessage]) -> list[ToolCall]:
    """The tool calls of one turn, each with its result, in the order the model made them.

    The model asks for a tool in an AIMessage (tool_calls) and the agent answers with a
    ToolMessage that carries the same tool_call_id: that id joins each call to its result.
    """
    results = {message.tool_call_id: message.text for message in turn if isinstance(message, ToolMessage)}
    return [
        ToolCall(name=call["name"], args=call["args"], result=results.get(call["id"], ""))
        for message in turn
        if isinstance(message, AIMessage)
        for call in message.tool_calls
    ]


def respond(question: str, session_id: str) -> ChatResponse:
    # The web's session_id is the thread_id: each conversation has its own history.
    result = assistant.invoke(
        {"messages": [{"role": "user", "content": question}]},
        {"configurable": {"thread_id": session_id}},
    )
    messages = result["messages"]
    # This turn starts at the last question: the earlier messages belong to previous turns.
    start = max(i for i, message in enumerate(messages) if isinstance(message, HumanMessage))
    return ChatResponse(response=messages[-1].text, tools=tools_used(messages[start:]))


app = create_app(respond, "Paso extra · reservas")
