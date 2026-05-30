
from langchain_core.messages import SystemMessage, HumanMessage
from qdrant_client import QdrantClient
from qdrant_client.models import Prefetch, Fusion, FusionQuery
from fastembed import TextEmbedding
from langgraph.graph import StateGraph, START, END
import os
import json, cohere
from app.agents.agent_state import AgentState
from app.llm_model import llm
from fastembed.sparse.bm25 import Bm25
from app.services.ingestion.qudrant_setup import get_client
from app.core.config import get_settings
from app.agents.utils import parse_llm_json


settings = get_settings()

DENSE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SPARSE_MODEL = "Qdrant/bm25"
BATCH_SIZE = 100
cohere_client = cohere.Client(api_key=settings.cohere_api_key)

def ticket_classifier(state: AgentState):
    if state['ticket_type'] == 'defect':
        return "defect_planner"
    return "feature_planner"

_dense_model : TextEmbedding = None
_sparse_model : Bm25 = None

def _get_dense_model() -> TextEmbedding:
    global _dense_model
    if _dense_model is None:
        _dense_model = TextEmbedding(DENSE_MODEL)
        
    return _dense_model

def _get_sparse_model() -> Bm25:
    global _sparse_model
    if _sparse_model is None:
        _sparse_model = Bm25(SPARSE_MODEL)
        
    return _sparse_model

def query_context_retrieval(vector_namespace: str, ticket_intent: str, top_k : int = 6):
    
    client = get_client()
    dense_model = _get_dense_model()
    sparse_model = _get_sparse_model()
    dense_vector = list(dense_model.embed([ticket_intent]))[0].tolist()
    sparse_result = list(sparse_model.embed([ticket_intent]))[0]
    from qdrant_client.models import SparseVector
    sparse_vector = SparseVector(
        indices = sparse_result.indices.tolist(),
        values  = sparse_result.values.tolist(),
    )
    results = client.query_points(
        collection_name=vector_namespace,
        prefetch=[
            Prefetch(query=dense_vector, using='dense', limit=20),
            Prefetch(query=sparse_vector, using='sparse', limit=20),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=35
    )
    
    docs=[]
    seen = set()
    for points in results.points:
        text = points.payload['text']
        if text in seen:
            continue
        
        seen.add(text)
        docs.append({
            'text':text,
            'file_path': points.payload['file_path'],
            'score': points.score
        })
        
    re_ranked_docs = cohere_client.rerank(
        query=ticket_intent,
        model='rerank-english-v3.0',
        documents=[doc['text'] for doc in docs],
        top_n=top_k
    )
    
    return [docs[doc.index] for doc in re_ranked_docs.results]


def planner_node(state: AgentState):
    retrieved_context = query_context_retrieval(state['vector_namespace'], state['ticket_intent'])
    context_text = chr(10).join([doc['text'] for doc in retrieved_context])

    system_prompt = """
        You are a senior software engineer responsible for analyzing software tickets and creating implementation plans.

        The ticket may represent:
        - a defect/bug fix
        - a new feature request

        Given:
        - the ticket description
        - ticket intent
        - relevant codebase context

        Generate a precise implementation plan.

        Respond ONLY in valid JSON:

        {
            "implementation_plan": [
                "Step 1: ...",
                "Step 2: ...",
                "Step 3: ..."
            ]
        }

        Rules:
        - If the ticket is a defect:
        - First identify the root cause
        - Then describe the required fixes

        - If the ticket is a feature:
        - First identify where the feature integrates into the existing codebase
        - Then describe the required implementation steps

        - Always reference relevant:
        - file names
        - classes
        - functions
        - modules
        from the provided context

        - Steps must be:
        - ordered
        - actionable
        - implementation-specific

        - Avoid vague statements like:
        - "update the code"
        - "fix the bug"

        - Focus only on implementation planning.
        - Do not generate code.
        - Return ONLY valid JSON.
        """
    response = llm.invoke([SystemMessage(content=system_prompt),
                           HumanMessage(content=f"""
                                        Ticket Type: {state['ticket_type']}
                                        Ticket Intent: {state['ticket_intent']}

                                        Retrieved Codebase Context:
                                        {context_text}
                                        """)]).content.strip().strip("")
    result = parse_llm_json(response)
    
    return {
        **state,
        'retrieved_context': retrieved_context,
        'implementation_plan': result['implementation_plan']
    }

planner_graph = StateGraph(AgentState)

planner_graph.add_node("planner_node", planner_node)
planner_graph.add_edge(START, 'planner_node')
planner_graph.add_edge('planner_node', END)
planner_agent = planner_graph.compile()