"""Global hold-to-talk hotkey listener.

On macOS this requires Input Monitoring (and usually Accessibility)
permission for the host process; Windows needs no permissions. Keys can be
combined with '+' into a chord (e.g. "ctrl+win"): recording starts when every
part is held and stops when any part is released.
"""

from collections.abc import Callable

from pynput import keyboard

Key = keyboard.Key

# Each name matches a set of physical keys, so "ctrl" means either Ctrl and
# "win" is the Windows key (⌘ on a Mac, where pynput calls both "cmd").
KEY_NAMES = {
    "alt_r": {Key.alt_r, Key.alt_gr},
    "alt_l": {Key.alt_l},
    "cmd_r": {Key.cmd_r},
    "ctrl_r": {Key.ctrl_r},
    "ctrl": {Key.ctrl, Key.ctrl_l, Key.ctrl_r},
    "win": {Key.cmd, Key.cmd_l, Key.cmd_r},
    "f13": {Key.f13},
    "f14": {Key.f14},
    "f15": {Key.f15},
}

DEFAULT_KEY = "ctrl+win"


class Chord:
    """Tracks which chord parts are down; press()/release() report edges."""

    def __init__(self, key_name: str):
        try:
            self.parts = [KEY_NAMES[p] for p in key_name.split("+")]
        except KeyError:
            raise SystemExit(
                f"unknown hotkey {key_name!r}; combine {', '.join(KEY_NAMES)} with '+'"
            )
        self.down = [False] * len(self.parts)
        self.held = False

    def press(self, key) -> bool:
        """True when this press completes the chord."""
        for i, keys in enumerate(self.parts):
            if key in keys:
                self.down[i] = True
        if self.held or not all(self.down):
            return False
        self.held = True
        return True

    def release(self, key) -> bool:
        """True when this release breaks a held chord."""
        hit = False
        for i, keys in enumerate(self.parts):
            if key in keys:
                self.down[i] = False
                hit = True
        if not (hit and self.held):
            return False
        self.held = False
        return True


def listen(on_press: Callable[[], None], on_release: Callable[[], None],
           key_name: str = DEFAULT_KEY) -> keyboard.Listener:
    """Block on a global listener; call on_press/on_release for the hotkey."""
    chord = Chord(key_name)

    def _press(key):
        if chord.press(key):
            on_press()

    def _release(key):
        if chord.release(key):
            on_release()

    listener = keyboard.Listener(on_press=_press, on_release=_release)
    listener.start()
    return listener
