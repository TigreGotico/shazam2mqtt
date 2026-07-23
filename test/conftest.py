"""Shared test fixtures: stub out hardware/network-only dependencies so the
suite runs without a microphone, PortAudio device, or the xazam package
installed.
"""

import sys
import types

if "xazam" not in sys.modules:
    xazam_stub = types.ModuleType("xazam")

    class _Stub:
        def __init__(self, *args, **kwargs):
            pass

    xazam_stub.ShazamClient = _Stub
    xazam_stub.ShazamTransport = _Stub
    xazam_stub.RecognitionResult = _Stub
    xazam_stub.Track = _Stub
    sys.modules["xazam"] = xazam_stub

if "sounddevice" not in sys.modules:
    sd_stub = types.ModuleType("sounddevice")

    class _InputStream:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

        def read(self, frames):
            raise NotImplementedError("stubbed sounddevice.InputStream.read")

        def close(self):
            pass

    class _PortAudioError(Exception):
        pass

    class _Default:
        device = (None, None)

    sd_stub.InputStream = _InputStream
    sd_stub.PortAudioError = _PortAudioError
    sd_stub.default = _Default()
    sd_stub.query_devices = lambda: []
    sys.modules["sounddevice"] = sd_stub
