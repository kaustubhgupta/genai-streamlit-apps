import streamlit as st

from utility.ingestion.rag_ingestion import ingest_materials, materials_folder
from utility.utilities.vectordb_utilities import fetch_docs_for_keyword_search

st.set_page_config(
    page_title="Ingestion Manager", page_icon=":file_folder:", layout="wide"
)
ingested_names = set()
for strategy in ("fixed", "recursive"):
    stored_docs = fetch_docs_for_keyword_search(strategy)
    for metadata in stored_docs.get("metadatas") or []:
        for value in (metadata or {}).values():
            if isinstance(value, str):
                ingested_names.add(value.replace("\\", "/").rsplit("/", 1)[-1])

available_names = {
    document.name
    for pattern in ("*.pdf", "*.txt")
    for document in materials_folder.glob(pattern)
}
ingested_names = sorted(ingested_names)
available_names = sorted(available_names)

st.title("RAG Documents Ingestion Manager")
st.write("Ingest documents from the `bootcamp_material` folder into the RAG database.")

new_sources = set(available_names) - set(ingested_names)
if new_sources:
    st.warning(f"New sources available to ingest: {', '.join(sorted(new_sources))}")

ingested_tab, available_tab = st.tabs(
    ["Currently ingested documents", "Available in folder"]
)
with ingested_tab:
    st.dataframe(
        [{"Document": name} for name in ingested_names],
        use_container_width=True,
    )
with available_tab:
    st.dataframe(
        [{"Document": name} for name in available_names],
        use_container_width=True,
    )

if st.button("Ingest documents", type="primary"):
    try:
        with st.spinner("Ingesting documents..."):
            ingest_materials()
        st.success("Document ingestion completed.")
    except Exception as exc:
        st.error(f"Could not ingest documents: {exc}")
