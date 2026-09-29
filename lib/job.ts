export type VideoFormat = "16:9" | "9:16";

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
