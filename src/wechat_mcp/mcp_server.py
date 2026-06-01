from __future__ import annotations

import argparse
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from .api import (
    add_contact_by_wechat_id as api_add_contact_by_wechat_id,
    fetch_messages_by_chat as api_fetch_messages_by_chat,
    publish_moment_without_media as api_publish_moment_without_media,
    reply_to_messages_by_chat as api_reply_to_messages_by_chat,
)
from .logging_config import logger


mcp = FastMCP("WeChat Helper MCP Server")


@mcp.tool()
def fetch_messages_by_chat(
    chat_name: str,
    last_n: int = 50,
) -> list[dict[str, Any]]:
    """
    Fetch recent messages for a specific chat (contact or group).

    This will:
    - Look for the chat in the left sidebar session list
    - If found, click it to open the chat
    - If not found, search for the chat via the search box
    - Once the chat is open, retrieve recent messages from that chat
    """
    return api_fetch_messages_by_chat(chat_name=chat_name, last_n=last_n)


@mcp.tool()
def reply_to_messages_by_chat(
    chat_name: str,
    reply_message: str | None = None,
) -> dict[str, Any]:
    """
    Optionally send a reply to a chat (contact or group).

    This tool is designed to be driven by the LLM using this MCP:
    - Call fetch_messages_by_chat first to inspect conversation history.
    - Have the LLM compose a reply string.
    - Call this tool with that reply string to send it.

    If reply_message is None or empty, no message is sent; the tool still
    ensures the chat is open.
    """
    return api_reply_to_messages_by_chat(
        chat_name=chat_name,
        reply_message=reply_message,
    )


@mcp.tool()
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
    Add a new contact using a WeChat ID.

    This tool automates the WeChat flow:
    - Type the given WeChat ID into the global search box.
    - Click the "Search WeChat ID" card under the "More" section.
    - In the "Add Contacts" window, click "Add to Contacts".
    - In the "Send Friend Request" window, optionally customize the
      friending message, remark, and privacy options, then confirm.

    The `privacy` argument controls the "Privacy" section of the
    friend-request window:
    - "all" (default) selects "Chats, Moments, WeRun, etc." and applies
      the `hide_my_posts` / `hide_their_posts` flags.
    - "chats_only" selects "Chats Only" and ignores the hide flags.
    """
    return api_add_contact_by_wechat_id(
        wechat_id=wechat_id,
        friending_msg=friending_msg,
        remark=remark,
        tags=tags,
        privacy=privacy,
        hide_my_posts=hide_my_posts,
        hide_their_posts=hide_their_posts,
    )


@mcp.tool()
def publish_moment_without_media(
    content: str,
    publish: bool = True,
) -> dict[str, Any]:
    """
    Publish a Moments post containing only text (no media).

    This will:
    - Open the main WeChat window and click the "Moments" button.
    - Long-press the "Post" button in the Moments window to open the
      composer sheet.
    - Fill the text entry area with the provided content.
    - If `publish` is True (default), click the "Post" button in the
      sheet to publish the moment; if False, leave the composer open
      without sending.
    """
    return api_publish_moment_without_media(content=content, publish=publish)


def main() -> None:
    """
    Entry point for the WeChat MCP server.
    """
    parser = argparse.ArgumentParser(description="WeChat Helper MCP Server")
    parser.add_argument(
        "--mcp-debug",
        action="store_true",
        help="Enable detailed MCP protocol debugging logs",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default="stdio",
        help="Transport protocol to use (default: stdio)",
    )

    args = parser.parse_args()

    if args.mcp_debug:
        logging.getLogger("mcp").setLevel(logging.DEBUG)
        logging.getLogger("anyio").setLevel(logging.DEBUG)
        logging.getLogger("httpx").setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

        debug_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(funcName)s:%(lineno)d - %(message)s"
        )
        for handler in logging.getLogger().handlers:
            handler.setFormatter(debug_formatter)

    logger.info("Starting WeChat Helper MCP Server")
    logger.info("Transport: %s", args.transport)
    logger.info("MCP Debug mode: %s", args.mcp_debug)

    if args.transport == "stdio":
        mcp.run()
    elif args.transport == "streamable-http":
        mcp.run(transport="streamable-http")
    elif args.transport == "sse":
        mcp.run(transport="sse")


if __name__ == "__main__":
    main()
