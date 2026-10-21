# Gen AI Apps

This project is part of the **GenAI Bootcamp**. It provides Streamlit applications for querying and exploring PostgreSQL data, evaluate RAG pipeline or review courses reviews against set of criterias using natural language.

## Available Applications

### 0. Ingestion Manager

Ingest PDF and text documents using fixed or recursive chunking, de-ingest documents, generate golden datasets, and scrape NamasteSQL course reviews. The Course reviews tab lists ingested courses and review counts. Re-ingesting an existing course replaces its stored reviews and requires confirmation.

<details>
<summary>Screenshots (5)</summary>

<table>
  <tr>
    <td><img width="480" alt="Ingestion Manager screenshot 1" src="https://github.com/user-attachments/assets/8a87fe49-c4b1-42ff-af14-eba22bfd731e" /></td>
    <td><img width="480" alt="Ingestion Manager screenshot 2" src="https://github.com/user-attachments/assets/830741c6-32cd-47bf-bb85-79441b904a15" /></td>
  </tr>
  <tr>
    <td><img width="480" alt="Ingestion Manager screenshot 3" src="https://github.com/user-attachments/assets/101bbb74-fc73-4214-8537-8fdaeac1b979" /></td>
    <td><img width="480" alt="Ingestion Manager screenshot 4" src="https://github.com/user-attachments/assets/fe1f0cd7-b369-4132-bc0d-e6d30a5afcd1" /></td>
  </tr>
  <tr>
    <td colspan="2" align="center"><img width="480" alt="Ingestion Manager screenshot 5" src="https://github.com/user-attachments/assets/8cf3b7f9-288b-4730-9a43-78e4f89c0674" /></td>
  </tr>
</table>

</details>

### 1. Database Querying

Select a schema and tables, ask a question in plain English, generate a validated read-only SQL query, and view the results.

<details>
<summary>Screenshots (1)</summary>

<img width="959" alt="Database Querying screenshot" src="https://github.com/user-attachments/assets/80e1cd7a-d890-4cbe-a132-3a2410082448" />

</details>

### 2. Data Chat

Select data sources and chat with your data. The application generates and executes read-only SQL when needed, while supporting follow-up questions and chat history.

<details>
<summary>Screenshots (1)</summary>

<img width="959" alt="Data Chat screenshot" src="https://github.com/user-attachments/assets/9b5f7ce5-bd0d-448b-8507-38e9f52a0099" />

</details>

### 3. Database Assistant

Ask database questions conversationally. The assistant can call database tools to inspect schemas and retrieve results, with support for follow-up conversations and saved chats.

<details>
<summary>Screenshots (1)</summary>

<img width="959" alt="Database Assistant screenshot" src="https://github.com/user-attachments/assets/20872cb0-842a-4f18-b986-292db2d1f9e1" />

</details>

### 4. Bootcamp Assistant

Ask questions about the GenAI Bootcamp and receive answers based on the bootcamp content. The assistant can provide follow-up answers and save chat history.

<details>
<summary>Screenshots (1)</summary>

<img width="959" alt="Bootcamp Assistant screenshot" src="https://github.com/user-attachments/assets/c16768e8-b0e5-49bd-9d1b-d3a2b2df78c6" />

</details>

### 5. RAG Evaluator

Evaluate retrieved context against golden datasets using contextual recall and precision. Configure the dataset, retrieval settings, evaluation thresholds, and judge model in the UI. Answer generation is not run.

<details>
<summary>Screenshots (3)</summary>

<table>
  <tr>
    <td><img width="320" alt="RAG Evaluator screenshot 1" src="https://github.com/user-attachments/assets/aa8f47f7-27c2-4e02-9718-078fc434f5a2" /></td>
    <td><img width="320" alt="RAG Evaluator screenshot 2" src="https://github.com/user-attachments/assets/341ab251-99da-4336-84db-2a6088d9d7d2" /></td>
    <td><img width="320" alt="RAG Evaluator screenshot 3" src="https://github.com/user-attachments/assets/6894c529-a642-435c-9ca6-a4f07d1b4d92" /></td>
  </tr>
</table>

</details>

### 6. Course Reviews Deep Dive

Evaluate ingested course reviews across satisfaction criteria, compare overall and criterion-level 0–5 scores, inspect matching reviews, and browse saved PostgreSQL evaluation history.

<details>
<summary>Screenshots (3)</summary>

<table>
  <tr>
    <td><img width="320" alt="Course Reviews Deep Dive screenshot 1" src="https://github.com/user-attachments/assets/8d19525f-e0e1-40ed-9e7f-21f33a5781e8" /></td>
    <td><img width="320" alt="Course Reviews Deep Dive screenshot 2" src="https://github.com/user-attachments/assets/fff68282-27bd-417d-9674-6a83176ab6d6" /></td>
    <td><img width="320" alt="Course Reviews Deep Dive screenshot 3" src="https://github.com/user-attachments/assets/86944aaf-d24d-4f33-9cb1-719b71e67b4c" /></td>
  </tr>
</table>

</details>

All applications are available from the main interface and can be switched between using the sidebar.

## Utility package

Reusable application logic is grouped by responsibility under `utility/`:

- `chunking/` — document text extraction and chunk generation.
- `embeddings/` — embedding model client and embedding generation.
- `retrieval/` — vector-store access, keyword search, and reranking.
- `database/` — SQL validation, database serialization, schema filtering, and reusable PostgreSQL JSON history persistence.
- `ui/` — shared Streamlit history selectors and chat rendering components.
- `ingestion/` — document ingestion and shared course-review listing/metadata queries.
- `evaluation/` and `tools/` — evaluation workflows and tool integrations.
