import streamlit as st
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from utility.tools.rag_query_tools import RAG_QUERY_TOOLS, RAG_TOOLS_MAPPING
from utility.database.history import load_history_records, save_history_record
from utility.database.sql_utilities import decode_json_value
from utility.tools.response_tool_utilities import normalize_response_tool
from utility.ui.page_utilities import render_chat_messages, render_history_selector

load_dotenv()

st.set_page_config(
    page_title="Bootcamp Assistant", page_icon=":bar_chart:", layout="wide"
)
st.title("Bootcamp Assistant")


ALL_TOOLS = [normalize_response_tool(tool) for tool in RAG_QUERY_TOOLS]
ALL_TOOLS_MAPPINGS = {**RAG_TOOLS_MAPPING}


if "bootcamp_chat_messages" not in st.session_state:
    st.session_state.bootcamp_chat_messages = []
if "bootcamp_chat_history" not in st.session_state:
    try:
        st.session_state.bootcamp_chat_history = load_history_records(
            "bootcamp_assistant",
            "bootcamp_chat_history",
            {
                "id": "TEXT",
                "timestamp": "TIMESTAMPTZ",
                "question": "TEXT",
                "messages": "JSONB",
                "response_id": "TEXT",
            },
            order_by="timestamp",
            descending=False,
            nullable_columns=("response_id",),
        )
    except Exception as exc:
        st.session_state.bootcamp_chat_history = []
        st.warning(f"Could not load chat history from PostgreSQL: {exc}")


def restore_chat(chat_id):
    history_item = next(
        item for item in st.session_state.bootcamp_chat_history if item["id"] == chat_id
    )
    st.session_state.bootcamp_selected_chat_id = chat_id
    st.session_state.bootcamp_chat_messages = [
        dict(message) for message in history_item["messages"]
    ]
    st.session_state.bootcamp_last_response_id = history_item.get("response_id")


def start_new_chat():
    st.session_state.bootcamp_chat_messages = []
    st.session_state.pop("bootcamp_selected_chat_id", None)
    st.session_state.pop("bootcamp_last_response_id", None)
    st.session_state["bootcamp_history_selection"] = None


# The radio widget updates its session-state value before the next script run.
# Restore the chat before creating the dependent sidebar widgets.
history_selection = st.session_state.get("bootcamp_history_selection")
if (
    history_selection is not None
    and history_selection != st.session_state.get("bootcamp_selected_chat_id")
    and any(
        item["id"] == history_selection
        for item in st.session_state.bootcamp_chat_history
    )
):
    restore_chat(history_selection)

with st.sidebar:

    st.button("New chat", on_click=start_new_chat)

    render_history_selector(
        st.session_state.bootcamp_chat_history,
        "bootcamp_history_selection",
        "Previous chats",
        "No previous chats yet.",
    )


render_chat_messages(st.session_state.bootcamp_chat_messages)


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
        chat_id = str(uuid.uuid4())
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

    save_history_record(
        "bootcamp_assistant",
        "bootcamp_chat_history",
        {
            "id": "TEXT",
            "timestamp": "TIMESTAMPTZ",
            "question": "TEXT",
            "messages": "JSONB",
            "response_id": "TEXT",
        },
        {
            "id": chat_id,
            "timestamp": history_item["timestamp"],
            "question": history_item["question"],
            "messages": st.session_state.bootcamp_chat_messages,
            "response_id": response_id,
        },
        update_columns=("messages", "response_id"),
        nullable_columns=("response_id",),
    )


user_input = st.chat_input("Ask a question or follow up...")


if user_input:

    try:
        query_start = datetime.now()
        with st.spinner("Working on user request..."):

            prompt = f"User Question: {user_input}\n\nPlease provide an answer in 250 words and if needed, search for relevant chunks. Look at the chunk scores and decide which chunks to use. At the end, list the document names (doc_name) for the sources you actually used under 'Documents used'. If the answer is not found in the provided chunks, respond with 'I don't know.'"

            request_args = {
                "model": os.getenv("OPENAI_MODEL"),
                "input": prompt,
                "tools": ALL_TOOLS,
            }
            previous_response_id = st.session_state.get("bootcamp_last_response_id")
            if previous_response_id:
                request_args["previous_response_id"] = previous_response_id

            client = OpenAI()
            response = client.responses.create(**request_args)
            response_id = response.id

            while True:
                tool_outputs = []
                for item in response.output:
                    if item.type == "function_call":
                        args = decode_json_value(item.arguments)
                        function_name = item.name
                        call_function = ALL_TOOLS_MAPPINGS[function_name]
                        st.info(f"Using tool: {function_name} with arguments: {args}")
                        try:
                            tool_result = call_function(**args)
                        except IndexError:
                            # Empty RAG results can cause tools to index a
                            # nonexistent first chunk. Let the model handle the
                            # empty result instead of failing the whole request.
                            tool_result = "No results found. exit"
                        tool_outputs.append(
                            {
                                "type": "function_call_output",
                                "call_id": item.call_id,
                                "output": str(tool_result),
                            }
                        )

                if not tool_outputs:
                    break

                response = client.responses.create(
                    model=os.getenv("OPENAI_MODEL"),
                    input=tool_outputs,
                    previous_response_id=response_id,
                    tools=ALL_TOOLS,
                )
                response_id = response.id

            output = response.output_text.strip()

            query_end = datetime.now()
            time_taken = query_end - query_start
            output += f"\n\nQuery Time: {time_taken}"

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
