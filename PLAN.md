# Susurrate — a local Wispr Flow clone

## How Wispr Flow works (research summary)

Wispr Flow is a system-wide voice dictation app. The core loop:

1. **Hold a hotkey** (fn by default) anywhere in the OS and speak.
2. Audio is captured from the mic while the key is held.
3. On release, audio is **transcribed** (Whisper-class ASR on their servers).
4. An **AI formatting pass** cleans the raw transcript: removes filler words
   ("um", "uh", "you know"), adds punctuation/capitalization, formats lists,
   applies self-corrections ("send it Tuesday — no, Wednesday" → "Wednesday").
5. The polished text is **inserted at the cursor** of whatever app has focus
   (Slack, Gmail, VS Code, any text field).

Supporting features: tone adapts to the target app, personal dictionary,
dictation history, 100+ languages, command mode ("make this formal"),
menu-bar presence.

Key difference in this rebuild: **everything runs locally** — whisper.cpp for
ASR, Ollama (llama3.2:3b) for the formatting pass, no network calls.

## Architecture

Python daemon (managed with `uv`), macOS-only:

```
hotkey (pynput, hold-to-talk)
  └─> recorder (sounddevice, 16 kHz mono WAV)
        └─> transcriber (whisper-cli subprocess, ggml-base.en)
              └─> formatter (rule-based cleanup; optional Ollama polish)
                    └─> injector (pbcopy → ⌘V via System Events → restore clipboard)
                          └─> history (~/.local/share/susurrate/history.jsonl)
```

Modules in `susurrate/`:

| Module | Job |
|---|---|
| `audio.py` | mic capture via sounddevice while hotkey held |
| `transcribe.py` | run `whisper-cli`, return plain text |
| `fmt.py` | strip fillers, fix spacing/capitalization; optional LLM pass via Ollama |
| `inject.py` | paste into focused app, preserving prior clipboard |
| `hotkey.py` | global hold-to-talk listener (default: right ⌥, configurable) |
| `history.py` | append each dictation to a JSONL log |
| `app.py` | CLI: `run` (daemon), `file <wav>`, `once` (record N seconds) |

## MVP scope (v0)

- Hold right-Option anywhere → speak → release → cleaned text pasted at cursor.
- Local-only: whisper.cpp `base.en` model, rule-based cleanup, Ollama polish optional (`--llm`).
- History log. No menu bar UI, no command mode, English-only (model swappable).

## Verification plan

1. `say` generates known speech → WAV → `susurrate file` → transcript matches → **pipeline verified headlessly**.
2. Formatter unit tests (filler removal, self-correction, capitalization).
3. Injection test: paste into TextEdit via AppleScript, read the document back.
4. Live end-to-end: run daemon, hold hotkey, dictate. (Needs mic + accessibility + input-monitoring permissions for the host app.)

## Later (not in MVP)

Menu bar icon (rumps), fn-key capture, per-app tone, personal dictionary,
command mode, multilingual model, streaming transcription.
