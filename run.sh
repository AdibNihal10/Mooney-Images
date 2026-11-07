# first we need to create images via docker 

docker build -t mooney-blender -f docker/Dockerfile .
docker run --rm \
  -v "$(pwd)/docker/render.py:/app/render.py:ro" \
  -v "$(pwd)/data/rendered:/output" \
  mooney-blender blender -b -P /app/render.py