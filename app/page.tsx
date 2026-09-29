"use client";

import { ChangeEvent, useMemo, useState } from "react";

type Format = "16:9" | "9:16";

export default function Home() {
  const [video, setVideo] = useState<File | null>(null);
  const [audio, setAudio] = useState<File | null>(null);
  const [format, setFormat] = useState<Format>("16:9");
  const [status, setStatus] = useState("Pronto para receber os arquivos.");

  const videoName = useMemo(
    () => video?.name ?? "Nenhum vídeo selecionado",
    [video]
  );

  const audioName = useMemo(
    () => audio?.name ?? "Nenhum áudio selecionado",
    [audio]
  );

  function selectVideo(event: ChangeEvent<HTMLInputElement>) {
    setVideo(event.target.files?.[0] ?? null);
    setStatus("Vídeo selecionado.");
  }

  function selectAudio(event: ChangeEvent<HTMLInputElement>) {
    setAudio(event.target.files?.[0] ?? null);
    setStatus("Áudio selecionado.");
  }

  function generate() {
    if (!video || !audio) {
      setStatus("Selecione o vídeo e a música antes de gerar.");
      return;
    }

    setStatus(
      "Arquivos preparados. A conexão com o processamento GPU será ativada na próxima etapa."
    );
  }

  return (
    <main className="min-h-screen px-5 py-10">
      <div className="mx-auto max-w-3xl">
        <header className="mb-10 text-center">
          <p className="mb-3 text-xs tracking-[0.35em] text-[var(--gold)]">
            ALCANTARA STUDIO
          </p>

          <h1 className="text-4xl font-semibold md:text-5xl">
            AI Video Studio
          </h1>

          <p className="mx-auto mt-4 max-w-xl text-sm leading-6 text-white/60">
            Transforme um vídeo seu em um videoclipe sincronizado com uma nova música.
          </p>
        </header>

        <section className="rounded-3xl border border-white/10 bg-[var(--panel)] p-6 shadow-2xl md:p-8">
          <div className="grid gap-5 md:grid-cols-2">
            <label className="cursor-pointer rounded-2xl border border-dashed border-white/20 p-6 transition hover:border-[var(--gold)]">
              <span className="block text-sm font-semibold">1. Vídeo-base</span>
              <span className="mt-2 block text-xs text-white/50">
                MP4 — seu vídeo cantando
              </span>
              <span className="mt-5 block truncate text-sm text-[var(--gold-light)]">
                {videoName}
              </span>
              <input
                className="hidden"
                type="file"
                accept="video/mp4,video/*"
                onChange={selectVideo}
              />
            </label>

            <label className="cursor-pointer rounded-2xl border border-dashed border-white/20 p-6 transition hover:border-[var(--gold)]">
              <span className="block text-sm font-semibold">2. Música</span>
              <span className="mt-2 block text-xs text-white/50">
                MP3 ou WAV
              </span>
              <span className="mt-5 block truncate text-sm text-[var(--gold-light)]">
                {audioName}
              </span>
              <input
                className="hidden"
                type="file"
                accept="audio/mpeg,audio/wav,audio/*"
                onChange={selectAudio}
              />
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

          <button
            type="button"
            onClick={generate}
            className="mt-8 w-full rounded-xl bg-[var(--gold)] px-5 py-4 text-sm font-bold tracking-wide text-black transition hover:brightness-110"
          >
            GERAR VÍDEO
          </button>

          <div className="mt-5 rounded-xl border border-white/5 bg-black/20 px-4 py-3 text-center text-xs text-white/60">
            {status}
          </div>
        </section>

        <p className="mt-6 text-center text-xs text-white/30">
          Alcantara Studio • laboratório privado de criação de vídeo
        </p>
      </div>
    </main>
  );
}
