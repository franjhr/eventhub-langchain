"""Step 2. Agent with memory: remembers each conversation, separated by session_id.

Run:  .venv/bin/uvicorn step2.app:app --port 8002
"""

from common.server import create_app
from step2.agent import create_assistant

assistant = create_assistant()


def respond(question: str, session_id: str) -> str:
    # The web's session_id is the thread_id: each conversation has its own history.
    result = assistant.invoke(
        {"messages": [{"role": "user", "content": question}]},
        {"configurable": {"thread_id": session_id}},
    )
    return result["messages"][-1].text


app = create_app(respond, "Paso 2 · memoria")
