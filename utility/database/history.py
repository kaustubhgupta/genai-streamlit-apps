import json
import re

from utility.database.json_utilities import remove_null_characters
from utility.database.sql_utilities import decode_json_value, sql_literal
from utility.tools.pg_tools import direct_db_access

IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
SUPPORTED_COLUMN_TYPES = {"TEXT", "TIMESTAMPTZ", "JSONB"}


def _qualified_table(schema, table):
    if not IDENTIFIER_RE.fullmatch(schema) or not IDENTIFIER_RE.fullmatch(table):
        raise ValueError(
            "History schema and table names must be simple SQL identifiers."
        )
    return f'"{schema}"."{table}"'


def _validate_columns(columns, primary_key):
    if primary_key not in columns:
        raise ValueError(f"History columns must include primary key '{primary_key}'.")
    for name, column_type in columns.items():
        if not IDENTIFIER_RE.fullmatch(name):
            raise ValueError(f"Invalid history column name: {name}")
        if column_type not in SUPPORTED_COLUMN_TYPES:
            raise ValueError(f"Unsupported history column type: {column_type}")


def ensure_history_table(schema, table, columns, primary_key="id", nullable_columns=()):
    """Create a JSON-friendly history table using validated identifiers/types."""
    _qualified_table(schema, table)
    _validate_columns(columns, primary_key)
    if not set(nullable_columns).issubset(columns):
        raise ValueError("Nullable history columns must be declared table columns.")
    direct_db_access(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
    definitions = []
    for name, column_type in columns.items():
        definition = f'"{name}" {column_type}'
        if name == primary_key:
            definition += " PRIMARY KEY"
        elif name not in nullable_columns:
            definition += " NOT NULL"
        definitions.append(definition)
    direct_db_access(
        f"CREATE TABLE IF NOT EXISTS {_qualified_table(schema, table)} "
        f"({', '.join(definitions)})"
    )


def load_history_records(
    schema,
    table,
    columns,
    order_by,
    primary_key="id",
    descending=True,
    nullable_columns=(),
):
    """Load history rows as dictionaries, decoding JSONB columns."""
    ensure_history_table(schema, table, columns, primary_key, nullable_columns)
    _validate_columns(columns, primary_key)
    if order_by not in columns:
        raise ValueError(f"Unknown history order column: {order_by}")

    selected_columns = ", ".join(f'"{name}"' for name in columns)
    direction = "DESC" if descending else "ASC"
    _, rows = direct_db_access(
        f"SELECT {selected_columns} FROM {_qualified_table(schema, table)} "
        f'ORDER BY "{order_by}" {direction}'
    )
    json_columns = {
        name for name, column_type in columns.items() if column_type == "JSONB"
    }
    return [
        {
            name: decode_json_value(value) if name in json_columns else value
            for name, value in zip(columns, row)
        }
        for row in (rows or [])
    ]


def save_history_record(
    schema,
    table,
    columns,
    record,
    update_columns=(),
    primary_key="id",
    nullable_columns=(),
):
    """Insert a history row, serializing JSONB and timestamp columns safely."""
    ensure_history_table(schema, table, columns, primary_key, nullable_columns)
    _validate_columns(columns, primary_key)
    missing = set(columns) - record.keys()
    if missing:
        raise ValueError("Missing history values for: " + ", ".join(sorted(missing)))
    if any(name not in columns or name == primary_key for name in update_columns):
        raise ValueError("History update columns must be non-key table columns.")

    values = []
    for name, column_type in columns.items():
        value = record[name]
        if column_type == "JSONB":
            value = (
                sql_literal(
                    json.dumps(
                        remove_null_characters(value),
                        ensure_ascii=False,
                        default=str,
                    )
                )
                if value is not None
                else "NULL"
            )
            values.append(f"{value}::jsonb")
        elif column_type == "TIMESTAMPTZ":
            timestamp = value.isoformat() if hasattr(value, "isoformat") else value
            values.append(f"{sql_literal(timestamp)}::timestamptz")
        else:
            values.append(sql_literal(value))

    columns_sql = ", ".join(f'"{name}"' for name in columns)
    values_sql = ", ".join(values)
    statement = (
        f"INSERT INTO {_qualified_table(schema, table)} "
        f"({columns_sql}) VALUES ({values_sql})"
    )
    if update_columns:
        updates_sql = ", ".join(
            f'"{name}" = EXCLUDED."{name}"' for name in update_columns
        )
        statement += f' ON CONFLICT ("{primary_key}") DO UPDATE SET {updates_sql}'
    direct_db_access(statement)
