from utility.utilities.embedding_chunking_utilities import (
    generate_single_sentence_embeddings,
)
from utility.utilities.vectordb_utilities import fetch_similar_results

question = "how does tool calling works"
question_embeds = generate_single_sentence_embeddings(question)
print(fetch_similar_results(question_embeds))
