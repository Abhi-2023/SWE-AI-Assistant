from langchain_core.messages import SystemMessage, HumanMessage
import json, os
from langgraph.graph import StateGraph, START, END
from app.agents.agent_state import AgentState
from app.llm_model import llm
from git import Repo
from github import Github

def write_files_to_disk(code_changes: dict[str, str], local_repo_path: str):
    for file_path, content in code_changes.items():
        full_path = os.path.join(local_repo_path, file_path)
        if dir_path := os.path.dirname(full_path):
            os.makedirs(dir_path, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)


def code_writer_node(state: AgentState):

    # Step 1 — Clone repo if not already cloned
    local_dir = state["local_repo_path"]
    if not os.path.exists(local_dir):
        auth_url = state["repo_url"].replace(
            "https://", f"https://{state['git_token']}@"
        )
        Repo.clone_from(auth_url, local_dir)
        print("Repository cloned successfully.")
    else:
        print("Repository already exists locally.")

    # Step 2 — Build prompts
    system_prompt = """
        You are a senior software engineer who implements features and fixes bugs.
        Work according to the implementation plan using the retrieved context.

        Respond ONLY in valid JSON:
        {
            "files_to_modify": ["src/auth/service.py", "src/middleware.py"],
            "code_changes": {
                "src/auth/service.py": "complete file content here",
                "src/middleware.py": "complete file content here"
            }
        }

        Rules:
        - Always return COMPLETE file content, never partial snippets
        - Use full relative paths from repo root
        - Follow existing code style from retrieved context
        - Only implement what the ticket intent and plan indicate
        - Return ONLY valid JSON, no extra text
        """

    context_text = chr(10).join([doc["text"] for doc in state["retrieved_context"]])
    file_paths = list({doc["file_path"] for doc in state["retrieved_context"]})

    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""
                Ticket Type: {state['ticket_type']}
                Ticket Intent: {state['ticket_intent']}

                Implementation Plan:
                {chr(10).join(state['implementation_plan'])}

                Relevant File Paths:
                {file_paths}

                Retrieved Context:
                {context_text}
                """),
        ]
    ).content.strip()

    # Step 3 — Parse response
    if response.startswith("```"):
        response = response.split("```")[1]
        if response.startswith("json"):
            response = response[4:]

    result = json.loads(response.strip())

    # Step 4 — Write files to disk
    write_files_to_disk(result["code_changes"], local_dir)

    return {
        **state,
        "files_to_modify": result["files_to_modify"],
        "code_changes": result["code_changes"],
    }


code_writer_graph = StateGraph(AgentState)
code_writer_graph.add_node("code_writer_node", code_writer_node)
code_writer_graph.add_edge(START, "code_writer_node")
code_writer_graph.add_edge("code_writer_node", END)
code_writer_agent = code_writer_graph.compile()
