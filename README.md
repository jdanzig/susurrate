# susurrate

Local, private Wispr Flow-style voice dictation for macOS. Hold a hotkey
anywhere, speak, release — cleaned-up text is inserted at your cursor.
Everything runs on-device: whisper.cpp for speech-to-text, optional Ollama
for AI polish. No cloud, no accounts.

## Requirements

- macOS, Homebrew
- `brew install whisper-cpp` (provides `whisper-cli`)
- [uv](https://docs.astral.sh/uv/)
- optional: [Ollama](https://ollama.com) with `llama3.2:3b` for the `--llm` polish pass

Download the speech model (~141 MB, one-time):

```sh
mkdir -p ~/.local/share/susurrate/models
curl -L -o ~/.local/share/susurrate/models/ggml-base.en.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
```

## macOS permissions

Grant these to the app you run susurrate from (Terminal, iTerm, …) in
System Settings → Privacy & Security:

| Permission | Needed for |
|---|---|
| Microphone | recording your voice |
| Input Monitoring | the global hold-to-talk hotkey |
| Accessibility | auto-pasting into the focused app |

Without Accessibility, susurrate still works: it leaves the text on your
clipboard and shows a notification so you can ⌘V yourself.

## Usage

```sh
uv run susurrate run              # daemon: hold right-Option to dictate
uv run susurrate run --key f13    # different hotkey (alt_r, alt_l, cmd_r, ctrl_r, f13–f15)
uv run susurrate --llm run        # add local-LLM cleanup (self-corrections, tone)
uv run susurrate once --seconds 5 # record once, print the transcript
uv run susurrate file audio.wav   # transcribe a 16 kHz mono WAV
```

Hold the hotkey, speak, release. The transcript is cleaned (fillers stripped,
punctuation fixed), pasted at your cursor, and logged to
`~/.local/share/susurrate/history.jsonl`. Your previous clipboard is restored.
Audio recordings are deleted as soon as they're transcribed.

## Remote mode: your own dictation cloud

Run the pipeline on an always-on machine (say, a Mac mini on your
[Tailscale](https://tailscale.com) tailnet) and dictate to it from anywhere:

```sh
uv run susurrate serve    # on the always-on machine
```

The server binds to your Tailscale IP by default (falling back to
127.0.0.1), generates a bearer token on first run, and prints both. One
endpoint: `POST /dictate` with an audio clip as the request body — WAV, m4a,
anything ffmpeg can read. Optional query params: `llm=1` for the Ollama
polish pass, `paste=1` to paste the result into the *server's* frontmost app
(off unless started with `--allow-paste`). Uploaded audio is deleted after
transcription, same as local recordings.

**From another Mac** — same hotkey experience, no models needed locally:

```sh
SUSURRATE_TOKEN=<token> uv run susurrate --remote http://100.x.y.z:8737 run
```

**From an iPhone** — no app required, just a Shortcut:

1. Install Tailscale on the phone and join your tailnet.
2. Shortcuts → new shortcut:
   - **Record Audio** (tap to stop)
   - **Get Contents of URL**: `http://100.x.y.z:8737/dictate?llm=1`,
     Method POST, header `Authorization: Bearer <token>`,
     Request Body → File → the recorded audio
   - **Get Value for** `text` **in** Contents of URL
   - **Copy to Clipboard** (or Show Result / Share)
3. Add it to the Action Button or lock screen. Hold, talk, paste anywhere.

Plain `curl` works too:

```sh
curl -X POST -H "Authorization: Bearer $TOKEN" \
  --data-binary @clip.m4a "http://100.x.y.z:8737/dictate?llm=1"
```

## How it compares

**vs [Wispr Flow](https://wisprflow.ai/):** same core loop (hotkey → speak →
polished text at cursor), but 100% local and free. Not (yet) included:
command mode, per-app tone, personal dictionary, menu-bar UI, streaming
transcription. See [PLAN.md](PLAN.md).

**vs [OpenSuperWhisper](https://github.com/starmel/OpenSuperWhisper):** if you
want a polished native dictation app, use that — it has a real UI, in-app
model management, multilingual auto-detection, and a mic picker. What it
doesn't have is the part that makes Wispr Flow feel different from plain
dictation: a formatting pass between transcript and paste. Susurrate strips
fillers and false starts, fixes punctuation, and can apply spoken
self-corrections ("Tuesday — no wait, Wednesday" → "Wednesday") through a
local LLM via [Ollama](https://ollama.com). [Superwhisper](https://superwhisper.com/)
has a similar AI layer, but it's closed-source and paid.

Susurrate is deliberately small: ~400 lines of Python you can read in ten
minutes, meant as a hackable base for experimenting with the
transcript→clean-text stage (prompts, models, rules).

## Development

```sh
uv run python -m unittest discover -s tests
```
