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

  const baseGpuUrl = gpuUrl.replace(/\/$/, "");

  try {
    const readyResponse = await fetch(`${baseGpuUrl}/ready`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000)
    });

    if (!readyResponse.ok) {
      const readiness = await readyResponse.json().catch(() => null);
      return NextResponse.json(
        {
          error: "A GPU Worker ainda não está pronta para gerar vídeos.",
          code: "GPU_BACKEND_NOT_READY",
          readiness
        },
        { status: 503 }
      );
    }
  } catch {
    return NextResponse.json(
      {
        error: "Não foi possível verificar a prontidão do backend GPU.",
        code: "GPU_BACKEND_UNREACHABLE"
      },
      { status: 502 }
    );
  }

  const incoming = await request.formData();
  const video = incoming.get("video");
  const audio = incoming.get("audio");
  const format = incoming.get("format");
  const scene = incoming.get("scene");

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
  body.append("scene", typeof scene === "string" ? scene : "original");

  try {
    const response = await fetch(`${gpuUrl.replace(/\/$/, "")}/generate`, {
      method: "POST",
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(10 * 60 * 1000)
    });

    const data = await response.json().catch(() => ({
      error: "O backend GPU retornou uma resposta inválida."
    }));
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    const message =
      error instanceof Error && error.name === "TimeoutError"
        ? "O backend GPU demorou demais para aceitar o job."
        : "Não foi possível conectar ao backend GPU.";

    return NextResponse.json(
      { error: message, code: "GPU_BACKEND_UNREACHABLE" },
      { status: 502 }
    );
  }
}
