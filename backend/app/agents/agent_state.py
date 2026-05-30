from typing import Literal, TypedDict, Optional


class AgentState(TypedDict):
    # ── User Input ────────────────────────────────────────
    user_id:              str
    user_message:         str
    vector_namespace:     Optional[str]
    
    # ── Chat History ──────────────────────────────────────────
    chat_history: list[dict] 
    
    # ── Router ────────────────────────────────────────────
    mode:                 Literal["rag", "agentic", "general", "no_namespace"]
    routing_reasoning:    str

    # ── Repo ──────────────────────────────────────────────
    repo_url:             str
    local_repo_path:      str

    # ── Ticket ────────────────────────────────────────────
    ticket_id:            str
    ticket_desc:          str

    # ── Classify Agent ────────────────────────────────────
    ticket_type:          Literal["defect", "feature"]
    ticket_intent:        str

    # ── Planner Agent ─────────────────────────────────────
    retrieved_context:    list[dict]
    implementation_plan:  list[str]

    # ── Code Writer Agent ─────────────────────────────────
    files_to_modify:      list[str]
    code_changes:         dict[str, str]

    # ── Test Runner Agent ─────────────────────────────────
    test_results:         str
    tests_passed:         bool

    # ── Debugger Agent ────────────────────────────────────
    error_log:            str
    retry_count:          int
    max_retries:          int

    # ── Git Agent ─────────────────────────────────────────
    base_branch:          str
    git_token:            str
    commit_message:       str
    pr_title:             str
    pr_url:               Optional[str]

    # ── LLM Response (general + rag modes) ────────────────
    llm_response:         Optional[str]

    # ── Conversation tracking ─────────────────────────────
    conversation_id:      str