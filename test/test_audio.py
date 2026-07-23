"""Adversarial unit tests for NoiseGate, rms_to_dbfs and NoiseLevelThrottler."""

import numpy as np
import pytest

from shazam2mqtt.audio import NoiseGate, NoiseLevelThrottler, rms_to_dbfs


# --------------------------------------------------------------------- #
# rms_to_dbfs
# --------------------------------------------------------------------- #

def test_rms_to_dbfs_zero_is_negative_infinity():
    assert rms_to_dbfs(0) == -np.inf


def test_rms_to_dbfs_negative_is_negative_infinity():
    # RMS is mathematically non-negative, but the function must not blow up
    # (log of a negative number) if it's ever handed a bogus value.
    assert rms_to_dbfs(-5.0) == -np.inf


def test_rms_to_dbfs_full_scale_is_zero_dbfs():
    assert rms_to_dbfs(32768.0) == pytest.approx(0.0, abs=1e-9)


def test_rms_to_dbfs_half_scale_is_about_minus_6db():
    assert rms_to_dbfs(16384.0) == pytest.approx(-6.02, abs=0.01)


# --------------------------------------------------------------------- #
# NoiseGate
# --------------------------------------------------------------------- #

def _chunk(db_level: float) -> np.ndarray:
    """Build an int16 chunk whose RMS corresponds to roughly ``db_level`` dBFS."""
    amplitude = 32767.0 * (10 ** (db_level / 20.0))
    return np.full(100, amplitude, dtype=np.int16)


def test_noise_gate_does_not_trigger_below_threshold():
    gate = NoiseGate(threshold_db=-40.0, hysteresis_chunks=3)
    quiet = _chunk(-60.0)
    for _ in range(10):
        assert gate.process(quiet) is False


def test_noise_gate_requires_full_hysteresis_streak():
    gate = NoiseGate(threshold_db=-40.0, hysteresis_chunks=3)
    loud = _chunk(-10.0)
    assert gate.process(loud) is False  # 1
    assert gate.process(loud) is False  # 2
    assert gate.process(loud) is True   # 3 -> triggers


def test_noise_gate_streak_resets_on_a_single_quiet_chunk():
    gate = NoiseGate(threshold_db=-40.0, hysteresis_chunks=3)
    loud = _chunk(-10.0)
    quiet = _chunk(-60.0)
    assert gate.process(loud) is False
    assert gate.process(loud) is False
    assert gate.process(quiet) is False  # resets streak
    assert gate.process(loud) is False   # back to 1
    assert gate.process(loud) is False   # 2
    assert gate.process(loud) is True    # 3 -> triggers


def test_noise_gate_explicit_reset():
    gate = NoiseGate(threshold_db=-40.0, hysteresis_chunks=2)
    loud = _chunk(-10.0)
    assert gate.process(loud) is False
    gate.reset()
    assert gate.process(loud) is False  # streak was cleared, back to 1


def test_noise_gate_hysteresis_of_one_triggers_immediately():
    gate = NoiseGate(threshold_db=-40.0, hysteresis_chunks=1)
    loud = _chunk(-10.0)
    assert gate.process(loud) is True


def test_noise_gate_boundary_at_exact_threshold_does_not_trigger():
    # process() uses a strict ">" comparison, so a value exactly at
    # threshold must not count as loud.
    gate = NoiseGate(threshold_db=-40.0, hysteresis_chunks=1)
    silence = np.zeros(100, dtype=np.int16)
    assert gate.process(silence) is False


# --------------------------------------------------------------------- #
# NoiseLevelThrottler
# --------------------------------------------------------------------- #

def test_throttler_first_call_always_publishes():
    calls = []
    throttler = NoiseLevelThrottler(calls.append, min_interval=100.0, min_delta=100.0)
    throttler.maybe_publish(-30.0)
    assert calls == [-30.0]


def test_throttler_suppresses_small_delta_within_interval(monkeypatch):
    calls = []
    throttler = NoiseLevelThrottler(calls.append, min_interval=10.0, min_delta=3.0)

    t = [1000.0]
    monkeypatch.setattr("shazam2mqtt.audio.time.time", lambda: t[0])

    throttler.maybe_publish(-30.0)  # first call, always publishes
    t[0] += 1.0
    throttler.maybe_publish(-31.0)  # delta 1 < 3, elapsed 1 < 10 -> suppressed
    assert calls == [-30.0]


def test_throttler_publishes_on_large_delta_even_within_interval(monkeypatch):
    calls = []
    throttler = NoiseLevelThrottler(calls.append, min_interval=10.0, min_delta=3.0)

    t = [1000.0]
    monkeypatch.setattr("shazam2mqtt.audio.time.time", lambda: t[0])

    throttler.maybe_publish(-30.0)
    t[0] += 1.0
    throttler.maybe_publish(-10.0)  # delta 20 >= 3 -> publishes despite short elapsed
    assert calls == [-30.0, -10.0]


def test_throttler_publishes_after_interval_even_with_small_delta(monkeypatch):
    calls = []
    throttler = NoiseLevelThrottler(calls.append, min_interval=10.0, min_delta=3.0)

    t = [1000.0]
    monkeypatch.setattr("shazam2mqtt.audio.time.time", lambda: t[0])

    throttler.maybe_publish(-30.0)
    t[0] += 11.0
    throttler.maybe_publish(-30.5)  # delta tiny, but elapsed >= interval -> publishes
    assert calls == [-30.0, -30.5]
