import { NextResponse } from "next/server";
import { isVideoFormat } from "@/lib/job";

export const runtime = "nodejs";

export async function POST(request: Request) {
  const gpuUrl = process.env.GPU_API_URL;

  if (!gpuUrl) {
    return NextResponse.json(
      {
        error: "GPU backend ainda não configurado.",
        code: "GPU_BACKEND_NOT_CONFIGURED"
      },
      { status: 503 }
    );
  }

  const incoming = await request.formData();
  const video = incoming.get("video");
  const audio = incoming.get("audio");
  const format = incoming.get("format");

  if (!(video instanceof File) || !(audio instanceof File)) {
    return NextResponse.json(
      { error: "Envie um vídeo e uma música." },
      { status: 400 }
    );
  }

  if (typeof format !== "string" || !isVideoFormat(format)) {
    return NextResponse.json(
      { error: "Formato deve ser 16:9 ou 9:16." },
      { status: 400 }
    );
  }

  const body = new FormData();
  body.append("video", video, video.name);
  body.append("audio", audio, audio.name);
  body.append("format", format);

  try {
    const response = await fetch(`${gpuUrl.replace(/\/$/, "")}/generate`, {
      method: "POST",
      body,
      cache: "no-store"
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json(
      {
        error: "Não foi possível conectar ao backend GPU.",
        code: "GPU_BACKEND_UNREACHABLE"
      },
      { status: 502 }
    );
  }
}
