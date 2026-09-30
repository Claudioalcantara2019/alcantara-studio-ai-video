import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET() {
  const gpuUrl = process.env.GPU_API_URL?.replace(/\/$/, "");
  let gpuBackendReady = false;
  let gpu: unknown = null;

  if (gpuUrl) {
    try {
      const response = await fetch(`${gpuUrl}/health`, {
        cache: "no-store",
        signal: AbortSignal.timeout(4000)
      });
      gpuBackendReady = response.ok;
      gpu = await response.json().catch(() => null);
    } catch {
      gpuBackendReady = false;
    }
  }

  return NextResponse.json({
    ok: true,
    service: "alcantara-studio-ai-video",
    gpuBackendConfigured: Boolean(gpuUrl),
    gpuBackendReady,
    gpu
  });
}
