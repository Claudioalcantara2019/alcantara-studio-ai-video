"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { SCENE_OPTIONS, SceneOption } from "@/lib/job";

type Format = "16:9" | "9:16";

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

  const videoName = useMemo(() => video?.name ?? "Nenhum vídeo selecionado", [video]);
  const audioName = useMemo(() => audio?.name ?? "Nenhum áudio selecionado", [audio]);

  useEffect(() => {
    let active = true;
    fetch("/api/health", { cache: "no-store" })
      .then((response) => response.json())
      .then((data) => {
        if (active) setBackendReady(Boolean(data.gpuBackendReady));
      })
      .catch(() => {
        if (active) setBackendReady(false);
      });
    return () => {
      active = false;
    };
  }, []);

  function formatBytes(bytes: number) {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function selectVideo(event: ChangeEvent<HTMLInputElement>) {
    setVideo(event.target.files?.[0] ?? null);
    setResultUrl(null);
    setJobId(null);
    setStatus("Vídeo selecionado.");
  }

  function selectAudio(event: ChangeEvent<HTMLInputElement>) {
    setAudio(event.target.files?.[0] ?? null);
    setResultUrl(null);
    setJobId(null);
    setStatus("Áudio selecionado.");
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

    if (!video.name.toLowerCase().endsWith(".mp4")) {
      setStatus("O vídeo-base precisa estar em MP4.");
      return;
    }

    const allowedAudio = [".mp3", ".wav", ".m4a", ".aac", ".flac"];
    if (!allowedAudio.some((extension) => audio.name.toLowerCase().endsWith(extension))) {
      setStatus("A música precisa estar em MP3, WAV, M4A, AAC ou FLAC.");
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
          <div className="mb-5 flex items-center justify-between rounded-xl border border-white/5 bg-black/20 px-4 py-3 text-xs">
            <span className="text-white/50">Backend GPU</span>
            <span className={backendReady ? "text-emerald-300" : backendReady === false ? "text-red-300" : "text-white/40"}>
              {backendReady ? "configurado" : backendReady === false ? "não configurado" : "verificando..."}
            </span>
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
              O cenário original é o único motor ativo nesta fase. Os demais estão reservados para a próxima etapa.
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

        <p className="mt-6 text-center text-xs text-white/30">
          Alcantara Studio • laboratório privado de criação de vídeo
        </p>
      </div>
    </main>
  );
}
