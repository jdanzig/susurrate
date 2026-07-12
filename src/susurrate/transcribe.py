"""Local speech-to-text via whisper.cpp's whisper-cli."""

import os
import shutil
import subprocess
from pathlib import Path

_MODEL_DIR = Path.home() / ".local/share/susurrate/models"
# Swap the model (and language) without code changes: point SUSURRATE_MODEL at
# a multilingual model (e.g. ggml-small.bin) and dictation goes multilingual.
DEFAULT_MODEL = Path(os.environ.get("SUSURRATE_MODEL", _MODEL_DIR / "ggml-base.en.bin"))
# 'auto' lets a multilingual model detect the spoken language per clip; it's a
# harmless no-op for English-only .en models.
LANGUAGE = os.environ.get("SUSURRATE_LANG", "auto")


class TranscribeError(RuntimeError):
    pass


def transcribe(wav_path: str | Path, model: str | Path = DEFAULT_MODEL,
               initial_prompt: str = "") -> str:
    """Transcribe a 16 kHz mono WAV file, returning plain text.

    initial_prompt biases recognition toward your vocabulary (proper nouns,
    jargon) — see the personal dictionary.
    """
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
