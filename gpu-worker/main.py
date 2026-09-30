import asyncio
import shutil
import json
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from musetalk_runner import run_musetalk

DATA_DIR = Path("/data/jobs")
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Alcantara Studio GPU Worker", version="0.3.0")
jobs: dict[str, dict] = {}
GPU_CONCURRENCY = max(1, int(__import__("os").getenv("GPU_CONCURRENCY", "1")))
MAX_VIDEO_DURATION_SECONDS = float(__import__("os").getenv("MAX_VIDEO_DURATION_SECONDS", "900"))
MAX_UPLOAD_BYTES = int(__import__("os").getenv("MAX_UPLOAD_BYTES", str(2 * 1024 * 1024 * 1024)))
GPU_SEMAPHORE = asyncio.Semaphore(GPU_CONCURRENCY)

def save_job(job: dict) -> None:
    job_dir = DATA_DIR / job["jobId"]
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")


def load_jobs() -> None:
    for job_file in DATA_DIR.glob("*/job.json"):
        try:
            job = json.loads(job_file.read_text(encoding="utf-8"))
            jobs[job["jobId"]] = job
        except Exception:
            continue




# Restore persisted jobs whenever the worker starts so status/result survive restarts.
load_jobs()


def utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def mark_interrupted_jobs() -> bool:
    # A Python asyncio task cannot survive a process restart. Do not leave
    # queued/processing jobs looking alive forever after a worker restart.
    changed = False
    for job in jobs.values():
        if job.get("status") in {"queued", "processing"}:
            job["status"] = "failed"
            job["stage"] = "failed"
            job["progress"] = 0
            job["message"] = "Processamento interrompido pela reinicialização do worker. Envie novamente."
            job["error"] = job["message"]
            job["failedAt"] = utc_now()
            save_job(job)
            changed = True
    return changed


@app.on_event("startup")
async def startup() -> None:
    mark_interrupted_jobs()


def normalize_video_for_musetalk(source: Path, destination: Path) -> None:
    import subprocess

    command = [
        "ffmpeg", "-y", "-i", str(source),
        "-vf", "fps=25",
        "-an",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        str(destination),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-5000:])


def media_duration(path: Path) -> float:
    import subprocess

    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("Não foi possível ler a duração do arquivo.")
    try:
        return float(result.stdout.strip())
    except ValueError:
        raise RuntimeError("Duração de mídia inválida.")


def probe_media(path: Path) -> dict:
    import subprocess

    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate",
            "-of", "json",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Não foi possível analisar a mídia: {path.name}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Resposta inválida do ffprobe para {path.name}")



def file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def cleanup_old_jobs(max_age_hours: int = 72) -> None:
    import time

    now = time.time()
    max_age = max_age_hours * 3600
    for job_dir in DATA_DIR.iterdir():
        if not job_dir.is_dir():
            continue
        try:
            if now - job_dir.stat().st_mtime > max_age:
                shutil.rmtree(job_dir, ignore_errors=True)
                jobs.pop(job_dir.name, None)
        except OSError:
            continue

def output_size(video_format: str) -> tuple[int, int]:
    return (1920, 1080) if video_format == "16:9" else (1080, 1920)



def compose_scene(source: Path, destination: Path, scene: str) -> None:
    if scene == "original":
        shutil.copy2(source, destination)
        return
    raise RuntimeError(
        f'Scenario "{scene}" ainda nao esta disponivel no motor de composicao.'
    )

def finalize_video(source: Path, destination: Path, video_format: str) -> None:
    width, height = output_size(video_format)
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height}"
    )

    command = [
        "ffmpeg", "-y",
        "-i", str(source),
        "-map", "0:v:0",
        "-map", "0:a:0?",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-ar", "48000",
        "-shortest",
        "-movflags", "+faststart",
        str(destination),
    ]

    import subprocess
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-5000:])

    if not destination.is_file() or destination.stat().st_size == 0:
        raise RuntimeError("O vídeo final não foi criado corretamente.")


