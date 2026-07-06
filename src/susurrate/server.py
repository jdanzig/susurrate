"""Dictation-as-a-service: run the pipeline on an always-on machine.

POST /dictate with an audio clip (wav, m4a, anything ffmpeg reads) and a
bearer token; get back JSON with the raw transcript and cleaned text.
Query params: llm=1 (Ollama polish), paste=1 (also paste into this
machine's frontmost app — only honored when the server allows it).

POST /agent (opt-in via --agent) pipes the cleaned transcript into a
command-line agent (default `claude -p`) and returns its reply. Query
params: llm=1, continue=1 (pass --continue to the agent), speak=1
(return the reply as spoken audio instead of JSON).
"""

import json
import os
import secrets
import shutil
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import history, inject
from .transcribe import TranscribeError

TOKEN_PATH = Path.home() / ".local/share/susurrate/token"
MAX_BODY = 50 * 1024 * 1024  # 50 MB of audio is minutes of speech


def load_token() -> str:
    """Read the shared-secret token, generating it on first use."""
    if TOKEN_PATH.exists():
        return TOKEN_PATH.read_text().strip()
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(24)
    TOKEN_PATH.write_text(token + "\n")
    TOKEN_PATH.chmod(0o600)
    return token


def tailscale_ip() -> str | None:
    if shutil.which("tailscale") is None:
        return None
    result = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True)
    ip = result.stdout.strip().splitlines()
    return ip[0] if result.returncode == 0 and ip else None


def _to_wav(data: bytes) -> Path:
    """Write an uploaded clip and convert it to 16 kHz mono WAV via ffmpeg."""
    src = Path(tempfile.mkstemp(prefix="susurrate-up-")[1])
    dst = src.with_suffix(".wav")
    try:
        src.write_bytes(data)
        result = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
             "-ar", "16000", "-ac", "1", str(dst)],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            raise ValueError(f"could not decode audio: {result.stderr.strip()[-200:]}")
        return dst
    finally:
        src.unlink(missing_ok=True)


def _speak_m4a(text: str) -> bytes:
    """Render text to spoken audio (m4a) via macOS `say` + ffmpeg."""
    aiff = Path(tempfile.mkstemp(suffix=".aiff")[1])
    m4a = aiff.with_suffix(".m4a")
    try:
        subprocess.run(["say", "-o", str(aiff), text], check=True, timeout=120)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff), str(m4a)],
            check=True, timeout=60,
        )
        return m4a.read_bytes()
    finally:
        aiff.unlink(missing_ok=True)
        m4a.unlink(missing_ok=True)


def _agent_env() -> dict:
    """Child env for the agent: drop vars a parent Claude session leaks in,
    which make a nested `claude -p` fail to authenticate."""
    env = dict(os.environ)
    for var in list(env):
        if var == "ANTHROPIC_BASE_URL" or var.startswith(("CLAUDE_CODE_", "CLAUDECODE")):
            env.pop(var)
    return env


class _Handler(BaseHTTPRequestHandler):
    token: str = ""
    allow_paste: bool = False
    agent_cmd: list[str] | None = None
    agent_dir: str = "."

    def _reply(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _reply_audio(self, data: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "audio/mp4")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _transcribe_body(self, use_llm: bool) -> tuple[str, str] | None:
        """Read the uploaded clip and run the pipeline. Replies on error."""
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= MAX_BODY:
            self._reply(400, {"error": f"body must be 1..{MAX_BODY} bytes of audio"})
            return None

        from .app import process  # late import: avoids a circular import

        wav = None
        try:
            wav = _to_wav(self.rfile.read(length))
            return process(wav, use_llm)
        except ValueError as e:
            self._reply(400, {"error": str(e)})
            return None
        except TranscribeError as e:
            self._reply(500, {"error": str(e)})
            return None
        finally:
            if wav is not None:
                wav.unlink(missing_ok=True)

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        if urlparse(self.path).path != "/":
            self._reply(404, {"error": "unknown path"})
            return
        from .webui import PAGE

        body = PAGE.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 (http.server API)
        url = urlparse(self.path)
        if self.headers.get("Authorization") != f"Bearer {self.token}":
            self._reply(401, {"error": "bad or missing bearer token"})
            return
        query = parse_qs(url.query)
        flag = lambda name: query.get(name, ["0"])[0] in ("1", "true")  # noqa: E731

        if url.path == "/dictate":
            self._dictate(flag("llm"), flag("paste"))
        elif url.path == "/agent":
            self._agent(flag("llm"), flag("continue"), flag("speak"))
        else:
            self._reply(404, {"error": "unknown path"})

    def _dictate(self, use_llm: bool, want_paste: bool) -> None:
        result = self._transcribe_body(use_llm)
        if result is None:
            return
        raw, text = result
        pasted = False
        if want_paste and self.allow_paste and text:
            inject.inject(text)
            pasted = True
        if text:
            history.append(raw, text)
        self._reply(200, {"text": text, "raw": raw, "pasted": pasted})

    def _agent(self, use_llm: bool, cont: bool, speak: bool) -> None:
        if self.agent_cmd is None:
            self._reply(403, {"error": "agent endpoint disabled (start with --agent)"})
            return
        result = self._transcribe_body(use_llm)
        if result is None:
            return
        raw, text = result
        if not text:
            self._reply(400, {"error": "empty transcript"})
            return

        cmd = [*self.agent_cmd, *(["--continue"] if cont else []), text]
        print(f"  agent ← {text}")
        try:
            proc = subprocess.run(
                cmd, cwd=self.agent_dir, env=_agent_env(),
                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                timeout=600,
            )
        except subprocess.TimeoutExpired:
            self._reply(504, {"error": "agent timed out after 600s"})
            return
        if proc.returncode != 0:
            detail = (proc.stderr.strip() or proc.stdout.strip())[-300:]
            self._reply(502, {"error": f"agent failed: {detail}"})
            return
        reply = proc.stdout.strip()
        history.append(raw, text)

        if speak and reply:
            try:
                self._reply_audio(_speak_m4a(reply))
                return
            except subprocess.SubprocessError:
                pass  # fall back to JSON
        self._reply(200, {"prompt": text, "reply": reply})

    def log_message(self, fmt, *args):  # quieter: one line per request
        print(f"  {self.client_address[0]} {fmt % args}")


def serve(host: str | None, port: int, allow_paste: bool,
          agent_cmd: list[str] | None = None, agent_dir: str = ".") -> None:
    token = load_token()
    if host is None:
        host = tailscale_ip() or "127.0.0.1"
    _Handler.token = token
    _Handler.allow_paste = allow_paste
    _Handler.agent_cmd = agent_cmd
    _Handler.agent_dir = agent_dir
    server = ThreadingHTTPServer((host, port), _Handler)
    print(f"susurrate serve: listening on http://{host}:{port}/dictate")
    print(f"  token: {token}   (also in {TOKEN_PATH})")
    print(f"  paste into this machine's frontmost app: {'enabled' if allow_paste else 'disabled'}")
    if agent_cmd:
        print(f"  agent endpoint: /agent → {' '.join(agent_cmd)} (in {agent_dir})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
