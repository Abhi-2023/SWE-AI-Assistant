from app.core.config import get_settings
from fastembed import TextEmbedding, SparseEmbedding
from app.services.ingestion.qdrant_ingestion_service import CodeChunk
from qdrant_client import QdrantClient, models
import uuid
from app.services.ingestion.qudrant_setup import get_client
settings = get_settings()

DENSE_MODEL = "sentence-transfomers/all-MiniLM-L6-v2"
SPARSE_MODEL = "Qdrant/bm25"
BATCH_SIZE = 100

_dense_model : TextEmbedding = None
_sparse_model : SparseEmbedding = None

def _get_dense_model() -> TextEmbedding:
    global _dense_model
    if _dense_model is None:
        _dense_model = TextEmbedding(DENSE_MODEL)
        
    return _dense_model

def _get_sparse_model() -> SparseEmbedding:
    global _sparse_model
    if _sparse_model is None:
        _sparse_model = SparseEmbedding(SPARSE_MODEL)
        
    return _sparse_model


def _embed_batch(chunks : list[CodeChunk]) -> list[models.PointStruct]:
    texts = [chunk.text for chunk in chunks]
    
    _dense_model = _get_dense_model()
    _sparse_model = _get_sparse_model()
    
    dense_vector = list(_dense_model.embed(texts))
    sparse_vector = list(_sparse_model.embed(texts))
    points = []
    for chunk, dense_vec, sparse_vec in zip(chunks, dense_vector, sparse_vector):
        point= models.PointStruct(
            id= str(uuid.uuid4()),
            payload={
                "text" : chunk.text,
                "file_path" : chunk.file_path,
                "start_line" : chunk.start_line,
                "end_line": chunk.end_line,
                "repo_name":chunk.repo_name,
                "language": chunk.language
            },
            vector={
                "dense" : dense_vec.tolist(),
                "sparse" : models.SparseVector(
                    indices=sparse_vec.indices.tolist(),
                    values = sparse_vec.values.tolist()
                )
            }
        )
        
        points.append(point)
        
    return points

def upsert_chunk_embeddings(chunks: list[CodeChunk], collection_name: str) -> int:
    cliet = get_client()
    
    total_upserted = 0
    
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i+BATCH_SIZE]
        embedded_batch = _embed_batch(batch)
        
        cliet.upsert(collection_name=collection_name, points = embedded_batch)
        
        total_upserted+=len(embedded_batch)
        
    return total_upserted

def deleted_chunks_embeddings(collection_name:str, file_path: str) -> None:
    client = get_client()
    
    client.delete(collection_name=collection_name, points_selector= models.FilterSelector(
        filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="file_path",
                    match=models.MatchValue(value=file_path)
                )
            ]
        )
    ))