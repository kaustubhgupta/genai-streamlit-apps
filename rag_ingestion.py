from pathlib import Path

from utility.utilities.embedding_chunking_utilities import (
    generate_batch_sentences_embeddings,
    generate_fixed_chunks,
)
from utility.utilities.vectordb_utilities import ingest_embeddings

notes_folder = Path("notes")

for document in sorted(notes_folder.glob("*.pdf")):
    chunked_data = generate_fixed_chunks(str(document))
    embeddings = generate_batch_sentences_embeddings(chunked_data["chunks"])
    ingest_embeddings(
        chunked_data["ids"],
        embeddings,
        chunked_data["chunks"],
        chunked_data["metadata"],
    )
