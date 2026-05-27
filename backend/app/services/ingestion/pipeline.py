from app.services.ingestion.qdrant_ingestion_service import clone_and_chunk
from app.services.ingestion.qudrant_setup import create_collection
from app.services.ingestion.embedder import upsert_chunk_embeddings
import shutil

def run_ingestion(gitHub_url: str, user_id: str)-> dict:
    
    chunks, clone_path, repo_name = clone_and_chunk(github_url=gitHub_url, user_id=user_id)
    collection_name = create_collection(user_id=user_id, repo_name=repo_name)
    total = upsert_chunk_embeddings(chunks=chunks, collection_name=collection_name)
    
    shutil.rmtree(clone_path, ignore_errors=True)
    
    return {
        "repo_name": repo_name,
        "collection_name": collection_name,
        "chunks_indexed": total,
        "status":"complete"
    }