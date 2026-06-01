from __future__ import annotations

from pathlib import Path
import time
from typing import Any

import AppKit
from ApplicationServices import (
    AXUIElementPerformAction,
    AXUIElementSetAttributeValue,
    kAXButtonRole,
    kAXRaiseAction,
    kAXSheetRole,
    kAXTextAreaRole,
    kAXValueAttribute,
)

from .logging_config import logger
from .wechat_accessibility import (
    _find_window_by_titles,
    _wait_for_window_titles,
    click_element_center,
    dfs,
    get_wechat_ax_app,
    long_press_element_center,
    send_key_with_modifiers,
)
from Quartz import kCGEventFlagMaskCommand, kCGEventFlagMaskShift
from .reply_to_messages_by_chat_utils import press_return


MAIN_WINDOW_TITLES = ("WeChat", "微信")
MOMENTS_WINDOW_TITLES = ("Moments", "朋友圈")
MOMENTS_BUTTON_TITLES = ("Moments", "朋友圈")
POST_BUTTON_TITLES = ("Post", "发表")


def _open_moments_window(ax_app: Any, timeout: float = 5.0) -> Any:
    """
    Ensure the WeChat Moments window is open by clicking the Moments
    button in the main WeChat window and waiting for the Moments window
    to appear.
    """
    moments_window = _find_window_by_titles(ax_app, MOMENTS_WINDOW_TITLES)
    if moments_window is not None:
        return moments_window

    main_window = _find_window_by_titles(ax_app, MAIN_WINDOW_TITLES)
    if main_window is None:
        raise RuntimeError(
            "Could not find main WeChat window with title 'WeChat' or '微信'"
        )

    def is_moments_button(el, role, title, identifier):
        return (
            role == kAXButtonRole
            and isinstance(title, str)
            and title in MOMENTS_BUTTON_TITLES
        )

    button = dfs(main_window, is_moments_button)
    if button is None:
        raise RuntimeError(
            "Could not find 'Moments'/'朋友圈' button in WeChat main window"
        )

    logger.info("Clicking Moments button in main window")
    click_element_center(button)
    time.sleep(0.4)

    moments_window = _wait_for_window_titles(
        ax_app,
        MOMENTS_WINDOW_TITLES,
        timeout=timeout,
    )
    if moments_window is None:
        raise RuntimeError(
            "The 'Moments'/'朋友圈' window did not appear after clicking"
        )

    return moments_window


def _open_moment_composer(moments_window: Any) -> None:
    """
    Open the Moments composer sheet by long-pressing the Post button in
    the Moments window.
    """

    def is_post_button(el, role, title, identifier):
        return (
            role == kAXButtonRole
            and isinstance(title, str)
            and title in POST_BUTTON_TITLES
        )

    button = dfs(moments_window, is_post_button)
    if button is None:
        raise RuntimeError("Could not find 'Post'/'发表' button in Moments window")

    logger.info("Long-pressing Post button to open composer sheet")
    long_press_element_center(button, hold_seconds=1.4)
    time.sleep(0.3)


def _click_moment_post_button(moments_window: Any) -> None:
    """
    Click the Moments Post button to open the media file picker.
    """

    def is_post_button(el, role, title, identifier):
        return (
            role == kAXButtonRole
            and isinstance(title, str)
            and title in POST_BUTTON_TITLES
        )

    button = dfs(moments_window, is_post_button)
    if button is None:
        raise RuntimeError("Could not find 'Post'/'发表' button in Moments window")

    logger.info("Clicking Post button to open media picker")
    click_element_center(button)
    time.sleep(0.6)


def _find_open_panel(root: Any) -> Any | None:
    """
    Locate the macOS open panel attached to the Moments window.
    """

    def is_open_panel(el, role, title, identifier):
        return role == kAXSheetRole and identifier == "open-panel"

    return dfs(root, is_open_panel)


def _wait_for_open_panel(root: Any, timeout: float = 5.0) -> Any:
    end = time.time() + timeout
    while time.time() < end:
        panel = _find_open_panel(root)
        if panel is not None:
            logger.info("Found macOS open panel")
            return panel
        time.sleep(0.1)
    raise RuntimeError("The macOS open panel did not appear after clicking Post")


def _wait_for_open_panel_to_close(root: Any, timeout: float = 8.0) -> None:
    end = time.time() + timeout
    while time.time() < end:
        if _find_open_panel(root) is None:
            logger.info("macOS open panel closed")
            return
        time.sleep(0.1)
    raise RuntimeError("The macOS open panel did not close after selecting media")


