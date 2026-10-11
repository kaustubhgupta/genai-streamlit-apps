# Gen AI Apps

This project is part of the **GenAI Bootcamp**. It provides Streamlit applications for querying and exploring PostgreSQL data using natural language.

## Available Applications

<img width="959" height="477" alt="image" src="https://github.com/user-attachments/assets/ca2f4fcc-da64-4ab3-a0d9-dcd8b8c65937" />


0. **Ingestion Manager** — Ingest data from PDF and text files. The application supports ingesting documents in fixed and recursive chunking strategies along with option to de ingest.
1. **Database Querying** — Select a schema and tables, ask a question in plain English, generate a validated read-only SQL query, and view the results.
2. **Data Chat** — Select data sources and chat with your data. The application generates and executes read-only SQL when needed, while supporting follow-up questions and chat history.
3. **Database Assistant** — Ask database questions conversationally. The assistant can call database tools to inspect schemas and retrieve results, with support for follow-up conversations and saved chats.
4. **Bootcamp Assistant** — Ask questions about the GenAI Bootcamp and receive answers based on the bootcamp content. The assistant can provide follow-up answers and save chat history.
5. **RAG Evaluator** — Evaluate retrieved context against golden datasets using contextual recall and precision. Configure the dataset, retrieval settings, evaluation thresholds, and judge model in the UI. Answer generation is not run.


All applications are available from the main interface and can be switched between using the sidebar.

## Utility package

Reusable application logic is grouped by responsibility under `utility/`:

- `chunking/` — document text extraction and chunk generation.
- `embeddings/` — embedding model client and embedding generation.
- `retrieval/` — vector-store access, keyword search, and reranking.
- `database/` — SQL validation, database serialization, and schema filtering.
- `ui/` — shared Streamlit history and chat rendering components.
- `ingestion/`, `evaluation/`, and `tools/` — ingestion workflows, evaluation, and tool integrations.

## Usage

Open the application and use the sidebar to select the tool you want to explore. For the querying and chat applications, choose a schema and at least one table before asking a question. Previous questions and conversations can be restored from the sidebar.
