"""CLI and daemon entry point."""

import argparse
import sys
import threading
import time

from . import fmt, history, inject, transcribe
from .transcribe import DEFAULT_MODEL


def process(wav_path, use_llm: bool) -> tuple[str, str]:
    """WAV -> (raw transcript, cleaned text)."""
    raw = transcribe.transcribe(wav_path)
    text = fmt.clean(raw)
    if use_llm and text:
        text = fmt.polish(text)
    return raw, text


def cmd_file(args) -> int:
    raw, text = process(args.wav, args.llm)
    if args.verbose:
        print(f"raw:   {raw}", file=sys.stderr)
    print(text)
    return 0


def cmd_once(args) -> int:
    from .audio import NoMicrophoneError, Recorder

    rec = Recorder()
    print(f"recording {args.seconds}s… speak now", file=sys.stderr)
    try:
        rec.start()
    except NoMicrophoneError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    time.sleep(args.seconds)
    wav = rec.stop()
    if wav is None:
        print("no audio captured", file=sys.stderr)
        return 1
    try:
        raw, text = process(wav, args.llm)
    finally:
        wav.unlink(missing_ok=True)
    if args.verbose:
        print(f"raw:   {raw}", file=sys.stderr)
    print(text)
    if args.paste:
        inject.inject(text)
    return 0


def cmd_run(args) -> int:
    from .audio import NoMicrophoneError, Recorder
    from .hotkey import DEFAULT_KEY, listen

    rec = Recorder()

    def on_press():
        try:
            rec.start()
        except NoMicrophoneError as e:
            print(f"error: {e}", file=sys.stderr)
            return
        print("● recording…", file=sys.stderr)

    def on_release():
        wav = rec.stop()
        if wav is None:
            print("  (too short, ignored)", file=sys.stderr)
            return
        # Process off the listener thread so the hotkey stays responsive.
        threading.Thread(target=_handle, args=(wav,), daemon=True).start()

    def _handle(wav):
        try:
            raw, text = process(wav, args.llm)
        except transcribe.TranscribeError as e:
            print(f"  error: {e}", file=sys.stderr)
            return
        finally:
            wav.unlink(missing_ok=True)  # don't keep voice recordings around
        if not text:
            print("  (empty transcript)", file=sys.stderr)
            return
        print(f"  → {text}", file=sys.stderr)
        history.append(raw, text)
        inject.inject(text)

    key = args.key or DEFAULT_KEY
    print(
        f"susurrate: hold [{key}] to dictate, release to insert. Ctrl-C to quit.",
        file=sys.stderr,
    )
    listen(on_press, on_release, key)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="susurrate", description="Local voice dictation (Wispr Flow-style)")
    p.add_argument("--llm", action="store_true", help="polish transcript with local Ollama LLM")
    p.add_argument("-v", "--verbose", action="store_true", help="print raw transcript to stderr")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("file", help="transcribe a WAV file")
    sp.add_argument("wav")
    sp.set_defaults(func=cmd_file)

    sp = sub.add_parser("once", help="record N seconds from the mic and transcribe")
    sp.add_argument("--seconds", type=float, default=5.0)
    sp.add_argument("--paste", action="store_true", help="paste result into the focused app")
    sp.set_defaults(func=cmd_once)

    sp = sub.add_parser("run", help="daemon: global hold-to-talk dictation")
    sp.add_argument("--key", choices=["alt_r", "alt_l", "cmd_r", "ctrl_r", "f13", "f14", "f15"])
    sp.set_defaults(func=cmd_run)

    args = p.parse_args()
    if not DEFAULT_MODEL.exists() and args.cmd in ("file", "once", "run"):
        print(f"warning: default model missing at {DEFAULT_MODEL}", file=sys.stderr)
    return args.func(args)
