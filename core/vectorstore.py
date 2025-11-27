import os
import uuid
from typing import List, Dict, Tuple
import chromadb
from sentence_transformers import SentenceTransformer
from django.conf import settings


CHROMA_DIR = os.path.join(getattr(settings, "BASE_DIR", "."), "chroma_storage")

_client = None
_collection = None
_model = None


def get_embedding_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def get_chroma_collection():
    global _client, _collection
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_DIR)
    if _collection is None:
        _collection = _client.get_or_create_collection(name="project_docs")  
    return _collection


def embed_texts(texts: List[str]) -> List[List[float]]:
    model = get_embedding_model()
    return model.encode(texts, convert_to_numpy=True).tolist()


def add_chunks_to_chroma(document_id: int, chunks: List[str], 
                         metadata: Dict[str, str] | None = None,) -> List[Tuple[str, str]]:
    """
    Returns list of (chunk_id, chunk_text) for saving into TextChunk.
    """
    collection = get_chroma_collection()
    embeddings = embed_texts(chunks)
    ids = [str(uuid.uuid4()) for _ in chunks]

    docs_metadata = []
    for order, cid in enumerate(ids):
        base = {"document_id": str(document_id), "order": str(order),}
        if metadata:
            base.update(metadata)  # adding new key-value pairs or updating existing ones
        docs_metadata.append(base)
    collection.upsert(ids=ids, documents=chunks, metadatas=docs_metadata, embeddings=embeddings)

    return list(zip(ids, embeddings, chunks))


def search_similar(query: str, n_results: int = 5):
    collection = get_chroma_collection()
    model = get_embedding_model()
    q_emb = model.encode([query], convert_to_numpy=True).tolist()
    res = collection.query(query_embeddings=q_emb, n_results=n_results)
    return res

