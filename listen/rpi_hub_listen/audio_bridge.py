"""WebSocket audio bridge — Phase 8.3.

Streams the active rtl_fm child's PCM stdout to connected browsers
over a WebSocket. The browser side (listen.js) plays the stream
through Web Audio's ``AudioContext.decodeAudioData`` after framing.

Design rules:

* **Single producer, many consumers** — the rtl_fm child is owned by
  :class:`dongle.Tuner`. The bridge subscribes to its stdout. We
  cannot move stdout ownership around mid-stream, so the bridge is
  attached when the tuner starts and detached when it stops.
* **Drop, don't buffer** — a slow client must not block the dongle.
  Each consumer has a bounded queue; once full, new frames are
  dropped for that consumer. The dongle never waits.
* **No transcoding** — we ship raw signed-16 LE PCM at the rate rtl_fm
  is configured for (22050 for weather, 44100 for FM broadcast). The
  browser does its own resampling via AudioContext.

This module is pure Python with no external deps beyond stdlib. We
deliberately do not pull starlette's WebSocket abstraction in here —
:mod:`main` uses ``WebSocket`` from FastAPI for the actual transport
and pipes through this module's :class:`AudioFanout`.
"""

from __future__ import annotations

import asyncio
import contextlib
import threading
from dataclasses import dataclass

# Per-consumer queue cap. Each frame is ~4 KB at 22050 mono 16-bit
# (200ms blocks); 16 frames ≈ 3.2 s of audio. A consumer that falls
# behind by more than that gets frames dropped.
QUEUE_DEPTH = 16
# Block size we read from rtl_fm stdout per pump tick.
PUMP_BLOCK_BYTES = 4096


@dataclass
class AudioFrame:
    pcm_le16: bytes  # raw 16-bit little-endian mono samples
    sample_rate: int


class AudioConsumer:
    """One subscriber. Owns its bounded queue."""

    def __init__(self) -> None:
        self.queue: asyncio.Queue[AudioFrame] = asyncio.Queue(maxsize=QUEUE_DEPTH)

    def offer(self, frame: AudioFrame) -> bool:
        """Try to enqueue. Returns False if the consumer is too slow."""

        try:
            self.queue.put_nowait(frame)
            return True
        except asyncio.QueueFull:
            return False


class AudioFanout:
    """Fan rtl_fm stdout out to N async consumers.

    The producer runs on a background thread because rtl_fm gives us a
    blocking file descriptor. Consumers live on the event loop. We
    bridge with :meth:`asyncio.AbstractEventLoop.call_soon_threadsafe`.
    """

    def __init__(self, sample_rate: int) -> None:
        self._sample_rate = sample_rate
        self._consumers: list[AudioConsumer] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def add(self, consumer: AudioConsumer) -> None:
        with self._lock:
            self._consumers.append(consumer)

    def remove(self, consumer: AudioConsumer) -> None:
        with self._lock, contextlib.suppress(ValueError):
            self._consumers.remove(consumer)

    def consumer_count(self) -> int:
        with self._lock:
            return len(self._consumers)

    def start(self, source_fd: int) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, args=(source_fd,), name="audio-fanout", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _run(self, source_fd: int) -> None:
        import os  # noqa: PLC0415

        while not self._stop.is_set():
            try:
                data = os.read(source_fd, PUMP_BLOCK_BYTES)
            except OSError:
                return
            if not data:
                return
            frame = AudioFrame(pcm_le16=data, sample_rate=self._sample_rate)
            self._dispatch(frame)

    def _dispatch(self, frame: AudioFrame) -> None:
        if self._loop is None:
            return
        with self._lock:
            consumers = list(self._consumers)
        for c in consumers:
            # Schedule on the loop because asyncio.Queue is not thread-safe.
            self._loop.call_soon_threadsafe(c.offer, frame)
