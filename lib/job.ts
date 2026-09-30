export type VideoFormat = "16:9" | "9:16";

export type SceneOption = {
  id: string;
  name: string;
  kind: "original" | "background";
};

export const SCENE_OPTIONS: SceneOption[] = [
  { id: "original", name: "Vídeo original", kind: "original" },
  { id: "studio", name: "Estúdio", kind: "background" },
  { id: "stage", name: "Palco", kind: "background" },
  { id: "cinematic", name: "Cenário cinematográfico", kind: "background" },
];

export type JobResponse = {
  jobId: string;
  status: "queued" | "processing" | "completed" | "failed";
  format: VideoFormat;
  message?: string;
  resultUrl?: string;
};

export function isVideoFormat(value: string): value is VideoFormat {
  return value === "16:9" || value === "9:16";
}
