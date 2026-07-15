"""Hidden-console daemon launcher for Windows — run with the venv's pythonw.exe.

Registered as a logon task by contrib/install-daemon-windows.ps1. pythonw has
no console, so all output goes to ~/.local/share/susurrate/daemon.log instead.
"""

import os
import sys
import time
from pathlib import Path

data = Path.home() / ".local/share/susurrate"
data.mkdir(parents=True, exist_ok=True)
log = data / "daemon.log"
if log.exists() and log.stat().st_size > 1_000_000:
    log.unlink()
sys.stdout = sys.stderr = open(log, "a", buffering=1, encoding="utf-8")
print(f"--- daemon start {time.strftime('%Y-%m-%dT%H:%M:%S')} ---")

# Belt and braces: if the task starts without the user env var, fall back to
# the conventional install location from setup-windows.ps1. Must happen
# before the susurrate import — transcribe.py reads the env at import time.
cli = Path.home() / "Tools/whisper.cpp/Release/whisper-cli.exe"
if "SUSURRATE_WHISPER_CLI" not in os.environ and cli.exists():
    os.environ["SUSURRATE_WHISPER_CLI"] = str(cli)

from susurrate.app import main  # noqa: E402

sys.argv = ["susurrate", "run"]
sys.exit(main())
