from langchain_core.messages import SystemMessage, HumanMessage
import json
from langgraph.graph import StateGraph, START, END
from app.agents.agent_state import AgentState
from app.llm_model import llm
from app.agents.utils import parse_llm_json


def classifier_node(state: AgentState):
    system_prompt = """
        You are a senior software engineer analyzing tickets.
        Given a ticket description, respond ONLY in valid JSON:
        {
            "ticket_type": "defect" or "feature",
            "ticket_intent": "clean precise one-line description of what needs to be done"
        }

        Classification rules:
        - defect  → bug, error, crash, wrong behavior, performance issue, security vulnerability
        - feature → new functionality, enhancement, improvement to existing feature, refactor

        ticket_intent rules:
        - Must be one clean sentence
        - Remove all noise from original ticket
        - Be specific about what needs to change
        """
    response = llm.invoke([SystemMessage(content=system_prompt)
                          , HumanMessage(content=f"Ticket: {state['ticket_desc']}")]).content.strip().strip("")
    result = parse_llm_json(response)

    
    return {
        **state,
        "ticket_type":result['ticket_type'],
        "ticket_intent":result['ticket_intent'],
    }
    
classifier_graph = StateGraph(AgentState)
classifier_graph.add_node("classifier_node", classifier_node)
classifier_graph.add_edge(START, 'classifier_node')
classifier_graph.add_edge('classifier_node', END)

classifier_agent = classifier_graph.compile()