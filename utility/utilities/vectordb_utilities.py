import chromadb

client = chromadb.PersistentClient()

fixed_chunking_collection = client.get_or_create_collection("fixed_chunking")
recursive_chunking_collection = client.get_or_create_collection("recursive_chunking")


def ingest_embeddings(ids, embeddings, documents, metadatas, strategy):
    if strategy == "fixed":
        collection = fixed_chunking_collection
    elif strategy == "recursive":
        collection = recursive_chunking_collection
    else:
        raise ValueError("strategy must be 'fixed' or 'recursive'")

    collection.upsert(
        ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas
    )


def fetch_similar_results(embeds, n_results=3, strategy="recursive"):
    if strategy == "fixed":
        collection = fixed_chunking_collection
    elif strategy == "recursive":
        collection = recursive_chunking_collection
    else:
        raise ValueError("strategy must be 'fixed' or 'recursive'")

    return collection.query(query_embeddings=embeds, n_results=n_results)


def fetch_docs_for_keyword_search(strategy):
    if strategy == "fixed":
        collection = fixed_chunking_collection
    elif strategy == "recursive":
        collection = recursive_chunking_collection
    else:
        raise ValueError("strategy must be 'fixed' or 'recursive'")

    all_docs = collection.get(include=["documents", "metadatas"])
    return all_docs
