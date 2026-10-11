import os

from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

load_dotenv()

chunk_size = int(os.environ.get("CHUNKING_SIZE"))
chunk_overlap_size = int(os.environ.get("CHUNK_OVERLAP_SIZE"))


def _read_text_file(file_path):
    with open(file_path, "r") as file:
        return file.read()


def _read_pdf_file(file_path):
    reader = PdfReader(file_path)
    return " ".join(page.extract_text() or "" for page in reader.pages)


def _generate_chunks(
    text,
    file_path,
    chunk_size,
    chunk_overlap_size,
    enable_metadata,
    strategy,
):
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if chunk_overlap_size < 0 or chunk_overlap_size >= chunk_size:
        raise ValueError("chunk_overlap_size must be between zero and chunk_size")

    chunks = []
    ids = []
    metadata = []

    if strategy == "fixed":
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            ids.append(f"{file_path}_{start}")
            start = end - chunk_overlap_size
    elif strategy == "recursive":
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap_size
        )
        chunks = splitter.split_text(text)
        ids = [f"{file_path}_{index}" for index in range(len(chunks))]
    else:
        raise ValueError("strategy must be 'fixed' or 'recursive'")

    if enable_metadata:
        metadata = [
            {
                "doc_name": file_path,
                "chunk_size": chunk_size,
                "chunk_overlap_size": chunk_overlap_size,
            }
            for _ in chunks
        ]

    return {"chunks": chunks, "ids": ids, "metadata": metadata}


def generate_file_chunks(
    file_path,
    text_loader,
    chunk_size=chunk_size,
    chunk_overlap_size=chunk_overlap_size,
    enable_metadata=True,
    strategy="recursive",
):
    """Chunk a file after converting it to text with the supplied loader."""
    text = text_loader(file_path)
    return _generate_chunks(
        text,
        file_path,
        chunk_size,
        chunk_overlap_size,
        enable_metadata,
        strategy,
    )


def generate_fixed_pdf_chunks(
    file_path,
    chunk_size=chunk_size,
    chunk_overlap_size=chunk_overlap_size,
    enable_metadata=True,
):
    return generate_file_chunks(
        file_path,
        _read_pdf_file,
        chunk_size,
        chunk_overlap_size,
        enable_metadata,
        strategy="fixed",
    )


def generate_fixed_text_chunks(
    file_path,
    chunk_size=chunk_size,
    chunk_overlap_size=chunk_overlap_size,
    enable_metadata=True,
):
    return generate_file_chunks(
        file_path,
        _read_text_file,
        chunk_size,
        chunk_overlap_size,
        enable_metadata,
        strategy="fixed",
    )


def generate_recursive_text_chunks(
    file_path,
    chunk_size=chunk_size,
    chunk_overlap_size=chunk_overlap_size,
    enable_metadata=True,
):
    return generate_file_chunks(
        file_path,
        _read_text_file,
        chunk_size,
        chunk_overlap_size,
        enable_metadata,
        strategy="recursive",
    )


def generate_recursive_pdf_chunks(
    file_path,
    chunk_size=chunk_size,
    chunk_overlap_size=chunk_overlap_size,
    enable_metadata=True,
):
    return generate_file_chunks(
        file_path,
        _read_pdf_file,
        chunk_size,
        chunk_overlap_size,
        enable_metadata,
        strategy="recursive",
    )
