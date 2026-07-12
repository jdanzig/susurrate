"""Client for a remote `susurrate serve` instance."""

import http.client
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from .server import TOKEN_PATH

# Split timeouts: bail fast if we can't *reach* the server (sketchy internet →
# fall back to local), but wait patiently once connected (the server may be
# mid-transcription — legit silence, not a network problem).
CONNECT_TIMEOUT = 4.0
READ_TIMEOUT = 60.0


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
            use_llm: bool = False) -> tuple[str, str]:
    """POST a WAV to the server; return (raw transcript, cleaned text).

    Uses a short connect timeout (reach the server fast, else give up so the
    caller can fall back to local) and a long read timeout (let the server
    finish transcribing).
    """
    parsed = urlparse(url.rstrip("/"))
    body = Path(wav_path).read_bytes()
    conn = http.client.HTTPSConnection(
        parsed.hostname, parsed.port or 443, timeout=CONNECT_TIMEOUT
    )
    try:
        conn.connect()  # TCP + TLS, bounded by CONNECT_TIMEOUT
        conn.sock.settimeout(READ_TIMEOUT)  # patient once we're through
        conn.request(
            "POST", f"{parsed.path}/dictate?llm={int(use_llm)}", body=body,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "audio/wav"},
        )
        resp = conn.getresponse()
        raw = resp.read()
    except (OSError, http.client.HTTPException) as e:
        raise RemoteError(f"cannot reach {url}: {e}") from e
    finally:
        conn.close()

    if resp.status != 200:
        detail = ""
        try:
            detail = json.loads(raw).get("error", "")
        except Exception:
            pass
        raise RemoteError(f"server returned {resp.status}: {detail}")
    payload = json.loads(raw)
    return payload.get("raw", ""), payload.get("text", "")
