from rank_bm25 import BM25Okapi
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

nltk.download("stopwords")
stemmer = PorterStemmer()

stop_words = set(stopwords.words("english"))


def process_document(doc):
    doc_lower = doc.lower()
    doc_removed_punc = re.sub(r"[^\w\s]", "", doc_lower)
    doc_splited = doc_removed_punc.split(" ")
    doc_filtered_stopwords = [word for word in doc_splited if word not in stop_words]
    doc_stemmed = [stemmer.stem(word) for word in doc_filtered_stopwords]
    return doc_stemmed


def keyword_search(chunks, user_query, top_chunks=5):
    prcoessed_chunks = [process_document(doc) for doc in chunks]
    processed_query = process_document(user_query)
    bm25 = BM25Okapi(prcoessed_chunks)
    scores = bm25.get_scores(processed_query)
    sorted_chunks = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in sorted_chunks[:top_chunks]]
