import json
import tempfile
import os
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

from app.agents.agent_state import AgentState
from app.agents.router_agent import route_message
from app.agents.agent_workflow import main_agent
from app.agents.planner_agent import query_context_retrieval
from app.llm_model import llm
from app.core.config import get_settings

settings = get_settings()


# ── SSE helper ────────────────────────────────────────────
def sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


# ── Node: Router ──────────────────────────────────────────
def router_node(state: AgentState) -> AgentState:
    result = route_message(
        user_message  = state["user_message"],
        has_namespace = state["vector_namespace"] is not None,
    )
    return {
        **state,
        "mode":             result["mode"],
        "routing_reasoning": result["reasoning"],
    }


# ── Node: General ─────────────────────────────────────────
def general_node(state: AgentState) -> AgentState:
    messages = [SystemMessage(content="""
            You are an expert Software Engineering and AI Assistant.

            Your responsibilities:
            - Answer software engineering questions clearly and accurately.
            - Help debug errors by reasoning from provided information.
            - When explaining concepts, start with intuition before diving into technical details.
            - Use examples whenever they improve understanding.
            - Prefer practical engineering advice over theoretical discussion unless explicitly requested.

            Response Guidelines:
            - Be concise for simple questions.
            - Be detailed for technical or educational questions.
            - Use bullet points for multi-step explanations.
            - Use code snippets when appropriate.
            - Clearly distinguish facts from assumptions.
            """)]
    
    for msg in state.get("chat_history", []):
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(SystemMessage(content=msg["content"]))
    
    messages.append(HumanMessage(content=state["user_message"]))
    
    response = llm.invoke(messages).content.strip()
    return {**state, "llm_response": response}


def rag_node(state: AgentState) -> AgentState:
    docs = query_context_retrieval(
        vector_namespace = state["vector_namespace"],
        ticket_intent    = state["user_message"],
        top_k            = 6,
    )
    context_text = "\n".join([doc["text"] for doc in docs])

    messages = [SystemMessage(content="""You are a senior software engineer.
    Answer the user's question using the provided codebase context.
    Be specific, reference file paths and function names where relevant.""")]

    for msg in state.get("chat_history", []):
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(SystemMessage(content=msg["content"]))

    messages.append(HumanMessage(content=f"""
    Question: {state["user_message"]}

    Codebase Context:
    {context_text}
    """))

    response = llm.invoke(messages).content.strip()
    return {
        **state,
        "retrieved_context": docs,
        "llm_response":      response,
    }


# ── Node: Agentic ─────────────────────────────────────────
def agentic_node(state: AgentState) -> AgentState:
    local_repo_path = os.path.join(
        tempfile.gettempdir(), "forge",
        str(state["user_id"]), str(state["conversation_id"])
    )

    agentic_state = {
        **state,
        "local_repo_path":     local_repo_path,
        "ticket_id":           state["conversation_id"],
        "vector_namespace":    state["vector_namespace"],
        "ticket_desc":         state["user_message"],
        "ticket_type":         "defect",
        "ticket_intent":       "",
        "retrieved_context":   [],
        "implementation_plan": [],
        "files_to_modify":     [],
        "code_changes":        {},
        "test_results":        "",
        "tests_passed":        False,
        "error_log":           "",
        "retry_count":         0,
        "max_retries":         3,
        "base_branch":         "main",
        "git_token":           settings.github_token,
        "commit_message":      "",
        "pr_title":            "",
        "pr_url":              None,
    }

    # Run full agent pipeline
    final = main_agent.invoke(agentic_state)

    return {
        **state,
        "ticket_type":        final.get("ticket_type", ""),
        "ticket_intent":      final.get("ticket_intent", ""),
        "files_to_modify":    final.get("files_to_modify", []),
        "code_changes":       final.get("code_changes", {}),
        "test_results":       final.get("test_results", ""),
        "tests_passed":       final.get("tests_passed", False),
        "commit_message":     final.get("commit_message", ""),
        "pr_title":           final.get("pr_title", ""),
        "pr_url":             final.get("pr_url"),
    }


# ── Node: No Namespace ────────────────────────────────────
def no_namespace_node(state: AgentState) -> AgentState:
    return {
        **state,
        "llm_response": "Please select a repository first.",
    }


# ── Conditional Router ────────────────────────────────────
def route_by_mode(state: AgentState) -> str:
    return state["mode"]


# ── Build Conversation Graph ──────────────────────────────
conversation_graph_builder = StateGraph(AgentState)

conversation_graph_builder.add_node("router_node",       router_node)
conversation_graph_builder.add_node("general_node",      general_node)
conversation_graph_builder.add_node("rag_node",          rag_node)
conversation_graph_builder.add_node("agentic_node",      agentic_node)
conversation_graph_builder.add_node("no_namespace_node", no_namespace_node)

conversation_graph_builder.add_edge(START, "router_node")

conversation_graph_builder.add_conditional_edges(
    "router_node",
    route_by_mode,
    {
        "general":      "general_node",
        "rag":          "rag_node",
        "agentic":      "agentic_node",
        "no_namespace": "no_namespace_node",
    }
)

conversation_graph_builder.add_edge("general_node",      END)
conversation_graph_builder.add_edge("rag_node",          END)
conversation_graph_builder.add_edge("agentic_node",      END)
conversation_graph_builder.add_edge("no_namespace_node", END)

conversation_graph = conversation_graph_builder.compile()