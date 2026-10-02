import os, sys, cv2
from pathlib import Path
import numpy as np
import torch
from transformers import WhisperModel

ROOT = Path(__file__).resolve().parent
MUSE_DIR = Path(os.getenv("MUSETALK_DIR", r"C:\\Users\\minim\\MuseTalk"))
os.chdir(MUSE_DIR)
sys.path.insert(0, str(MUSE_DIR))
sys.path.insert(0, str(ROOT))

from openvino_runner import OpenVINOBackend
from openvino_musetalk import preprocess_image
from musetalk.utils.audio_processor import AudioProcessor
from musetalk.models.unet import PositionalEncoding

video = MUSE_DIR / "test5.mp4"
audio = MUSE_DIR / "test5.mp3"

cap = cv2.VideoCapture(str(video))
ok, frame = cap.read()
cap.release()
if not ok:
    raise RuntimeError("Não foi possível ler test5.mp4")

# Detect a face quickly without running the slow DWPose pipeline.
cascade = cv2.CascadeClassifier(str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"))
gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
if len(faces) == 0:
    raise RuntimeError("Não encontrei um rosto no primeiro frame.")
x, y, w, h = max(faces, key=lambda r: r[2] * r[3])
margin_x = int(w * 0.15)
margin_top = int(h * 0.15)
margin_bottom = int(h * 0.20)
x1 = max(0, x - margin_x)
y1 = max(0, y - margin_top)
x2 = min(frame.shape[1], x + w + margin_x)
y2 = min(frame.shape[0], y + h + margin_bottom)
crop = frame[y1:y2, x1:x2]

backend = OpenVINOBackend()
masked = backend.encode_latents(preprocess_image(crop, True), sample=False)
ref = backend.encode_latents(preprocess_image(crop, False), sample=False)
latent = np.concatenate([masked, ref], axis=1).astype(np.float32)

# One Whisper chunk, matching the main OpenVINO pipeline.
audio_processor = AudioProcessor(feature_extractor_path=str(MUSE_DIR / "models" / "whisper"))
whisper = WhisperModel.from_pretrained(str(MUSE_DIR / "models" / "whisper")).to(device="cpu", dtype=torch.float32).eval()
whisper.requires_grad_(False)
pe = PositionalEncoding(d_model=384).to("cpu").eval()
features, librosa_length = audio_processor.get_audio_feature(str(audio))
chunks = audio_processor.get_whisper_chunk(features, torch.device("cpu"), torch.float32, whisper, librosa_length, fps=25, audio_padding_length_left=2, audio_padding_length_right=2)
with torch.no_grad():
    audio_feature = pe(chunks[0:1]).detach().cpu().numpy().astype(np.float32)

timestep = np.zeros(1, dtype=np.int64)
pred = backend.unet_inference(latent, timestep, audio_feature)
decoded = backend.decode_latents(pred)[0]
decoded = cv2.resize(decoded.astype(np.uint8), (crop.shape[1], crop.shape[0]))

out = MUSE_DIR / "results" / "unet-check.png"
side = np.concatenate([crop, decoded], axis=1)
cv2.imwrite(str(out), side)
print("UNET_CHECK:", out)
