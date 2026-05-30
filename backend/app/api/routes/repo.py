from pydantic import BaseModel, HttpUrl, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from fastapi import APIRouter, Depends, HTTPException, status
from app.db.database import get_db
from app.db.models.repository import Repository
from app.core.security import get_current_user
from app.services.ingestion.qudrant_setup import get_collection_name, delete_collection
from app.services.ingestion.pipeline import run_ingestion

router = APIRouter(prefix='/repo', tags=['repo'])

class IngestRequest(BaseModel):
    github_url: HttpUrl
    sync_branch : str = "main"
    
    @field_validator("github_url")
    @classmethod
    def validate_github_url(cls, v: HttpUrl)-> str:
        url = str(v).rstrip("/").replace(".git", "")
        parts = url.replace("https://github.com/", "").split("/")
        if v.host != "github.com" or len(parts) < 2 or not all(parts[:2]):
            raise ValueError("Must be a valid GitHub repo URL: https://github.com/owner/repo")
        return url

class IngestResponse(BaseModel):
    repo_id: str
    vector_namespace: str
    chunks_indexed: int
    status: str
    
class DeletedResponse(BaseModel):
    repo_name: str
    vector_namespace: str
    status: str
    
def extract_repo_name(repo_url: str) -> str:
    return repo_url.rstrip("/").split("/")[-1].replace(".git", "")



@router.post("/ingestion", response_model=IngestResponse)
async def ingest_repo(body: IngestRequest, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    repo_name = extract_repo_name(body.github_url)

    result = await db.execute(select(Repository).where(Repository.github_url == body.github_url, Repository.user_id == user.id))

    if result.scalar_one_or_none():
        raise HTTPException(
            status_code = 400,
            detail      = f"Repo '{repo_name}' already ingested. Use re-index to update."
        )

    vector_namespace = get_collection_name(user_id=user.id, repo_name = repo_name)

    repo = Repository(
        user_id = user.id,
        github_url = body.github_url,
        vector_namespace=vector_namespace,
        sync_branch = body.sync_branch
    )

    db.add(repo)
    await db.commit()
    await db.refresh(repo)

    try:
        result = run_ingestion(body.github_url, user.id)
    except Exception as e:
        await db.delete(repo)
        await db.commit()
        raise HTTPException(
            status_code=500, detail=f"Ingestion failed: {str(e)}"
        ) from e
    
    from datetime import datetime, timezone
    repo.last_synced_at = datetime.now(timezone.utc)
    await db.commit()
    
    return {
        "repo_id": repo.id,
        "vector_namespace": vector_namespace,
        "chunks_indexed": result['chunks_indexed'],
        "status": result['status']
    }
    
@router.delete("/delete-repo")
async def delete_repo(body: IngestRequest, user= Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    repo_name = extract_repo_name(body.github_url)

    result = await db.execute(select(Repository).where(Repository.github_url == body.github_url, Repository.user_id == user.id))

    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code = 400,
            detail      = f"Repo '{repo_name}' Does not exist."
        )

    try:
        vector_namespace = delete_collection(user_id=user.id, repo_name=repo_name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error deleting repository",
        ) from e
        
    await db.delete(repo)
    await db.commit()
        
    return {
        "repo_name": repo_name,
        "vector_namespace": vector_namespace,
        "status": "Deleted"
    }
        
    
    
    
    
@router.get('/list_repo')
async def get_user_repos(user= Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = db.execute(select(Repository).where(Repository.user_id == user.id))
    repos = result.scalars().all()
    
    return [
        {
            "repo_id":          r.id,
            "github_url":       r.github_url,
            "vector_namespace": r.vector_namespace,
            "last_synced_at":   r.last_synced_at,
        }
        for r in repos
    ]
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    