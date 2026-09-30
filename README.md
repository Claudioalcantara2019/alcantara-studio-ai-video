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

## Processamento de vídeos longos

O worker foi preparado para o fluxo de músicas longas, como uma faixa de 4 minutos ou mais.

- Limite padrão por arquivo: **15 minutos**.
- Limite padrão de upload: **500 MB por arquivo**.
- A duração do vídeo-base deve cobrir a duração da música.
- O worker mede as durações antes de ocupar a GPU.
- Jobs em andamento não continuam automaticamente depois de uma reinicialização do worker; eles são marcados como interrompidos para evitar jobs presos na fila.
- O job registra timestamps, tamanho dos arquivos e limites utilizados.
- Esses limites podem ser alterados por variáveis de ambiente.

Variáveis principais:

```text
GPU_CONCURRENCY=1
MAX_VIDEO_DURATION_SECONDS=900
MAX_UPLOAD_BYTES=524288000
```

A limitação é deliberadamente conservadora nesta fase. Ela pode ser ampliada depois que o processamento real de vídeos de 4:17 for validado em uma GPU NVIDIA.

## Estrutura local do projeto

O repositório contém o código do aplicativo e do worker GPU. Os modelos grandes do MuseTalk e os arquivos temporários de processamento não devem ser versionados no GitHub; eles ficam na máquina de processamento, usando os volumes definidos no Docker Compose.

Estrutura conceitual:

```text
alcantara-studio-ai-video/
├── app/                 # interface web e API
├── gpu-worker/          # processamento com MuseTalk
├── lib/                 # tipos e regras compartilhadas
├── docker-compose.gpu.yml
└── README.md
```

No uso final, a intenção é empacotar a interface em um aplicativo Windows simples, mantendo o processamento pesado separado da interface.

## Arquitetura

Interface Next.js/Vercel
→ API de controle
→ backend com GPU
→ MuseTalk
→ MP4 final

A Vercel não executará a inferência pesada. O processamento de IA será separado em um backend com GPU.

## Interface atual

A interface já apresenta o estado do backend GPU e acompanha o job em tempo real.

Ela também valida, antes do envio:

- vídeo-base em MP4;
- formatos de áudio suportados;
- limite de 500 MB por arquivo.

Durante o processamento, mostra:

- ID do job;
- etapa atual;
- percentual informado pelo worker;
- mensagem retornada pelo backend;
- botão para baixar o MP4 quando concluído.

O endpoint `/api/health` consulta o backend GPU quando configurado, permitindo distinguir entre **backend configurado** e **GPU realmente pronta**.

## Validação automática

O GitHub Actions agora valida os dois lados do projeto:

1. compila os arquivos Python do GPU Worker;
2. verifica os endpoints principais do worker;
3. instala as dependências web;
4. executa o build de produção do Next.js.

Assim, alterações futuras na interface podem ser detectadas pelo CI antes de serem consideradas concluídas.

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
