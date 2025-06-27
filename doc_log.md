docker run --privileged --name smartalbum -v /dev:/dev -v /opt:/opt -v $PWD:/workspace -p 18088:18088 -it ubuntu:20.04

docker run --privileged --name smartalbum -v /dev:/dev -v /opt:/opt -v $PWD:/workspace -p 18088:18088 -it ubuntu:20.04


docker run \
    --privileged \
    -d \
    -p 18088:18088 \
    --name smart-album-container \
    -v /dev:/dev \
    -v /opt:/opt \
    -v $(pwd)/uploads:/workspace/smart_album/uploads \
    -v $(pwd)/thumbnails:/workspace/smart_album/thumbnails \
    -v $(pwd)/data:/workspace/smart_album/data \
    smart-album:latest
docker run --privileged -d -p 18088:18088 --name smart-album-container -v /dev:/dev -v /opt:/opt -v $(pwd)/uploads:/workspace/smart_album/uploads -v $(pwd)/thumbnails:/workspace/smart_album/thumbnails -v $(pwd)/data:/workspace/smart_album/data my-smart-album:latest



docker build -f packaging_file/Dockerfile -t my-smart-album:latest . > build.log 2>&1

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

export DEBIAN_FRONTEND=noninteractive
ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
apt update
apt install -y tzdata
dpkg-reconfigure --frontend noninteractive tzdata
apt install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt update
apt install -y python3.10 python3.10-venv python3.10-dev python3.10-distutils python3-pip
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
update-alternatives --install /usr/bin/python  python  /usr/bin/python3.10 1
update-alternatives --set python3 /usr/bin/python3.10
update-alternatives --set python  /usr/bin/python3.10
apt-get install -y --no-install-recommends file locales dkms libncurses5 build-essential gcc g++ unzip cmake libgl1
python3.10 -m ensurepip --upgrade
python3.10 -m pip install --upgrade pip
ln -sf /usr/bin/pip3.10 /usr/bin/pip
ln -sf /usr/local/bin/pip3.10 /usr/bin/pip3.10
update-alternatives --install /usr/bin/pip pip /usr/bin/pip3.10 1
update-alternatives --set pip /usr/bin/pip3.10

cd /workspace/smart-album-tpu/
pip install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple


python3 -m dfss --url=open@sophgo.com:SILK/level-4/smart-album/sophon-sail.zip
unzip sophon-sail.zip
rm sophon-sail.zip
cd sophon-sail
mkdir build && cd build
cmake -DONLY_RUNTIME=ON ..
make pysail -j 64
cd ../python
chmod +x sophon_whl.sh
./sophon_whl.sh
pip3 install ./dist/sophon-3.10.3-py3-none-any.whl --force-reinstall



export PYTHONPATH="/opt/sophon/libsophon-current/lib:/opt/sophon/sophon-opencv-latest/opencv-python:$PYTHONPATH"
export LD_LIBRARY_PATH="/opt/sophon/libsophon-current/lib:/opt/sophon/sophon-opencv-latest/lib:/opt/sophon/sophon-ffmpeg-latest/lib:/opt/sophon/sophon-soc-libisp_1.0.0/lib:$LD_LIBRARY_PATH"



pyinstaller --onedir \
    --name 'smart_album' \
    --add-data 'models/BM1684X:models/BM1684X' \
    --add-data 'models/shibing624:models/shibing624' \
    --add-data 'static:static' \
    --add-data 'templates:templates' \
    --add-data 'data/app_config.json:data' \
    --add-data 'clip/vocab.txt:clip' \
    --add-data "$(python3 -c 'import numpy; import os; print(os.path.dirname(numpy.__file__))'):numpy" \
    --hidden-import 'sophon.sail' \
    --hidden-import 'cv2' \
    --hidden-import 'distutils' \
    app.py