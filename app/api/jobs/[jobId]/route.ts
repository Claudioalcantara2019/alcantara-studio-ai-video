import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const gpuUrl = process.env.GPU_API_URL;

  if (!gpuUrl) {
    return NextResponse.json(
      { error: "GPU backend ainda não configurado." },
      { status: 503 }
    );
  }

  const { jobId } = await params;

  try {
    const response = await fetch(
      `${gpuUrl.replace(/\/$/, "")}/jobs/${encodeURIComponent(jobId)}`,
      { cache: "no-store", signal: AbortSignal.timeout(15000) }
    );

    const data = await response.json().catch(() => ({
      error: "Resposta inválida do backend GPU."
    }));
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json(
      { error: "Não foi possível consultar o backend GPU." },
      { status: 502 }
    );
  }
}


export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const gpuUrl = process.env.GPU_API_URL;

  if (!gpuUrl) {
    return NextResponse.json(
      { error: "GPU backend ainda não configurado." },
      { status: 503 }
    );
  }

  const { jobId } = await params;

  try {
    const response = await fetch(
      `${gpuUrl.replace(/\/$/, "")}/jobs/${encodeURIComponent(jobId)}`,
      {
        method: "DELETE",
        cache: "no-store",
        signal: AbortSignal.timeout(15000)
      }
    );

    const data = await response.json().catch(() => ({
      error: "Resposta inválida do backend GPU."
    }));

    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json(
      { error: "Não foi possível cancelar o job no backend GPU." },
      { status: 502 }
    );
  }
}


export async function POST(
  request: Request,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const gpuUrl = process.env.GPU_API_URL;
  if (!gpuUrl) return NextResponse.json({ error: "GPU backend ainda não configurado." }, { status: 503 });
  const { jobId } = await params;
  if (request.headers.get("x-job-action") !== "retry") {
    return NextResponse.json({ error: "Ação de job inválida." }, { status: 400 });
  }
  try {
    const response = await fetch(gpuUrl.replace(/\/$/, "") + "/jobs/" + encodeURIComponent(jobId) + "/retry", {
      method: "POST", cache: "no-store", signal: AbortSignal.timeout(15000)
    });
    const data = await response.json().catch(() => ({ error: "Resposta inválida do backend GPU." }));
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ error: "Não foi possível repetir o job no backend GPU." }, { status: 502 });
  }
}
