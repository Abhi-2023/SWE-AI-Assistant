import os
import shutil
from dataclasses import dataclass
from git import Repo
from app.core.config import get_settings

settings = get_settings()

SUPPORTED_EXTENSIONS = {
    ".py":   "python",
    ".js":   "javascript",
    ".ts":   "typescript",
    ".java": "java",
    ".go":   "golang",
}

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__",
    ".venv", "venv", "myvenv", "dist", "build", ".idea", ".vscode"
}

CHUNK_SIZE    = 400   # tokens (approx chars / 4)
CHUNK_OVERLAP = 80


@dataclass
class CodeChunk:
    text:       str
    file_path:  str
    start_line: int
    end_line:   int
    language:   str
    repo_name:  str


def clone_repo(github_url: str, user_id: str) -> tuple[str, str]:
    """
    Clone a GitHub repo to /tmp/forge/{user_id}/{repo_name}.
    Returns (clone_path, repo_name).
    """
    repo_name  = github_url.rstrip("/").split("/")[-1].replace(".git", "")
    clone_path = os.path.join("/tmp", "forge", user_id, repo_name)

    if os.path.exists(clone_path):
        shutil.rmtree(clone_path)

    auth_url = github_url
    if settings.github_token:
        # inject token for private repos
        auth_url = github_url.replace(
            "https://", f"https://{settings.github_token}@"
        )

    Repo.clone_from(auth_url, clone_path)
    return clone_path, repo_name


def _walk_source_files(clone_path: str) -> list[tuple[str, str]]:
    """
    Walk the repo, return list of (absolute_path, language)
    for all supported source files.
    """
    results = []
    for root, dirs, files in os.walk(clone_path):
        # prune skip dirs in-place so os.walk doesn't descend into them
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                abs_path = os.path.join(root, filename)
                results.append((abs_path, SUPPORTED_EXTENSIONS[ext]))
    return results


def _chunk_text(
    text:      str,
    file_path: str,
    language:  str,
    repo_name: str,
    clone_path: str,
) -> list[CodeChunk]:
    """
    Split file text into overlapping chunks.
    Chunk boundaries are aligned to line breaks where possible.
    """
    lines = text.splitlines()
    relative_path = os.path.relpath(file_path, clone_path)

    chunks      = []
    char_size    = CHUNK_SIZE    * 4   # ~4 chars per token
    char_overlap = CHUNK_OVERLAP * 4

    current_chars = 0
    chunk_lines:  list[str] = []
    chunk_start:  int       = 1

    for line_no, line in enumerate(lines, start=1):
        chunk_lines.append(line)
        current_chars += len(line) + 1  # +1 for newline

        if current_chars >= char_size:
            chunk_text = "\n".join(chunk_lines)
            chunks.append(CodeChunk(
                text       = chunk_text,
                file_path  = relative_path,
                start_line = chunk_start,
                end_line   = line_no,
                language   = language,
                repo_name  = repo_name,
            ))

            # roll back by overlap amount
            overlap_chars = 0
            rollback_idx  = len(chunk_lines) - 1
            while rollback_idx > 0 and overlap_chars < char_overlap:
                overlap_chars += len(chunk_lines[rollback_idx]) + 1
                rollback_idx  -= 1

            chunk_lines   = chunk_lines[rollback_idx:]
            chunk_start   = line_no - len(chunk_lines) + 1
            current_chars = sum(len(l) + 1 for l in chunk_lines)

    # flush remaining lines as final chunk
    if chunk_lines:
        chunks.append(CodeChunk(
            text       = "\n".join(chunk_lines),
            file_path  = relative_path,
            start_line = chunk_start,
            end_line   = len(lines),
            language   = language,
            repo_name  = repo_name,
        ))

    return chunks


def chunk_repository(clone_path: str, repo_name: str) -> list[CodeChunk]:
    """
    Walk the cloned repo, read all source files, return all chunks.
    """
    all_chunks: list[CodeChunk] = []
    source_files = _walk_source_files(clone_path)

    for file_path, language in source_files:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception:
            continue

        if not text.strip():
            continue

        chunks = _chunk_text(text, file_path, language, repo_name, clone_path)
        all_chunks.extend(chunks)

    return all_chunks


def clone_and_chunk(github_url: str, user_id: str) -> tuple[list[CodeChunk], str, str]:
    """
    Main entry point.
    Returns (chunks, clone_path, repo_name).
    """
    clone_path, repo_name = clone_repo(github_url, user_id)
    chunks = chunk_repository(clone_path, repo_name)
    return chunks, clone_path, repo_name