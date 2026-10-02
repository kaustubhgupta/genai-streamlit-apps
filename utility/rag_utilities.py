from openai import OpenAI
from dotenv import load_dotenv
from pypdf import PdfReader
import os

load_dotenv()

client = OpenAI()
model_name = os.environ.get("OPENAI_EMBEDDING_MODEL")
num_dims = int(os.environ.get("OPENAI_EMBEDDING_DIM"))
chunk_size = int(os.environ.get("FIXED_CHUNKING_SIZE"))
chunk_overlap_size = int(os.environ.get("CHUNK_OVERLAP_SIZE"))


def get_single_sentence_embeddings(input_sentence, dimensions=num_dims):

    response = client.embeddings.create(
        input=input_sentence, model=model_name, dimensions=dimensions
    )

    return response.data[0].embedding


def generate_fixed_chunks(
    file_path, chunk_size=chunk_size, chunk_overlap_size=chunk_overlap_size
):
    reader = PdfReader(file_path)

    pdf_text = ""
    for page in reader.pages:
        pdf_text = pdf_text + page.extract_text() + " "

    chunks = []
    start = 0

    while start < len(pdf_text):
        end = start + chunk_size
        chunk = pdf_text[start:end]
        chunks.append(chunk)
        start = end - chunk_overlap_size

    return chunks
