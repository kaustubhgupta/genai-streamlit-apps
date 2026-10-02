import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="GenAI Bootcamp Apps",
    page_icon="🏠",
)


def master_page():
    st.title("GenAI Bootcamp Apps")
    st.write(
        "This homepage provides access to the applications built during the "
        "GenAI Bootcamp. Use the sidebar on the left to explore the available "
        "apps.\n\n"
        "1. **Database Querying** — Select a schema and tables, ask a question in plain English, generate a validated read-only SQL query, and view the results.\n"
        "2. **Data Chat** — Select data sources and chat with your data. The application generates and executes read-only SQL when needed, while supporting follow-up questions and chat history.\n"
        "3. **Database Assistant** — Ask database questions conversationally. The assistant can call database tools to inspect schemas and retrieve results, with support for follow-up conversations and saved chats.\n"
        "4. **Bootcamp Assistant** — Ask questions about the GenAI Bootcamp and receive answers based on the bootcamp content. The assistant can provide follow-up answers and save chat history.\n"
    )


PAGE_NAMES = {
    "data_querying.py": "Data Querying",
    "data_chating.py": "Data Chat",
    "database_assisstant.py": "Database Assistant",
    "bootcamp_assistant.py": "Bootcamp Assistant",
}

PAGE_ORDER = [
    "data_querying.py",
    "data_chating.py",
    "database_assisstant.py",
    "bootcamp_assistant.py",
]

pages_dir = Path(__file__).parent / "pages"

app_pages = []

for page_name in PAGE_ORDER:
    page_path = pages_dir / page_name

    if page_path.exists():
        app_pages.append(
            st.Page(
                str(page_path),
                title=PAGE_NAMES.get(
                    page_name,
                    page_path.stem.replace("_", " ").title(),
                ),
            )
        )

navigation = st.navigation(
    {
        "GenAI Bootcamp Apps": [
            st.Page(
                master_page,
                title="GenAI Bootcamp Apps",
                icon="🏠",
                default=True,
            ),
            *app_pages,
        ]
    }
)

navigation.run()
