"""Step 1. Base chain: answers only from policies.md, with no memory and no tools.

Run:  .venv/bin/uvicorn step1.app:app --port 8001
"""

from common.server import create_app
from step1.chain import create_chain

chain = create_chain()


def respond(question: str, session_id: str) -> str:
    # session_id is not used: in step 1 every question is independent (no memory).
    return chain.invoke({"question": question})


app = create_app(respond, "Paso 1 · cadena")