async def process_job(job_id: str) -> None:
    job = jobs[job_id]
    async with GPU_SEMAPHORE:
        job["status"] = "processing"
        job["startedAt"] = utc_now()
        job["progress"] = 5
        job["message"] = "Preparando vídeo para o processamento..."
        job["stage"] = "normalizing"
        save_job(job)
        workdir = DATA_DIR / job_id

        try:
            video_info = probe_media(workdir / "input.mp4")
            audio_info = probe_media(workdir / job["audio_filename"])
            video_duration = float(video_info.get("format", {}).get("duration", 0))
            audio_duration = float(audio_info.get("format", {}).get("duration", 0))
            video_streams = [s for s in video_info.get("streams", []) if s.get("codec_type") == "video"]
            audio_streams = [s for s in audio_info.get("streams", []) if s.get("codec_type") == "audio"]

            if not video_streams:
                raise RuntimeError("O arquivo enviado não contém uma faixa de vídeo válida.")
            if not audio_streams:
                raise RuntimeError("O arquivo enviado não contém uma faixa de áudio válida.")

            job["media"] = {
                "video_duration": round(video_duration, 3),
                "audio_duration": round(audio_duration, 3),
                "video_codec": video_streams[0].get("codec_name"),
                "audio_codec": audio_streams[0].get("codec_name"),
            }
            save_job(job)

            if video_duration + 0.5 < audio_duration:
                raise RuntimeError(
                    f"O vídeo-base ({video_duration:.1f}s) é menor que a música ({audio_duration:.1f}s). "
                    "O vídeo precisa cobrir toda a duração da música."
                )

            if video_duration > audio_duration + 0.5:
                job["message"] = (
                    f"Vídeo-base ({video_duration:.1f}s) maior que a música "
                    f"({audio_duration:.1f}s); o resultado será limitado à duração da música."
                )
            save_job(job)

            normalized_video = workdir / "musetalk_input_25fps.mp4"
            await asyncio.to_thread(
                normalize_video_for_musetalk,
                workdir / "input.mp4",
                normalized_video,
            )

            job["progress"] = 15
            job["message"] = "Executando MuseTalk..."
            job["stage"] = "musetalk"
            save_job(job)

            musetalk_output = await asyncio.to_thread(
                run_musetalk,
                normalized_video,
                workdir / job["audio_filename"],
                workdir,
            )

            # Keep the generated video aligned to the requested music duration.
            generated_duration = media_duration(musetalk_output)
            target_duration = audio_duration
            if generated_duration > target_duration + 0.05:
                trimmed_musetalk = workdir / "musetalk_trimmed.mp4"
                import subprocess
                trim = subprocess.run(
                    [
                        "ffmpeg", "-y", "-i", str(musetalk_output),
                        "-t", f"{target_duration:.3f}",
                        "-c", "copy",
                        str(trimmed_musetalk),
                    ],
                    capture_output=True,
                    text=True,
                )
                if trim.returncode != 0:
                    raise RuntimeError("Não foi possível ajustar a duração do resultado MuseTalk.")
                musetalk_output = trimmed_musetalk

            job["progress"] = 80
            job["message"] = "Aplicando cenário..."
            job["stage"] = "scene"
            save_job(job)

            composed_path = workdir / "composed.mp4"
            await asyncio.to_thread(
                compose_scene,
                musetalk_output,
                composed_path,
                job["scene"],
            )

            job["progress"] = 90
            job["message"] = "Finalizando vídeo..."
            job["stage"] = "finalizing"
            save_job(job)

            final_path = workdir / "final.mp4"
            await asyncio.to_thread(
                finalize_video,
                composed_path,
                final_path,
                job["format"],
            )

            job["status"] = "completed"
            job["completedAt"] = utc_now()
            job["progress"] = 100
            job["stage"] = "completed"
            job["message"] = "Vídeo pronto."
            job["resultUrl"] = f"/jobs/{job_id}/result"
            save_job(job)

        except Exception as exc:
            job["status"] = "failed"
            job["progress"] = 0
            job["stage"] = "failed"
            job["message"] = f"Erro: {str(exc)}"
            job["error"] = str(exc)
            job["failedAt"] = utc_now()
            save_job(job)


