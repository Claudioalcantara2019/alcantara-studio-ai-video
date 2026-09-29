# Alcantara Studio AI Video

Aplicação web do Alcantara Studio para transformar um vídeo-base de apresentação/canto em um videoclipe sincronizado com uma nova música.

## Fluxo planejado

1. Enviar vídeo-base (MP4).
2. Enviar música (MP3/WAV).
3. Escolher formato 16:9 ou 9:16.
4. Enviar o trabalho para o backend GPU.
5. Processar com MuseTalk.
6. Receber o MP4 final.
7. Disponibilizar o resultado para download.

## Arquitetura

Interface Next.js/Vercel
→ API de controle
→ backend com GPU
→ MuseTalk
→ MP4 final

A Vercel não executará a inferência pesada. O processamento de IA será separado em um backend com GPU.

## Estado atual

A interface inicial está pronta. A integração com o backend GPU será adicionada na próxima etapa.
