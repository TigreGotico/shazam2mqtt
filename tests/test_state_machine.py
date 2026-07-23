"""Adversarial tests for ShazamStateMachine: cooldown, same-song cooldown,
and the N-consecutive-no-match debounce.

Uses a stub MQTT client and a stubbed ShazamBridge so no network/broker is
needed. Tests are plain async functions driven via asyncio.run() rather than
pytest-asyncio (not a guaranteed dependency here).
"""

import asyncio
import types

from shazam2mqtt.state_machine import ShazamStateMachine


class StubMqtt:
    def __init__(self):
        self.matches = []
        self.unknowns = []
        self.silences = 0
        self._listen_callback = None

    def set_listen_callback(self, callback):
        self._listen_callback = callback

    def publish_match(self, **kwargs):
        self.matches.append(kwargs)

    def publish_unknown(self, reason="No match"):
        self.unknowns.append(reason)

    def publish_silence(self):
        self.silences += 1


class StubConfig:
    def __init__(
        self,
        cooldown_seconds=10,
        same_song_cooldown_seconds=30,
        required_no_matches=2,
    ):
        self.cooldown_seconds = cooldown_seconds
        self.same_song_cooldown_seconds = same_song_cooldown_seconds
        self.required_no_matches = required_no_matches


def _make_track(title="Song A", subtitle="Artist A", confidence=5, key="k1"):
    return types.SimpleNamespace(
        title=title,
        subtitle=subtitle,
        confidence=confidence,
        apple_music_url="",
        cover_art="",
        genres=[],
        spotify_uri="",
        deezer_uri="",
        url="",
        key=key,
        lyrics="",
        metadata_table={},
        related_videos=[],
    )


class StubShazamBridge:
    """Replays a scripted sequence of identify() results."""

    def __init__(self, results):
        self._results = list(results)
        self.calls = 0

    async def identify(self, wav_bytes):
        self.calls += 1
        result = self._results.pop(0)
        return result

    async def get_track_info(self, track_id):
        return None


def _matched_result(track):
    return types.SimpleNamespace(matched=True, track=track)


def _no_match_result():
    return types.SimpleNamespace(matched=False, track=None)


def _make_sm(results, cfg=None, now=None):
    cfg = cfg or StubConfig()
    mqtt = StubMqtt()
    sm = ShazamStateMachine(cfg, mqtt)
    sm.shazam = StubShazamBridge(results)
    if now is not None:
        sm._last_trigger = now
    return sm, mqtt


def test_first_trigger_always_runs_and_publishes_match():
    track = _make_track()
    sm, mqtt = _make_sm([_matched_result(track)])
    asyncio.run(sm.on_trigger(b"wav"))
    assert len(mqtt.matches) == 1
    assert mqtt.matches[0]["title"] == "Song A"


def test_trigger_within_cooldown_is_ignored():
    track = _make_track()
    sm, mqtt = _make_sm([_matched_result(track), _matched_result(track)])

    async def scenario():
        await sm.on_trigger(b"wav1")  # runs, sets _last_trigger = now
        await sm.on_trigger(b"wav2")  # within cooldown -> ignored

    asyncio.run(scenario())
    assert len(mqtt.matches) == 1
    assert sm.shazam.calls == 1


def test_trigger_after_cooldown_elapses_runs_again():
    track = _make_track()
    cfg = StubConfig(cooldown_seconds=0)
    sm, mqtt = _make_sm([_matched_result(track), _matched_result(track)], cfg=cfg)

    async def scenario():
        await sm.on_trigger(b"wav1")
        sm._last_trigger -= 1  # simulate time passing beyond the (zero) cooldown
        await sm.on_trigger(b"wav2")

    asyncio.run(scenario())
    assert len(mqtt.matches) == 2


def test_same_song_uses_longer_cooldown():
    track = _make_track()
    cfg = StubConfig(cooldown_seconds=0, same_song_cooldown_seconds=1000)
    sm, mqtt = _make_sm(
        [_matched_result(track), _matched_result(track), _matched_result(track)],
        cfg=cfg,
    )

    async def scenario():
        await sm.on_trigger(b"wav1")  # first sighting -> same_song_flag stays False
        sm._last_trigger -= 1  # clear the (zero) normal cooldown
        await sm.on_trigger(b"wav2")  # same track again -> same_song_flag becomes True
        sm._last_trigger -= 1  # would clear the *normal* cooldown...
        await sm.on_trigger(b"wav3")  # ...but same-song cooldown (1000s) still active

    asyncio.run(scenario())
    assert len(mqtt.matches) == 2
    assert sm.shazam.calls == 2  # third call short-circuited before identify()


