"""Local speech-to-text via whisper.cpp's whisper-cli."""

import shutil
import subprocess
from pathlib import Path

DEFAULT_MODEL = Path.home() / ".local/share/susurrate/models/ggml-base.en.bin"


class TranscribeError(RuntimeError):
    pass


def transcribe(wav_path: str | Path, model: str | Path = DEFAULT_MODEL) -> str:
    """Transcribe a 16 kHz mono WAV file, returning plain text."""
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
            "--no-timestamps",
            "--no-prints",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise TranscribeError(f"whisper-cli failed: {result.stderr.strip()[-500:]}")
    return result.stdout.strip()
