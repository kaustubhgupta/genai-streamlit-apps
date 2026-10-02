from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
from utilities.embedding_chunking_utilities import (
    generate_single_sentence_embeddings,
)

sentences = [
    "dbt is a SQL transformation framework",
    "SQL is database language",
    "dbt can help you modularize SQL",
    "dbt supports data testing and catching early errors",
    "In data pipelines, we should be aware of doing data quality testing",
]

embeddings = [generate_single_sentence_embeddings(x) for x in sentences]

qs_embedding = generate_single_sentence_embeddings("what is SQL engine DBT")

print("Cosine Similarities: {}".format(cosine_similarity([qs_embedding], embeddings)))
print("Euclidean Distances: {}".format(euclidean_distances([qs_embedding], embeddings)))
