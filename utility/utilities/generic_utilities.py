import re
from pydantic import BaseModel, Field
from typing import Literal

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
