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
      { cache: "no-store" }
    );

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json(
      { error: "Não foi possível consultar o backend GPU." },
      { status: 502 }
    );
  }
}
