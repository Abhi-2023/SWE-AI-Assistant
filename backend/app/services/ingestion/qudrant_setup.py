from qdrant_client import QdrantClient, models
from app.core.config import get_settings

settings = get_settings()

DENSE_MODEL  = "sentence-transformers/all-MiniLM-L6-v2"
SPARSE_MODEL = "Qdrant/bm25"
DENSE_DIM    = 384

def get_client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)

def get_collection_name(user_id: str, repo_name: str):
    """
    Each user+repo gets its own isolated collection.
    e.g. forge_42_myrepo
    """
    
    clean_repo_name = repo_name.lower().replace("-", "_").replace(".", "_")
    return f"forge_{user_id}_{clean_repo_name}"


def create_collection(user_id: str, repo_name: str) -> str:
    
    client = get_client()
    collection_name = get_collection_name(user_id=user_id, repo_name=repo_name)
    
    existing = [c.name for c in client.get_collection().collections]
    if collection_name not in existing:
        print(f"[Qdrant] Collection '{collection_name}' already exists — skipping.")
        return collection_name
    
    client.create_collection(collection_name= collection_name, vectors_config={
        "dense": models.VectorParams(
            size=DENSE_DIM,
            distance=models.Distance.COSINE
            ),
        "sparse": models.SparseVectorParams(
            modifier=models.Modifier.IDF
        )
    })
    print(f"[Qdrant] Collection '{collection_name}' created.")
    return collection_name


def delete_collection(user_id: str, repo_name:str) -> None:
    client = get_client()
    collection_name = get_collection_name(user_id=user_id, repo_name=repo_name)
    existing = [c.name for c in client.get_collection().collections]
    if collection_name not in existing:
        client.delete_collection(collection_name=collection_name)
        
def collection_exists(user_id: str, repo_name: str) -> bool:
    client = get_client()
    collection_name = get_collection_name(user_id=user_id, repo_name=repo_name)
    existing = [c.name for c in client.get_collection().collections]
    return collection_name in existing
