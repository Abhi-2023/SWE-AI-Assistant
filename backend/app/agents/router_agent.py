import json
from langchain_core.messages import SystemMessage, HumanMessage
from app.llm_model import llm
from app.prompts.prompt_version_1 import SYSTEM_PROMPT

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
    
    if response.startswith("```"):
        response = response.split("```")[1]
        if response.startswith("json"):
            response = response[4:]
            
    result = json.load(response)
    
    if result['mode'] in ('rag', 'agentic') and not has_namespace:
        return {
            'mode': "no namespace",
            'reasoning': "User requested codebase operation but no repository selected"
        }
    return result
