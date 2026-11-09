#!/usr/bin/env bash
set -e

# Setting up uv package manager
if ! command -v uv >/dev/null 2>&1; then
    printf "Installing uv...\n"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
printf "Setting up 'uv' for the project:\n"
uv sync --locked
printf "UV sync completed\n"

# Checking docker status
if ! command -v docker >/dev/null 2>&1; then 
    printf "Install it from: https://docs.docker.com/engine/install/\n"
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
        printf "Docker engine is unavailable, start the docker application\n"
        exit 1   
fi

# creating data which includes models and images
printf "Creating models and images via docker\n"
docker build -t mooney-blender -f docker/Dockerfile .
docker run --rm \
  -v "$(pwd)/docker/render.py:/app/render.py:ro" \
  -v "$(pwd)/data/rendered:/output" \
  -v "$(pwd)/data/models:/models" \
  mooney-blender blender -b -P /app/render.py