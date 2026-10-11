from functools import lru_cache

from sentence_transformers import CrossEncoder


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    return CrossEncoder("BAAI/bge-reranker-v2-m3")


def warmup() -> None:
    """Call once at server startup so the first tool call isn't slow."""
    get_reranker().predict([["warmup", "warmup"]])


def rerank_docs(query, docs, top_k=3):
    if not docs:
        return []
    scores = get_reranker().predict([[query, doc] for doc in docs])
    ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
    return [{"document": doc, "score": float(score)} for doc, score in ranked[:top_k]]
