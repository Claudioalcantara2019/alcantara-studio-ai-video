#!/usr/bin/env bash
set -euo pipefail

cd /opt/MuseTalk

mkdir -p models/musetalkV15 models/syncnet models/dwpose models/face-parse-bisent models/sd-vae models/whisper

if ! command -v huggingface-cli >/dev/null 2>&1; then
  python3.10 -m pip install -U "huggingface_hub[cli]==0.30.2"
fi

if ! python3.10 -c "import gdown" >/dev/null 2>&1; then
  python3.10 -m pip install "gdown==4.7.3"
fi

huggingface-cli download TMElyralab/MuseTalk   --local-dir models   --include "musetalkV15/musetalk.json" "musetalkV15/unet.pth"

huggingface-cli download stabilityai/sd-vae   --local-dir models/sd-vae   --include "config.json" "diffusion_pytorch_model.bin"

huggingface-cli download openai/whisper-tiny   --local-dir models/whisper   --include "config.json" "pytorch_model.bin" "preprocessor_config.json"

huggingface-cli download yzd-v/DWPose   --local-dir models/dwpose   --include "dw-ll_ucoco_384.pth"

huggingface-cli download ByteDance/LatentSync   --local-dir models/syncnet   --include "latentsync_syncnet.pt"

if [ ! -s models/face-parse-bisent/79999_iter.pth ]; then
  gdown --id 154JgKpzCPW82qINcVieuPH3fZ2e0P812 -O models/face-parse-bisent/79999_iter.pth
fi

if [ ! -s models/face-parse-bisent/resnet18-5c106cde.pth ]; then
  curl -L --fail --retry 3 https://download.pytorch.org/models/resnet18-5c106cde.pth -o models/face-parse-bisent/resnet18-5c106cde.pth
fi

echo "MuseTalk 1.5 models ready."
