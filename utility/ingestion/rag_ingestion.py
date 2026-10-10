from pathlib import Path

from utility.utilities.embedding_chunking_utilities import (
    generate_batch_sentences_embeddings,
    generate_fixed_pdf_chunks,
    generate_fixed_text_chunks,
    generate_recursive_pdf_chunks,
    generate_recursive_text_chunks,
)
from utility.utilities.vectordb_utilities import (
    ingest_embeddings,
    de_ingest_embeddings,
    list_docs_in_collection,
)


def ingest_materials(documents, materials_folder):
    materials_folder = Path(materials_folder)
    documents = [Path(document) for document in documents]
    document_names = [str(document) for document in documents]
    chunkers = {
        ".pdf": (generate_fixed_pdf_chunks, generate_recursive_pdf_chunks),
        ".txt": (generate_fixed_text_chunks, generate_recursive_text_chunks),
    }
    strategy_data = {
        "fixed": {"ids": [], "chunks": [], "metadata": []},
        "recursive": {"ids": [], "chunks": [], "metadata": []},
    }

    for document in documents:
        document_chunkers = chunkers.get(document.suffix.lower())
        if document_chunkers is None:
            raise ValueError(f"Unsupported document type: {document}")

        for strategy, chunker in zip(strategy_data, document_chunkers):
            chunked_data = chunker(str(document))
            for key in ("ids", "chunks", "metadata"):
                strategy_data[strategy][key].extend(chunked_data[key])

    for strategy, chunked_data in strategy_data.items():
        if not chunked_data["chunks"]:
            continue
        embeddings = generate_batch_sentences_embeddings(chunked_data["chunks"])
        ingest_embeddings(
            chunked_data["ids"],
            embeddings,
            chunked_data["chunks"],
            chunked_data["metadata"],
            strategy=strategy,
            doc_name=document_names,
        )


def de_ingest_materials(documents, materials_folder):
    materials_folder = Path(materials_folder)
    documents = [Path(document) for document in documents]
    document_names = [str(document) for document in documents]

    for strategy in ["fixed", "recursive"]:
        de_ingest_embeddings(strategy=strategy, doc_name=document_names)


def list_ingested_documents():
    ingested_by_strategy = {
        strategy: set(list_docs_in_collection(strategy))
        for strategy in ("fixed", "recursive")
    }
    ingested_names = set().union(*ingested_by_strategy.values())
    return sorted(ingested_names)
