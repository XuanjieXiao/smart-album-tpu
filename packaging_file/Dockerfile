# Build linux kernel general dockerfile configuration file
FROM ubuntu:20.04

# define param
ARG PLATFORM="BM1688"
ARG LICENSE_BM="10001"
RUN echo "The PLATFORM is: $PLATFORM"
RUN echo "The LICENSE_BM is: ${LICENSE_BM}"

# Add apt sources
RUN cp -a /etc/apt/sources.list /etc/apt/sources.list.bak
RUN sed -i 's|http://.*.ubuntu.com|http://ports.ubuntu.com|g' /etc/apt/sources.list && \
    echo "deb http://ports.ubuntu.com/ubuntu-ports focal main restricted universe multiverse" > /etc/apt/sources.list && \
    echo "deb http://ports.ubuntu.com/ubuntu-ports focal-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb http://ports.ubuntu.com/ubuntu-ports focal-security main restricted universe multiverse" >> /etc/apt/sources.list

# Add apt software
ENV DEBIAN_FRONTEND=noninteractive 

RUN mkdir -p /workspace/smart-album/models /data/log
COPY .  /workspace/smart-album/
WORKDIR /workspace/smart-album
COPY ./start_run.sh  /workspace/smart-album/
RUN chmod 777 /tmp

RUN echo "LICENSE_BM: ${LICENSE_BM}" > /data/config.yaml && \
    chmod 644 /data/config.yaml && cat /data/config.yaml

# Add library path
ENV PYTHONPATH "$PYTHONPATH:/opt/sophon/libsophon-current/lib:/opt/sophon/sophon-opencv-latest/opencv-python/"
ENV LD_LIBRARY_PATH "$LD_LIBRARY_PATH:/opt/sophon/libsophon-current/lib:/opt/sophon/sophon-opencv-latest/lib:/opt/sophon/sophon-ffmpeg-latest/lib:/opt/sophon/sophon-soc-libisp_1.0.0/lib"

RUN apt-get update && apt-get install -y apt-utils \
    && apt-get install -y --on-install-recommends unzip \
    && apt-get install -y --no-install-recommends locales libncurses5 python3-dev python3-pip build-essential gcc g++ portaudio19-dev \
    && pip3 install -r /workspace/smart-album/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && python3 -m dfss --url=open@sophgo.com:/SILK/level-4/silkcpt/v1.0.4/silkcpt_aarch64/silkcpt-1.0.4-py3-none-manylinux2014_aarch64.whl \
    && pip3 install silkcpt-1.0.4-py3-none-manylinux2014_aarch64.whl \
    && rm -rf silkcpt-1.0.4-py3-none-manylinux2014_aarch64.whl

WORKDIR /workspace/smart-album

RUN if [ "$PLATFORM" = "BM1688" ]; then \
    python3 -m dfss --url=open@sophgo.com:/SILK/level-3/smart-album/sophon_arm-3.10.3-py3-none-any.whl \
    && pip3 install sophon_arm-3.10.3-py3-none-any.whl \
    && mkdir -p /workspace/smart-album/models/BM1688 \
    && mkdir -p /workspace/smart-album/BM1688 \
    && touch /workspace/smart-album/models/BM1688/pass \
    && cd /workspace/smart-album/BM1688 \
    fi \
    && if [ "$PLATFORM" = "BM1684X" ]; then \
        python3 -m dfss --url=open@sophgo.com:/SILK/level-3/smart-album/sail_1684X/sophon_arm-3.10.3-py3-none-any.whl \
        && pip3 install sophon_arm-3.10.3-py3-none-any.whl \
        && mkdir /workspace/smart-album/models/BM1684X \
        && mkdir /workspace/smart-album/BM1684X \
        && touch /workspace/smart-album/models/BM1684X/pass \
        && cd /workspace/smart-album/BM1684X \
    fi \
    && cd /workspace/smart-album \
    && pyinstaller --onedir --add-data "tmp:tmp" --add-data "LLMs:LLMs" --add-data "models:models" subserver.py \
    && mv dist/subserver ./ \
    && pyinstaller --onedir --add-data "subserver:subserver" server.py \
    && if [ "$PLATFORM" = "BM1684X" ]; then \
        rm -rf dist/server/_internal/subserver/_internal/models/BM1684X \
        && mv BM1684X dist/server/_internal/subserver/_internal/models/; \
    else \
        rm -rf dist/server/_internal/subserver/_internal/models/BM1688 \
        && mv BM1688 dist/server/_internal/subserver/_internal/models/; \
    fi \
    && mv dist/server ../ \
    && mv request.py ../server \
    && mv test.py ../server \
    && mv Packaging_file/start_run.sh ../server \
    && cd /workspace/server/_internal/subserver/_internal/LLMs \
    && rm -f qwen/qwen* baichuan2/baichuan2* chatglm2/chatglm2* chatglm3/chatglm3* chatglm4/chatglm4* minicpm3/minicpm3* \
    && cd /workspace \
    && rm -rf smart-album \
    && apt-get remove -y --no-install-recommends unzip g++ gcc python3-pip apt-utils  build-essential \
    && apt-get purge -y g++ gcc apt-utils build-essential \
    && apt-get autoremove -y \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && rm -rf /root/.cache/* \
# Set the locale
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

WORKDIR /workspace/server
ENTRYPOINT ["/bin/bash", "start_run.sh"]