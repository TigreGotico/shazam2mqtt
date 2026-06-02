# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Install system dependencies for audio, build, and git (for xazam install)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libportaudio2 \
    alsa-utils \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Install xazam from its GitHub repo (dev branch).
#    Pass GITHUB_TOKEN if the repo is private.
ARG GITHUB_TOKEN
RUN if [ -n "$GITHUB_TOKEN" ]; then \
      pip install --no-cache-dir \
        "git+https://${GITHUB_TOKEN}@github.com/TigreGotico/pyshazam.git@dev"; \
    else \
      pip install --no-cache-dir \
        "git+https://github.com/TigreGotico/pyshazam.git@dev"; \
    fi

# 2. Install shazam2mqtt
COPY pyproject.toml ./
COPY README.md ./
COPY shazam2mqtt/ ./shazam2mqtt/
RUN pip install --no-cache-dir "."

# Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
