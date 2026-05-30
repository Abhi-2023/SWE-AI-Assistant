from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import APIRouter, Depends, HTTPException
from app.db.database import get_db
from app.db.models.repository import Repository
from app.db.models.user import User
from app.db.models.message import Message
from app.db.models.conversation import Conversation
from app.api.routes.auth import get_current_user
from app.core.config import get_settings
from app.services.streaming import conversation_graph, sse
from fastapi.responses import StreamingResponse

settings = get_settings()
router   = APIRouter(prefix='/chat', tags=['chat'])


class ChatRequest(BaseModel):
    message:          str
    vector_namespace: str | None = None
    conversation_id:  str | None = None  # None = new conversation


@router.post("/send")
async def send_message(
    payload:      ChatRequest,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_user),
):
    # ── Resolve repo from namespace ───────────────────────
    repo = None
    if payload.vector_namespace:
        result = await db.execute(
            select(Repository).where(
                Repository.vector_namespace == payload.vector_namespace,
                Repository.user_id         == current_user.id,
            )
        )
        repo = result.scalar_one_or_none()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

    # ── Continue existing or create new conversation ──────
    if payload.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id      == payload.conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conversation.status = "running"
        await db.commit()
    else:
        conversation = Conversation(
            user_id            = current_user.id,
            repo_id            = repo.id if repo else None,
            status             = "running",
            ticket_description = payload.message,
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

    # ── Fetch message history from this conversation ──────
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
    )
    history = [
        {"role": m.role, "content": m.content}
        for m in result.scalars().all()
    ]

    # ── Save user message ─────────────────────────────────
    db.add(Message(
        conversation_id = conversation.id,
        role            = "user",
        content         = payload.message,
    ))
    await db.commit()

    # ── Build initial state ───────────────────────────────
    initial_state = {
        "user_id":             current_user.id,
        "user_message":        payload.message,
        "vector_namespace":    repo.vector_namespace if repo else None,
        "chat_history":        history,
        "mode":                "",
        "routing_reasoning":   "",
        "repo_url":            repo.github_url if repo else "",
        "local_repo_path":     "",
        "ticket_id":           conversation.id,
        "ticket_desc":         payload.message,
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
        "llm_response":        None,
        "conversation_id":     conversation.id,
    }

    # ── Stream ────────────────────────────────────────────
    async def stream(db: AsyncSession):
        try:
            agent_steps = []

            async for event in conversation_graph.astream(initial_state):
                for node_name, node_state in event.items():
                    step = {
                        "type":   "step",
                        "agent":  node_name,
                        "status": "complete",
                    }
                    agent_steps.append(step)
                    yield sse(step)

            final = node_state

            # Update conversation
            conversation.mode        = final.get("mode", "general")
            conversation.ticket_type = final.get("ticket_type")
            conversation.status      = "completed"
            db.add(conversation)

            # Save assistant message
            db.add(Message(
                conversation_id = conversation.id,
                role            = "assistant",
                content         = final.get("llm_response") or final.get("pr_url") or "Done.",
                pr_url          = final.get("pr_url"),
                agent_steps     = agent_steps,
                files_changed   = final.get("files_to_modify", []),
            ))
            await db.commit()

            # Emit final event
            if final.get("pr_url"):
                yield sse({
                    "type":          "pr",
                    "pr_url":        final["pr_url"],
                    "pr_title":      final.get("pr_title", ""),
                    "files_changed": final.get("files_to_modify", []),
                    "tests_passed":  final.get("tests_passed", False),
                })
            elif final.get("llm_response"):
                yield sse({
                    "type":    "message",
                    "content": final["llm_response"],
                })

            yield sse({"type": "done"})

        except Exception as e:
            conversation.status = "failed"
            db.add(conversation)
            await db.commit()
            yield sse({"type": "error", "detail": str(e)})
            yield sse({"type": "done"})

    return StreamingResponse(
        stream(db=db),
        media_type = "text/event-stream",
        headers    = {
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/conversations")
async def get_user_conversations(
    user: User         = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
    )
    return [
        {
            "conversation_id":    c.id,
            "ticket_description": c.ticket_description,
            "ticket_type":        c.ticket_type,
            "mode":               c.mode,
            "status":             c.status,
            "created_at":         c.created_at,
        }
        for c in result.scalars().all()
    ]


@router.get("/conversation/{conversation_id}/messages")
async def get_messages_by_conversation_id(
    conversation_id: str,
    user: User         = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id      == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return [
        {
            "id":            m.id,
            "role":          m.role,
            "content":       m.content,
            "pr_url":        m.pr_url,
            "agent_steps":   m.agent_steps,
            "files_changed": m.files_changed,
            "created_at":    m.created_at,
        }
        for m in result.scalars().all()
    ]


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: User         = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id      == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete(conversation)  # cascades to messages
    await db.commit()
    return {"status": "deleted", "conversation_id": conversation_id}