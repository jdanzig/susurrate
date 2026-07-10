"""Personal dictionary: corrections you teach by editing a transcript.

Fix a word once in the web app; it's stored here and applied to every future
dictation — both as a whisper bias hint and as a post-transcription
substitution. Learning is guarded so ordinary content edits (changing your
mind about a word) don't become permanent rules: a substitution is only
learned when the original token is *not* a real English word, i.e. it looks
like a mistranscription or a proper noun whisper hasn't seen.
"""

import difflib
import json
import re
from functools import lru_cache
from pathlib import Path

DICT_PATH = Path.home() / ".local/share/susurrate/dictionary.json"
WORDS_PATH = Path("/usr/share/dict/words")
_TOKEN = re.compile(r"[A-Za-z']+")

# Baked in so a fresh install already knows its own name — whisper reliably
# mishears "susurrate". Your saved corrections override these.
DEFAULTS = {
    "sesarite": "Susurrate",
    "susurate": "Susurrate",
    "sussurate": "Susurrate",
    "sutterate": "Susurrate",
    "susserate": "Susurrate",
}


@lru_cache(maxsize=1)
def _real_words() -> frozenset[str]:
    try:
        return frozenset(w.strip().lower() for w in WORDS_PATH.read_text().splitlines())
    except OSError:
        return frozenset()


def _load_file() -> dict[str, str]:
    try:
        return json.loads(DICT_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def load() -> dict[str, str]:
    """Active corrections: hardcoded DEFAULTS plus your saved edits (yours win)."""
    return {**DEFAULTS, **_load_file()}


def save(corrections: dict[str, str]) -> None:
    DICT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DICT_PATH.write_text(json.dumps(corrections, ensure_ascii=False, indent=2) + "\n")


def apply(text: str, corrections: dict[str, str] | None = None) -> str:
    """Replace known mistranscriptions, matching whole words, case-insensitively."""
    corrections = load() if corrections is None else corrections
    if not corrections or not text:
        return text

    def repl(m: re.Match) -> str:
        return corrections.get(m.group(0).lower(), m.group(0))

    pattern = re.compile(
        r"\b(?:%s)\b" % "|".join(re.escape(w) for w in corrections),
        re.IGNORECASE,
    )
    return pattern.sub(repl, text)


def prompt(corrections: dict[str, str] | None = None, limit: int = 200) -> str:
    """A whisper initial-prompt hint biasing it toward your vocabulary."""
    corrections = load() if corrections is None else corrections
    terms = list(dict.fromkeys(corrections.values()))  # unique, order-preserving
    return " ".join(terms)[:limit]


def _learnable(wrong: str, right: str) -> bool:
    """Only learn a real transcription fix, not a change of mind."""
    return (
        wrong.lower() != right.lower()
        and wrong.lower() not in _real_words()  # a real word → likely a content edit
    )


def learn(original: str, edited: str) -> dict[str, str]:
    """Diff original→edited, persist single-word transcription fixes.

    Returns the {wrong: right} pairs newly learned this call.
    """
    a = _TOKEN.findall(original)
    b = _TOKEN.findall(edited)
    learned: dict[str, str] = {}
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b).get_opcodes():
        # Only 1-for-1 word swaps; skip inserts, deletes, and phrase rewrites.
        if tag == "replace" and i2 - i1 == 1 and j2 - j1 == 1:
            wrong, right = a[i1], b[j1]
            if _learnable(wrong, right):
                learned[wrong.lower()] = right
    if learned:
        corrections = _load_file()  # persist only your edits, not the DEFAULTS
        corrections.update(learned)
        save(corrections)
    return learned
