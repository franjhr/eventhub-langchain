"""Step 1. The assistant's LCEL chain: prompt | llm | parser."""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from common.config import OPENAI_API_KEY, OPENAI_MODEL
from common.data import load_policies
from step1.prompts import prompt_template


llm = ChatOpenAI(
    model=OPENAI_MODEL,
    api_key=OPENAI_API_KEY,
    reasoning_effort="low",
    timeout=30,
    max_retries=1,
)


def create_chain() -> Runnable:
    prompt = prompt_template.partial(policies=load_policies())
    return prompt | llm | StrOutputParser()
