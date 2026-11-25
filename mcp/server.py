import sys
from pathlib import Path

from fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utility.tools.pg_tools import direct_db_access, fetch_schema
from utility.tools.rag_query_tools import query_rag_documents
import os

CHUNK_SIZE_FILTER_THRESHOLD = int(os.environ.get("CHUNK_SIZE_FILTER_THRESHOLD"))
VECTOR_SEARCH_CHUNK_THRESHOLD = int(os.environ.get("VECTOR_SEARCH_CHUNK_THRESHOLD"))
KEYWORD_SEARCH_CHUNK_THRESHOLD = int(os.environ.get("KEYWORD_SEARCH_CHUNK_THRESHOLD"))
RERANK_TOP_K = int(os.environ.get("RERANK_TOP_K"))

mcp_app = FastMCP("MCP Tools")


@mcp_app.tool()
def mcp_fetch_schema(table_name, schema="public"):
    """Function to fetch schema of a table in postgress database.

    Args:
        table_name: name of the table
        schema: schema where table needs to be searched

    Returns:
        descriptive table schema in LLM friendly manner.

    Example Output:
        Schema: retail_data
        Table: inventory_master
        Columns:
            inventory_id: bigint
            inventory_date: date
            store_id: bigint
            product_id: bigint
            opening_qty: integer
            received_qty: integer
            sold_qty: integer
            damaged_qty: integer
    """
    return fetch_schema(table_name, schema)


@mcp_app.tool()
def mcp_direct_db_access(script):
    """Execute a SQL query against PostgreSQL DML and DDL queries are supported.
       But no delete operations are allowed. If passed, it will be ignored and
       no changes will be made to the database.

    Args:
        script: SQL script to be executed

    Returns:
        For SELECT queries:
        Returns:
            columns -> list of column names
            rows    -> list of tuples

        For non-SELECT queries:
            Returns:
                [] -> no columns
                [] -> no rows
    """
    if "delete" in script.lower():
        return {
            "columns": [],
            "rows": [],
            "message": "Delete operations are not allowed.",
        }
    return direct_db_access(script)


@mcp_app.tool()
def mcp_query_bootcamp_materials(
    user_input,
    chunked_data_type="recursive",
    rerank_strategy="strategy1",
    keyword_search_flag=True,
    CHUNK_SIZE_FILTER_THRESHOLD=CHUNK_SIZE_FILTER_THRESHOLD,
    VECTOR_SEARCH_CHUNK_THRESHOLD=VECTOR_SEARCH_CHUNK_THRESHOLD,
    KEYWORD_SEARCH_CHUNK_THRESHOLD=KEYWORD_SEARCH_CHUNK_THRESHOLD,
    RERANK_TOP_K=RERANK_TOP_K,
):
    """Retrieve and assemble relevant RAG chunks for a user query on everything related to bootcamp.
       The bootcamp content is stored in a vector database and this tool helps to fetch the relevant chunks from it.
       The bootcamp is related to AI engineering.

    This tool converts the input question into embeddings, searches the vector store
    for the nearest chunks using the chunked data strategy, filters out chunks below a
    configured length threshold, optionally reranks the remaining chunks, and returns
    a newline-delimited context string that includes per-chunk scores and source
    document names.

    Args:
        user_input (str, required): The natural-language question or instruction to answer.
        chunked_data_type (str, required): can take these 2 vales -> "fixed" or "recursive".
        rerank_strategy (str, optional): can take these 2 vales -> "strategy1" or "strategy2".
                        default value is: strategy1. Don't make change to this parameter unless you already tried
                        once and didn't got the expected answer
        keyword_search_flag (bool, optional): Whether to include results from keyword-based search. Default value is: True.
        CHUNK_SIZE_FILTER_THRESHOLD (int, optional): Minimum chunk length required for
            inclusion. Defaults to the module-level threshold.
        VECTOR_SEARCH_CHUNK_THRESHOLD (int, optional): Maximum number of candidate chunks
            to retrieve from the vector database. Defaults to the module-level threshold.
        KEYWORD_SEARCH_CHUNK_THRESHOLD (int, optional): Maximum number of keyword search
            results to include. Defaults to the module-level threshold.
        RERANK_TOP_K (int, optional): Maximum number of reranked chunks to keep in the
            final result. Defaults to the module-level value.

    Returns:
        str: A formatted string containing each selected chunk, a score label, and the
            source document names, with one chunk per line.

    Example:
        query_rag_documents(user_input="How an LLM is trained?")
    """
    return query_rag_documents(
        user_input,
        chunked_data_type,
        rerank_strategy,
        keyword_search_flag,
        CHUNK_SIZE_FILTER_THRESHOLD,
        VECTOR_SEARCH_CHUNK_THRESHOLD,
        KEYWORD_SEARCH_CHUNK_THRESHOLD,
        RERANK_TOP_K,
    )


if __name__ == "__main__":
    # mcp_app.run(transport="stdio")
    mcp_app.run(transport="http", host="127.0.0.1", port=8081)
