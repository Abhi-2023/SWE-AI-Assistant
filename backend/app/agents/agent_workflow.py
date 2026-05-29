from app.agents.agent_state import AgentState
from app.agents.classifier_understand_agent import classifier_agent
from app.agents.planner_agent import planner_agent
from app.agents.code_writer_agent import code_writer_agent
from app.agents.test_debug_agent import test_debug_agent
from app.agents.git_agent import git_agent
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

final_state = StateGraph(AgentState)

final_state.add_node("classifier_understand_agent", classifier_agent)
final_state.add_node("planner_agent", planner_agent)
final_state.add_node("code_writer_agent", code_writer_agent)
final_state.add_node("test_debug_agent", test_debug_agent)
final_state.add_node("git_agent", git_agent)

final_state.add_edge(START, "classifier_understand_agent")
final_state.add_edge("classifier_understand_agent", "planner_agent")
final_state.add_edge("planner_agent", "code_writer_agent")
final_state.add_edge("code_writer_agent", "test_debug_agent")
final_state.add_edge("test_debug_agent", "git_agent")

main_agent = final_state.compile()

