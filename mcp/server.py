import sys
from pathlib import Path

from fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utility.tools.pg_tools import direct_db_access, fetch_schema, load_schema_tables

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


if __name__ == "__main__":
    mcp_app.run(transport="stdio")
