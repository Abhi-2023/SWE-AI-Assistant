import hmac
import hashlib
import json
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from celery import group

from app.db.database import get_db
from app.db.models.repository import Repository
from app.core.config import get_settings
from app.workers.tasks import re_embed_files_task

settings = get_settings()
router   = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_github_signature(payload_body: bytes, signature_header: str) -> bool:
    if not signature_header:
        return False
    expected = f"sha256={hmac.new(key=settings.github_webhook_secret.encode(), msg=payload_body, digestmod=hashlib.sha256).hexdigest()}"
    return hmac.compare_digest(expected, signature_header)


@router.post("/github")
async def github_webhook(
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    #  Verify signature
    payload_body     = await request.body()
    signature_header = request.headers.get("X-Hub-Signature-256", "")

    if not verify_github_signature(payload_body, signature_header):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    #  Check event type
    event = request.headers.get("X-GitHub-Event", "")
    if event != "push":
        return {"status": "ignored", "event": event}

    #  Parse payload
    payload        = json.loads(payload_body)
    repo_full_name = payload.get("repository", {}).get("full_name")
    pushed_branch  = payload.get("ref", "").replace("refs/heads/", "")
    github_url     = f"https://github.com/{repo_full_name}"

    #  Find all matched repos in DB
    result = await db.execute(
        select(Repository).where(
            Repository.github_url  == github_url,
            Repository.sync_branch == pushed_branch,
        )
    )
    matched_repos = result.scalars().all()

    if not matched_repos:
        return {
            "status": "ignored",
            "reason": f"No repos syncing from branch '{pushed_branch}'",
        }

    #  Collect changed files across all commits
    commits  = payload.get("commits", [])
    added    = set()
    modified = set()
    removed  = set()

    for commit in commits:
        added.update(commit.get("added", []))
        modified.update(commit.get("modified", []))
        removed.update(commit.get("removed", []))

    changed_files = list(added | modified)
    deleted_files = list(removed)

    if not changed_files and not deleted_files:
        return {"status": "ignored", "reason": "no file changes"}

    #  Fire all repo sync tasks in parallel 
    task_group = group(
        re_embed_files_task.s(
            repo_id          = repo.id,
            vector_namespace = repo.vector_namespace,
            github_url       = github_url,
            user_id          = repo.user_id,
            changed_files    = changed_files,
            deleted_files    = deleted_files,
        )
        for repo in matched_repos
    )
    task_group.apply_async()

    return {
        "status":        "queued",
        "repo":          repo_full_name,
        "branch":        pushed_branch,
        "repos_syncing": len(matched_repos),
        "changed_files": len(changed_files),
        "deleted_files": len(deleted_files),
    }