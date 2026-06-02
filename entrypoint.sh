#!/usr/bin/env bash
set -e

# Optional ALSA debugging
# amixer info || true

exec python -m shazam2mqtt "$@"
