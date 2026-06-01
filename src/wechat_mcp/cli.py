from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

from .api import (
    add_contact_by_wechat_id,
    fetch_messages_by_chat,
    publish_moment_with_media,
    publish_moment_without_media,
    reply_to_chat,
    search_chats,
)
from .logging_config import logger
from .wechat_accessibility import get_current_chat_name


def _configure_cli_logging(verbose: bool) -> None:
    for handler in logger.handlers:
        is_console = isinstance(handler, logging.StreamHandler) and not isinstance(
            handler,
            logging.FileHandler,
        )
        if is_console:
            handler.setLevel(logging.INFO if verbose else logging.CRITICAL + 1)


def _write_json(payload: Any) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


def _add_common_json_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print compact JSON instead of pretty JSON.",
    )


def _write_json_with_args(payload: Any, args: argparse.Namespace) -> None:
    if args.compact:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        sys.stdout.write("\n")
        return
    _write_json(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wechat-mac",
        description="Command line tools for automating WeChat on macOS.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Also print runtime logs to stderr.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    current_chat_parser = subparsers.add_parser(
        "current-chat",
        help="Print the currently open WeChat chat title.",
    )
    _add_common_json_args(current_chat_parser)

    fetch_parser = subparsers.add_parser(
        "fetch-messages",
        help="Fetch recent messages from a contact or group chat.",
    )
    fetch_parser.add_argument("--chat", required=True, help="Contact or group name.")
    fetch_parser.add_argument(
        "--last-n",
        type=int,
        default=50,
        help="Number of recent messages to fetch.",
    )
    _add_common_json_args(fetch_parser)

    search_parser = subparsers.add_parser(
        "search-chats",
        help="Search contacts and group chats without opening a result.",
    )
    search_parser.add_argument("--query", required=True, help="Search keyword.")
    _add_common_json_args(search_parser)

    reply_parser = subparsers.add_parser(
        "reply",
        help="Send a message to a contact or group chat.",
    )
    reply_parser.add_argument("--chat", required=True, help="Contact or group name.")
    reply_parser.add_argument("--message", required=True, help="Message to send.")
    _add_common_json_args(reply_parser)

    add_contact_parser = subparsers.add_parser(
        "add-contact",
        help="Add a contact by WeChat ID.",
    )
    add_contact_parser.add_argument("--wechat-id", required=True, help="WeChat ID.")
    add_contact_parser.add_argument(
        "--friending-msg",
        help="Optional friend request message.",
    )
    add_contact_parser.add_argument("--remark", help="Optional contact remark.")
    add_contact_parser.add_argument("--tags", help="Optional tags text.")
    add_contact_parser.add_argument(
        "--privacy",
        choices=["all", "chats_only"],
        default="all",
        help="Privacy mode for the new contact.",
    )
    add_contact_parser.add_argument(
        "--hide-my-posts",
        action="store_true",
        help="Hide your Moments posts from this contact.",
    )
    add_contact_parser.add_argument(
        "--hide-their-posts",
        action="store_true",
        help="Hide this contact's Moments posts.",
    )
    _add_common_json_args(add_contact_parser)

    moment_parser = subparsers.add_parser(
        "publish-moment",
        help="Publish or prepare a Moments post.",
    )
    moment_parser.add_argument("--content", required=True, help="Moment text content.")
    moment_parser.add_argument(
        "--image",
        action="append",
        dest="images",
        help="Image path to include. Currently supports one image.",
    )
    moment_parser.add_argument(
        "--draft",
        action="store_true",
        help="Fill the composer but do not click Post.",
    )
    _add_common_json_args(moment_parser)

    return parser


def run_command(args: argparse.Namespace) -> Any:
    if args.command == "current-chat":
        return {"current_chat": get_current_chat_name()}

    if args.command == "fetch-messages":
        if args.last_n <= 0:
            return {"error": "--last-n must be greater than 0"}
        return fetch_messages_by_chat(chat_name=args.chat, last_n=args.last_n)

    if args.command == "search-chats":
        return search_chats(query=args.query)

    if args.command == "reply":
        return reply_to_chat(chat_name=args.chat, message=args.message)

    if args.command == "add-contact":
        return add_contact_by_wechat_id(
            wechat_id=args.wechat_id,
            friending_msg=args.friending_msg,
            remark=args.remark,
            tags=args.tags,
            privacy=args.privacy,
            hide_my_posts=args.hide_my_posts,
            hide_their_posts=args.hide_their_posts,
        )

    if args.command == "publish-moment":
        if args.images:
            return publish_moment_with_media(
                content=args.content,
                image_paths=args.images,
                publish=not args.draft,
            )
        return publish_moment_without_media(
            content=args.content,
            publish=not args.draft,
        )

    raise ValueError(f"Unsupported command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_cli_logging(verbose=args.verbose)
    try:
        result = run_command(args)
    except Exception as exc:  # noqa: BLE001
        logger.exception("CLI command %s failed: %s", args.command, exc)
        result = {
            "error": str(exc),
            "command": args.command,
        }
    _write_json_with_args(result, args)
    return 1 if isinstance(result, dict) and result.get("error") else 0


if __name__ == "__main__":
    raise SystemExit(main())
