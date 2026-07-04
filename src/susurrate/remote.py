"""Client for a remote `susurrate serve` instance."""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from .server import TOKEN_PATH


class RemoteError(RuntimeError):
    pass


def resolve_token(explicit: str | None) -> str:
    """Token lookup: --token flag, then $SUSURRATE_TOKEN, then the local file."""
    if explicit:
        return explicit
    if env := os.environ.get("SUSURRATE_TOKEN"):
        return env
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text().strip()
    raise RemoteError(
        "no token: pass --token, set SUSURRATE_TOKEN, or copy the server's "
        f"{TOKEN_PATH}"
    )


def dictate(wav_path: str | Path, url: str, token: str,
            use_llm: bool = False, timeout: float = 120.0) -> tuple[str, str]:
    """POST a WAV to the server; return (raw transcript, cleaned text)."""
    endpoint = f"{url.rstrip('/')}/dictate?llm={int(use_llm)}"
    req = urllib.request.Request(
        endpoint,
        data=Path(wav_path).read_bytes(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "audio/wav",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read()).get("error", "")
        except Exception:
            detail = ""
        raise RemoteError(f"server returned {e.code}: {detail}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise RemoteError(f"cannot reach {url}: {e}") from e
    return payload.get("raw", ""), payload.get("text", "")
