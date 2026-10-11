import streamlit as st


def render_history_selector(history, selection_key, label, empty_message):
    """Render the common reverse-chronological selector used by history sidebars."""
    if not history:
        st.caption(empty_message)
        return

    history_items = list(reversed(history))
    with st.container(height=250, border=False):
        st.radio(
            label,
            [item["id"] for item in history_items],
            index=None,
            format_func=lambda item_id: next(
                f'{item["timestamp"]:%Y-%m-%d %H:%M} — {item["question"]}'
                for item in history_items
                if item["id"] == item_id
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
