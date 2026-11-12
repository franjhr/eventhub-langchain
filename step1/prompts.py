"""Step 1. Prompt template: the system prompt (system_prompt.md) and the user's question.

system_prompt.md has a single variable, {policies}, filled with policies.md.
Any other curly braces in that file would break the template: escape them as {{ }} if needed.
"""

from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

SYSTEM_PROMPT_PATH = Path(__file__).parent / "system_prompt.md"
SYSTEM_PROMPT = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

if not SYSTEM_PROMPT.strip():
    raise RuntimeError(f"The system prompt is empty: {SYSTEM_PROMPT_PATH}")

prompt_template = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "{question}"),
    ]
)
