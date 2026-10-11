def normalize_response_tool(tool):
    """Convert a function tool definition to the Responses API format."""
    normalized_tool = dict(tool)
    function = normalized_tool.pop("function", None)
    if function:
        normalized_tool.update(function)
    return normalized_tool
