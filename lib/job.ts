export type VideoFormat = "16:9" | "9:16";

export type SceneOption = {
  id: string;
  name: string;
  kind: "original" | "look";
};

export const SCENE_OPTIONS: SceneOption[] = [
  { id: "original", name: "Original", kind: "original" },
  { id: "studio", name: "Estúdio — tratamento", kind: "look" },
  { id: "stage", name: "Palco — tratamento", kind: "look" },
  { id: "cinematic", name: "Cinematográfico — tratamento", kind: "look" },
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
