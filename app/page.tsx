"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { SCENE_OPTIONS, SceneOption } from "@/lib/job";

type Format = "16:9" | "9:16";

type HistoryJob = {
  jobId: string;
  status: string;
  scene?: string;
  format?: string;
  message?: string;
  createdAt?: string;
  performance?: { processingSeconds?: number; generatedDurationSeconds?: number; resultBytes?: number } | null;
  stageTiming?: Record<string, number>;
  gpu?: { name?: string; peakAllocatedMb?: number; peakReservedMb?: number };
  retryOf?: string;
};

export default function Home() {
  const [video, setVideo] = useState<File | null>(null);
  const [audio, setAudio] = useState<File | null>(null);
  const [format, setFormat] = useState<Format>("16:9");
  const [scene, setScene] = useState<SceneOption>(SCENE_OPTIONS[0]);
  const [status, setStatus] = useState("Pronto para receber os arquivos.");
  const [busy, setBusy] = useState(false);
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const [backendReady, setBackendReady] = useState<boolean | null>(null);
  const [videoDuration, setVideoDuration] = useState<number | null>(null);
  const [audioDuration, setAudioDuration] = useState<number | null>(null);
  const [history, setHistory] = useState<HistoryJob[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [health, setHealth] = useState<{
    gpuBackendConfigured: boolean;
    gpuBackendReady: boolean;
    gpu: {
      ok?: boolean;
      version?: string;
      gpu?: { available?: boolean; name?: string | null; ready?: boolean };
      readiness?: {
        ready?: boolean;
        python?: string | null;
        tools?: Record<string, boolean>;
        models?: Record<string, boolean>;
      };
    } | null;
  } | null>(null);

  const videoName = useMemo(() => video?.name ?? "Nenhum vídeo selecionado", [video]);
  const audioName = useMemo(() => audio?.name ?? "Nenhum áudio selecionado", [audio]);

  useEffect(() => {
    let active = true;

    async function refreshHealth() {
      try {
        const response = await fetch("/api/health", { cache: "no-store" });
        const data = await response.json();
        if (active) {
          setHealth(data);
          setBackendReady(Boolean(data.gpuBackendReady));
        }
      } catch {
        if (active) {
          setBackendReady(false);
          setHealth(null);
        }
      }
    }

    refreshHealth();
    refreshHistory();
    const timer = window.setInterval(() => { refreshHealth(); refreshHistory(); }, 10000);

    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  async function refreshHistory() {
    setHistoryLoading(true);
    try {
      const response = await fetch("/api/jobs/history?limit=20", { cache: "no-store" });
      const data = await response.json();
      if (response.ok && Array.isArray(data.jobs)) setHistory(data.jobs);
    } catch {
      // Histórico é auxiliar; não interrompe a geração.
    } finally {
      setHistoryLoading(false);
    }
  }

  async function retryHistoryJob(id: string) {
    setStatus("Reenviando o job para a GPU...");
    try {
      const response = await fetch("/api/jobs/" + encodeURIComponent(id), {
        method: "POST",
        headers: { "x-job-action": "retry" }
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error ?? "Não foi possível repetir o job.");
      setJobId(data.jobId);
      setBusy(true);
      setResultUrl(null);
      setProgress(0);
      setStage(data.stage ?? "queued");
      setStatus("Job repetido e enviado para processamento.");
      await waitForJob(data.jobId);
    } catch (error) {
      setStage("failed");
      setStatus(error instanceof Error ? error.message : "Erro ao repetir o job.");
    } finally {
      setBusy(false);
      await refreshHistory();
    }
  }

  function formatBytes(bytes: number) {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function readMediaDuration(file: File, kind: "video" | "audio") {
    const url = URL.createObjectURL(file);
    const media = kind === "video" ? document.createElement("video") : document.createElement("audio");
    media.preload = "metadata";
    media.onloadedmetadata = () => {
      const duration = Number.isFinite(media.duration) ? media.duration : null;
      if (kind === "video") setVideoDuration(duration);
      else setAudioDuration(duration);
      URL.revokeObjectURL(url);
    };
    media.onerror = () => {
      if (kind === "video") setVideoDuration(null);
      else setAudioDuration(null);
      URL.revokeObjectURL(url);
    };
    media.src = url;
  }

  function selectVideo(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    setVideo(selected);
    setVideoDuration(null);
    if (selected) readMediaDuration(selected, "video");
    setResultUrl(null);
    setJobId(null);
    setStatus("Vídeo selecionado.");
  }

  function selectAudio(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    setAudio(selected);
    setAudioDuration(null);
    if (selected) readMediaDuration(selected, "audio");
    setResultUrl(null);
    setJobId(null);
    setStatus("Áudio selecionado.");
  }

  function formatDuration(seconds: number | null) {
    if (seconds === null) return "--:--";
    const total = Math.round(seconds);
    return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
  }

  async function cancelJob() {
    if (!jobId) return;
    try {
      const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`, { method: "DELETE" });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error ?? "Não foi possível cancelar o job.");
      }
      setStatus("Cancelamento solicitado. A GPU vai interromper o processamento.");
      setStage("cancelling");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Erro ao cancelar o job.");
    }
  }

  async function waitForJob(id: string) {
    const started = Date.now();
    const maxWait = 60 * 60 * 1000;

    for (;;) {
      if (Date.now() - started > maxWait) {
        throw new Error("O processamento ultrapassou o tempo de espera da interface. O job pode continuar no backend.");
      }

      await new Promise((resolve) => setTimeout(resolve, 2500));

      const response = await fetch(`/api/jobs/${encodeURIComponent(id)}`, { cache: "no-store" });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message ?? data.error ?? "Falha ao consultar o job.");
      }

      if (data.status === "completed") {
        setResultUrl(`/api/jobs/${encodeURIComponent(id)}/result`);
        setProgress(100);
        setStage("completed");
        setStatus("Vídeo pronto.");
        return;
      }

      setProgress(typeof data.progress === "number" ? data.progress : 0);
      setStage(typeof data.stage === "string" ? data.stage : data.status);

      if (data.status === "cancelled") {
        setProgress(0);
        setStage("cancelled");
        setStatus("Job cancelado.");
        return;
      }

      if (data.status === "failed") {
        throw new Error(data.message ?? data.error ?? "O processamento falhou.");
      }

      setStatus(data.message ?? "Processando...");
    }
  }

  async function generate() {
    if (!video || !audio) {
      setStatus("Selecione o vídeo e a música antes de gerar.");
      return;
    }

    if (backendReady !== true) {
      setStatus("A GPU ainda não está pronta. Inicie o backend GPU e tente novamente.");
      return;
    }

    if (!video.name.toLowerCase().endsWith(".mp4")) {
      setStatus("O vídeo-base precisa estar em MP4.");
      return;
    }

    const allowedAudio = [".mp3", ".wav", ".m4a", ".aac", ".flac"];
    if (!allowedAudio.some((extension) => audio.name.toLowerCase().endsWith(extension))) {
      setStatus("A música precisa estar em MP3, WAV, M4A, AAC ou FLAC.");
      return;
    }

    if (videoDuration !== null && audioDuration !== null && videoDuration + 0.5 < audioDuration) {
      setStatus(`O vídeo-base (${formatDuration(videoDuration)}) é menor que a música (${formatDuration(audioDuration)}).`);
      return;
    }

    const maxBytes = 2 * 1024 * 1024 * 1024;
    if (video.size > maxBytes || audio.size > maxBytes) {
      setStatus("Cada arquivo precisa ter no máximo 2 GB.");
      return;
    }

    setBusy(true);
    setResultUrl(null);
    setJobId(null);
    setStage("uploading");
    setProgress(0);
    setStatus("Enviando arquivos para o processamento...");

    const form = new FormData();
    form.append("video", video);
    form.append("audio", audio);
    form.append("format", format);
    form.append("scene", scene.id);

    try {
      const response = await fetch("/api/jobs", { method: "POST", body: form });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error ?? data.message ?? "Não foi possível iniciar o processamento.");
      }

      setJobId(data.jobId);
      setStage(data.stage ?? "queued");
      setStatus(`Job ${data.jobId} recebido.`);
      await waitForJob(data.jobId);
    } catch (error) {
      setStage("failed");
      setStatus(error instanceof Error ? error.message : "Erro de comunicação com o servidor.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen px-5 py-10">
      <div className="mx-auto max-w-3xl">
        <header className="mb-10 text-center">
          <p className="mb-3 text-xs tracking-[0.35em] text-[var(--gold)]">ALCANTARA STUDIO</p>
          <h1 className="text-4xl font-semibold md:text-5xl">AI Video Studio</h1>
          <p className="mx-auto mt-4 max-w-xl text-sm leading-6 text-white/60">
            Vídeo + música → sincronização labial.
          </p>
        </header>

        <section className="rounded-3xl border border-white/10 bg-[var(--panel)] p-6 shadow-2xl md:p-8">
          <div className="mb-5 rounded-xl border border-white/5 bg-black/20 px-4 py-3 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-white/50">Backend GPU</span>
              <span className={backendReady ? "text-emerald-300" : backendReady === false ? "text-red-300" : "text-white/40"}>
                {backendReady ? "GPU pronta" : backendReady === false ? "GPU indisponível" : "verificando..."}
              </span>
            </div>

            {health && (
              <div className="mt-3 grid gap-2 border-t border-white/5 pt-3 sm:grid-cols-2">
                <div className="flex items-center justify-between">
                  <span className="text-white/35">API GPU</span>
                  <span className={health.gpuBackendConfigured ? "text-emerald-300" : "text-red-300"}>
                    {health.gpuBackendConfigured ? "configurada" : "não configurada"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-white/35">CUDA / GPU</span>
                  <span className={health.gpu?.readiness?.ready ? "text-emerald-300" : "text-red-300"}>
                    {health.gpu?.gpu?.name ?? (health.gpu?.readiness?.ready ? "pronta" : "não pronta")}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-white/35">FFmpeg</span>
                  <span className={health.gpu?.readiness?.tools?.ffmpeg ? "text-emerald-300" : "text-red-300"}>
                    {health.gpu?.readiness?.tools?.ffmpeg ? "OK" : "faltando"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-white/35">Modelos MuseTalk</span>
                  <span className={
                    health.gpu?.readiness?.models &&
                    Object.values(health.gpu.readiness.models).every(Boolean)
                      ? "text-emerald-300"
                      : "text-red-300"
                  }>
                    {health.gpu?.readiness?.models &&
                    Object.values(health.gpu.readiness.models).every(Boolean)
                      ? "completos"
                      : "incompletos"}
                  </span>
                </div>
              </div>
            )}

            {backendReady === false && health?.gpuBackendConfigured && (
              <p className="mt-3 border-t border-white/5 pt-3 text-[11px] leading-5 text-red-200/70">
                O worker respondeu, mas ainda não está pronto para gerar. Verifique NVIDIA/CUDA, FFmpeg e os modelos do MuseTalk.
              </p>
            )}

            {backendReady === false && health?.gpuBackendConfigured === false && (
              <p className="mt-3 border-t border-white/5 pt-3 text-[11px] leading-5 text-red-200/70">
                O frontend ainda não está apontando para um GPU Worker. No Windows local, o endereço esperado é http://127.0.0.1:8000.
              </p>
            )}
          </div>

          <div className="grid gap-5 md:grid-cols-2">
            <label className="cursor-pointer rounded-2xl border border-dashed border-white/20 p-6 transition hover:border-[var(--gold)]">
              <span className="block text-sm font-semibold">1. Vídeo-base</span>
              <span className="mt-2 block text-xs text-white/50">Seu vídeo cantando • MP4</span>
              <span className="mt-5 block truncate text-sm text-[var(--gold-light)]">{videoName}</span>
              {video && <span className="mt-1 block text-[11px] text-white/40">{formatBytes(video.size)}</span>}
              <input className="hidden" type="file" accept="video/mp4" onChange={selectVideo} />
            </label>

            <label className="cursor-pointer rounded-2xl border border-dashed border-white/20 p-6 transition hover:border-[var(--gold)]">
              <span className="block text-sm font-semibold">2. Música</span>
              <span className="mt-2 block text-xs text-white/50">A música que terá a nova sincronização</span>
              <span className="mt-5 block truncate text-sm text-[var(--gold-light)]">{audioName}</span>
              {audio && <span className="mt-1 block text-[11px] text-white/40">{formatBytes(audio.size)}</span>}
              <input className="hidden" type="file" accept=".mp3,.wav,.m4a,.aac,.flac,audio/*" onChange={selectAudio} />
            </label>
          </div>

          <div className="mt-5 grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-white/5 bg-black/20 px-4 py-3">
              <span className="block text-[10px] uppercase tracking-wider text-white/35">Duração do vídeo</span>
              <span className="mt-1 block text-sm font-semibold text-[var(--gold-light)]">{formatDuration(videoDuration)}</span>
            </div>
            <div className="rounded-xl border border-white/5 bg-black/20 px-4 py-3">
              <span className="block text-[10px] uppercase tracking-wider text-white/35">Duração da música</span>
              <span className="mt-1 block text-sm font-semibold text-[var(--gold-light)]">{formatDuration(audioDuration)}</span>
            </div>
          </div>
          <div className="mt-3 rounded-xl border border-white/5 bg-black/10 px-4 py-3 text-xs text-white/40">
            O vídeo-base precisa cobrir toda a duração da música. A conferência também é repetida pelo backend antes de ocupar a GPU.
          </div>

          <div className="mt-7">
            <p className="mb-3 text-sm font-semibold">Formato do vídeo</p>
            <div className="grid grid-cols-2 gap-3">
              {(["16:9", "9:16"] as Format[]).map((item) => {
                const selected = format === item;
                return (
                  <button
                    key={item}
                    type="button"
                    onClick={() => setFormat(item)}
                    className={
                      "rounded-xl border px-4 py-3 text-sm font-semibold transition " +
                      (selected
                        ? "border-[var(--gold)] bg-[var(--gold)]/10 text-[var(--gold-light)]"
                        : "border-white/10 text-white/60 hover:border-white/30")
                    }
                  >
                    {item}
                    <span className="ml-2 text-xs font-normal opacity-60">
                      {item === "16:9" ? "YouTube" : "Shorts"}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="mt-7">
            <p className="mb-3 text-sm font-semibold">Cenário</p>
            <select
              value={scene.id}
              onChange={(event) => {
                const selected = SCENE_OPTIONS.find((item) => item.id === event.target.value);
                if (selected) setScene(selected);
              }}
              className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none"
            >
              {SCENE_OPTIONS.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
            <p className="mt-2 text-xs text-white/40">
              Os quatro modos já estão ativos. Nesta fase, os três últimos aplicam tratamento visual sem alterar roupa ou substituir o fundo por IA.
            </p>
          </div>

          <button
            type="button"
            onClick={generate}
            disabled={busy}
            className="mt-8 w-full rounded-xl bg-[var(--gold)] px-5 py-4 text-sm font-bold tracking-wide text-black transition hover:brightness-110 disabled:cursor-wait disabled:opacity-60"
          >
            {busy ? "PROCESSANDO..." : "GERAR VÍDEO"}
          </button>

          <div className="mt-5 rounded-xl border border-white/5 bg-black/20 px-4 py-3 text-center text-xs text-white/60">
            {status}
            {jobId && <span className="mt-1 block text-[10px] text-white/30">Job: {jobId}</span>}
          </div>

          {busy && jobId && (
            <button
              type="button"
              onClick={cancelJob}
              className="mt-3 w-full rounded-xl border border-red-400/40 px-5 py-3 text-xs font-bold text-red-200 transition hover:bg-red-400/10"
            >
              CANCELAR PROCESSAMENTO
            </button>
          )}

          {busy && (
            <div className="mt-3">
              <div className="mb-1 flex justify-between text-[11px] text-white/40">
                <span>Processamento</span>
                <span>{stage} • {progress}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-white/5">
                <div className="h-full rounded-full bg-[var(--gold)] transition-all duration-500" style={{ width: progress + "%" }} />
              </div>
            </div>
          )}

          {resultUrl && (
            <a
              href={resultUrl}
              className="mt-4 block w-full rounded-xl border border-[var(--gold)] px-5 py-4 text-center text-sm font-bold text-[var(--gold-light)] transition hover:bg-[var(--gold)]/10"
            >
              BAIXAR VÍDEO MP4
            </a>
          )}
        </section>


        <section className="mt-6 rounded-3xl border border-white/10 bg-[var(--panel)] p-6 shadow-2xl md:p-8">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs tracking-[0.2em] text-[var(--gold)]">HISTÓRICO</p>
              <h2 className="mt-1 text-lg font-semibold">Últimos processamentos</h2>
            </div>
            <button type="button" onClick={refreshHistory} className="text-xs text-white/40 hover:text-white/70">
              {historyLoading ? "atualizando..." : "ATUALIZAR"}
            </button>
          </div>
          {history.length === 0 ? (
            <p className="mt-5 text-xs text-white/40">Nenhum processamento registrado ainda.</p>
          ) : (
            <div className="mt-5 space-y-2">
              {history.map((item) => (
                <div key={item.jobId} className="rounded-xl border border-white/5 bg-black/20 px-4 py-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-mono text-[10px] text-white/30">{item.jobId.slice(0, 12)}</span>
                    <span className={item.status === "completed" ? "text-xs text-emerald-300" : item.status === "failed" ? "text-xs text-red-300" : item.status === "cancelled" ? "text-xs text-yellow-300" : "text-xs text-white/50"}>{item.status}</span>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-white/40">
                    <span>{item.format ?? "--"}</span>
                    <span>{item.scene ?? "--"}</span>
                    {item.performance?.processingSeconds != null && <span>{Math.round(item.performance.processingSeconds)}s de processamento</span>}
                    {item.gpu?.peakAllocatedMb != null && <span>VRAM pico {item.gpu.peakAllocatedMb} MB</span>}
                  </div>
                  {(item.status === "failed" || item.status === "cancelled") && (
                    <button type="button" onClick={() => retryHistoryJob(item.jobId)} disabled={busy} className="mt-3 rounded-lg border border-[var(--gold)]/50 px-3 py-2 text-[11px] font-semibold text-[var(--gold-light)] disabled:opacity-40">
                      REPETIR ESTE JOB
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        <p className="mt-6 text-center text-xs text-white/30">
          Alcantara Studio • laboratório privado de criação de vídeo
        </p>
      </div>
    </main>
  );
}
