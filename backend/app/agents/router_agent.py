import json
from langchain_core.messages import SystemMessage, HumanMessage
from app.llm_model import llm
from app.prompts.prompt_version_1 import SYSTEM_PROMPT
from app.agents.utils import parse_llm_json


def route_message(user_message: str, has_namespace: str)-> dict:
    """
    Classify user message into rag / agentic / general.

    Args:
        user_message:  the raw message from the user
        has_namespace: whether the user has a vector namespace selected

    Returns:
        {
            "mode": "rag" | "agentic" | "general",
            "reasoning": str
        }
    """
    
    response = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=f"User Message : {user_message}")]).content.strip().strip("")
    
    result = parse_llm_json(response)

    
    if result['mode'] in ('rag', 'agentic') and not has_namespace:
        return {
            'mode': "no namespace",
            'reasoning': "User requested codebase operation but no repository selected"
        }
    return result
