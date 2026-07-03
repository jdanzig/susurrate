"""Global hold-to-talk hotkey listener.

Requires Input Monitoring (and usually Accessibility) permission for the host
process. Default key is right Option — easy to hold, never part of shortcuts
on its own.
"""

from collections.abc import Callable

from pynput import keyboard

KEY_NAMES = {
    "alt_r": keyboard.Key.alt_r,
    "alt_l": keyboard.Key.alt_l,
    "cmd_r": keyboard.Key.cmd_r,
    "ctrl_r": keyboard.Key.ctrl_r,
    "f13": keyboard.Key.f13,
    "f14": keyboard.Key.f14,
    "f15": keyboard.Key.f15,
}

DEFAULT_KEY = "alt_r"


def listen(on_press: Callable[[], None], on_release: Callable[[], None],
           key_name: str = DEFAULT_KEY) -> keyboard.Listener:
    """Block on a global listener; call on_press/on_release for the hotkey."""
    try:
        hotkey = KEY_NAMES[key_name]
    except KeyError:
        raise SystemExit(f"unknown hotkey {key_name!r}; choose from {', '.join(KEY_NAMES)}")

    held = False

    def _press(key):
        nonlocal held
        if key == hotkey and not held:
            held = True
            on_press()

    def _release(key):
        nonlocal held
        if key == hotkey and held:
            held = False
            on_release()

    listener = keyboard.Listener(on_press=_press, on_release=_release)
    listener.start()
    return listener
