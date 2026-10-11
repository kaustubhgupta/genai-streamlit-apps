from deepeval.synthesizer import Synthesizer
from utility.retrieval.vector_store import fetch_docs_by_filename
from pathlib import Path
import os


def generate_golden_dataset(file_path):
    model = os.getenv("OPENAI_EVAL_MODEL")
    chunk_size_filter_threshold = int(os.getenv("CHUNK_SIZE_FILTER_THRESHOLD"))
    output_dir = Path("./golden_dataset")
    output_dir.mkdir(parents=True, exist_ok=True)

    file_path = Path(file_path)
    file_name = str(file_path)
    name_only = file_path.stem
    contexts = fetch_docs_by_filename(file_name, "recursive")

    if not contexts or "documents" not in contexts or not contexts["documents"]:
        return

    metadatas = contexts.get("metadatas", [])
    filtered_indices = [
        index
        for index, chunk in enumerate(contexts["documents"])
        if len(chunk) >= chunk_size_filter_threshold
    ]
    if not filtered_indices:
        return

    processed_context = [[contexts["documents"][index]] for index in filtered_indices]
    source_files = [
        metadatas[index]["doc_name"]
        for index in filtered_indices
        if index < len(metadatas) and "doc_name" in metadatas[index]
    ]

    synthesizer = Synthesizer(model=model)
    synthesizer.generate_goldens_from_contexts(
        contexts=processed_context,
        include_expected_output=True,
        source_files=source_files,
    )
    synthesizer.save_as(
        file_type="json",
        directory=str(output_dir),
        file_name=f"golden_{name_only}",
    )
