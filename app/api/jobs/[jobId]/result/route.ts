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
      `${gpuUrl.replace(/\/$/, "")}/jobs/${encodeURIComponent(jobId)}/result`,
      { cache: "no-store" }
    );

    if (!response.ok) {
      const data = await response.json().catch(() => ({ error: "Resultado indisponível." }));
      return NextResponse.json(data, { status: response.status });
    }

    const contentType = response.headers.get("content-type") ?? "video/mp4";
    const buffer = await response.arrayBuffer();

    return new Response(buffer, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Content-Disposition": `attachment; filename="alcantara-studio-${jobId}.mp4"`,
        "Cache-Control": "no-store"
      }
    });
  } catch {
    return NextResponse.json(
      { error: "Não foi possível baixar o resultado." },
      { status: 502 }
    );
  }
}
