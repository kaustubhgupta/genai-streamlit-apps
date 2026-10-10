# Gen AI Apps

This project is part of the **GenAI Bootcamp**. It provides Streamlit applications for querying and exploring PostgreSQL data using natural language.

## Available Applications

0. **Ingestion Manager** — Ingest data from PDF and text files. The application supports ingesting documents in fixed and recursive chunking strategies along with option to de ingest.
1. **Database Querying** — Select a schema and tables, ask a question in plain English, generate a validated read-only SQL query, and view the results.
2. **Data Chat** — Select data sources and chat with your data. The application generates and executes read-only SQL when needed, while supporting follow-up questions and chat history.
3. **Database Assistant** — Ask database questions conversationally. The assistant can call database tools to inspect schemas and retrieve results, with support for follow-up conversations and saved chats.
4. **Bootcamp Assistant** — Ask questions about the GenAI Bootcamp and receive answers based on the bootcamp content. The assistant can provide follow-up answers and save chat history."


All applications are available from the main interface and can be switched between using the sidebar.

## Usage

Open the application and use the sidebar to select the tool you want to explore. For the querying and chat applications, choose a schema and at least one table before asking a question. Previous questions and conversations can be restored from the sidebar.