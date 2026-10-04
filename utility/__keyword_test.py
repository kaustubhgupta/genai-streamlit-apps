from utilities.keyword_based_search import keyword_search

chunks = [
    "dbt is a SQL transformation framework and engine.",
    "SQL is database language for query,",
    "dbt can help you modularize SQL.",
    "dbt supports data testing, and catching early errors",
    "In data pipelines, we should be aware of doing data quality testing? yes! Ofcourse",
]

query = "what is a dbt query?"

print(keyword_search(chunks, query, 2))
