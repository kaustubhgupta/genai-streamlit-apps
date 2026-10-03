from utility.utilities.embedding_chunking_utilities import (
    generate_single_sentence_embeddings,
)
from utility.utilities.vectordb_utilities import fetch_similar_results
import os

CHUNK_SIZE_FILTER_THRESHOLD = int(os.environ.get("CHUNK_SIZE_FILTER_THRESHOLD"))
VECTOR_SEARCH_CHUNK_THRESHOLD = int(os.environ.get("VECTOR_SEARCH_CHUNK_THRESHOLD"))
RERANK_TOP_K = int(os.environ.get("RERANK_TOP_K"))


def query_rag_documents(
    user_input,
    chunked_data_type,
    rerank_flag,
    CHUNK_SIZE_FILTER_THRESHOLD=CHUNK_SIZE_FILTER_THRESHOLD,
    VECTOR_SEARCH_CHUNK_THRESHOLD=VECTOR_SEARCH_CHUNK_THRESHOLD,
    RERANK_TOP_K=RERANK_TOP_K,
):
    """Retrieve and assemble relevant RAG chunks for a user query on everything related to bootcamp content.

    This tool converts the input question into embeddings, searches the vector store
    for the nearest chunks using the selected strategy, filters out chunks below a
    configured length threshold, optionally reranks the remaining chunks, and returns
    a newline-delimited context string that includes per-chunk scores and source
    document names.

    Args:
        user_input (str): The natural-language question or instruction to answer.
        chunked_data_type (str): can take these 2 vales -> "fixed" or "recursive"
        rerank_flag (bool): Whether to rerank the filtered chunk results before
            returning them. Try with rerank_flag=False first, and if the results are not satisfactory, set rerank_flag=True.
        CHUNK_SIZE_FILTER_THRESHOLD (int, optional): Minimum chunk length required for
            inclusion. Defaults to the module-level threshold.
        VECTOR_SEARCH_CHUNK_THRESHOLD (int, optional): Maximum number of candidate chunks
            to retrieve from the vector database. Defaults to the module-level threshold.
        RERANK_TOP_K (int, optional): Maximum number of reranked chunks to keep in the
            final result. Defaults to the module-level value.

    Returns:
        str: A formatted string containing each selected chunk, a score label, and the
            source document names, with one chunk per line.

    Example:
        query_rag_documents(
            user_input="How an LLM is trained?",
            chunked_data_type="recursive",
            rerank_flag=True,
        )
    """

    user_input_embeddings = generate_single_sentence_embeddings(
        user_input,
    )

    similar_chunks = fetch_similar_results(
        user_input_embeddings,
        n_results=VECTOR_SEARCH_CHUNK_THRESHOLD,
        strategy=chunked_data_type,
    )
    similar_docs = similar_chunks["documents"][0]
    similar_metadatas = similar_chunks.get("metadatas", [[]])[0]
    document_names = {}
    for document, metadata in zip(similar_docs, similar_metadatas):
        document_names.setdefault(document, set()).add(
            (metadata or {}).get("doc_name", "Unknown document")
        )
    filtered_similar_docs = [
        document
        for document in similar_docs
        if len(document) > CHUNK_SIZE_FILTER_THRESHOLD
    ]
    if rerank_flag:
        from utility.utilities.chunk_reranker import rerank_docs

        final_docs = rerank_docs(user_input, filtered_similar_docs, RERANK_TOP_K)
    else:
        final_docs = [
            {"document": document, "score": "NA"} for document in filtered_similar_docs
        ]

    final_additional_context = ""
    for doc in final_docs:
        sources = ", ".join(
            sorted(document_names.get(doc["document"], {"Unknown document"}))
        )
        final_additional_context += (
            f"Chunk Score {doc['score'] if rerank_flag else 'NA since it is not ranked'} (Document: {sources}): "
            f"{doc['document']}\n"
        )

    return final_additional_context


RAG_QUERY_TOOLS = [
    {
        "type": "function",
        "name": "query_rag_documents",
        "description": "Retrieve and assemble relevant RAG chunks for a user query.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_input": {
                    "type": "string",
                    "description": "The natural-language question or instruction to answer.",
                },
                "chunked_data_type": {
                    "type": "string",
                    "description": "can take these 2 vales -> 'fixed' or 'recursive'",
                },
                "rerank_flag": {
                    "type": "boolean",
                    "description": "Whether to rerank the filtered chunk results before returning them.",
                },
                "CHUNK_SIZE_FILTER_THRESHOLD": {
                    "type": "integer",
                    "description": "Minimum chunk length required for inclusion.",
                },
                "VECTOR_SEARCH_CHUNK_THRESHOLD": {
                    "type": "integer",
                    "description": "Maximum number of candidate chunks to retrieve from the vector database.",
                },
                "RERANK_TOP_K": {
                    "type": "integer",
                    "description": "Maximum number of reranked chunks to keep in the final result.",
                },
            },
            "required": ["user_input", "chunked_data_type", "rerank_flag"],
        },
    }
]

RAG_TOOLS_MAPPING = {
    "query_rag_documents": query_rag_documents,
}
