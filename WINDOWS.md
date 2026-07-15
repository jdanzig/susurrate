# susurrate on Windows

This tree is a Windows port of [susurrate](https://github.com/jdanzig/susurrate)
(upstream is macOS-only). Ported 2026-07-13. The macOS code paths are kept, so
the same tree still runs on a Mac.

## What was changed

- `src/susurrate/inject.py` — paste-at-cursor now dispatches on platform:
  Windows uses `pyperclip` (clipboard) + `pynput` (synthesized Ctrl+V).
  No special permissions needed on Windows.
- `src/susurrate/transcribe.py` — new `SUSURRATE_WHISPER_CLI` env var points at
  the `whisper-cli.exe` binary (Windows has no `brew install whisper-cpp`;
  prebuilt binaries come from the whisper.cpp GitHub releases).
- `src/susurrate/dictionary.py` — `/usr/share/dict/words` doesn't exist on
  Windows; the learn-guard wordlist now also loads from
  `~/.local/share/susurrate/words` (any one-word-per-line file; setup script
  installs [dwyl/english-words](https://github.com/dwyl/english-words)).
- `pyproject.toml` — added `pyperclip` (Windows only).

Data lives in `%USERPROFILE%\.local\share\susurrate\` (same relative path as
macOS): models, dictionary, history, token, words.

## Setup on a new Windows machine

1. Copy this folder to `C:\Users\<you>\Tools\susurrate` (keep it out of
   OneDrive — Python venvs and sync don't mix).
2. Open PowerShell in that folder and run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\setup-windows.ps1
   ```

   The script installs uv (via winget), downloads the whisper.cpp Windows
   binaries and the `ggml-base.en.bin` model, installs the wordlist, sets the
   `SUSURRATE_WHISPER_CLI` user environment variable, runs `uv sync`, and runs
   the test suite. It's idempotent — safe to re-run.
3. Open a **new** terminal (to pick up the env var) and test:

   ```powershell
   uv run susurrate once --seconds 5   # speak; transcript prints
   uv run susurrate run                # daemon: hold right-Alt to dictate
   ```

## Usage notes (Windows specifics)

- Default hotkey is **Ctrl+Win** held together (either Ctrl, either Win key).
  Other options: `--key alt_r` (right Alt / AltGr), `--key ctrl_r`,
  `--key f13`–`f15`, or any `+` chord of ctrl, win, alt_r, alt_l, cmd_r,
  ctrl_r (this differs from upstream, which only takes single keys).
- No permission prompts: unlike macOS, Windows needs no Input Monitoring or
  Accessibility grants. Microphone access for desktop apps is allowed by
  default (Settings → Privacy & security → Microphone if not).
- `serve` mode works as on macOS. ffmpeg is only needed to accept non-WAV
  uploads (phone m4a clips): `winget install Gyan.FFmpeg`.
- Optional LLM polish (`--llm`) needs [Ollama for Windows](https://ollama.com)
  with `llama3.2:3b` pulled.
- To auto-start the daemon at logon (the Windows equivalent of the launchd
  template in `contrib/`), run once:

  ```powershell
  powershell -ExecutionPolicy Bypass -File .\contrib\install-daemon-windows.ps1
  ```

  This registers Task Scheduler task "susurrate": starts hidden at logon
  (via `contrib/daemon-windows.vbs` → `contrib/daemon-windows.py`), restarts
  on crash, logs to `~\.local\share\susurrate\daemon.log`. Manage it with
  `Stop-ScheduledTask susurrate` / `Start-ScheduledTask susurrate` /
  `Unregister-ScheduledTask susurrate`. Don't also run `susurrate run`
  manually — two daemons paste twice.
