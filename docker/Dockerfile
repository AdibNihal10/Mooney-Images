FROM ubuntu:24.04
RUN apt-get update
RUN apt-get update && apt-get install -y blender libegl1
# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install Objaverse into Blender's Python environment
RUN uv pip install --system --break-system-packages --python /usr/bin/python3.12 objaverse