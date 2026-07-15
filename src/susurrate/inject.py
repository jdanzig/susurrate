"""Insert text at the cursor of the frontmost app via clipboard + synthesized paste."""

import subprocess
import sys
import time


def inject(text: str, restore_clipboard: bool = True) -> None:
    """Paste `text` into the focused app, then restore the previous clipboard."""
    if not text:
        return
    if sys.platform == "win32":
        _inject_windows(text, restore_clipboard)
    else:
        _inject_macos(text, restore_clipboard)


def _inject_windows(text: str, restore_clipboard: bool) -> None:
    """Clipboard + synthesized Ctrl+V. No special permissions needed."""
    import pyperclip
    from pynput.keyboard import Controller, Key

    previous = pyperclip.paste() if restore_clipboard else None
    pyperclip.copy(text)
    time.sleep(0.05)  # let the clipboard update land before pasting
    kb = Controller()
    with kb.pressed(Key.ctrl):
        kb.tap("v")
    if previous is not None:
        time.sleep(0.3)  # let the paste land before swapping the clipboard back
        pyperclip.copy(previous)


def _pbpaste() -> str:
    return subprocess.run(["pbpaste"], capture_output=True, text=True).stdout


def _pbcopy(text: str) -> None:
    subprocess.run(["pbcopy"], input=text, text=True, check=True)


def _inject_macos(text: str, restore_clipboard: bool) -> None:
    """Clipboard + synthesized ⌘V.

    Requires Accessibility permission for the host process (System Settings >
    Privacy & Security > Accessibility).
    """
    previous = _pbpaste() if restore_clipboard else None
    _pbcopy(text)
    result = subprocess.run(
        [
            "osascript",
            "-e",
            'tell application "System Events" to keystroke "v" using command down',
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # No Accessibility permission: leave the text on the clipboard so the
        # user can paste manually, and tell them via a notification.
        subprocess.run(
            [
                "osascript",
                "-e",
                'display notification "Text copied — press ⌘V to paste. '
                '(Grant Accessibility permission for auto-paste.)" '
                'with title "susurrate"',
            ],
            capture_output=True,
        )
        return
    if previous is not None:
        time.sleep(0.3)  # let the paste land before swapping the clipboard back
        _pbcopy(previous)
