from utility.utilities.embedding_chunking_utilities import (
    generate_single_sentence_embeddings,
)
from utility.utilities.vectordb_utilities import fetch_similar_results
from utility.utilities.chunk_reranker import rerank_docs
import os


CHUNK_FILTER_THRESHOLD = int(os.environ.get("CHUNK_FILTER_THRESHOLD"))
SIMILAR_CHUNK_THRESHOLD = int(os.environ.get("SIMILAR_CHUNK_THRESHOLD"))