from pathlib import Path

from utility.utilities.embedding_chunking_utilities import (
    generate_batch_sentences_embeddings,
    generate_fixed_pdf_chunks,
    generate_fixed_text_chunks,
)
from utility.utilities.vectordb_utilities import ingest_embeddings

pdfs_folder = Path("notes")
texts_folder = Path("session_summaries")

for document in sorted(pdfs_folder.glob("*.pdf")):
    chunked_data = generate_fixed_pdf_chunks(str(document))
    embeddings = generate_batch_sentences_embeddings(chunked_data["chunks"])
    ingest_embeddings(
        chunked_data["ids"],
        embeddings,
        chunked_data["chunks"],
        chunked_data["metadata"],
    )

for document in sorted(texts_folder.glob("*.txt")):
    chunked_data = generate_fixed_text_chunks(str(document))
    embeddings = generate_batch_sentences_embeddings(chunked_data["chunks"])
    ingest_embeddings(
        chunked_data["ids"],
        embeddings,
        chunked_data["chunks"],
        chunked_data["metadata"],
    )
