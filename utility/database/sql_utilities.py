import json
import os
import re
from typing import Literal

from pydantic import BaseModel, Field

FORBIDDEN_SQL_OPERATIONS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "MERGE",
    "CREATE",
    "ALTER",
    "DROP",
    "TRUNCATE",
    "CALL",
    "EXPLAIN",
)


class StrictSQLQuery(BaseModel):
    query: str = Field(
        ...,
        description="The SQL query to be executed. Return only the requested structured SQL query with no markdown or explanation.",
    )
    operation_type: Literal[
        "INSERT",
        "DELETE",
        "SELECT",
        "UPDATE",
        "MERGE",
        "CREATE",
        "ALTER",
        "DROP",
        "TRUNCATE",
        "CALL",
        "EXPLAIN",
    ] = Field(..., description="The type of SQL operation being performed.")


def contains_forbidden_sql_operation(query):
    """Return the blocked SQL operation found in a query, if any."""
    pattern = r"\\b(" + "|".join(FORBIDDEN_SQL_OPERATIONS) + r")\\b"
    match = re.search(pattern, query, flags=re.IGNORECASE)
    return match.group(1).upper() if match else None


def decode_json_value(value):
    """Decode a JSON string from the database while leaving decoded values intact."""
    return json.loads(value) if isinstance(value, str) else value


def filter_excluded_schemas(schema_tables, excluded_schemas=None):
    """Remove schemas listed in EXCLUDED_SCHEMAS or an explicit comma-separated value."""
    if excluded_schemas is None:
        excluded_schemas = os.getenv("EXCLUDED_SCHEMAS", "")
    excluded = {
        schema.strip().lower()
        for schema in excluded_schemas.split(",")
        if schema.strip()
    }
    return {
        schema: tables
        for schema, tables in schema_tables.items()
        if schema.lower() not in excluded
    }


def sql_literal(value):
    """Return a SQL string literal with embedded quotes escaped."""
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"
