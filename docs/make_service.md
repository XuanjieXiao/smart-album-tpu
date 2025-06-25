# Smart Album Service Deployment Guide

## Building and Running the Smart Album Service
docker build -f packaging_file/Dockerfile_x86 -t my-smart-album:latest .

docker run \
    --privileged \
    -d \
    -it \
    -v /dev:/dev \
    -v /opt:/opt \
    -v "$(pwd)/data:/app/data" \
    -v "$(pwd)/uploads:/app/uploads" \
    -v "$(pwd)/thumbnails:/app/thumbnails" \
    -p 18080:18088 \
    --name smart-album-container \
    my-smart-album:latest

docker logs -f smart-album-container


