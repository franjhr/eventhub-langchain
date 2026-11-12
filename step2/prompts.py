"""Step 2. System prompt: system_prompt.md with the policies inserted.

create_agent takes the system prompt as plain text, not as a template. The {policies}
marker is replaced with str.replace, so other curly braces in the file need no escaping.
"""

from pathlib import Path

from common.data import load_policies

SYSTEM_PROMPT_PATH = Path(__file__).parent / "system_prompt.md"
POLICIES_MARKER = "{policies}"

_template = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

if not _template.strip():
    raise RuntimeError(f"The system prompt is empty: {SYSTEM_PROMPT_PATH}")
if POLICIES_MARKER not in _template:
    raise RuntimeError(f"The system prompt has no {POLICIES_MARKER} marker: {SYSTEM_PROMPT_PATH}")

system_prompt = _template.replace(POLICIES_MARKER, load_policies())