def _find_open_button(root: Any) -> Any | None:
    def is_open_button(el, role, title, identifier):
        return (
            role == kAXButtonRole
            and (identifier == "OKButton" or title in ("Open", "打开"))
        )

    return dfs(root, is_open_button)


def _select_file_in_open_panel(panel: Any, path: Path) -> None:
    """
    Select a file in the macOS open panel using Cmd+Shift+G and a POSIX path.
    """
    pb = AppKit.NSPasteboard.generalPasteboard()
    pb.clearContents()
    pb.setString_forType_(str(path), AppKit.NSPasteboardTypeString)

    send_key_with_modifiers(
        5,  # G
        kCGEventFlagMaskCommand | kCGEventFlagMaskShift,
    )
    time.sleep(0.2)
    send_key_with_modifiers(9, kCGEventFlagMaskCommand)  # V
    time.sleep(0.1)
    press_return()
    time.sleep(0.8)

    open_button = _find_open_button(panel)
    if open_button is None:
        raise RuntimeError("Could not find Open/打开 button in macOS open panel")

    click_element_center(open_button)
    time.sleep(1.0)


def _find_moments_sheet(moments_window: Any, timeout: float = 5.0) -> Any | None:
    """
    Wait for the Moments composer sheet to appear inside the Moments
    window, returning the sheet element or None if the timeout expires.
    """

    def is_sheet(el, role, title, identifier):
        return role == kAXSheetRole

    end = time.time() + timeout
    while time.time() < end:
        sheet = dfs(moments_window, is_sheet)
        if sheet is not None:
            logger.info("Found Moments composer sheet")
            return sheet
        time.sleep(0.1)

    logger.warning("Timed out waiting for Moments composer sheet")
    return None


def _find_editor_root(moments_window: Any, timeout: float = 5.0) -> Any | None:
    """
    Return the root element that contains the Moments composer controls.

    Prefer the dedicated AXSheet element; fall back to the Moments
    window itself if the sheet cannot be located.
    """
    sheet = _find_moments_sheet(moments_window, timeout=timeout)
    if sheet is not None:
        return sheet

    logger.warning(
        "Falling back to using the Moments window as editor root "
        "because composer sheet was not found"
    )
    return moments_window


def _find_moment_text_area(root: Any) -> Any | None:
    """
    Locate the text entry area used to compose a Moments post.
    """

    def is_text_area(el, role, title, identifier):
        return role == kAXTextAreaRole

    return dfs(root, is_text_area)


def _find_post_button_in_editor(root: Any) -> Any | None:
    """
    Locate the Post button within the composer editor root (sheet or
    Moments window).
    """

    def is_post_button(el, role, title, identifier):
        return (
            role == kAXButtonRole
            and isinstance(title, str)
            and title in POST_BUTTON_TITLES
        )

    return dfs(root, is_post_button)


