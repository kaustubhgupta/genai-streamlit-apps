from pathlib import Path

from utility.utilities.embedding_chunking_utilities import (
    generate_batch_sentences_embeddings,
    generate_fixed_pdf_chunks,
    generate_fixed_text_chunks,
)
from utility.utilities.vectordb_utilities import ingest_embeddings

materials_folder = Path("bootcamp_material")

for pattern, chunker in (
    ("*.pdf", generate_fixed_pdf_chunks),
    ("*.txt", generate_fixed_text_chunks),
):
    for document in sorted(materials_folder.glob(pattern)):
        chunked_data = chunker(str(document))
        embeddings = generate_batch_sentences_embeddings(chunked_data["chunks"])
        ingest_embeddings(
            chunked_data["ids"],
            embeddings,
            chunked_data["chunks"],
            chunked_data["metadata"],
        )