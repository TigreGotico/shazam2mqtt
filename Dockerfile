# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Install system dependencies for audio and build
RUN apt-get update && apt-get install -y --no-install-recommends \
    libportaudio2 \
    alsa-utils \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Install xazam from PyPI
RUN pip install --no-cache-dir xazam

# 2. Install shazam2mqtt
COPY pyproject.toml ./
COPY README.md ./
COPY shazam2mqtt/ ./shazam2mqtt/
RUN pip install --no-cache-dir "."

# Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
