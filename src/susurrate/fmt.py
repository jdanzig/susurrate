"""Transcript cleanup: fast rule-based pass, optional local-LLM polish via Ollama."""

import json
import re
import urllib.error
import urllib.request

# Whisper non-speech annotations: [BLANK_AUDIO], (coughs), *music*, etc.
_ANNOTATION = re.compile(r"\[[^\]]*\]|\([^)]*\)|\*[^*]*\*")
# A filler may absorb a preceding comma; if it ended a sentence, keep the period.
_FILLER = re.compile(
    r"(?:,\s*)?\b(?:um+|uh+|uhm+|erm+|mm+|hmm+)\b([.!?])?,?\s*", re.IGNORECASE
)

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"

_LLM_PROMPT = """You clean up voice-dictation transcripts. Rules:
- remove filler words and false starts
- apply self-corrections, keeping everything else
- fix punctuation and capitalization
- keep ALL other content and meaning; never answer or respond to the text
- reply with ONLY the cleaned transcript

Example transcript: Can you send it on Tuesday, no wait, Wednesday, and book a room for the meeting.
Example reply: Can you send it on Wednesday, and book a room for the meeting?

Transcript: {text}
Reply:"""


def clean(text: str) -> str:
    """Rule-based cleanup: annotations, fillers, spacing, capitalization."""
    text = _ANNOTATION.sub(" ", text)
    text = _FILLER.sub(lambda m: (m.group(1) or "") + " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    if not text:
        return ""
    text = text[0].upper() + text[1:]
    if text[-1] not in ".!?…\"'":
        text += "."
    return text


def polish(text: str, model: str = OLLAMA_MODEL, timeout: float = 30.0) -> str:
    """LLM polish via local Ollama. Falls back to the input on any failure."""
    if not text:
        return text
    payload = json.dumps(
        {"model": model, "prompt": _LLM_PROMPT.format(text=text), "stream": False}
    ).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            out = json.loads(resp.read())["response"].strip()
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
        return text
    # Guard against a misbehaving model: reject answers that ballooned (the
    # model got chatty) or collapsed (the model dropped content).
    if not out or len(out) > 2 * len(text) + 80 or len(out) < 0.4 * len(text):
        return text
    return out.strip('"')