def runtime_readiness() -> dict:
    required_tools = {
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "ffprobe": shutil.which("ffprobe") is not None,
    }

    python_version = None
    try:
        import platform
        python_version = platform.python_version()
    except Exception:
        pass

    gpu_available = False
    gpu_name = None
    try:
        import torch
        gpu_available = bool(torch.cuda.is_available())
        if gpu_available:
            gpu_name = torch.cuda.get_device_name(0)
    except Exception:
        gpu_available = False

    required_models = {
        "musetalk": Path("/opt/MuseTalk/models/musetalkV15/unet.pth").is_file(),
        "whisper": Path("/opt/MuseTalk/models/whisper/pytorch_model.bin").is_file(),
        "dwpose": Path("/opt/MuseTalk/models/dwpose/dw-ll_ucoco_384.pth").is_file(),
        "face_parse": Path("/opt/MuseTalk/models/face-parse-bisent/79999_iter.pth").is_file(),
        "syncnet": Path("/opt/MuseTalk/models/syncnet/latentsync_syncnet.pt").is_file(),
        "sd_vae": Path("/opt/MuseTalk/models/sd-vae/diffusion_pytorch_model.bin").is_file(),
    }

    return {
        "tools": required_tools,
        "python": python_version,
        "gpu": {
            "available": gpu_available,
            "name": gpu_name,
        },
        "models": required_models,
        "ready": (
            all(required_tools.values())
            and gpu_available
            and all(required_models.values())
        ),
    }


@app.get("/health")
def health() -> dict:
    cleanup_old_jobs()

    queued = sum(1 for job in jobs.values() if job.get("status") == "queued")
    processing = sum(1 for job in jobs.values() if job.get("status") == "processing")
    readiness = runtime_readiness()

    return {
        "ok": readiness["ready"],
        "service": "alcantara-studio-gpu-worker",
        "musetalk": "MuseTalk 1.5",
        "jobs": len(jobs),
        "queued": queued,
        "processing": processing,
        "gpu_concurrency": GPU_CONCURRENCY,
        "limits": {
            "max_video_duration_seconds": MAX_VIDEO_DURATION_SECONDS,
            "max_upload_bytes": MAX_UPLOAD_BYTES,
        },
        "readiness": readiness,
    }


@app.get("/ready")
def ready():
    readiness = runtime_readiness()
    if not readiness["ready"]:
        return JSONResponse(status_code=503, content=readiness)
    return readiness


@app.get("/gpu")
def gpu_status():
    readiness = runtime_readiness()
    return {
        "available": readiness["gpu"]["available"],
        "name": readiness["gpu"]["name"],
        "ready": readiness["ready"],
    }


def validate_upload_metadata(video: UploadFile, audio: UploadFile) -> str | None:
    video_name = (video.filename or "").lower()
    audio_name = (audio.filename or "").lower()

    if video_name and Path(video_name).suffix not in {".mp4", ".mov", ".mkv", ".webm"}:
        return "O vídeo deve estar em MP4, MOV, MKV ou WebM."
    if audio_name and Path(audio_name).suffix not in {".mp3", ".wav", ".m4a", ".aac", ".flac"}:
        return "O áudio deve estar em MP3, WAV, M4A, AAC ou FLAC."
    return None


