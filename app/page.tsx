"use client";

import { ChangeEvent, useMemo, useState } from "react";
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

  const videoName = useMemo(() => video?.name ?? "Nenhum vídeo selecionado", [video]);
  const audioName = useMemo(() => audio?.name ?? "Nenhum áudio selecionado", [audio]);

  function selectVideo(event: ChangeEvent<HTMLInputElement>) {
    setVideo(event.target.files?.[0] ?? null);
    setResultUrl(null);
    setStatus("Vídeo selecionado.");
  }

  function selectAudio(event: ChangeEvent<HTMLInputElement>) {
    setAudio(event.target.files?.[0] ?? null);
    setResultUrl(null);
    setStatus("Áudio selecionado.");
  }

  async function waitForJob(jobId: string) {
    for (;;) {
      await new Promise((resolve) => setTimeout(resolve, 2500));

      const response = await fetch(`/api/jobs/${jobId}`, { cache: "no-store" });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error ?? "Falha ao consultar o job.");
      }

      if (data.status === "completed") {
        const url = `/api/jobs/${jobId}/result`;
        setResultUrl(url);
        setProgress(100);
        setStatus("Vídeo pronto.");
        return;
      }

      setProgress(typeof data.progress === "number" ? data.progress : 0);

      if (data.status === "failed") {
        throw new Error(data.error ?? "O processamento falhou.");
      }

      if (data.status === "processing") {
        setStatus(data.message ?? "Processando... isso pode levar alguns minutos.");
      } else {
        setStatus(data.message ?? "Job na fila de processamento...");
      }
    }
  }

  async function generate() {
    if (!video || !audio) {
      setStatus("Selecione o vídeo e a música antes de gerar.");
      return;
    }

    setBusy(true);
    setResultUrl(null);
    setProgress(0);
    setStatus("Enviando arquivos para o processamento...");

    const form = new FormData();
    form.append("video", video);
    form.append("audio", audio);
    form.append("format", format);
    form.append("scene", scene.id);

    try {
      const response = await fetch("/api/jobs", {
        method: "POST",
        body: form
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error ?? "Não foi possível iniciar o processamento.");
      }

      setStatus(`Job ${data.jobId} recebido.`);
      await waitForJob(data.jobId);
    } catch (error) {
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
          <div className="grid gap-5 md:grid-cols-2">
            <label className="cursor-pointer rounded-2xl border border-dashed border-white/20 p-6 transition hover:border-[var(--gold)]">
              <span className="block text-sm font-semibold">1. Vídeo-base</span>
              <span className="mt-2 block text-xs text-white/50">Seu vídeo cantando • MP4</span>
              <span className="mt-5 block truncate text-sm text-[var(--gold-light)]">{videoName}</span>
              <input className="hidden" type="file" accept="video/mp4,video/*" onChange={selectVideo} />
            </label>

            <label className="cursor-pointer rounded-2xl border border-dashed border-white/20 p-6 transition hover:border-[var(--gold)]">
              <span className="block text-sm font-semibold">2. Música</span>
              <span className="mt-2 block text-xs text-white/50">A música que terá a nova sincronização</span>
              <span className="mt-5 block truncate text-sm text-[var(--gold-light)]">{audioName}</span>
              <input className="hidden" type="file" accept="audio/mpeg,audio/wav,audio/*" onChange={selectAudio} />
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
              O cenário original é o foco do motor atual. Novos cenários serão adicionados depois, sem alterar o núcleo de sincronização.
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
          </div>

          {busy && (
            <div className="mt-3">
              <div className="mb-1 flex justify-between text-[11px] text-white/40">
                <span>Progresso</span>
                <span>{progress}%</span>
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
