"""Python API for automating WeChat on macOS."""

from .api import (
    add_contact_by_wechat_id,
    ensure_chat_open,
    fetch_messages_by_chat,
    publish_moment_with_media,
    publish_moment_without_media,
    reply_to_chat,
    reply_to_messages_by_chat,
    search_chats,
)

__all__ = [
    "add_contact_by_wechat_id",
    "ensure_chat_open",
    "fetch_messages_by_chat",
    "publish_moment_with_media",
    "publish_moment_without_media",
    "reply_to_chat",
    "reply_to_messages_by_chat",
    "search_chats",
]
