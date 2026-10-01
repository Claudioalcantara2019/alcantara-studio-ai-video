import os
import sys
import cv2
import glob
import math
import copy
import pickle
import shutil
import argparse
import subprocess
from pathlib import Path

import numpy as np
import torch
from omegaconf import OmegaConf
from transformers import WhisperModel
from tqdm import tqdm

# Make the official MuseTalk checkout importable.
MUSE_DIR = Path(os.getenv("MUSETALK_DIR", r"C:\Users\minim\MuseTalk"))
if str(MUSE_DIR) not in sys.path:
    sys.path.insert(0, str(MUSE_DIR))

from musetalk.utils.blending import get_image
from musetalk.utils.face_parsing import FaceParsing
from musetalk.utils.audio_processor import AudioProcessor
from musetalk.utils.preprocessing import get_landmark_and_bbox, read_imgs, coord_placeholder

from openvino_runner import OpenVINOBackend

def _ffmpeg_ok():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except Exception:
        return False

def _ensure_ffmpeg():
    if _ffmpeg_ok():
        return
    local = MUSE_DIR / "ffmpeg.exe"
    if local.is_file():
        os.environ["PATH"] = str(MUSE_DIR) + os.pathsep + os.environ.get("PATH", "")
    if not _ffmpeg_ok():
        raise RuntimeError("ffmpeg não encontrado. Coloque ffmpeg.exe em MUSETALK_DIR.")

def preprocess_image(img, half_mask):
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    rgb = cv2.resize(rgb, (256, 256), interpolation=cv2.INTER_LANCZOS4)
    x = rgb.astype(np.float32) / 255.0
    x = np.transpose(x, (2, 0, 1))[None, ...]
    if half_mask:
        x[:, :, 128:, :] = 0.0
    x = (x - 0.5) / 0.5
    return x.astype(np.float32)

def encode_frame(backend, crop):
    masked = backend.encode_latents(preprocess_image(crop, True), sample=True)
    ref = backend.encode_latents(preprocess_image(crop, False), sample=True)
    return np.concatenate([masked, ref], axis=1).astype(np.float32)

def pad_batch(x, size):
    n = x.shape[0]
    if n == size:
        return x, n
    if n > size:
        raise ValueError(f"batch maior que {size}: {n}")
    pad = np.repeat(x[-1:], size - n, axis=0)
    return np.concatenate([x, pad], axis=0), n

