# 阶段 1: 构建环境和打包可执行文件
FROM ubuntu:20.04 as builder

# 设置环境变量为非交互式，避免时区等配置弹窗
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# 安装系统依赖和 Python 3.10
RUN apt-get update && \
    apt-get install -y tzdata software-properties-common build-essential gcc g++ unzip cmake libgl1 git curl wget && \
    ln -fs /usr/share/zoneinfo/${TZ} /etc/localtime && \
    dpkg-reconfigure --frontend noninteractive tzdata && \
    add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.10 python3.10-venv python3.10-dev python3.10-distutils python3-pip && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 && \
    python3.10 -m ensurepip --upgrade && \
    python3.10 -m pip install --upgrade pip && \
    ln -sf /usr/bin/pip3.10 /usr/bin/pip && \
    ln -sf /usr/local/bin/pip3.10 /usr/bin/pip3.10 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3.10 1 && \
    update-alternatives --set pip /usr/bin/pip3.10 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /workspace/smart_album
RUN mkdir -p /workspace/smart_album/models/BM1684X
RUN mkdir /workspace/smart_album/thumbnails
RUN mkdir /workspace/smart_album/uploads
RUN mkdir /workspace/smart_album/data
RUN mkdir /workspace/smart_album/static
RUN mkdir /workspace/smart_album/scripts
RUN mkdir /workspace/smart_album/templates
RUN mkdir /workspace/smart_album/tools
RUN mkdir /workspace/smart_album/bce_embedding
RUN mkdir /workspace/smart_album/clip
COPY ./requirements.txt  /workspace/smart_album
COPY ./bce_embedding /workspace/smart_album/bce_embedding
COPY ./clip /workspace/smart_album/clip
COPY *.py /workspace/smart_album
COPY ./scripts /workspace/smart_album/scripts
COPY ./static /workspace/smart_album/static
COPY ./templates /workspace/smart_album/templates
COPY ./models/BM1684X /workspace/smart_album/models/BM1684X
COPY ./tools /workspace/smart_album/tools
COPY ./data/app_config.json /workspace/smart_album/data


# 安装 Python 依赖
# 使用 --no-cache-dir 减小镜像体积
RUN pip install --no-cache-dir pyinstaller==6.8.0 && \
    pip install --no-cache-dir torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple && \
    pip install --no-cache-dir --upgrade urllib3 chardet

# 安装 Sophon SAIL 库

RUN python3 -m dfss --url=open@sophgo.com:sophon-demo/Qwen/qwq/sophon-libsophon_0.5.2_amd64.deb && \
    python3 -m dfss --url=open@sophgo.com:sophon-demo/Qwen/qwq/sophon-libsophon-dev_0.5.2_amd64.deb && \
    dpkg -i sophon-libsophon_0.5.2_amd64.deb sophon-libsophon-dev_0.5.2_amd64.deb && \
    python3 -m dfss --url=open@sophgo.com:SILK/level-4/smart-album/sophon-sail.zip && \
    unzip sophon-sail.zip && \
    rm sophon-sail.zip && \
    cd sophon-sail && \
    mkdir build && cd build && \
    cmake -DONLY_RUNTIME=ON .. && \
    make pysail -j$(nproc) && \
    cd ../python && \
    chmod +x sophon_whl.sh && \
    ./sophon_whl.sh && \
    pip3 install --no-cache-dir ./dist/sophon-3.10*.whl --force-reinstall

# 使用 PyInstaller 打包应用
# --hidden-import 确保 PyInstaller 能找到动态加载的库
RUN pyinstaller app.py \
    --name smart_album \
    --noconfirm \
    --onedir \
    --add-data "static:static" \
    --add-data "templates:templates" \
    --add-data "models:models" \
    --add-data "data/app_config.json:data" \
    --add-data "clip/vocab.txt:clip" \
    --collect-data transformers \
    --hidden-import="sophon.sail" \
    --hidden-import="flask_cors" \
    --hidden-import="faiss" \
    --hidden-import="sklearn" \
    --hidden-import="timm"

# 阶段 2: 创建最终的、轻量化的运行镜像
FROM ubuntu:20.04

# 设置环境变量
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# 仅安装必要的运行时库
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgl1 python3.10 && \
    rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /workspace/smart_album

# 从 builder 阶段复制打包好的应用
COPY --from=builder /workspace/smart_album/dist/smart_album .

# 声明数据卷，用于持久化存储用户上传的图片和数据库文件
VOLUME ["/smart_album/data", "/smart_album/uploads", "/smart_album/thumbnails"]

# 声明应用监听的端口
EXPOSE 18088

# 容器启动时执行的命令
# 模型路径是相对于工作目录 /smart_album 的，这与 PyInstaller 打包后的结构一致
CMD ["./smart_album", \
     "--image_model=./models/BM1684X/cn_clip_image_vit_h_14_bm1684x_f16_1b.bmodel", \
     "--text_model=./models/BM1684X/cn_clip_text_vit_h_14_bm1684x_f16_1b.bmodel", \
     "--bce_model=./models/BM1684X/text2vec_base_chinese_bm1684x_f16_1b.bmodel", \
     "--dev_id=5"]