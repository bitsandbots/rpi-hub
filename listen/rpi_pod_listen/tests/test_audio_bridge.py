"""Unit tests for the WebSocket audio bridge primitives."""

from __future__ import annotations

from listen.rpi_pod_listen import audio_bridge


def test_consumer_drops_when_full() -> None:
    c = audio_bridge.AudioConsumer()
    for _ in range(audio_bridge.QUEUE_DEPTH):
        assert c.offer(audio_bridge.AudioFrame(pcm_le16=b"x", sample_rate=22050))
    # One more must drop.
    assert not c.offer(audio_bridge.AudioFrame(pcm_le16=b"x", sample_rate=22050))


def test_fanout_add_remove_count() -> None:
    fanout = audio_bridge.AudioFanout(sample_rate=22050)
    assert fanout.consumer_count() == 0
    c = audio_bridge.AudioConsumer()
    fanout.add(c)
    assert fanout.consumer_count() == 1
    fanout.remove(c)
    assert fanout.consumer_count() == 0
    # Removing twice is a no-op.
    fanout.remove(c)
    assert fanout.consumer_count() == 0
