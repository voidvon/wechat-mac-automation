from __future__ import annotations

import time
from typing import Any

from .add_contact_by_wechat_id_utils import (
    add_contact_by_wechat_id as ax_add_contact_by_wechat_id,
)
from .fetch_messages_by_chat_utils import ChatMessage, fetch_recent_messages
from .logging_config import logger
from .publish_moment_utils import publish_moment_with_media as ax_publish_moment_media
from .publish_moment_utils import publish_moment_without_media as ax_publish_moment
from .reply_to_messages_by_chat_utils import send_message
from .wechat_accessibility import get_current_chat_name, open_chat_for_contact
from .wechat_accessibility import (
    _collect_search_entries,
    _summarize_search_candidates,
    focus_and_type_search,
    get_search_list,
    get_wechat_ax_app,
)


def ensure_chat_open(chat_name: str) -> dict[str, Any] | None:
    """
    Ensure the requested chat is open in WeChat.

    Returns None on success. When WeChat search cannot resolve an exact chat
    match, returns the candidate/error payload produced by the accessibility
    layer.
    """
    current_chat = get_current_chat_name()
    same_chat = current_chat == chat_name if current_chat is not None else False
    logger.info(
        "Current chat title=%r, target=%r, same_chat=%s",
        current_chat,
        chat_name,
        same_chat,
    )
    if same_chat:
        return None

    open_result = open_chat_for_contact(chat_name)
    if isinstance(open_result, dict) and open_result.get("error"):
        return open_result
    return None


def search_chats(query: str) -> dict[str, Any]:
    """
    Search WeChat contacts/groups without opening a result.
    """
    try:
        ax_app = get_wechat_ax_app()
        focus_and_type_search(ax_app, query)
        time.sleep(0.5)
        search_list = get_search_list(ax_app)
        entries = _collect_search_entries(search_list)
        candidates = _summarize_search_candidates(entries)
        return {
            "query": query,
            "candidates": candidates,
            "entries": [entry.text for entry in entries if entry.text],
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error in search_chats for query=%s: %s", query, exc)
        return {
            "error": str(exc),
            "query": query,
        }


def fetch_messages_by_chat(chat_name: str, last_n: int = 50) -> list[dict[str, Any]]:
    """
    Fetch recent messages from a contact or group chat.
    """
    try:
        logger.info("API fetch_messages_by_chat called for chat=%s", chat_name)
        open_error = ensure_chat_open(chat_name)
        if open_error is not None:
            enriched = dict(open_error)
            enriched.setdefault("tool", "fetch_messages_by_chat")
            return [enriched]

        messages: list[ChatMessage] = fetch_recent_messages(last_n=last_n)
        result = [msg.to_dict() for msg in messages]
        logger.info("Returning %d messages for chat=%s", len(result), chat_name)
        return result
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Error in fetch_messages_by_chat for chat=%s: %s",
            chat_name,
            exc,
        )
        return [
            {
                "error": str(exc),
                "chat_name": chat_name,
            }
        ]


def reply_to_messages_by_chat(
    chat_name: str,
    reply_message: str | None = None,
) -> dict[str, Any]:
    """
    Open a contact or group chat and optionally send a reply.
    """
    logger.info(
        "API reply_to_messages_by_chat called for chat=%s (has_reply=%s)",
        chat_name,
        bool(reply_message),
    )
    try:
        open_error = ensure_chat_open(chat_name)
        if open_error is not None:
            return {
                "error": open_error.get("error"),
                "chat_name": chat_name,
                "candidates": open_error.get("candidates", {}),
                "reply_message": reply_message,
                "sent": False,
                "tool": "reply_to_messages_by_chat",
            }

        sent = False
        if reply_message is not None and reply_message.strip():
            send_message(reply_message)
            sent = True
            logger.info(
                "Reply sent to chat=%s; message length=%d",
                chat_name,
                len(reply_message),
            )

        return {
            "chat_name": chat_name,
            "reply_message": reply_message,
            "sent": sent,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Error in reply_to_messages_by_chat for chat=%s: %s",
            chat_name,
            exc,
        )
        return {
            "error": str(exc),
            "chat_name": chat_name,
        }


def reply_to_chat(chat_name: str, message: str) -> dict[str, Any]:
    """
    Convenience alias for callers that want to send a non-empty message.
    """
    return reply_to_messages_by_chat(chat_name=chat_name, reply_message=message)


def add_contact_by_wechat_id(
    wechat_id: str,
    friending_msg: str | None = None,
    remark: str | None = None,
    tags: str | None = None,
    privacy: str | None = None,
    hide_my_posts: bool = False,
    hide_their_posts: bool = False,
) -> dict[str, Any]:
    """
    Add a new contact by WeChat ID.
    """
    logger.info(
        "API add_contact_by_wechat_id called for ID=%s (privacy=%r)",
        wechat_id,
        privacy,
    )
    try:
        return ax_add_contact_by_wechat_id(
            wechat_id=wechat_id,
            friending_msg=friending_msg,
            remark=remark,
            tags=tags,
            privacy=privacy,
            hide_my_posts=hide_my_posts,
            hide_their_posts=hide_their_posts,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Error in add_contact_by_wechat_id for ID=%s: %s",
            wechat_id,
            exc,
        )
        return {
            "error": str(exc),
            "wechat_id": wechat_id,
        }


def publish_moment_without_media(
    content: str,
    publish: bool = True,
) -> dict[str, Any]:
    """
    Publish or prepare a text-only Moments post.
    """
    logger.info(
        "API publish_moment_without_media called (content_length=%d, publish=%s)",
        len(content) if isinstance(content, str) else -1,
        publish,
    )
    try:
        return ax_publish_moment(content=content, publish=publish)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error in publish_moment_without_media: %s", exc)
        return {
            "error": str(exc),
            "content": content,
        }


def publish_moment_with_media(
    content: str,
    image_paths: list[str],
    publish: bool = True,
) -> dict[str, Any]:
    """
    Publish or prepare a Moments post with image media.
    """
    logger.info(
        "API publish_moment_with_media called (content_length=%d, image_count=%d, publish=%s)",
        len(content) if isinstance(content, str) else -1,
        len(image_paths),
        publish,
    )
    try:
        return ax_publish_moment_media(
            content=content,
            image_paths=image_paths,
            publish=publish,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error in publish_moment_with_media: %s", exc)
        return {
            "error": str(exc),
            "content": content,
            "image_paths": image_paths,
        }
