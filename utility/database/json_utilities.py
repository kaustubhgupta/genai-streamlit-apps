import re


def remove_null_characters(value):
    """Remove NUL characters recursively before storing values as PostgreSQL JSONB."""
    if isinstance(value, str):
        return re.sub(r"\\u0000", "", value.replace("\x00", ""), flags=re.IGNORECASE)
    if isinstance(value, list):
        return [remove_null_characters(item) for item in value]
    if isinstance(value, dict):
        return {
            remove_null_characters(key): remove_null_characters(item)
            for key, item in value.items()
        }
    return value