@app.post("/generate")
async def generate(
    video: UploadFile = File(...),
    audio: UploadFile = File(...),
    format: str = Form("16:9"),
    scene: str = Form("original"),
):
    allowed_scenes = {"original", "studio", "stage", "cinematic"}
    if scene not in allowed_scenes:
        return JSONResponse(
            status_code=400,
            content={"error": "Cenário inválido."},
        )

    if format not in {"16:9", "9:16"}:
        return JSONResponse(
            status_code=400,
            content={"error": "Formato deve ser 16:9 ou 9:16."},
        )

    upload_error = validate_upload_metadata(video, audio)
    if upload_error:
        return JSONResponse(status_code=400, content={"error": upload_error})

    job_id = uuid4().hex
    workdir = DATA_DIR / job_id
    workdir.mkdir(parents=True, exist_ok=True)

    video_path = workdir / "input.mp4"
    audio_suffix = Path(audio.filename or "audio.mp3").suffix.lower()
    if audio_suffix not in {".mp3", ".wav", ".m4a", ".aac", ".flac"}:
        audio_suffix = ".mp3"
    audio_path = workdir / f"audio{audio_suffix}"

    try:
        with video_path.open("wb") as target:
            shutil.copyfileobj(video.file, target)
        with audio_path.open("wb") as target:
            shutil.copyfileobj(audio.file, target)
    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        raise

    video_size = file_size(video_path)
    audio_size = file_size(audio_path)
    if video_size == 0 or audio_size == 0:
        shutil.rmtree(workdir, ignore_errors=True)
        return JSONResponse(
            status_code=400,
            content={"error": "Um dos arquivos enviados está vazio.", "code": "EMPTY_UPLOAD"},
        )

    if video_size > MAX_UPLOAD_BYTES or audio_size > MAX_UPLOAD_BYTES:
        shutil.rmtree(workdir, ignore_errors=True)
        limit_mb = MAX_UPLOAD_BYTES / (1024 * 1024)
        return JSONResponse(
            status_code=413,
            content={
                "error": f"Arquivo excede o limite de {limit_mb:.0f} MB.",
                "code": "UPLOAD_TOO_LARGE",
            },
        )

    try:
        video_probe = probe_media(video_path)
        audio_probe = probe_media(audio_path)
        video_duration = float(video_probe.get("format", {}).get("duration", 0))
        audio_duration = float(audio_probe.get("format", {}).get("duration", 0))
    except Exception as exc:
        shutil.rmtree(workdir, ignore_errors=True)
        return JSONResponse(
            status_code=400,
            content={"error": str(exc), "code": "INVALID_MEDIA"},
        )

    if video_duration <= 0 or audio_duration <= 0:
        shutil.rmtree(workdir, ignore_errors=True)
        return JSONResponse(
            status_code=400,
            content={"error": "Não foi possível determinar a duração dos arquivos.", "code": "INVALID_DURATION"},
        )

    if video_duration + 0.5 < audio_duration:
        shutil.rmtree(workdir, ignore_errors=True)
        return JSONResponse(
            status_code=400,
            content={
                "error": (
                    f"O vídeo-base ({video_duration:.1f}s) é menor que a música "
                    f"({audio_duration:.1f}s). O vídeo precisa cobrir toda a duração da música."
                ),
                "code": "VIDEO_SHORTER_THAN_AUDIO",
                "videoDuration": round(video_duration, 3),
                "audioDuration": round(audio_duration, 3),
            },
        )

    if video_duration > MAX_VIDEO_DURATION_SECONDS or audio_duration > MAX_VIDEO_DURATION_SECONDS:
        shutil.rmtree(workdir, ignore_errors=True)
        limit_min = MAX_VIDEO_DURATION_SECONDS / 60
        return JSONResponse(
            status_code=413,
            content={
                "error": f"Por segurança, o processamento está limitado a {limit_min:.0f} minutos por arquivo.",
                "code": "MEDIA_TOO_LONG",
            },
        )

    jobs[job_id] = {
        "jobId": job_id,
        "status": "queued",
        "format": format,
        "scene": scene,
        "audio_filename": audio_path.name,
        "progress": 0,
        "stage": "queued",
        "message": "Job aguardando a GPU...",
        "createdAt": utc_now(),
        "limits": {
            "maxDurationSeconds": MAX_VIDEO_DURATION_SECONDS,
            "maxUploadBytes": MAX_UPLOAD_BYTES,
        },
        "upload": {
            "videoBytes": video_size,
            "audioBytes": audio_size,
            "videoDuration": round(video_duration, 3),
            "audioDuration": round(audio_duration, 3),
        }
    }

    save_job(jobs[job_id])
    asyncio.create_task(process_job(job_id))
    return jobs[job_id]


@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "Job não encontrado."})
    return job


@app.get("/jobs/{job_id}/result")
def job_result(job_id: str):
    job = jobs.get(job_id)
    if not job or job.get("status") != "completed":
        return JSONResponse(status_code=404, content={"error": "Resultado ainda não disponível."})

    result = DATA_DIR / job_id / "final.mp4"
    if not result.exists():
        return JSONResponse(status_code=404, content={"error": "Arquivo de resultado não encontrado."})

    return FileResponse(
        result,
        media_type="video/mp4",
        filename=f"alcantara-studio-{job_id}.mp4",
    )
