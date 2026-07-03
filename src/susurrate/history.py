"""Append-only dictation history."""

import json
import time
from pathlib import Path

HISTORY_PATH = Path.home() / ".local/share/susurrate/history.jsonl"


def append(raw: str, cleaned: str) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "raw": raw, "text": cleaned}
    with HISTORY_PATH.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