def publish_moment_without_media(content: str, publish: bool = True) -> dict[str, Any]:
    """
    Publish a Moments post containing only text (no media).

    High-level flow:
    - Click the "Moments" button in the main WeChat window to open the
      Moments window.
    - Long-press the "Post" button in the Moments window to reveal the
      composer sheet.
    - In the composer sheet, set the text entry area's value to the
      provided content.
    - If `publish` is True (default), click the "Post" button in the
      sheet to publish the moment; if False, leave the composer open
      without sending, so that the user can modify the draft in the
      composer.
    """
    if not isinstance(content, str) or not content.strip():
        return {
            "error": "content must be a non-empty string",
            "content": content,
            "stage": "validate_input",
        }

    logger.info(
        "Starting publish_moment_without_media (content_length=%d, publish=%s)",
        len(content),
        publish,
    )

    try:
        ax_app = get_wechat_ax_app()
        moments_window = _open_moments_window(ax_app)
        _open_moment_composer(moments_window)

        editor_root = _find_editor_root(moments_window, timeout=5.0)
        if editor_root is None:
            error_msg = "Could not locate Moments composer editor root"
            logger.warning(error_msg)
            return {
                "error": error_msg,
                "content": content,
                "stage": "editor_root",
            }

        text_area = _find_moment_text_area(editor_root)
        if text_area is None:
            error_msg = "Could not find text entry area in Moments composer"
            logger.warning(error_msg)
            return {
                "error": error_msg,
                "content": content,
                "stage": "text_area",
            }

        AXUIElementPerformAction(text_area, kAXRaiseAction)
        err = AXUIElementSetAttributeValue(text_area, kAXValueAttribute, content)
        if err != 0:
            error_msg = f"Failed to set composer text, AX error {err}"
            logger.warning(error_msg)
            return {
                "error": error_msg,
                "content": content,
                "stage": "set_text",
            }

        if not publish:
            logger.info(
                "Moments composer text updated; publish=False so skipping Post click"
            )
            return {
                "content": content,
                "posted": False,
            }

        logger.info("Moments composer text updated; clicking Post in sheet")
        post_button = _find_post_button_in_editor(editor_root)
        if post_button is None:
            error_msg = "Could not find 'Post'/'发表' button in Moments composer"
            logger.warning(error_msg)
            return {
                "error": error_msg,
                "content": content,
                "stage": "post_button",
            }

        click_element_center(post_button)
        time.sleep(0.5)

        logger.info("Moments post submitted successfully")
        return {
            "content": content,
            "posted": True,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error while publishing moment without media: %s", exc)
        return {
            "error": str(exc),
            "content": content,
            "stage": "unexpected_error",
        }


def publish_moment_with_media(
    content: str,
    image_paths: list[str],
    publish: bool = True,
) -> dict[str, Any]:
    """
    Publish a Moments post with image media and text content.
    """
    if not isinstance(content, str):
        return {
            "error": "content must be a string",
            "content": content,
            "stage": "validate_input",
        }

    if not image_paths:
        return {
            "error": "image_paths must contain at least one path",
            "content": content,
            "stage": "validate_input",
        }

    if len(image_paths) > 1:
        return {
            "error": "only one image is currently supported",
            "content": content,
            "image_paths": image_paths,
            "stage": "validate_input",
        }

    paths = [Path(path).expanduser().resolve() for path in image_paths]
    for path in paths:
        if not path.is_file():
            return {
                "error": f"image path does not exist or is not a file: {path}",
                "content": content,
                "image_paths": [str(item) for item in paths],
                "stage": "validate_input",
            }

    logger.info(
        "Starting publish_moment_with_media (content_length=%d, image_count=%d, publish=%s)",
        len(content),
        len(paths),
        publish,
    )

    try:
        ax_app = get_wechat_ax_app()
        moments_window = _open_moments_window(ax_app)
        panel = _find_open_panel(moments_window)
        if panel is None:
            _click_moment_post_button(moments_window)
            panel = _wait_for_open_panel(moments_window)

        _select_file_in_open_panel(panel, paths[0])
        _wait_for_open_panel_to_close(moments_window)

        moments_window = _wait_for_window_titles(
            ax_app,
            MOMENTS_WINDOW_TITLES,
            timeout=5.0,
        )
        if moments_window is None:
            raise RuntimeError("The Moments window disappeared after selecting media")

        editor_root = _find_editor_root(moments_window, timeout=5.0)
        if editor_root is None:
            error_msg = "Could not locate Moments composer editor root"
            logger.warning(error_msg)
            return {
                "error": error_msg,
                "content": content,
                "image_paths": [str(item) for item in paths],
                "stage": "editor_root",
            }

        if content:
            text_area = _find_moment_text_area(editor_root)
            if text_area is None:
                error_msg = "Could not find text entry area in Moments composer"
                logger.warning(error_msg)
                return {
                    "error": error_msg,
                    "content": content,
                    "image_paths": [str(item) for item in paths],
                    "stage": "text_area",
                }

            AXUIElementPerformAction(text_area, kAXRaiseAction)
            err = AXUIElementSetAttributeValue(text_area, kAXValueAttribute, content)
            if err != 0:
                error_msg = f"Failed to set composer text, AX error {err}"
                logger.warning(error_msg)
                return {
                    "error": error_msg,
                    "content": content,
                    "image_paths": [str(item) for item in paths],
                    "stage": "set_text",
                }

        if not publish:
            logger.info(
                "Moments media composer prepared; publish=False so skipping Post click"
            )
            return {
                "content": content,
                "image_paths": [str(item) for item in paths],
                "posted": False,
            }

        logger.info("Moments media composer prepared; clicking Post in sheet")
        post_button = _find_post_button_in_editor(editor_root)
        if post_button is None:
            error_msg = "Could not find 'Post'/'发表' button in Moments composer"
            logger.warning(error_msg)
            return {
                "error": error_msg,
                "content": content,
                "image_paths": [str(item) for item in paths],
                "stage": "post_button",
            }

        click_element_center(post_button)
        time.sleep(0.5)

        logger.info("Moments media post submitted successfully")
        return {
            "content": content,
            "image_paths": [str(item) for item in paths],
            "posted": True,
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error while publishing moment with media: %s", exc)
        return {
            "error": str(exc),
            "content": content,
            "image_paths": [str(item) for item in paths],
            "stage": "unexpected_error",
        }
