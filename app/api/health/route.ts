import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    ok: true,
    service: "alcantara-studio-ai-video",
    gpuBackendConfigured: Boolean(process.env.GPU_API_URL)
  });
}
