from pathlib import Path

from utility.utilities.embedding_chunking_utilities import (
    generate_batch_sentences_embeddings,
    generate_fixed_pdf_chunks,
    generate_fixed_text_chunks,
    generate_recursive_pdf_chunks,
    generate_recursive_text_chunks,
)
from utility.utilities.vectordb_utilities import ingest_embeddings

materials_folder = Path("bootcamp_material")

for pattern, chunker in (
    ("*.pdf", generate_fixed_pdf_chunks),
    ("*.txt", generate_fixed_text_chunks),
    ("*.pdf", generate_recursive_pdf_chunks),
    ("*.txt", generate_recursive_text_chunks),
):
    for document in sorted(materials_folder.glob(pattern)):
        chunked_data = chunker(str(document))
        embeddings = generate_batch_sentences_embeddings(chunked_data["chunks"])

        if "fixed" in chunker.__name__:
            strategy = "fixed"
        elif "recursive" in chunker.__name__:
            strategy = "recursive"
        ingest_embeddings(
            chunked_data["ids"],
            embeddings,
            chunked_data["chunks"],
            chunked_data["metadata"],
            strategy=strategy,
        )
