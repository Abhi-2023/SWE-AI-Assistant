import os
import tempfile
from celery import Celery
from app.core.config import get_settings
from app.services.ingestion.qdrant_ingestion_service import (
    _force_remove,
    _chunk_text,
    SUPPORTED_EXTENSIONS,
)
from app.services.ingestion.embedder import upsert_chunk_embeddings, deleted_chunks_embeddings
from git import Repo

settings = get_settings()

# ── Celery app 
celery_app = Celery(
    "forge",
    broker  = settings.redis_url,
    backend = settings.redis_url,
)

celery_app.conf.update(
    task_serializer         = "json",
    result_serializer       = "json",
    accept_content          = ["json"],
    timezone                = "UTC",
    task_acks_late          = True,   # ack after task completes, not before
    worker_prefetch_multiplier = 1,   # one task at a time per worker
)


# ── Helper: clone repo ────────────────────────────────────
def _clone_repo_for_sync(github_url: str, user_id: str, repo_id: str) -> str:
    clone_path = os.path.join(
        tempfile.gettempdir(), "forge_sync", user_id, repo_id
    )
    if os.path.exists(clone_path):
        _force_remove(clone_path)

    auth_url = github_url.replace(
        "https://", f"https://{settings.github_token}@"
    )
    Repo.clone_from(auth_url, clone_path)
    return clone_path


# ── Helper: chunk a single file ───────────────────────────
def _chunk_single_file(
    file_path:  str,
    clone_path: str,
    repo_name:  str,
) -> list:
    ext      = os.path.splitext(file_path)[1].lower()
    language = SUPPORTED_EXTENSIONS.get(ext)

    if not language:
        return []

    abs_path = os.path.join(clone_path, file_path)
    if not os.path.exists(abs_path):
        return []

    try:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception:
        return []

    if not text.strip():
        return []

    return _chunk_text(text, abs_path, language, repo_name, clone_path)


# ── Main task ─
@celery_app.task(
    name                = "re_embed_files",
    bind                = True,
    max_retries         = 3,
    default_retry_delay = 60,
)
def re_embed_files_task(
    self,
    repo_id:          str,
    vector_namespace: str,
    github_url:       str,
    user_id:          str,
    changed_files:    list,
    deleted_files:    list,
):
    clone_path = None
    try:
        repo_name  = github_url.rstrip("/").split("/")[-1]

        print(f"[Worker] Syncing {repo_name} — "
              f"{len(changed_files)} changed, {len(deleted_files)} deleted")

        # Step 1 — Clone latest repo
        clone_path = _clone_repo_for_sync(github_url, user_id, repo_id)

        # Step 2 — Delete removed files from Qdrant
        for file_path in deleted_files:
            deleted_chunks_embeddings(
                collection_name = vector_namespace,
                file_path       = file_path,
            )
            print(f"[Worker] Deleted: {file_path}")

        # Step 3 — Delete old chunks + re-embed changed files
        all_chunks = []
        for file_path in changed_files:
            deleted_chunks_embeddings(
                collection_name = vector_namespace,
                file_path       = file_path,
            )
            chunks = _chunk_single_file(file_path, clone_path, repo_name)
            all_chunks.extend(chunks)
            print(f"[Worker] Re-chunked {file_path} → {len(chunks)} chunks")

        # Step 4 — Upsert new chunks
        if all_chunks:
            total = upsert_chunk_embeddings(all_chunks, vector_namespace)
            print(f"[Worker] Upserted {total} chunks → {vector_namespace}")

        # Step 5 — Update last_synced_at
        _update_last_synced(repo_id)

        print(f"[Worker] Sync complete for {repo_name}")
        return {
            "status":          "complete",
            "repo_id":         repo_id,
            "chunks_upserted": len(all_chunks),
            "files_deleted":   len(deleted_files),
        }

    except Exception as e:
        print(f"[Worker] Error: {str(e)}")
        raise self.retry(exc=e) from e

    finally:
        if clone_path and os.path.exists(clone_path):
            _force_remove(clone_path)


# ── Update last_synced_at (sync SQLAlchemy for Celery) ────
def _update_last_synced(repo_id: str):
    from datetime import datetime, timezone
    from sqlalchemy import create_engine, update
    from app.db.models.repository import Repository

    sync_url = settings.database_url.replace(
        "postgresql+asyncpg", "postgresql+psycopg2"
    )
    engine = create_engine(sync_url)
    with engine.begin() as conn:
        conn.execute(
            update(Repository)
            .where(Repository.id == repo_id)
            .values(last_synced_at=datetime.now(timezone.utc))
        )
    engine.dispose()