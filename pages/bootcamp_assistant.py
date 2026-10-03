import streamlit as st
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from utility.utilities.embedding_chunking_utilities import (
    generate_single_sentence_embeddings,
)
from utility.utilities.vectordb_utilities import fetch_similar_results
from utility.utilities.chunk_reranker import rerank_docs

load_dotenv()

CHUNK_FILTER_THRESHOLD = int(os.environ.get("CHUNK_FILTER_THRESHOLD"))
SIMILAR_CHUNK_THRESHOLD = int(os.environ.get("SIMILAR_CHUNK_THRESHOLD"))

st.set_page_config(
    page_title="Bootcamp Assistant", page_icon=":bar_chart:", layout="wide"
)
st.title("Bootcamp Assistant")


if "bootcamp_chat_messages" not in st.session_state:
    st.session_state.bootcamp_chat_messages = []
if "bootcamp_chat_history" not in st.session_state:
    st.session_state.bootcamp_chat_history = []


def restore_chat(chat_id):
    history_item = next(
        item for item in st.session_state.bootcamp_chat_history if item["id"] == chat_id
    )
    st.session_state.selected_chat_id = chat_id
    st.session_state.bootcamp_chat_messages = [
        dict(message) for message in history_item["messages"]
    ]
    st.session_state.last_response_id = history_item.get("response_id")
    st.session_state.bootcamp_search_strategy = history_item.get(
        "search_strategy", "recursive"
    )


# The radio widget updates its session-state value before the next script run.
# Restore the chat before creating the dependent sidebar widgets.
history_selection = st.session_state.get("bootcamp_history_selection")
if (
    history_selection is not None
    and history_selection != st.session_state.get("selected_chat_id")
    and any(
        item["id"] == history_selection
        for item in st.session_state.bootcamp_chat_history
    )
):
    restore_chat(history_selection)

with st.sidebar:

    st.subheader("Available resources")
    search_strategy = st.selectbox(
        "Search strategy",
        options=["recursive", "fixed", "semantic"],
        index=0,
        key="bootcamp_search_strategy",
    )
    notes_dir = Path(__file__).resolve().parent.parent / "bootcamp_material"
    resource_paths = sorted(
        (
            path.relative_to(notes_dir)
            for path in notes_dir.rglob("*")
            if path.is_file()
        ),
        key=lambda path: str(path).lower(),
    )
    if resource_paths:
        with st.container(height=250, border=True):
            for resource_path in resource_paths:
                st.write(f"• {resource_path}")
    else:
        st.caption("No resources found in the notes folder.")

    if st.button("New chat"):
        st.session_state.bootcamp_chat_messages = []
        st.session_state.pop("bootcamp_selected_chat_id", None)
        st.session_state.pop("bootcamp_last_response_id", None)
        st.session_state.pop("bootcamp_history_selection", None)
        st.rerun()

    if st.session_state.bootcamp_chat_history:
        history_items = list(reversed(st.session_state.bootcamp_chat_history))

        st.radio(
            "Previous chats",
            [item["id"] for item in history_items],
            index=None,
            format_func=lambda item_id: next(
                f'{item["timestamp"]:%Y-%m-%d %H:%M} — {item["question"]}'
                for item in history_items
                if item["id"] == item_id
            ),
            key="bootcamp_history_selection",
        )
    else:
        st.caption("No previous chats yet.")


for message in st.session_state.bootcamp_chat_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("rows"):
            st.dataframe(
                [dict(zip(message["columns"], row)) for row in message["rows"]],
                use_container_width=True,
            )


def save_chat_history(question, response_id, search_strategy):
    """Create a history entry for a new chat or update the active chat."""
    chat_id = st.session_state.get("bootcamp_selected_chat_id")
    history_item = next(
        (
            item
            for item in st.session_state.bootcamp_chat_history
            if item["id"] == chat_id
        ),
        None,
    )

    if history_item is None:
        chat_id = len(st.session_state.bootcamp_chat_history)
        history_item = {
            "id": chat_id,
            "timestamp": datetime.now(),
            "question": question,
            "messages": [],
            "response_id": response_id,
            "search_strategy": search_strategy,
        }
        st.session_state.bootcamp_chat_history.append(history_item)
        st.session_state.bootcamp_selected_chat_id = chat_id

    history_item["messages"] = [
        dict(message) for message in st.session_state.bootcamp_chat_messages
    ]
    history_item["response_id"] = response_id
    history_item["search_strategy"] = search_strategy
    st.session_state.bootcamp_last_response_id = response_id


user_input = st.chat_input("Ask a question or follow up...")


if user_input:
    user_input_embeddings = generate_single_sentence_embeddings(
        user_input,
    )
    try:
        with st.spinner("Working on user request..."):
            similar_chunks = fetch_similar_results(
                user_input_embeddings,
                n_results=SIMILAR_CHUNK_THRESHOLD,
                strategy=search_strategy,
            )
            similar_docs = similar_chunks["documents"][0]
            similar_metadatas = similar_chunks.get("metadatas", [[]])[0]
            document_names = {}
            for document, metadata in zip(similar_docs, similar_metadatas):
                document_names.setdefault(document, set()).add(
                    (metadata or {}).get("doc_name", "Unknown document")
                )
            filtered_similar_docs = [
                document
                for document in similar_docs
                if len(document) > CHUNK_FILTER_THRESHOLD
            ]
            ranked_docs = rerank_docs(user_input, filtered_similar_docs)
            prompt = f"User Question: {user_input}\n\nRelevant Chunks:\n"
            for doc in ranked_docs:
                sources = ", ".join(
                    sorted(document_names.get(doc["document"], {"Unknown document"}))
                )
                prompt += (
                    f"Chunk Score {doc['score']} (Document: {sources}): "
                    f"{doc['document']}\n"
                )
            prompt += "\nPlease provide an answer in 250 words based on the relevant chunks. Look at the chunk scores and decide which chunks to use. At the end, list the document names (doc_name) for the sources you actually used under 'Documents used'. If the answer is not found in the provided chunks, respond with 'I don't know.'"

            request_args = {
                "model": os.getenv("OPENAI_MODEL"),
                "input": prompt,
            }
            previous_response_id = st.session_state.get("bootcamp_last_response_id")
            if previous_response_id:
                request_args["previous_response_id"] = previous_response_id

            response = OpenAI().responses.create(**request_args)
            response_id = response.id
            output = response.output_text.strip()

            st.session_state.bootcamp_chat_messages.extend(
                [
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": output},
                ]
            )
            save_chat_history(user_input, response_id, search_strategy)
        st.rerun()
    except Exception as exc:
        st.error(f"Could not generate or run the query: {exc}")
