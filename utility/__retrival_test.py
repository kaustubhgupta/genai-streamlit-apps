from utility.embeddings.openai_embeddings import (
    generate_single_sentence_embeddings,
)
from utility.retrieval.vector_store import fetch_similar_results

question = "how does tool calling works"
question_embeds = generate_single_sentence_embeddings(question)
print(fetch_similar_results(question_embeds))
