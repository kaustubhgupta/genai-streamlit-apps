import chromadb

client = chromadb.PersistentClient()

fixed_chunking_collection = client.get_or_create_collection("fixed_chunking")
recursive_chunking_collection = client.get_or_create_collection("recursive_chunking")

collection_mapping = {
    "fixed": fixed_chunking_collection,
    "recursive": recursive_chunking_collection,
}


def ingest_embeddings(ids, embeddings, documents, metadatas, strategy, doc_name):
    collection = collection_mapping.get(strategy)
    if collection is None:
        raise ValueError("strategy must be 'fixed' or 'recursive'")

    collection.delete(where={"doc_name": {"$in": doc_name}})

    collection.upsert(
        ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas
    )


def de_ingest_embeddings(strategy, doc_name):
    collection = collection_mapping.get(strategy)
    if collection is None:
        raise ValueError("strategy must be 'fixed' or 'recursive'")

    collection.delete(where={"doc_name": {"$in": doc_name}})


def list_docs_in_collection(strategy):
    collection = collection_mapping.get(strategy)
    if collection is None:
        raise ValueError("strategy must be 'fixed' or 'recursive'")

    all_docs = collection.get(include=["metadatas"])
    doc_names = set()
    for metadata in all_docs.get("metadatas") or []:
        doc_name = (metadata or {}).get("doc_name")
        if isinstance(doc_name, str):
            doc_names.add(doc_name.replace("\\", "/").rsplit("/", 1)[-1])
    return sorted(doc_names)


def fetch_similar_results(embeds, n_results=3, strategy="recursive"):
    collection = collection_mapping.get(strategy)
    if collection is None:
        raise ValueError("strategy must be 'fixed' or 'recursive'")

    return collection.query(query_embeddings=embeds, n_results=n_results)


def fetch_docs_for_keyword_search(strategy):
    collection = collection_mapping.get(strategy)
    if collection is None:
        raise ValueError("strategy must be 'fixed' or 'recursive'")

    all_docs = collection.get(include=["documents", "metadatas"])
    return all_docs
