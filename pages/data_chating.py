import streamlit as st
import os
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from utility.tools.pg_tools import direct_db_access, fetch_schema, load_schema_tables
from utility.utilities.generic_utilities import contains_forbidden_sql_operation

load_dotenv()

st.set_page_config(page_title="Data Chat", page_icon="💬")
st.title("Data Chat")


if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "chat_history" not in st.session_state:
    try:
        direct_db_access("CREATE SCHEMA IF NOT EXISTS data_chat_assistant")
        direct_db_access("""
            CREATE TABLE IF NOT EXISTS data_chat_assistant.data_chat_history (
                id TEXT PRIMARY KEY,
                timestamp TIMESTAMPTZ NOT NULL,
                question TEXT NOT NULL,
                selected_schema TEXT NOT NULL,
                selected_tables JSONB NOT NULL,
                messages JSONB NOT NULL
            )
            """)
        _, stored_chats = direct_db_access("""
            SELECT id, timestamp, question, selected_schema, selected_tables, messages
            FROM data_chat_assistant.data_chat_history
            ORDER BY timestamp
            """)
        st.session_state.chat_history = [
            {
                "id": chat_id,
                "timestamp": timestamp,
                "question": question,
                "schema": selected_schema,
                "tables": (
                    json.loads(selected_tables)
                    if isinstance(selected_tables, str)
                    else selected_tables
                ),
                "messages": (
                    json.loads(messages) if isinstance(messages, str) else messages
                ),
            }
            for (
                chat_id,
                timestamp,
                question,
                selected_schema,
                selected_tables,
                messages,
            ) in (stored_chats or [])
        ]
    except Exception as exc:
        st.session_state.chat_history = []
        st.warning(f"Could not load chat history from PostgreSQL: {exc}")


@st.cache_data
def get_schema_tables():
    return load_schema_tables()


try:
    schema_tables = get_schema_tables()
except Exception as exc:
    st.error(f"Could not load database metadata: {exc}")
    st.stop()

excluded_schemas = {
    schema.strip().lower()
    for schema in os.getenv("EXCLUDED_SCHEMAS", "").split(",")
    if schema.strip()
}

schema_tables = {
    schema: tables
    for schema, tables in schema_tables.items()
    if schema.lower() not in excluded_schemas
}

if not schema_tables:
    st.warning("No schemas with tables were found in the database.")
    st.stop()


def restore_chat(chat_id):
    history_item = next(
        item for item in st.session_state.chat_history if item["id"] == chat_id
    )
    schema = history_item["schema"]
    if schema not in schema_tables:
        schema = sorted(schema_tables)[0]
    st.session_state.selected_chat_id = chat_id
    st.session_state.chat_messages = [
        dict(message) for message in history_item["messages"]
    ]
    st.session_state.selected_schema = schema
    st.session_state.selected_tables = [
        table
        for table in history_item["tables"]
        if table in schema_tables.get(schema, [])
    ]


def start_new_chat():
    st.session_state.chat_messages = []
    st.session_state.pop("selected_chat_id", None)
    st.session_state["history_selection"] = None
    st.session_state.selected_tables = []
    st.session_state.selected_schema = sorted(schema_tables)[0]


# The radio widget updates its session-state value before the next script run.
# Restore the chat before creating the dependent sidebar widgets.
history_selection = st.session_state.get("history_selection")
if (
    history_selection is not None
    and history_selection != st.session_state.get("selected_chat_id")
    and any(item["id"] == history_selection for item in st.session_state.chat_history)
):
    restore_chat(history_selection)

with st.sidebar:
    st.header("Data sources")

    selected_schema = st.selectbox(
        "Schema", sorted(schema_tables), key="selected_schema"
    )
    selected_tables = st.multiselect(
        "Tables", schema_tables[selected_schema], key="selected_tables"
    )
    st.button("New chat", on_click=start_new_chat)

    if st.session_state.chat_history:
        history_items = list(reversed(st.session_state.chat_history))

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
                key="history_selection",
            )
    else:
        st.caption("No previous chats yet.")


for message in st.session_state.chat_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("rows"):
            st.dataframe(
                [dict(zip(message["columns"], row)) for row in message["rows"]],
                use_container_width=True,
            )


