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

load_dotenv()

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

    st.subheader("Available PDFs")
    notes_dir = Path(__file__).resolve().parent.parent / "bootcamp_material"
    pdf_names = sorted(path.name for path in notes_dir.glob("*.pdf"))
    if pdf_names:
        for pdf_name in pdf_names:
            st.write(f"• {pdf_name}")
    else:
        st.caption("No PDFs found in the notes folder.")

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


def save_chat_history(question, response_id):
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
        }
        st.session_state.bootcamp_chat_history.append(history_item)
        st.session_state.bootcamp_selected_chat_id = chat_id

    history_item["messages"] = [
        dict(message) for message in st.session_state.bootcamp_chat_messages
    ]
    history_item["response_id"] = response_id
    st.session_state.bootcamp_last_response_id = response_id


user_input = st.chat_input("Ask a question or follow up...")


if user_input:
    user_input_embeddings = generate_single_sentence_embeddings(
        user_input,
    )
    try:
        with st.spinner("Working on user request..."):
            relevant_chunks = fetch_similar_results(user_input_embeddings, n_results=5)
            prompt = f"User Question: {user_input}\n\nRelevant PDF Chunks:\n"
            for i, chunk in enumerate(relevant_chunks["documents"][0]):
                prompt += f"Chunk {i + 1}: {chunk}\n"
            prompt += "\nPlease provide a detailed answer based on the relevant PDF chunks. If the answer is not found in the provided chunks, please respond with 'I don't know.'"
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
            save_chat_history(user_input, response_id)
        st.rerun()
    except Exception as exc:
        st.error(f"Could not generate or run the query: {exc}")
