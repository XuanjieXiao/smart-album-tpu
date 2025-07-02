# 智能相册服务部署指南
因国内dockerhub的限制，需要换源，请使用下面方法换源：

修改 /etc/docker/daemon.json（没有就新建）
```bash
sudo vim /etc/docker/daemon.json
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
## 构建并运行 X86 智能相册服务
通过以下命令新建X86服务器使用的BM1684X的docker的image：
```bash
docker build -f packaging_file/Dockerfile_X86 -t smart_album_x86_1684x_1core:latest .
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
    smart_album_x86_1684x_1core:latest
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
# 编译打包1684x的平台20.04版本
docker build -f packaging_file/Dockerfile_SOC_1684x --build-arg PLATFORM="BM1684X" -t smart_album_soc_1684x_1core:latest . 
# 编译打包BM1688的22.04的版本
docker build -f packaging_file/Dockerfile_SOC_1688 --build-arg PLATFORM="BM1688_1CORE" -t smart_album_soc_1688_1core:latest . 
docker build -f packaging_file/Dockerfile_SOC_1688 --build-arg PLATFORM="BM1688_2CORE" -t smart_album_soc_1688_2core:latest . 
# 编译打包BM1688的20.04的版本
docker build -f packaging_file/Dockerfile_SOC_1688_20 --build-arg PLATFORM="BM1688_2CORE" -t smart_album_soc_1688_2core_20:v1.0.0 . 
#可以编译"BM1684X" 、 "BM1688_1CORE" "BM1688_2CORE"三种平台，为ubuntu20.04版本
docker build -f packaging_file/Dockerfile_SOC --build-arg PLATFORM="BM1688_2CORE" -t smart_album_soc_1688_2core_20:latest . 
```

启动一个container，注意选择 **-e PLATFORM=BM1684X** 参数，保证正确的选择环境：
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
    -e PLATFORM=BM1684X \
    --name smart-album-container \
    smart_album_soc_1684x_1core:latest
```

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
    -e PLATFORM=BM1688_2CORE \
    --name smart-album-container \
    smart_album_soc_1688_2core:latest
```

## debug调试模式进入docker，方便进行问题定位
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
    smart_album_soc_1688_2core:latest
```



## 保存docker镜像
```bash
docker save -o smart_album_soc_1684x_1core.tar smart_album_soc_1684x_1core:latest
docker save -o smart_album_soc_1688_1core.tar smart_album_soc_1688_1core:latest
docker save -o smart_album_soc_1688_2core.tar smart_album_soc_1688_2core:latest
docker save -o smart_album_soc_1688_2core_20.tar smart_album_soc_1688_2core_20:latest
```

## 加载docker镜像：
```bash
docker load < smart_album_soc_1684x_1core.tar
docker load < smart_album_soc_1688_1core.tar
docker load < smart_album_soc_1688_2core.tar
```