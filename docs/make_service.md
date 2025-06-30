# Smart Album Service Deployment Guide
因国内dockerhub的限制，需要换源，请使用下面方法换源：

修改 /etc/docker/daemon.json（没有就新建）
```bash
vim /etc/docker/daemon.json
```
添加以下内容：
```bash
{
    "registry-mirrors": [
        "https://docker-0.unsee.tech"
    ]
}
```
重启docker服务：
```bash
sudo systemctl restart docker
```
## Building and Running the Smart Album Service for X86
通过以下命令新建X86服务器使用的BM1684X的docker的image：
```bash
docker build -f packaging_file/Dockerfile_X86 -t my-smart-album:latest .
```
启动一个container：
```bash
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
```
输出启动的container的日志：
```bash
docker logs -f smart-album-container
```
## Building and Running the Smart Album Service for SOC
请注意修改对应的参数：
```
--build-arg PLATFORM="BM1684X"
可以选择 "BM1684X" 、 "BM1688_1CORE" "BM1688_2CORE"
```

```bash
docker build -f packaging_file/Dockerfile_SOC --build-arg PLATFORM="BM1684X" -t smart-album:latest . 
docker build -f packaging_file/Dockerfile_SOC --build-arg PLATFORM="BM1688_1CORE" -t smart-album:latest . 
docker build -f packaging_file/Dockerfile_SOC --build-arg PLATFORM="BM1688_2CORE" -t smart-album:latest . 
```

启动一个container：
```bash
docker run \
    --privileged \
    -d \
    -it \
    -v /dev:/dev \
    -v /opt:/opt \
    -v "$(pwd)/data:/app/data" \
    -v "$(pwd)/uploads:/app/uploads" \
    -v "$(pwd)/thumbnails:/app/thumbnails" \
    -p 18088:18088 \
    --name smart-album-container \
    smart-album:latest
```

## Running the Smart Album Service in Interactive Mode(debug调试模式进入docker，方便进行问题定位)
```bash
docker run \
    --rm \
    -it \
    -v /dev:/dev \
    -v /opt:/opt \
    -v "$(pwd)/data:/app/data" \
    -v "$(pwd)/uploads:/app/uploads" \
    -v "$(pwd)/thumbnails:/app/thumbnails" \
    -p 18088:18088 \
    --entrypoint bash \
    smart-album:latest
```