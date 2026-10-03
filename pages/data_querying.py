import streamlit as st
import os
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from utility.tools.pg_tools import direct_db_access, fetch_schema, load_schema_tables
from utility.utilities.generic_utilities import StrictSQLQuery

load_dotenv()

st.set_page_config(
    page_title="Database Querying", page_icon=":bar_chart:", layout="wide"
)
st.title("Database Querying")

if "question_history" not in st.session_state:
    try:
        direct_db_access("CREATE SCHEMA IF NOT EXISTS data_quering_assistant")
        direct_db_access("""
            CREATE TABLE IF NOT EXISTS data_quering_assistant.question_history (
                id TEXT PRIMARY KEY,
                timestamp TIMESTAMPTZ NOT NULL,
                question TEXT NOT NULL,
                selected_schema TEXT NOT NULL,
                selected_tables JSONB NOT NULL,
                generated_query TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                result JSONB
            )
            """)
        _, stored_questions = direct_db_access("""
            SELECT id, timestamp, question, selected_schema, selected_tables,
                   generated_query, operation_type, result
            FROM data_quering_assistant.question_history
            ORDER BY timestamp
            """)
        st.session_state.question_history = [
            {
                "id": history_id,
                "timestamp": timestamp,
                "question": question,
                "schema": selected_schema,
                "tables": (
                    json.loads(selected_tables)
                    if isinstance(selected_tables, str)
                    else selected_tables
                ),
                "query": generated_query,
                "operation_type": operation_type,
                "result": (
                    tuple(json.loads(result) if isinstance(result, str) else result)
                    if result is not None
                    else None
                ),
            }
            for (
                history_id,
                timestamp,
                question,
                selected_schema,
                selected_tables,
                generated_query,
                operation_type,
                result,
            ) in (stored_questions or [])
        ]
    except Exception as exc:
        st.session_state.question_history = []
        st.warning(f"Could not load question history from PostgreSQL: {exc}")
if "last_result" not in st.session_state:
    st.session_state.last_result = None


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


def restore_history(history_id):
    history_item = next(
        item for item in st.session_state.question_history if item["id"] == history_id
    )
    schema = history_item["schema"]
    if schema not in schema_tables:
        schema = sorted(schema_tables)[0]
    st.session_state.active_history_id = history_id
    st.session_state.user_input = history_item["question"]
    st.session_state.selected_schema = schema
    st.session_state.selected_tables = [
        table
        for table in history_item["tables"]
        if table in schema_tables.get(schema, [])
    ]
    st.session_state.last_result = history_item.get("result")


def start_new_chat():
    st.session_state.user_input = ""
    st.session_state.last_result = None
    st.session_state.pop("active_history_id", None)
    st.session_state["selected_history_id"] = None
    st.session_state.selected_tables = []
    st.session_state.selected_schema = sorted(schema_tables)[0]


# Restore history before rendering widgets whose values depend on the selection.
history_selection = st.session_state.get("selected_history_id")
if (
    history_selection is not None
    and history_selection != st.session_state.get("active_history_id")
    and any(
        item["id"] == history_selection for item in st.session_state.question_history
    )
):
    restore_history(history_selection)


with st.sidebar:
    st.header("Question history")
    st.button("New chat", on_click=start_new_chat)

    if st.session_state.question_history:
        history_items = list(reversed(st.session_state.question_history))

        st.radio(
            "Previous questions",
            [item["id"] for item in history_items],
            index=None,
            format_func=lambda item_id: next(
                f'{item["timestamp"]:%Y-%m-%d %H:%M} — {item["question"]}'
                for item in history_items
                if item["id"] == item_id
            ),
            key="selected_history_id",
        )
    else:
        st.caption("No questions asked yet.")


def save_question_history(history_item):
    def sql_literal(value):
        if value is None:
            return "NULL"
        return "'" + str(value).replace("'", "''") + "'"

    tables_json = json.dumps(history_item["tables"])
    result = history_item.get("result")
    result_json = json.dumps(result, default=str) if result is not None else None
    direct_db_access(f"""
        INSERT INTO data_quering_assistant.question_history
            (id, timestamp, question, selected_schema, selected_tables,
             generated_query, operation_type, result)
        VALUES (
            {sql_literal(history_item['id'])},
            {sql_literal(history_item['timestamp'].isoformat())}::timestamptz,
            {sql_literal(history_item['question'])},
            {sql_literal(history_item['schema'])},
            {sql_literal(tables_json)}::jsonb,
            {sql_literal(history_item['query'])},
            {sql_literal(history_item['operation_type'])},
            {sql_literal(result_json)}::jsonb
        )
        ON CONFLICT (id) DO UPDATE SET
            selected_schema = EXCLUDED.selected_schema,
            selected_tables = EXCLUDED.selected_tables,
            generated_query = EXCLUDED.generated_query,
            operation_type = EXCLUDED.operation_type,
            result = EXCLUDED.result
        """)


user_input = st.text_input("Ask your question:", key="user_input")
schema_col, tables_col = st.columns(2)
with schema_col:
    selected_schema = st.selectbox(
        "Schema", sorted(schema_tables), key="selected_schema"
    )
with tables_col:
    selected_tables = st.multiselect(
        "Tables", schema_tables[selected_schema], key="selected_tables"
    )

if st.button("Ask") and user_input.strip() and selected_tables:
    table_schemas = "\n\n".join(
        fetch_schema(table, selected_schema) for table in selected_tables
    )
    prompt = (
        f"Question: {user_input}\n"
        f"Use only these table schemas:\n{table_schemas}\n"
        "Do not reference tables from any other schema.\n"
        "For a WITH query, set operation_type to SELECT.\n"
        "Return only the requested structured SQL query with no markdown and no explanation."
    )
    try:
        with st.spinner("Generating query from the LLM..."):
            response = OpenAI().responses.parse(
                model=os.getenv("OPENAI_MODEL"),
                input=prompt,
                text_format=StrictSQLQuery,
            )
            validated_query = response.output_parsed
            if validated_query is None:
                raise ValueError("The model did not return a structured SQL query.")

        history_item = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(),
            "question": user_input,
            "query": validated_query.query,
            "operation_type": validated_query.operation_type,
            "schema": selected_schema,
            "tables": selected_tables,
        }
        st.session_state.question_history.append(history_item)

        if validated_query.operation_type != "SELECT":
            save_question_history(history_item)
            st.error(
                "Blocked unsafe SQL operation. "
                "Only read-only SELECT or WITH queries are allowed."
            )
        else:
            with st.spinner("Running query against the database..."):
                columns, rows = direct_db_access(validated_query.query)

            history_item["result"] = (
                validated_query.query,
                validated_query.operation_type,
                columns,
                rows,
            )
            st.session_state.last_result = history_item["result"]
            save_question_history(history_item)
            st.rerun()
    except Exception as exc:
        st.error(f"Could not generate or run the query: {exc}")

if st.session_state.last_result is not None:
    query, operation_type, columns, rows = st.session_state.last_result
    st.subheader("Generated query")
    st.code(query, language="sql")
    st.subheader("Results")
    if rows:
        st.dataframe(
            [dict(zip(columns, row)) for row in rows],
            use_container_width=True,
        )
    else:
        st.info("The query returned no rows.")
