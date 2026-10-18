from datetime import datetime

import streamlit as st


def format_history_timestamp(timestamp):
    """Format database or serialized timestamps consistently for history labels."""
    if isinstance(timestamp, datetime):
        return timestamp.astimezone().strftime("%Y-%m-%d %H:%M")
    return str(timestamp).replace("T", " ")[:16]


def render_history_selector(
    history,
    selection_key,
    label,
    empty_message,
    item_id_key="id",
    format_func=None,
    reverse=True,
):
    """Render a reusable history selector and return its selected record ID."""
    if not history:
        st.caption(empty_message)
        return None

    history_items = list(reversed(history)) if reverse else list(history)
    with st.container(height=250, border=False):
        return st.radio(
            label,
            [item[item_id_key] for item in history_items],
            index=None,
            format_func=lambda item_id: (
                format_func(
                    next(item for item in history_items if item[item_id_key] == item_id)
                )
                if format_func
                else next(
                    f'{item["timestamp"]:%Y-%m-%d %H:%M} — {item["question"]}'
                    for item in history_items
                    if item[item_id_key] == item_id
                )
            ),
            key=selection_key,
        )


def render_chat_messages(messages):
    """Render chat messages and any tabular result attached to a message."""
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("rows"):
                st.dataframe(
                    [dict(zip(message["columns"], row)) for row in message["rows"]],
                    use_container_width=True,
                )
