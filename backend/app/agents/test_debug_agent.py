import os
import json
import docker
from langgraph.graph import StateGraph, START, END
from app.agents.agent_state import AgentState
from app.llm_model import llm
from app.agents.utils import parse_llm_json


def write_files_to_disk(code_changes: dict[str, str], local_repo_path: str):
    for file_path, content in code_changes.items():
        full_path = os.path.join(local_repo_path, file_path)
        if dir_path := os.path.dirname(full_path):
            os.makedirs(dir_path, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)


# ── Test Runner Node ──────────────────────────────────────────────────────────
def test_runner_node(state: AgentState) -> AgentState:
    client = docker.from_env()

    try:
        output = client.containers.run(
            image="forge-test-runner",
            command="pytest tests/ -v --tb=short",
            volumes={state["local_repo_path"]: {"bind": "/app", "mode": "rw"}},
            working_dir="/app",
            remove=True,
            stdout=True,
            stderr=True,
        )

        output = output.decode("utf-8")
        tests_passed = "failed" not in output.lower() and "error" not in output.lower()
        error_log = "" if tests_passed else output

    except docker.errors.ContainerError as e:
        output = e.stderr.decode("utf-8")
        tests_passed = False
        error_log = output

    return {
        **state,
        "test_results": output,
        "tests_passed": tests_passed,
        "error_log": error_log,
    }


# ── Debugger Node ─────────────────────────────────────────────────────────────
def debugger_node(state: AgentState) -> AgentState:
    prompt = f"""
You are a senior software engineer debugging failing tests.

Error Log:
{state['error_log']}

Current Code Changes:
{state['code_changes']}

Original Codebase Context:
{chr(10).join([doc['text'] for doc in state['retrieved_context']])}

Analyze the error and fix the code.
Respond ONLY in valid JSON:
{{
    "code_changes": {{
        "full/path/to/file.py": "complete fixed file content"
    }}
}}

Rules:
- Always return COMPLETE file content, never partial
- Only fix what the error log indicates
- Use exact same file paths as current code changes
- Follow existing code style from context
"""

    response = llm.invoke(prompt).content.strip()

    result = parse_llm_json(response)


    # Write fixed files to disk so test runner picks them up
    write_files_to_disk(result["code_changes"], state["local_repo_path"])

    return {
        **state,
        "code_changes": result["code_changes"],
        "retry_count": state["retry_count"] + 1,
    }


# ── Test Router ───────────────────────────────────────────────────────────────
def route_after_test(state: AgentState) -> str:
    if state["tests_passed"]:
        return "pass"
    return "pass" if state["retry_count"] >= state["max_retries"] else "debugger"


# ── Test Subgraph ─────────────────────────────────────────────────────────────
test_graph_builder = StateGraph(AgentState)

test_graph_builder.add_node("test_runner", test_runner_node)
test_graph_builder.add_node("debugger", debugger_node)

test_graph_builder.add_edge(START, "test_runner")

test_graph_builder.add_conditional_edges(
    "test_runner",
    route_after_test,
    {
        "pass": END,
        "debugger": "debugger",
    },
)

test_graph_builder.add_edge("debugger", "test_runner")

test_debug_agent = test_graph_builder.compile()
