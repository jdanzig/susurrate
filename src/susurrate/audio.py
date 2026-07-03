"""Microphone capture: start on hotkey press, stop on release, write a WAV."""

import queue
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16_000  # what whisper expects


class NoMicrophoneError(RuntimeError):
    pass


class Recorder:
    """Push-to-talk recorder. start() begins capture, stop() returns a WAV path."""

    def __init__(self, out_dir: str | Path | None = None):
        self.out_dir = Path(out_dir) if out_dir else Path.home() / ".local/share/susurrate/recordings"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self._chunks: queue.Queue[np.ndarray] = queue.Queue()
        self._stream: sd.InputStream | None = None
        self._counter = 0

    @property
    def recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        if self._stream is not None:
            return
        self._chunks = queue.Queue()
        try:
            self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
                callback=lambda indata, frames, t, status: self._chunks.put(indata.copy()),
            )
        except sd.PortAudioError as e:
            raise NoMicrophoneError(
                "no audio input device available — connect a microphone "
                "(and grant Microphone permission to your terminal)"
            ) from e
        self._stream.start()

    def stop(self) -> Path | None:
        """Stop capture and write the WAV. Returns None if nothing was recorded."""
        if self._stream is None:
            return None
        self._stream.stop()
        self._stream.close()
        self._stream = None

        frames = []
        while not self._chunks.empty():
            frames.append(self._chunks.get())
        if not frames:
            return None
        audio = np.concatenate(frames)
        if len(audio) < SAMPLE_RATE // 4:  # under 250 ms: accidental tap
            return None

        self._counter += 1
        path = self.out_dir / f"rec-{self._counter}.wav"
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            w.writeframes(audio.tobytes())
        return path
