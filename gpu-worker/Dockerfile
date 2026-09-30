FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV MUSETALK_DIR=/opt/MuseTalk
ENV MUSETALK_PYTHON=python3.10

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 python3.10-dev python3-pip ffmpeg git wget ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN git clone --depth 1 https://github.com/TMElyralab/MuseTalk.git /opt/MuseTalk

WORKDIR /opt/MuseTalk
RUN python3.10 -m pip install --upgrade pip setuptools wheel

RUN python3.10 -m pip install \
    torch==2.0.1+cu118 \
    torchvision==0.15.2+cu118 \
    torchaudio==2.0.2+cu118 \
    --index-url https://download.pytorch.org/whl/cu118

RUN python3.10 -m pip install -r requirements.txt

RUN python3.10 -m pip install --no-cache-dir -U openmim \
    && mim install mmengine \
    && mim install "mmcv==2.0.1" \
    && mim install "mmdet==3.1.0" \
    && mim install "mmpose==1.1.0"

WORKDIR /app
COPY requirements.txt .
RUN python3.10 -m pip install -r requirements.txt

COPY main.py .
COPY musetalk_runner.py .
COPY download_models.sh .
RUN chmod +x /app/download_models.sh

RUN mkdir -p /data/jobs

EXPOSE 8000
CMD ["python3.10", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
