import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI()
model_name = os.environ.get("OPENAI_EMBEDDING_MODEL")
num_dims = int(os.environ.get("OPENAI_EMBEDDING_DIM"))


def generate_single_sentence_embeddings(input_sentence, dimensions=num_dims):
    response = client.embeddings.create(
        input=input_sentence, model=model_name, dimensions=dimensions
    )
    return response.data[0].embedding


def generate_batch_sentences_embeddings(sentences, dimensions=num_dims):
    response = client.embeddings.create(
        input=sentences, model=model_name, dimensions=dimensions
    )
    return [item.embedding for item in response.data]
