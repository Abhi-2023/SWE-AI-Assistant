from langchain_core.messages import SystemMessage, HumanMessage
import json
from langgraph.graph import StateGraph, START, END
from app.agents.agent_state import AgentState
from app.llm_model import llm

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
    if response.startswith("```"):
        response = response.split("```")[1]
        if response.startswith("json"):
            response = response[4:]

    result = json.loads(response.strip())
    
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