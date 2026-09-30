import asyncio
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from musetalk_runner import run_musetalk

DATA_DIR = Path("/data/jobs")
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Alcantara Studio GPU Worker", version="0.2.0")
jobs: dict[str, dict] = {}


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
    job["status"] = "processing"
    job["message"] = "Preparando processamento com MuseTalk..."
    workdir = DATA_DIR / job_id

    try:
        musetalk_output = await asyncio.to_thread(
            run_musetalk,
            workdir / "input.mp4",
            workdir / "audio.mp3",
            workdir,
        )

        composed_path = workdir / "composed.mp4"
        await asyncio.to_thread(
            compose_scene,
            musetalk_output,
            composed_path,
            job["scene"],
        )

        final_path = workdir / "final.mp4"
        await asyncio.to_thread(
            finalize_video,
            composed_path,
            final_path,
            job["format"],
        )

        job["status"] = "completed"
        job["message"] = "Vídeo pronto."
        job["resultUrl"] = f"/jobs/{job_id}/result"
    except Exception as exc:
        job["status"] = "failed"
        job["message"] = "O processamento falhou."
        job["error"] = str(exc)


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "alcantara-studio-gpu-worker",
        "musetalk": "MuseTalk 1.5",
        "jobs": len(jobs),
    }


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

    job_id = uuid4().hex
    workdir = DATA_DIR / job_id
    workdir.mkdir(parents=True, exist_ok=True)

    video_path = workdir / "input.mp4"
    audio_path = workdir / "audio.mp3"

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
    }

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