def save_chat_history(question):
    """Create a history entry for a new chat or update the active chat."""
    chat_id = st.session_state.get("selected_chat_id")
    history_item = next(
        (item for item in st.session_state.chat_history if item["id"] == chat_id),
        None,
    )

    if history_item is None:
        chat_id = str(uuid.uuid4())
        history_item = {
            "id": chat_id,
            "timestamp": datetime.now(),
            "question": question,
            "schema": selected_schema,
            "tables": list(selected_tables),
            "messages": [],
        }
        st.session_state.chat_history.append(history_item)
        st.session_state.selected_chat_id = chat_id

    history_item["schema"] = selected_schema
    history_item["tables"] = list(selected_tables)
    history_item["messages"] = [
        dict(message) for message in st.session_state.chat_messages
    ]

    def sql_literal(value):
        if value is None:
            return "NULL"
        return "'" + str(value).replace("'", "''") + "'"

    tables_json = json.dumps(history_item["tables"])
    messages_json = json.dumps(st.session_state.chat_messages, default=str)
    direct_db_access(f"""
        INSERT INTO data_chat_assistant.data_chat_history
            (id, timestamp, question, selected_schema, selected_tables, messages)
        VALUES (
            {sql_literal(chat_id)},
            {sql_literal(history_item['timestamp'].isoformat())}::timestamptz,
            {sql_literal(history_item['question'])},
            {sql_literal(history_item['schema'])},
            {sql_literal(tables_json)}::jsonb,
            {sql_literal(messages_json)}::jsonb
        )
        ON CONFLICT (id) DO UPDATE SET
            selected_schema = EXCLUDED.selected_schema,
            selected_tables = EXCLUDED.selected_tables,
            messages = EXCLUDED.messages
        """)


user_input = st.chat_input("Ask a question or follow up...")

if user_input and selected_tables:
    table_schemas = "\n\n".join(
        fetch_schema(table, selected_schema) for table in selected_tables
    )

    prompt = (
        f"Past conversation messages: {st.session_state.chat_messages}\n"
        f"New question: {user_input}\n"
        f"Use only these table schemas:\n{table_schemas}\n"
        "Do not reference tables from any other schema.\n"
        "This is a read-only application. Never generate or execute INSERT, UPDATE, DELETE, MERGE, CREATE, ALTER, DROP, TRUNCATE, CALL, or EXPLAIN statements. "
        "Only generate read-only SELECT or WITH queries; refuse prohibited requests directly without SQL.\n"
        "Return only executable SQL, without markdown or explanation in case the response requires a SQL query. In case of simple followup questions, answer them directly without providing a SQL query"
    )
    try:
        with st.spinner("Generating query from the LLM..."):
            response = OpenAI().responses.create(
                model=f"{os.getenv('OPENAI_MODEL')}", input=prompt
            )
            query = response.output_text.strip()
            if query.startswith("```"):
                query = query.strip("`").removeprefix("sql").strip()

            forbidden_operation = contains_forbidden_sql_operation(query)
            sql_keywords = ("SELECT", "WITH")
            if forbidden_operation:
                st.error(
                    f"Blocked unsafe SQL operation: {forbidden_operation}. "
                    "Only read-only SELECT or WITH queries are allowed."
                )
                st.stop()

            if not query.lstrip().upper().startswith(sql_keywords):
                st.session_state.chat_messages.extend(
                    [
                        {"role": "user", "content": user_input},
                        {"role": "assistant", "content": query},
                    ]
                )
                save_chat_history(user_input)
                st.rerun()
                st.stop()

        with st.spinner("Running query against the database..."):
            columns, rows = direct_db_access(query)

        result_text = f"```sql\n{query}\n```\n\n"
        result_text += "**Results**" if rows else "The query returned no rows."
        st.session_state.chat_messages.extend(
            [
                {"role": "user", "content": user_input},
                {
                    "role": "assistant",
                    "content": result_text,
                    "columns": columns,
                    "rows": rows,
                },
            ]
        )
        save_chat_history(user_input)
        st.rerun()
    except Exception as exc:
        st.error(f"Could not generate or run the query: {exc}")
elif user_input and not selected_tables:
    st.warning("Select at least one table before asking a question.")
