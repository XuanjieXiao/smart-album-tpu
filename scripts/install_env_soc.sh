#!/bin/bash
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
pip install -r requirements.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
pip install pyinstaller -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
python3 -m dfss --install sail
pip install numpy==1.25.0 -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple