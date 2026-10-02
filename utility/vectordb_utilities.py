import chromadb

client = chromadb.PersistentClient()

docs_collection = client.get_or_create_collection("notes_embedding")


def ingest_embeddings(ids, embeddings, documents, metadatas):
    docs_collection.upsert(
        ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas
    )


def fetch_similar_results(embeds, n_results=3):
    return docs_collection.query(query_embeddings=embeds, n_results=n_results)
