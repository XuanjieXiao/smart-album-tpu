#!/bin/bash
set -e

PLATFORM=$1
DOCKERFILE_ORIG="packaging_file/Dockerfile_SOC"

if [[ "$PLATFORM" == "BM1684X" ]]; then
  BASE_IMAGE="ubuntu:20.04"
elif [[ "$PLATFORM" == "BM1688_1CORE" || "$PLATFORM" == "BM1688_2CORE" ]]; then
  BASE_IMAGE="ubuntu:22.04"
else
  echo "Error: Unsupported PLATFORM $PLATFORM"
  exit 1
fi

echo "Building with base image: $BASE_IMAGE"

# 替换 __BASE_IMAGE__ 并构建临时 Dockerfile
sed "s#__BASE_IMAGE__#FROM $BASE_IMAGE#g" "$DOCKERFILE_ORIG" > Dockerfile.temp

# 构建镜像
docker build -f Dockerfile.temp --build-arg PLATFORM="$PLATFORM" -t smart-album:"$PLATFORM" .

# 清理临时文件
rm Dockerfile.temp
