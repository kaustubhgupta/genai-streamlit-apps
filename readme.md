# Gen AI Apps

This project is part of the **GenAI Bootcamp**. It provides Streamlit applications for querying and exploring PostgreSQL data using natural language.

## Available Applications

<img width="959" height="477" alt="image" src="https://github.com/user-attachments/assets/ca2f4fcc-da64-4ab3-a0d9-dcd8b8c65937" />


0. **Ingestion Manager** — Ingest PDF and text documents using fixed or recursive chunking, de-ingest documents, generate golden datasets, and scrape NamasteSQL course reviews. The Course reviews tab lists ingested courses and review counts. Re-ingesting an existing course replaces its stored reviews and requires confirmation.
1. **Database Querying** — Select a schema and tables, ask a question in plain English, generate a validated read-only SQL query, and view the results.
2. **Data Chat** — Select data sources and chat with your data. The application generates and executes read-only SQL when needed, while supporting follow-up questions and chat history.
3. **Database Assistant** — Ask database questions conversationally. The assistant can call database tools to inspect schemas and retrieve results, with support for follow-up conversations and saved chats.
4. **Bootcamp Assistant** — Ask questions about the GenAI Bootcamp and receive answers based on the bootcamp content. The assistant can provide follow-up answers and save chat history.
5. **RAG Evaluator** — Evaluate retrieved context against golden datasets using contextual recall and precision. Configure the dataset, retrieval settings, evaluation thresholds, and judge model in the UI. Answer generation is not run.
6. **Course Reviews Deep Dive** — Evaluate ingested course reviews across satisfaction criteria, compare overall and criterion-level 0–5 scores, inspect matching reviews, and browse saved PostgreSQL evaluation history.


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

## Usage

Open the application and use the sidebar to select the tool you want to explore. For the querying and chat applications, choose a schema and at least one table before asking a question. You can restore previous questions and conversations from the sidebar.

### Course review ingestion

Use the **Course reviews** tab in the Ingestion Manager to submit a NamasteSQL course link. The app scrapes the course's reviews and stores course metadata and reviews in the PostgreSQL `reviews.course_reviews_master` and `reviews.course_reviews` tables. If the link is already ingested, the app asks for confirmation before replacing its stored reviews.

The Course Reviews Deep Dive page evaluates each review against the criteria rubric and saves each run, its score summaries, and per-review results to `course_reviews_evaluation.evaluation_history`. Select a previous run from the page's history sidebar to revisit its scores and matching reviews.

The scraper uses Playwright with Chromium. After installing project dependencies, install the browser with:

```sh
playwright install chromium
```
