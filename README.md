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

A interface inicial e a API de jobs estão implementadas. O backend GPU com MuseTalk 1.5 está estruturado em Docker/CUDA, com download automatizado dos modelos, volume persistente, healthcheck e reinício automático.

O pipeline também possui uma camada separada de composição de cenário. O cenário "Vídeo original" funciona; as opções de cenários adicionais estão preparadas na interface e serão ativadas quando o motor de composição correspondente for implementado.

## Requisitos de evolução

- Interface final simples para uso diário no computador.
- Upload de MP4 + MP3/WAV.
- Saída 16:9 e 9:16.
- Download direto do MP4.
- Seleção de cenários/fundos sem alterar o núcleo do MuseTalk.
- Arquitetura preparada para futuros elementos visuais, como microfone lateral.
- Possibilidade futura de empacotar a interface como aplicativo Windows.
