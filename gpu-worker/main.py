from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

app = FastAPI(title="Alcantara Studio GPU Worker", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "alcantara-studio-gpu-worker",
        "musetalk": "pending"
    }


@app.post("/generate")
async def generate(
    video: UploadFile = File(...),
    audio: UploadFile = File(...),
    format: str = Form("16:9"),
):
    if format not in {"16:9", "9:16"}:
        return JSONResponse(
            status_code=400,
            content={"error": "Formato deve ser 16:9 ou 9:16."},
        )

    if not video.filename:
        return JSONResponse(status_code=400, content={"error": "Vídeo não informado."})

    if not audio.filename:
        return JSONResponse(status_code=400, content={"error": "Áudio não informado."})

    job_id = uuid4().hex

    with TemporaryDirectory(prefix=f"alcantara-{job_id}-") as tmp:
        video_path = Path(tmp) / Path(video.filename).name
        audio_path = Path(tmp) / Path(audio.filename).name

        video_path.write_bytes(await video.read())
        audio_path.write_bytes(await audio.read())

    return {
        "jobId": job_id,
        "status": "queued",
        "format": format,
        "message": "Job recebido. A execução MuseTalk será conectada nesta etapa."
    }
