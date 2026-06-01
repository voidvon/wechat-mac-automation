from __future__ import annotations

import json

import pytest

from wechat_mcp import cli


def run_cli(argv: list[str], capsys):
    exit_code = cli.main(argv)
    captured = capsys.readouterr()
    return exit_code, json.loads(captured.out)


def test_help_lists_cli_commands(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--help"])

    captured = capsys.readouterr()
    assert exc_info.value.code == 0
    assert "fetch-messages" in captured.out
    assert "search-chats" in captured.out
    assert "publish-moment" in captured.out


def test_current_chat_outputs_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "get_current_chat_name", lambda: "小区验收")

    exit_code, payload = run_cli(["current-chat"], capsys)

    assert exit_code == 0
    assert payload == {"current_chat": "小区验收"}


def test_fetch_messages_outputs_json(monkeypatch, capsys) -> None:
    def fake_fetch_messages_by_chat(chat_name: str, last_n: int):
        return [
            {
                "sender": "OTHER",
                "text": f"{chat_name}:{last_n}",
            }
        ]

    monkeypatch.setattr(cli, "fetch_messages_by_chat", fake_fetch_messages_by_chat)

    exit_code, payload = run_cli(
        ["fetch-messages", "--chat", "文件传输助手", "--last-n", "2"],
        capsys,
    )

    assert exit_code == 0
    assert payload == [{"sender": "OTHER", "text": "文件传输助手:2"}]


def test_fetch_messages_rejects_invalid_last_n(capsys) -> None:
    exit_code, payload = run_cli(
        ["fetch-messages", "--chat", "文件传输助手", "--last-n", "0"],
        capsys,
    )

    assert exit_code == 1
    assert payload == {"error": "--last-n must be greater than 0"}


def test_search_chats_outputs_json(monkeypatch, capsys) -> None:
    def fake_search_chats(query: str):
        return {
            "query": query,
            "candidates": {
                "contacts": ["阳光茗妹"],
                "group_chats": [],
            },
            "entries": ["联系人", "阳光茗妹"],
        }

    monkeypatch.setattr(cli, "search_chats", fake_search_chats)

    exit_code, payload = run_cli(["search-chats", "--query", "zcca14"], capsys)

    assert exit_code == 0
    assert payload == {
        "query": "zcca14",
        "candidates": {
            "contacts": ["阳光茗妹"],
            "group_chats": [],
        },
        "entries": ["联系人", "阳光茗妹"],
    }


def test_reply_outputs_json(monkeypatch, capsys) -> None:
    def fake_reply_to_chat(chat_name: str, message: str):
        return {
            "chat_name": chat_name,
            "reply_message": message,
            "sent": True,
        }

    monkeypatch.setattr(cli, "reply_to_chat", fake_reply_to_chat)

    exit_code, payload = run_cli(
        ["reply", "--chat", "文件传输助手", "--message", "hello"],
        capsys,
    )

    assert exit_code == 0
    assert payload == {
        "chat_name": "文件传输助手",
        "reply_message": "hello",
        "sent": True,
    }


def test_add_contact_outputs_json(monkeypatch, capsys) -> None:
    def fake_add_contact_by_wechat_id(**kwargs):
        return {
            "wechat_id": kwargs["wechat_id"],
            "privacy": kwargs["privacy"],
            "hide_my_posts": kwargs["hide_my_posts"],
            "hide_their_posts": kwargs["hide_their_posts"],
            "sent": True,
        }

    monkeypatch.setattr(cli, "add_contact_by_wechat_id", fake_add_contact_by_wechat_id)

    exit_code, payload = run_cli(
        [
            "add-contact",
            "--wechat-id",
            "wxid_test",
            "--friending-msg",
            "hi",
            "--remark",
            "Test User",
            "--privacy",
            "chats_only",
            "--hide-my-posts",
            "--hide-their-posts",
        ],
        capsys,
    )

    assert exit_code == 0
    assert payload == {
        "wechat_id": "wxid_test",
        "privacy": "chats_only",
        "hide_my_posts": True,
        "hide_their_posts": True,
        "sent": True,
    }


def test_publish_moment_draft_outputs_json(monkeypatch, capsys) -> None:
    def fake_publish_moment_without_media(content: str, publish: bool):
        return {
            "content": content,
            "posted": publish,
        }

    monkeypatch.setattr(
        cli,
        "publish_moment_without_media",
        fake_publish_moment_without_media,
    )

    exit_code, payload = run_cli(
        ["publish-moment", "--content", "draft text", "--draft"],
        capsys,
    )

    assert exit_code == 0
    assert payload == {
        "content": "draft text",
        "posted": False,
    }


def test_publish_moment_with_image_draft_outputs_json(monkeypatch, capsys) -> None:
    def fake_publish_moment_with_media(
        content: str,
        image_paths: list[str],
        publish: bool,
    ):
        return {
            "content": content,
            "image_paths": image_paths,
            "posted": publish,
        }

    monkeypatch.setattr(
        cli,
        "publish_moment_with_media",
        fake_publish_moment_with_media,
    )

    exit_code, payload = run_cli(
        [
            "publish-moment",
            "--content",
            "image draft",
            "--image",
            "/tmp/example.png",
            "--draft",
        ],
        capsys,
    )

    assert exit_code == 0
    assert payload == {
        "content": "image draft",
        "image_paths": ["/tmp/example.png"],
        "posted": False,
    }


def test_publish_moment_with_multiple_images_rejected(capsys) -> None:
    exit_code, payload = run_cli(
        [
            "publish-moment",
            "--content",
            "image draft",
            "--image",
            "/tmp/a.png",
            "--image",
            "/tmp/b.png",
            "--draft",
        ],
        capsys,
    )

    assert exit_code == 1
    assert payload["error"] == "only one image is currently supported"


def test_compact_json_output(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "get_current_chat_name", lambda: "文件传输助手")

    exit_code = cli.main(["current-chat", "--compact"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == '{"current_chat":"文件传输助手"}\n'
