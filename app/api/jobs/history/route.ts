import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET(request: Request) {
  const gpuUrl = process.env.GPU_API_URL;
  if (!gpuUrl) {
    return NextResponse.json({ error: "GPU backend ainda não configurado." }, { status: 503 });
  }

  const url = new URL(request.url);
  const limit = url.searchParams.get("limit") ?? "20";

  try {
    const response = await fetch(
      `${gpuUrl.replace(/\/$/, "")}/jobs?limit=${encodeURIComponent(limit)}`,
      { cache: "no-store", signal: AbortSignal.timeout(10000) }
    );
    const data = await response.json().catch(() => ({ error: "Resposta inválida do backend GPU." }));
    return NextResponse.json(data, { status: response.status });
  } catch {
    return NextResponse.json({ error: "Não foi possível consultar o histórico de jobs." }, { status: 502 });
  }
}
