from app.agents.agent_state import AgentState
from app.llm_model import llm
from git import Repo
from github import Github
from langgraph.graph import StateGraph, START, END
from urllib.parse import urlparse
from app.services.ingestion.embedder import _force_remove
import shutil


class GitTools:
    def __init__(self, repo_path: str, token: str):
        self.repo = Repo(repo_path)
        self.client = Github(token)

    def get_diff(self) -> str:
        return self.repo.git.diff()

    def create_branch(self, branch_name: str):
        self.repo.git.checkout("-b", branch_name)

    def commit(self, message: str):
        self.repo.git.add(A=True)
        self.repo.index.commit(message)

    def push(self, branch_name: str):
        origin = self.repo.remote(name="origin")
        origin.push(branch_name)

    def create_pr(
        self, repo_name: str, title: str, body: str, head: str, base: str
    ) -> str:
        repo = self.client.get_repo(repo_name)
        pr = repo.create_pull(title=title, body=body, head=head, base=base)
        return pr.html_url

# ── Git Agent Node ────────────────────────────────────────────────────────────
def git_agent_node(state: AgentState) -> AgentState:
    try:
        git_tools = GitTools(
            repo_path=state["local_repo_path"], token=state["git_token"]
        )

        diff = git_tools.get_diff()

        # Generate commit message
        commit_promt = f"""
            Generate a conventional commit message based on this diff and ticket intent.
            Diff: {diff}\n"
            Ticket Intent: {state['ticket_intent']}\n"
            Respond with ONLY the commit message, nothing else."""

        commit_msg = llm.invoke(commit_promt).content.strip().strip('"')

        # Generate branch name
        branch_name_prompt = f"""
            Generate a git branch name using this format: ticket_type/ticket_id-short-desc
            Ticket Type: {state['ticket_type']}
            Ticket ID: {state['ticket_id']}
            Intent: {state['ticket_intent']}
            Respond with ONLY the branch name, nothing else."""

        branch_name = llm.invoke(branch_name_prompt).content.strip().strip('"')

        # Generate PR title
        pr_title_prompt = f"""
            Generate a clear PR title in 10-14 words based on this diff.
            Diff: {diff}
            Respond with ONLY the PR title, nothing else."""

        pr_title = llm.invoke(pr_title_prompt).content.strip().strip('"')

        # Git operations
        git_tools.create_branch(branch_name)
        git_tools.commit(commit_msg)
        git_tools.push(branch_name)

        # Parse repo name from URL
        repo_name = urlparse(state["repo_url"]).path.strip("/")

        pr_url = git_tools.create_pr(
            repo_name=repo_name,
            title=pr_title,
            body=f"## Summary\n{state['ticket_intent']}\n\n## Type\n{state['ticket_type']}\n\n## Tests Passed\n{state['tests_passed']}",
            head=branch_name,
            base=state["base_branch"],
        )

        return {
            **state,
            "commit_message": commit_msg,
            "pr_title": pr_title,
            "pr_url": pr_url,
        }

    finally:
        # Always cleanup local repo after git agent
        _force_remove(state["local_repo_path"])
        
        
git_graph_builder = StateGraph(AgentState)

git_graph_builder.add_node("git_agent", git_agent_node)

git_graph_builder.add_edge(START, "git_agent")
git_graph_builder.add_edge("git_agent", END)

git_agent = git_graph_builder.compile()