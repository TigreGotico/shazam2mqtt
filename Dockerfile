# syntax=docker/dockerfile:1
# Build context must include both pyshazam/ and shazam2mqtt/ directories.
# Example (from workspace root):
#   docker build -f apps/shazam2mqtt/Dockerfile .

FROM python:3.11-slim

# Install system dependencies for audio and build
RUN apt-get update && apt-get install -y --no-install-recommends \
    libportaudio2 \
    alsa-utils \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Install pyshazam first (local dependency)
COPY clients/music/pyshazam /tmp/pyshazam
RUN pip install --no-cache-dir /tmp/pyshazam && rm -rf /tmp/pyshazam

# 2. Install shazam2mqtt
COPY apps/shazam2mqtt/pyproject.toml ./
COPY apps/shazam2mqtt/README.md ./
COPY apps/shazam2mqtt/shazam2mqtt/ ./shazam2mqtt/
RUN pip install --no-cache-dir "."

# Entrypoint
COPY apps/shazam2mqtt/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
