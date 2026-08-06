"""Local speech-to-text via whisper.cpp — CLI per clip, or a resident server."""

import json
import os
import shutil
import subprocess
import urllib.request
import uuid
from pathlib import Path

_MODEL_DIR = Path.home() / ".local/share/susurrate/models"
# Swap the model (and language) without code changes: point SUSURRATE_MODEL at
# a multilingual model (e.g. ggml-small.bin) and dictation goes multilingual.
DEFAULT_MODEL = Path(os.environ.get("SUSURRATE_MODEL", _MODEL_DIR / "ggml-base.en.bin"))
# 'auto' lets a multilingual model detect the spoken language per clip; it's a
# harmless no-op for English-only .en models.
LANGUAGE = os.environ.get("SUSURRATE_LANG", "auto")
# Point this at a running whisper.cpp `whisper-server` (e.g. http://127.0.0.1:8181)
# to skip reloading the model on every clip — ~0.5s faster per dictation. When
# unset, we spawn whisper-cli per clip (needed on clients with no server).
WHISPER_SERVER = os.environ.get("SUSURRATE_WHISPER_SERVER")


class TranscribeError(RuntimeError):
    pass


def transcribe(wav_path: str | Path, model: str | Path = DEFAULT_MODEL,
               initial_prompt: str = "") -> str:
    """Transcribe a 16 kHz mono WAV file, returning plain text.

    initial_prompt biases recognition toward your vocabulary (proper nouns,
    jargon) — see the personal dictionary.
    """
    if WHISPER_SERVER:
        return _transcribe_server(wav_path, initial_prompt)

    if shutil.which("whisper-cli") is None:
        raise TranscribeError("whisper-cli not found (brew install whisper-cpp)")
    model = Path(model)
    if not model.exists():
        raise TranscribeError(f"whisper model not found: {model}")

    result = subprocess.run(
        [
            "whisper-cli",
            "-m", str(model),
            "-f", str(wav_path),
            "-l", LANGUAGE,
            "--no-timestamps",
            "--no-prints",
            *(["--prompt", initial_prompt] if initial_prompt else []),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise TranscribeError(f"whisper-cli failed: {result.stderr.strip()[-500:]}")
    return result.stdout.strip()


def _transcribe_server(wav_path: str | Path, initial_prompt: str) -> str:
    """POST the clip to a resident whisper-server /inference (model stays loaded)."""
    fields = {"language": LANGUAGE, "response_format": "json"}
    if initial_prompt:
        fields["prompt"] = initial_prompt
    boundary = "----susurrate" + uuid.uuid4().hex
    body = bytearray()
    for name, value in fields.items():
        body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\""
                 f"\r\n\r\n{value}\r\n").encode()
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
             "filename=\"a.wav\"\r\nContent-Type: audio/wav\r\n\r\n").encode()
    body += Path(wav_path).read_bytes() + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        f"{WHISPER_SERVER.rstrip('/')}/inference", data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read()).get("text", "").strip()
    except (OSError, json.JSONDecodeError) as e:
        raise TranscribeError(f"whisper-server ({WHISPER_SERVER}) failed: {e}") from e
