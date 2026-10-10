import os
import random
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import streamlit as st

from utility.ingestion.rag_ingestion import (
    de_ingest_materials,
    ingest_materials,
    list_ingested_documents,
)

st.set_page_config(
    page_title="Ingestion Manager", page_icon=":file_folder:", layout="wide"
)

materials_folder_value = os.getenv("MATERIALS_FOLDER")
if not materials_folder_value:
    st.error("Set the MATERIALS_FOLDER environment variable to the documents folder.")
    st.stop()

materials_folder = Path(materials_folder_value).expanduser()
if not materials_folder.is_dir():
    st.error(f"MATERIALS_FOLDER is not an existing directory: {materials_folder}")
    st.stop()


def _set_all_selected(document_names, key_prefix, select_all_key):
    selected = st.session_state[select_all_key]
    for name in document_names:
        st.session_state[f"{key_prefix}_{name}"] = selected


def _update_select_all(document_names, key_prefix, select_all_key):
    st.session_state[select_all_key] = bool(document_names) and all(
        st.session_state.get(f"{key_prefix}_{name}", False) for name in document_names
    )


ingested_names = list_ingested_documents()

available_names = {
    document.name
    for pattern in ("*.pdf", "*.txt")
    for document in materials_folder.glob(pattern)
}
ingested_names = sorted(ingested_names)
available_names = sorted(available_names)

st.title("RAG Documents Ingestion Manager")
st.write(f"Ingest documents from `{materials_folder}` into the RAG database.")

if st.session_state.pop("show_ingested_documents", False):
    st.session_state["ingestion_manager_tabs"] = "Currently ingested documents"
    st.toast("Document ingestion completed.")
if st.session_state.pop("show_deingested_documents", False):
    st.session_state["ingestion_manager_tabs"] = "Currently ingested documents"
    st.toast("Document de-ingestion completed.")

new_sources = set(available_names) - set(ingested_names)
if new_sources:
    st.warning(f"New sources available to ingest!")

ingested_tab, add_documents_tab, remove_documents_tab = st.tabs(
    ["Currently ingested documents", "Add documents", "De-ingest documents"],
    key="ingestion_manager_tabs",
    on_change="rerun",
)
with ingested_tab:
    pdf_column, txt_column = st.columns(2)
    for column, extension, label in (
        (pdf_column, ".pdf", "PDF documents"),
        (txt_column, ".txt", "Text documents"),
    ):
        with column:
            st.subheader(label)
            documents = [
                {"Document": name}
                for name in ingested_names
                if name.lower().endswith(extension)
            ]
            if documents:
                st.dataframe(
                    documents,
                    height=400,
                    use_container_width=True,
                )
            else:
                st.info(f"No ingested {label.lower()}.")
with add_documents_tab:
    documents_to_add = available_names
    if not documents_to_add:
        st.info("There are no documents available to ingest.")
    else:
        for name in documents_to_add:
            key = f"ingest_document_{name}"
            if key not in st.session_state:
                st.session_state[key] = False
        if st.session_state.pop("reset_ingestion_selections", False):
            for name in documents_to_add:
                st.session_state[f"ingest_document_{name}"] = False
            st.session_state["select_all_documents"] = False
        if "select_all_documents" not in st.session_state:
            st.session_state["select_all_documents"] = False

        st.checkbox(
            "Select all documents",
            key="select_all_documents",
            on_change=_set_all_selected,
            args=(documents_to_add, "ingest_document", "select_all_documents"),
        )
        pdf_column, txt_column = st.columns(2)
        for column, extension, label in (
            (pdf_column, ".pdf", "PDF documents"),
            (txt_column, ".txt", "Text documents"),
        ):
            with column:
                st.subheader(label)
                for name in documents_to_add:
                    if name.lower().endswith(extension):
                        st.checkbox(
                            name,
                            key=f"ingest_document_{name}",
                            on_change=_update_select_all,
                            args=(
                                documents_to_add,
                                "ingest_document",
                                "select_all_documents",
                            ),
                        )

        selected_documents = [
            str(materials_folder / name)
            for name in documents_to_add
            if st.session_state.get(f"ingest_document_{name}", False)
        ]
        if st.button(
            "Ingest selected documents",
            type="primary",
            disabled=not selected_documents,
        ):
            try:
                stage_messages = (
                    "Chunking the documents...",
                    "Generating embeddings for the document chunks...",
                    "Storing embeddings in the database...",
                    "Preparing document metadata...",
                    "Indexing content for retrieval...",
                )
                with st.spinner("Ingesting documents..."):
                    status = st.empty()
                    next_message_at = time.monotonic() + 5
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        ingestion = executor.submit(
                            ingest_materials, selected_documents, materials_folder
                        )
                        while not ingestion.done():
                            now = time.monotonic()
                            if now >= next_message_at:
                                status.info(random.choice(stage_messages))
                                next_message_at = now + 2
                            time.sleep(0.2)
                        ingestion.result()
                    status.empty()
                st.session_state["reset_ingestion_selections"] = True
                st.session_state["show_ingested_documents"] = True
                st.rerun()
            except Exception as exc:
                st.error(f"Could not ingest documents: {exc}")

with remove_documents_tab:
    documents_to_remove = ingested_names
    if not documents_to_remove:
        st.info("There are no ingested documents to remove.")
    else:
        for name in documents_to_remove:
            key = f"de_ingest_document_{name}"
            if key not in st.session_state:
                st.session_state[key] = False
        if st.session_state.pop("reset_deingestion_selections", False):
            for name in documents_to_remove:
                st.session_state[f"de_ingest_document_{name}"] = False
            st.session_state["select_all_deingest_documents"] = False
        if "select_all_deingest_documents" not in st.session_state:
            st.session_state["select_all_deingest_documents"] = False

        st.checkbox(
            "Select all documents",
            key="select_all_deingest_documents",
            on_change=_set_all_selected,
            args=(
                documents_to_remove,
                "de_ingest_document",
                "select_all_deingest_documents",
            ),
        )
        pdf_column, txt_column = st.columns(2)
        for column, extension, label in (
            (pdf_column, ".pdf", "PDF documents"),
            (txt_column, ".txt", "Text documents"),
        ):
            with column:
                st.subheader(label)
                for name in documents_to_remove:
                    if name.lower().endswith(extension):
                        st.checkbox(
                            Path(name).name,
                            key=f"de_ingest_document_{name}",
                            on_change=_update_select_all,
                            args=(
                                documents_to_remove,
                                "de_ingest_document",
                                "select_all_deingest_documents",
                            ),
                        )

        selected_documents = [
            str(Path(name) if Path(name).is_absolute() else materials_folder / name)
            for name in documents_to_remove
            if st.session_state.get(f"de_ingest_document_{name}", False)
        ]
        if st.button(
            "De-ingest selected documents",
            type="primary",
            disabled=not selected_documents,
        ):
            try:
                with st.spinner("De-ingesting documents..."):
                    de_ingest_materials(selected_documents, materials_folder)
                st.session_state["reset_deingestion_selections"] = True
                st.session_state["show_deingested_documents"] = True
                st.rerun()
            except Exception as exc:
                st.error(f"Could not de-ingest documents: {exc}")
