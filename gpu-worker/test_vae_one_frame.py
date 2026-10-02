import os, sys, cv2, pickle
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
MUSE_DIR = Path(os.getenv("MUSETALK_DIR", r"C:\\Users\\minim\\MuseTalk"))
os.chdir(MUSE_DIR)
sys.path.insert(0, str(MUSE_DIR))
sys.path.insert(0, str(ROOT))

from openvino_runner import OpenVINOBackend
from musetalk.utils.preprocessing import read_imgs, coord_placeholder
from openvino_musetalk import preprocess_image

video = MUSE_DIR / "test5.mp4"
coord_file = MUSE_DIR / "results" / "test5.pkl"
cap = cv2.VideoCapture(str(video))
ok, frame = cap.read()
cap.release()
if not ok:
    raise RuntimeError("Não foi possível ler test5.mp4")

if coord_file.exists():
    with open(coord_file, "rb") as f:
        coords = pickle.load(f)
    bbox = next((b for b in coords if b != coord_placeholder), None)
else:
    bbox = None

if bbox is None:
    h, w = frame.shape[:2]
    side = min(h, w)
    x1, y1 = (w-side)//2, (h-side)//2
    bbox = [x1, y1, x1+side, y1+side]

x1, y1, x2, y2 = bbox
y2 = min(y2 + 10, frame.shape[0])
crop = frame[y1:y2, x1:x2]

backend = OpenVINOBackend()
latent = backend.encode_latents(preprocess_image(crop, False), sample=False)
recon = backend.decode_latents(latent)[0]
recon = cv2.resize(recon.astype(np.uint8), (crop.shape[1], crop.shape[0]))

out = MUSE_DIR / "results" / "vae-check.png"
# Side-by-side: original crop | OpenVINO VAE reconstruction.
side = np.concatenate([crop, recon], axis=1)
cv2.imwrite(str(out), side)
print("VAE_CHECK:", out)
