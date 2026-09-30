import os
import subprocess
from pathlib import Path

MUSE_DIR = Path(os.getenv("MUSETALK_DIR", "/opt/MuseTalk"))
PYTHON = os.getenv("MUSETALK_PYTHON", "python3.10")
MODEL = MUSE_DIR / "models" / "musetalkV15" / "unet.pth"
CONFIG = MUSE_DIR / "models" / "musetalkV15" / "musetalk.json"
WHISPER = MUSE_DIR / "models" / "whisper"
DWPose = MUSE_DIR / "models" / "dwpose"
FACE_PARSE = MUSE_DIR / "models" / "face-parse-bisent"
SYNCNET = MUSE_DIR / "models" / "syncnet"
SD_VAE = MUSE_DIR / "models" / "sd-vae"


def validate_paths(video: Path, audio: Path) -> None:
    if not video.is_file():
        raise RuntimeError(f"Vídeo de entrada não encontrado: {video}")
    if not audio.is_file():
        raise RuntimeError(f"Áudio de entrada não encontrado: {audio}")
    if video.stat().st_size == 0:
        raise RuntimeError("O vídeo de entrada está vazio.")
    if audio.stat().st_size == 0:
        raise RuntimeError("O áudio de entrada está vazio.")


def run_musetalk(video: Path, audio: Path, workdir: Path) -> Path:
    validate_paths(video, audio)

    if not MUSE_DIR.exists():
        raise RuntimeError(f"MuseTalk não encontrado em {MUSE_DIR}")

    if not workdir.exists():
        workdir.mkdir(parents=True, exist_ok=True)

    required = [
        MODEL,
        CONFIG,
        WHISPER / "config.json",
        WHISPER / "pytorch_model.bin",
        WHISPER / "preprocessor_config.json",
        DWPose / "dw-ll_ucoco_384.pth",
        FACE_PARSE / "79999_iter.pth",
        FACE_PARSE / "resnet18-5c106cde.pth",
        SYNCNET / "latentsync_syncnet.pt",
        SD_VAE / "config.json",
        SD_VAE / "diffusion_pytorch_model.bin",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise RuntimeError("Modelos MuseTalk ausentes: " + ", ".join(missing))

    config_file = workdir / "inference.yaml"
    config_file.write_text(
        f'task_0:\n'
        f'  video_path: "{video.as_posix()}"\n'
        f'  audio_path: "{audio.as_posix()}"\n'
        f'  result_name: "musetalk_result.mp4"\n',
        encoding="utf-8",
    )

    result_dir = workdir / "musetalk"
    result_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(MUSE_DIR)
    env["MPLBACKEND"] = "Agg"
    env["TOKENIZERS_PARALLELISM"] = "false"
    env["PYTORCH_CUDA_ALLOC_CONF"] = os.getenv(
        "PYTORCH_CUDA_ALLOC_CONF",
        "expandable_segments:True",
    )

    command = [
        PYTHON,
        "scripts/inference.py",
        "--inference_config", str(config_file),
        "--unet_config", str(CONFIG),
        "--unet_model_path", str(MODEL),
        "--whisper_dir", str(WHISPER),
        "--result_dir", str(result_dir),
        "--version", "v15",
        "--use_float16",
        "--batch_size", os.getenv("MUSETALK_BATCH_SIZE", "4"),
    ]

    completed = subprocess.run(
        command,
        cwd=MUSE_DIR,
        env=env,
        capture_output=True,
        text=True,
    )

    if completed.returncode != 0:
        raise RuntimeError(
            "MuseTalk falhou.\nSTDOUT:\n"
            + completed.stdout[-6000:]
            + "\nSTDERR:\n"
            + completed.stderr[-6000:]
        )

    candidates = list(result_dir.rglob("musetalk_result.mp4"))
    if not candidates:
        candidates = list(result_dir.rglob("*.mp4"))

    if not candidates:
        raise RuntimeError("MuseTalk terminou sem produzir MP4.")

    return candidates[-1]
