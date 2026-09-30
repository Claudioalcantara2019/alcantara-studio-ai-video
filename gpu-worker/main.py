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

app = FastAPI(title="Alcantara Studio GPU Worker", version="0.2.0")
jobs: dict[str, dict] = {}
GPU_CONCURRENCY = 1
GPU_SEMAPHORE = asyncio.Semaphore(GPU_CONCURRENCY)

def save_job(job: dict) -> None:
    job_dir = DATA_DIR / job["jobId"]
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")


def load_jobs() -> None:
    for job_file in DATA_DIR.glob("*/job.json"):
        try:
            job = json.loads(job_file.read_text(encoding="utf-8"))
            if job.get("status") == "processing":
                job["status"] = "failed"
                job["stage"] = "failed"
                job["progress"] = 0
                job["message"] = "Processamento interrompido pela reinicialização do worker."
            jobs[job["jobId"]] = job
        except Exception:
            continue




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
        "ffmpeg", "-y", "-i", str(source),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(destination),
    ]

    import subprocess
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-5000:])


async def process_job(job_id: str) -> None:
    job = jobs[job_id]
    async with GPU_SEMAPHORE:
        job["status"] = "processing"
        job["progress"] = 5
        save_job(job)
        job["message"] = "Preparando vídeo para o processamento..."
        job["stage"] = "normalizing"
        workdir = DATA_DIR / job_id

        try:
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
            save_job(job)


@app.get("/health")
def health() -> dict:
    queued = sum(1 for job in jobs.values() if job.get("status") == "queued")
    processing = sum(1 for job in jobs.values() if job.get("status") == "processing")
    return {
        "ok": True,
        "service": "alcantara-studio-gpu-worker",
        "musetalk": "MuseTalk 1.5",
        "jobs": len(jobs),
        "queued": queued,
        "processing": processing,
        "gpu_concurrency": GPU_CONCURRENCY,
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

    jobs[job_id] = {
        "jobId": job_id,
        "status": "queued",
        "format": format,
        "scene": scene,
        "audio_filename": audio_path.name,
        "progress": 0,
        "stage": "queued",
        "message": "Job aguardando a GPU..."
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
