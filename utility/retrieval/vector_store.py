import chromadb

client = chromadb.PersistentClient()

fixed_chunking_collection = client.get_or_create_collection("fixed_chunking")
recursive_chunking_collection = client.get_or_create_collection("recursive_chunking")

collection_mapping = {
    "fixed": fixed_chunking_collection,
    "recursive": recursive_chunking_collection,
}


def _get_collection(strategy):
    collection = collection_mapping.get(strategy)
    if collection is None:
        raise ValueError("strategy must be 'fixed' or 'recursive'")
    return collection


def ingest_embeddings(ids, embeddings, documents, metadatas, strategy, doc_name):
    collection = _get_collection(strategy)
    collection.delete(where={"doc_name": {"$in": doc_name}})
    collection.upsert(
        ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas
    )


def de_ingest_embeddings(strategy, doc_name):
    _get_collection(strategy).delete(where={"doc_name": {"$in": doc_name}})


def list_docs_in_collection(strategy):
    all_docs = _get_collection(strategy).get(include=["metadatas"])
    doc_names = set()
    for metadata in all_docs.get("metadatas") or []:
        doc_name = (metadata or {}).get("doc_name")
        if isinstance(doc_name, str):
            doc_names.add(doc_name.replace("\\", "/").rsplit("/", 1)[-1])
    return sorted(doc_names)


def fetch_similar_results(embeds, n_results=3, strategy="recursive"):
    return _get_collection(strategy).query(query_embeddings=embeds, n_results=n_results)


def fetch_docs_for_keyword_search(strategy):
    return _get_collection(strategy).get(include=["documents", "metadatas"])


def fetch_docs_by_filename(file_name, strategy):
    return _get_collection(strategy).get(
        where={"doc_name": {"$in": [file_name]}},
        include=["documents", "metadatas"],
    )
