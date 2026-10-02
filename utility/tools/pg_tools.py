from configparser import ConfigParser
import psycopg2
import logging

logger = logging.getLogger(__name__)


def config(filename="database.ini", section="postgresql"):
    """
    Load database configuration from database.ini.
    """
    parser = ConfigParser()
    parser.read(filename)

    db = {}

    if parser.has_section(section):
        params = parser.items(section)

        for param in params:
            db[param[0]] = param[1]

        logger.info("All DB parameters loaded")

    else:
        error_message = f"Section {section} not found in the {filename} file"

        logger.error(error_message)
        raise Exception(error_message)

    return db


def db_conn():
    """
    Connect to the PostgreSQL database server.
    """
    conn = None

    try:
        params = config()
        conn = psycopg2.connect(**params)

        logger.info("Connection established with PostgreSQL DB")

    except (Exception, psycopg2.DatabaseError) as error:
        logger.exception(error)

    return conn


def direct_db_access(script, caller="data_app"):
    """
    Execute a SQL query against PostgreSQL.

    For SELECT queries:
        Returns:
            columns -> list of column names
            rows    -> list of tuples

    For non-SELECT queries:
        Returns:
            [] -> no columns
            [] -> no rows
    """

    conn = db_conn()

    if conn is None:
        raise ConnectionError(
            "Could not establish a connection to the PostgreSQL database."
        )

    try:
        with conn, conn.cursor() as cur:

            logger.info("Executing SQL query")

            cur.execute(script)

            # SELECT / queries that return a result set
            if cur.description:

                columns = [description[0] for description in cur.description]

                rows = cur.fetchall()

                return (
                    (columns, rows)
                    if caller != "llm"
                    else {"columns": columns, "rows": rows}
                )

            # INSERT / UPDATE / DELETE / DDL
            conn.commit()

            return ([], []) if caller != "llm" else {"columns": [], "rows": []}

    except Exception as error:
        conn.rollback()
        logger.exception(error)
        raise


def fetch_schema(table_name, schema="public"):
    """
    Return a table's schema in an LLM-friendly format.
    """

    table_name = table_name.strip()
    schema = schema.strip()

    if not table_name:
        raise ValueError("Table name cannot be empty")

    if not schema:
        raise ValueError("Schema cannot be empty")

    # Escape single quotes before using values in SQL
    escaped_schema = schema.replace("'", "''")
    escaped_table_name = table_name.replace("'", "''")

    script = f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = '{escaped_schema}'
          AND table_name = '{escaped_table_name}'
        ORDER BY ordinal_position
    """

    try:
        _, columns = direct_db_access(script)

        if not columns:
            raise ValueError(
                f"Table '{table_name}' was not found " f"in the '{schema}' schema"
            )

        return "\n".join(
            [
                f"Schema: {schema}",
                f"Table: {table_name}",
                "Columns:",
                *[
                    f"- {column_name}: {data_type}"
                    for column_name, data_type in columns
                ],
            ]
        )

    except Exception as error:
        logger.exception(error)
        raise


def load_schema_tables():
    """
    Get the full mapping of schema and tables across full database
    """
    schema_tables = {}
    _, rows = direct_db_access("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_type = 'BASE TABLE'
        ORDER BY table_schema, table_name
        """)
    for schema, table in rows or []:
        schema_tables.setdefault(schema, []).append(table)
    return schema_tables


PG_TOOLS = [
    {
        "type": "function",
        "name": "direct_db_access",
        "description": "Execute a SQL query against PostgreSQL",
        "parameters": {
            "type": "object",
            "properties": {
                "script": {
                    "type": "string",
                    "description": "SQL Script to execute in PostgreSQL DB",
                },
                "caller": {
                    "type": "string",
                    "description": "Who is calling this tool, pass value as 'llm' ",
                },
            },
            "required": ["script", "caller"],
        },
    },
    {
        "type": "function",
        "name": "fetch_schema",
        "description": "Return a table schema in an LLM-friendly format.",
        "parameters": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "table name for which schema is required",
                },
                "schema": {
                    "type": "string",
                    "description": "Schema in which table is present",
                },
            },
            "required": ["table_name", "schema"],
        },
    },
    {
        "type": "function",
        "name": "load_schema_tables",
        "description": "Get the full mapping of schema and tables across full database",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]

PG_TOOLS_MAPPING = {
    "direct_db_access": direct_db_access,
    "fetch_schema": fetch_schema,
    "load_schema_tables": load_schema_tables,
}
