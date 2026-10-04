import streamlit as st
import os
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from utility.tools.pg_tools import PG_TOOLS, PG_TOOLS_MAPPING
from utility.tools.calendar_tools import CALENDAR_TOOLS, CALENDAR_TOOLS_MAPPING
from utility.tools.pg_tools import direct_db_access

load_dotenv()

st.set_page_config(
    page_title="Database Assistant", page_icon=":bar_chart:", layout="wide"
)
st.title("Database Assistant")


def normalize_response_tool(tool):
    """Convert Chat Completions-style tools to Responses API format."""
    tool = dict(tool)
    function = tool.pop("function", None)
    if function:
        tool.update(function)
    return tool


ALL_TOOLS = [normalize_response_tool(tool) for tool in PG_TOOLS + CALENDAR_TOOLS]
ALL_TOOLS_MAPPINGS = {**PG_TOOLS_MAPPING, **CALENDAR_TOOLS_MAPPING}

if "database_chat_messages" not in st.session_state:
    st.session_state.database_chat_messages = []
if "database_chat_history" not in st.session_state:
    try:
        direct_db_access("CREATE SCHEMA IF NOT EXISTS database_assistant")
        direct_db_access("""
            CREATE TABLE IF NOT EXISTS database_assistant.database_chat_history (
                id TEXT PRIMARY KEY,
                timestamp TIMESTAMPTZ NOT NULL,
                question TEXT NOT NULL,
                messages JSONB NOT NULL,
                response_id TEXT
            )
            """)
        _, stored_chats = direct_db_access("""
            SELECT id, timestamp, question, messages, response_id
            FROM database_assistant.database_chat_history
            ORDER BY timestamp
            """)
        st.session_state.database_chat_history = [
            {
                "id": chat_id,
                "timestamp": timestamp,
                "question": question,
                "messages": (
                    json.loads(messages) if isinstance(messages, str) else messages
                ),
                "response_id": response_id,
            }
            for chat_id, timestamp, question, messages, response_id in (
                stored_chats or []
            )
        ]
    except Exception as exc:
        st.session_state.database_chat_history = []
        st.warning(f"Could not load chat history from PostgreSQL: {exc}")


def restore_chat(chat_id):
    history_item = next(
        item for item in st.session_state.database_chat_history if item["id"] == chat_id
    )
    st.session_state.database_selected_chat_id = chat_id
    st.session_state.database_chat_messages = [
        dict(message) for message in history_item["messages"]
    ]
    st.session_state.database_last_response_id = history_item.get("response_id")


def start_new_chat():
    st.session_state.database_chat_messages = []
    st.session_state.pop("database_selected_chat_id", None)
    st.session_state.pop("database_last_response_id", None)
    st.session_state["database_history_selection"] = None


# The radio widget updates its session-state value before the next script run.
# Restore the chat before creating the dependent sidebar widgets.
history_selection = st.session_state.get("database_history_selection")
if (
    history_selection is not None
    and history_selection != st.session_state.get("database_selected_chat_id")
    and any(
        item["id"] == history_selection
        for item in st.session_state.database_chat_history
    )
):
    restore_chat(history_selection)

with st.sidebar:

    st.button("New chat", on_click=start_new_chat)

    if st.session_state.database_chat_history:
        history_items = list(reversed(st.session_state.database_chat_history))

        with st.container(height=250, border=False):
            st.radio(
                "Previous chats",
                [item["id"] for item in history_items],
                index=None,
                format_func=lambda item_id: next(
                    f'{item["timestamp"]:%Y-%m-%d %H:%M} — {item["question"]}'
                    for item in history_items
                    if item["id"] == item_id
                ),
                key="database_history_selection",
            )
    else:
        st.caption("No previous chats yet.")


for message in st.session_state.database_chat_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("rows"):
            st.dataframe(
                [dict(zip(message["columns"], row)) for row in message["rows"]],
                use_container_width=True,
            )


def save_chat_history(question, response_id):
    """Create a history entry for a new chat or update the active chat."""
    chat_id = st.session_state.get("database_selected_chat_id")
    history_item = next(
        (
            item
            for item in st.session_state.database_chat_history
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
        st.session_state.database_chat_history.append(history_item)
        st.session_state.database_selected_chat_id = chat_id

    history_item["messages"] = [
        dict(message) for message in st.session_state.database_chat_messages
    ]
    history_item["response_id"] = response_id
    st.session_state.database_last_response_id = response_id

    def sql_literal(value):
        if value is None:
            return "NULL"
        return "'" + str(value).replace("'", "''") + "'"

    messages_json = json.dumps(st.session_state.database_chat_messages)
    direct_db_access(f"""
        INSERT INTO database_assistant.database_chat_history
            (id, timestamp, question, messages, response_id)
        VALUES (
            {sql_literal(chat_id)},
            {sql_literal(history_item['timestamp'].isoformat())}::timestamptz,
            {sql_literal(history_item['question'])},
            {sql_literal(messages_json)}::jsonb,
            {sql_literal(response_id)}
        )
        ON CONFLICT (id) DO UPDATE SET
            messages = EXCLUDED.messages,
            response_id = EXCLUDED.response_id
        """)


user_input = st.chat_input("Ask a question or follow up...")


if user_input:
    prompt = f"User Question: {user_input}\n"
    try:
        with st.spinner("Working on user request..."):
            request_args = {
                "model": f"{os.getenv('OPENAI_MODEL')}",
                "input": prompt,
                "tools": ALL_TOOLS,
            }
            previous_response_id = st.session_state.get("database_last_response_id")
            if previous_response_id:
                request_args["previous_response_id"] = previous_response_id

            response = OpenAI().responses.create(**request_args)

            response_id = response.id

            while True:
                tool_outputs = []
                llm_output = response.output
                for item in llm_output:
                    if item.type == "function_call":
                        args = json.loads(item.arguments)
                        function_name = item.name
                        call_function = ALL_TOOLS_MAPPINGS[function_name]
                        st.info(f"Using tool: {function_name}")
                        tool_result = call_function(**args)
                        tool_call_id = item.call_id
                        tool_outputs.append(
                            {
                                "type": "function_call_output",
                                "call_id": tool_call_id,
                                "output": str(tool_result),
                            }
                        )

                if not tool_outputs:
                    break

                response = OpenAI().responses.create(
                    model=f"{os.getenv('OPENAI_MODEL')}",
                    input=tool_outputs,
                    previous_response_id=response_id,
                    tools=ALL_TOOLS,
                )
                response_id = response.id

            output = response.output_text.strip()

            st.session_state.database_chat_messages.extend(
                [
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": output},
                ]
            )
            save_chat_history(user_input, response_id)
        st.rerun()
    except Exception as exc:
        st.error(f"Could not generate or run the query: {exc}")