def run(args):
    _ensure_ffmpeg()
    backend = OpenVINOBackend()
    print("OpenVINO MuseTalk backend:", backend.info())

    device = torch.device("cpu")
    dtype = torch.float32

    audio_processor = AudioProcessor(feature_extractor_path=args.whisper_dir)
    whisper = WhisperModel.from_pretrained(args.whisper_dir).to(device=device, dtype=dtype).eval()
    whisper.requires_grad_(False)

    # Positional encoding is small and remains in PyTorch CPU.
    from musetalk.models.unet import PositionalEncoding
    pe = PositionalEncoding(d_model=384).to(device).eval()

    fp = FaceParsing(left_cheek_width=args.left_cheek_width,
                     right_cheek_width=args.right_cheek_width)

    cfg = OmegaConf.load(args.inference_config)
    for task_id in cfg:
        video_path = cfg[task_id]["video_path"]
        audio_path = cfg[task_id]["audio_path"]

        input_basename = Path(video_path).stem
        audio_basename = Path(audio_path).stem
        temp_dir = Path(args.result_dir) / "openvino_v15"
        temp_dir.mkdir(parents=True, exist_ok=True)
        result_dir = temp_dir / f"{input_basename}_{audio_basename}"
        result_dir.mkdir(parents=True, exist_ok=True)

        save_dir_full = temp_dir / input_basename
        save_dir_full.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["ffmpeg", "-v", "fatal", "-i", video_path, "-start_number", "0",
             str(save_dir_full / "%08d.png")],
            check=True,
        )
        input_img_list = sorted(glob.glob(str(save_dir_full / "*.[jpJP][pnPN]*[gG]")))
        fps = cv2.VideoCapture(video_path).get(cv2.CAP_PROP_FPS)

        whisper_features, librosa_length = audio_processor.get_audio_feature(audio_path)
        whisper_chunks = audio_processor.get_whisper_chunk(
            whisper_features, device, dtype, whisper, librosa_length, fps=fps,
            audio_padding_length_left=args.audio_padding_length_left,
            audio_padding_length_right=args.audio_padding_length_right,
        )

        crop_coord_path = Path(args.result_dir) / f"{input_basename}.pkl"
        if crop_coord_path.exists() and args.use_saved_coord:
            with open(crop_coord_path, "rb") as f:
                coord_list = pickle.load(f)
            frame_list = read_imgs(input_img_list)
        else:
            print("Extracting landmarks...")
            coord_list, frame_list = get_landmark_and_bbox(input_img_list, 0)
            with open(crop_coord_path, "wb") as f:
                pickle.dump(coord_list, f)

        print("Number of frames:", len(frame_list))

        latent_cache = []
        for bbox, frame in tqdm(zip(coord_list, frame_list), total=len(frame_list), desc="VAE encode"):
            if bbox == coord_placeholder:
                latent_cache.append(None)
                continue
            x1, y1, x2, y2 = bbox
            y2 = min(y2 + args.extra_margin, frame.shape[0])
            crop = frame[y1:y2, x1:x2]
            latent_cache.append(encode_frame(backend, crop))

        valid_latents = [x for x in latent_cache if x is not None]
        if not valid_latents:
            raise RuntimeError("Nenhum rosto válido foi encontrado.")

        # The exported UNet has a fixed batch of 8.
        batch_size = 8
        res_frames = []
        cycle_frames = frame_list + frame_list[::-1]
        cycle_coords = coord_list + coord_list[::-1]
        cycle_latents = latent_cache + latent_cache[::-1]

        video_num = len(whisper_chunks)
        for start in tqdm(range(0, video_num, batch_size), desc="UNet + VAE decode"):
            wbatch = whisper_chunks[start:start + batch_size]
            actual = len(wbatch)

            # Find a valid latent for every requested frame.
            lats = []
            for j in range(actual):
                item = cycle_latents[(start + j) % len(cycle_latents)]
                if item is None:
                    item = valid_latents[(start + j) % len(valid_latents)]
                lats.append(item)
            latent_batch = np.concatenate(lats, axis=0).astype(np.float32)
            latent_batch, _ = pad_batch(latent_batch, batch_size)

            # Positional encoding stays on CPU, then crosses to NumPy.
            with torch.no_grad():
                wb = torch.stack(wbatch).to(device=device, dtype=dtype)
                audio_features = pe(wb).detach().cpu().numpy().astype(np.float32)

            if audio_features.shape[0] < batch_size:
                audio_features = np.concatenate(
                    [audio_features, np.repeat(audio_features[-1:], batch_size - audio_features.shape[0], axis=0)],
                    axis=0,
                )

            timestep = np.zeros(batch_size, dtype=np.int64)
            pred = backend.unet_inference(latent_batch, timestep, audio_features)
            pred = pred[:actual]

            decoded = backend.decode_latents(pred)
            res_frames.extend(list(decoded))

        # Blend generated face back into original frames.
        for i, res_frame in enumerate(tqdm(res_frames, desc="Blending")):
            bbox = cycle_coords[i % len(cycle_coords)]
            if bbox == coord_placeholder:
                continue
            ori = copy.deepcopy(cycle_frames[i % len(cycle_frames)])
            x1, y1, x2, y2 = bbox
            y2 = min(y2 + args.extra_margin, ori.shape[0])
            try:
                res_frame = cv2.resize(res_frame.astype(np.uint8), (x2 - x1, y2 - y1))
            except Exception:
                continue
            combined = get_image(ori, res_frame, [x1, y1, x2, y2],
                                 mode=args.parsing_mode, fp=fp)
            cv2.imwrite(str(result_dir / f"{i:08d}.png"), combined)

        temp_video = temp_dir / f"temp_{input_basename}_{audio_basename}.mp4"
        output = temp_dir / f"{input_basename}_{audio_basename}_openvino.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-v", "warning", "-r", str(fps), "-f", "image2",
             "-i", str(result_dir / "%08d.png"), "-vcodec", "libx264",
             "-vf", "format=yuv420p", "-crf", "18", str(temp_video)],
            check=True,
        )
        subprocess.run(
            ["ffmpeg", "-y", "-v", "warning", "-i", audio_path, "-i",
             str(temp_video), "-shortest", str(output)],
            check=True,
        )
        print("RESULT:", output)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--inference_config", default=str(MUSE_DIR / "configs" / "inference" / "test.yaml"))
    p.add_argument("--whisper_dir", default=str(MUSE_DIR / "models" / "whisper"))
    p.add_argument("--result_dir", default=str(MUSE_DIR / "results"))
    p.add_argument("--extra_margin", type=int, default=10)
    p.add_argument("--audio_padding_length_left", type=int, default=2)
    p.add_argument("--audio_padding_length_right", type=int, default=2)
    p.add_argument("--use_saved_coord", action="store_true")
    p.add_argument("--parsing_mode", default="jaw")
    p.add_argument("--left_cheek_width", type=int, default=90)
    p.add_argument("--right_cheek_width", type=int, default=90)
    run(p.parse_args())

if __name__ == "__main__":
    main()