def test_different_song_does_not_get_same_song_cooldown():
    track_a = _make_track(title="Song A", key="k1")
    track_b = _make_track(title="Song B", key="k2")
    cfg = StubConfig(cooldown_seconds=0, same_song_cooldown_seconds=1000)
    sm, mqtt = _make_sm(
        [_matched_result(track_a), _matched_result(track_b)],
        cfg=cfg,
    )

    async def scenario():
        await sm.on_trigger(b"wav1")
        sm._last_trigger -= 1  # clear the (zero) normal cooldown
        await sm.on_trigger(b"wav2")

    asyncio.run(scenario())
    assert len(mqtt.matches) == 2
    assert [m["title"] for m in mqtt.matches] == ["Song A", "Song B"]


def test_reentrant_trigger_while_busy_is_ignored():
    """If on_trigger is somehow called again while already processing one,
    it must be dropped rather than run concurrently.
    """
    track = _make_track()
    sm, mqtt = _make_sm([_matched_result(track)])
    sm._busy = True

    asyncio.run(sm.on_trigger(b"wav"))
    assert mqtt.matches == []
    assert sm.shazam.calls == 0


def test_no_match_below_required_count_keeps_previous_state():
    cfg = StubConfig(required_no_matches=3)
    sm, mqtt = _make_sm([_no_match_result(), _no_match_result()], cfg=cfg)

    async def scenario():
        await sm.on_trigger(b"wav1")
        sm._last_trigger = 0.0  # bypass cooldown for the test
        await sm.on_trigger(b"wav2")

    asyncio.run(scenario())
    assert mqtt.unknowns == []
    assert sm._consecutive_no_matches == 2


def test_no_match_reaching_required_count_publishes_unknown():
    cfg = StubConfig(required_no_matches=2, cooldown_seconds=0)
    sm, mqtt = _make_sm([_no_match_result(), _no_match_result()], cfg=cfg)

    async def scenario():
        await sm.on_trigger(b"wav1")
        sm._last_trigger -= 1
        await sm.on_trigger(b"wav2")

    asyncio.run(scenario())
    assert mqtt.unknowns == ["No match"]


def test_match_after_no_matches_resets_the_counter():
    track = _make_track()
    cfg = StubConfig(required_no_matches=5, cooldown_seconds=0)
    sm, mqtt = _make_sm(
        [_no_match_result(), _no_match_result(), _matched_result(track)],
        cfg=cfg,
    )

    async def scenario():
        await sm.on_trigger(b"wav1")
        sm._last_trigger -= 1
        await sm.on_trigger(b"wav2")
        sm._last_trigger -= 1
        await sm.on_trigger(b"wav3")

    asyncio.run(scenario())
    assert sm._consecutive_no_matches == 0
    assert mqtt.unknowns == []
    assert len(mqtt.matches) == 1


def test_on_quiet_resets_no_match_counter_and_publishes_silence():
    cfg = StubConfig(required_no_matches=10)
    sm, mqtt = _make_sm([])
    sm._consecutive_no_matches = 3
    sm._same_song_flag = True

    asyncio.run(sm.on_quiet())

    assert mqtt.silences == 1
    assert sm._consecutive_no_matches == 0
    assert sm._same_song_flag is False


def test_listen_now_without_force_listen_wiring_does_not_raise():
    sm, mqtt = _make_sm([])
    # force_listen/loop were never provided -> must degrade gracefully.
    sm._on_listen_command()


def test_listen_now_schedules_event_threadsafe_when_wired():
    calls = []

    class StubLoop:
        def call_soon_threadsafe(self, fn, *args):
            calls.append((fn, args))
            fn(*args)

    cfg = StubConfig()
    mqtt = StubMqtt()
    force_listen = asyncio.Event()
    sm = ShazamStateMachine(cfg, mqtt, force_listen=force_listen, loop=StubLoop())

    sm._on_listen_command()

    assert len(calls) == 1
    assert force_listen.is_set()
