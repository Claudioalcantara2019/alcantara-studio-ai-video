# Execução local no Windows

Este diretório reúne os comandos para voltar ao fluxo normal de desenvolvimento no VS Code.

## Pré-requisitos

Para executar o worker GPU localmente, a máquina precisa ter:

- Windows 10/11;
- Docker Desktop;
- Docker com suporte ao NVIDIA Container Toolkit;
- GPU NVIDIA compatível com CUDA;
- Git;
- Node.js 20+ para a interface Next.js.

A máquina atual com Intel UHD não atende ao requisito de GPU NVIDIA para o worker MuseTalk.

## 1. Abrir o projeto

Clone o repositório para:

`C:\Projetos\alcantara-studio-ai-video`

e abra essa pasta no VS Code.

## 2. Verificar a GPU

No PowerShell:

```powershell
nvidia-smi
```

Depois:

```powershell
docker run --rm --gpus all nvidia/cuda:11.8.0-runtime-ubuntu22.04 nvidia-smi
```

O segundo comando confirma que o Docker consegue enxergar a GPU.


## 3. Diagnóstico completo

Na raiz do projeto:

```powershell
.\scripts\windows\diagnose-project.ps1
```

Esse comando não altera nada e não inicia jobs. Ele mostra Node/npm/Python/Docker, NVIDIA, acesso da GPU pelo Docker, estado do worker e arquivos principais. É útil para descobrir rapidamente qual camada está faltando.

## 4. Portão NVIDIA

Antes do worker, execute:

```powershell
.\\scripts\\windows\\go-nvidia.ps1
```

Se esse comando falhar, pare aqui: ainda não é hora de iniciar o MuseTalk. Ele precisa confirmar que o Windows enxerga a NVIDIA e que um container CUDA consegue acessar a GPU.

## 4. Subir o worker

Na raiz do projeto:

```powershell
.\scripts\windows\start-gpu-worker.ps1
```

O script chama o Docker Compose e deixa o worker na porta 8000.

## 5. Rodar a interface

Em outro terminal:

```powershell
.\scripts\windows\start-web.ps1
```

A interface Next.js ficará disponível localmente.

## 6. Diagnóstico rápido

Use:

```powershell
.\scripts\windows\check-gpu.ps1
```

Ele verifica:

- NVIDIA visível no Windows;
- Docker instalado;
- acesso do Docker à GPU;
- endpoint local do worker.

## Importante

O primeiro início do worker pode ser demorado porque os modelos do MuseTalk são grandes e são baixados para o volume Docker persistente.

Depois que os modelos estiverem no volume, reiniciar o container não deve exigir novo download completo.

O Docker Compose mantém:

- modelos em `musetalk-models`;
- jobs em `alcantara-jobs`.

O objetivo desta estrutura é permitir que o projeto seja desenvolvido normalmente no VS Code, enquanto o processamento pesado fica isolado no container GPU.


## Controle rápido do sistema

Depois que a máquina NVIDIA estiver configurada, o fluxo diário pode ser reduzido a:

```powershell
.\scripts\windows\start-all.ps1
```

Esse comando:

1. verifica NVIDIA + Docker;
2. inicia o GPU Worker;
3. espera o worker ficar pronto;
4. prepara `.env.local`;
5. abre `http://localhost:3000`;
6. inicia a interface Next.js.

Para consultar o estado sem iniciar nada:

```powershell
.\scripts\windows\status.ps1
```

Para parar o worker:

```powershell
.\scripts\windows\stop-all.ps1
```

O Next.js iniciado pelo `start-all.ps1` roda em primeiro plano; para encerrá-lo, use `Ctrl+C` na janela correspondente.


## Primeiro teste real de ponta a ponta

Depois que o GPU Worker estiver READY, é possível testar o pipeline sem depender do navegador:

    .\scripts\windows\test-pipeline.ps1 -VideoPath "C:\caminho\video.mp4" -AudioPath "C:\caminho\musica.mp3"

Para o primeiro teste de 4:17, recomenda-se manter -Format 16:9 e -Scene original, isolando primeiro o MuseTalk.

Exemplo:

    .\scripts\windows\test-pipeline.ps1 -VideoPath "C:\Videos\base-4m17.mp4" -AudioPath "C:\Musicas\faixa-4m17.mp3" -Format "16:9" -Scene "original" -OutputPath "C:\Videos\alcantara-4m17-teste.mp4"

O script:

1. verifica se o Worker está READY;
2. envia vídeo e música para /generate;
3. acompanha o job;
4. detecta falha;
5. baixa o MP4 final;
6. mostra tamanho e métricas de performance registradas pelo Worker.

Isso permite separar problemas da interface web de problemas do pipeline GPU/MuseTalk.

### Ordem recomendada do primeiro teste

**Teste 1 — curto:** vídeo curto + música curta.

**Teste 2 — 4:17:** vídeo-base de pelo menos 4:17 + música de 4:17.

Somente depois de confirmar esses dois testes vale trabalhar em otimização de VRAM, novos cenários ou empacotamento Windows.

### Benchmark curto → 4:17

Quando houver uma máquina NVIDIA disponível, o benchmark executa primeiro um teste curto e salva as métricas. Se também forem fornecidos os arquivos longos, executa em seguida o teste de 4:17 e cria um relatório consolidado em `reports/`.

Exemplo somente com teste curto:

```powershell
.\scripts\windows\benchmark-pipeline.ps1 -ShortVideoPath "C:\caminho\video-curto.mp4" -ShortAudioPath "C:\caminho\musica-curta.mp3"
```

Exemplo curto + 4:17:

```powershell
.\scripts\windows\benchmark-pipeline.ps1 -ShortVideoPath "C:\caminho\video-curto.mp4" -ShortAudioPath "C:\caminho\musica-curta.mp3" -LongVideoPath "C:\caminho\video-4m17.mp4" -LongAudioPath "C:\caminho\musica-4m17.mp3"
```

O benchmark registra job ID, tempos por etapa, GPU/VRAM, duração e tamanho do resultado.

### Primeiro teste NVIDIA em um comando

Com uma máquina Windows + NVIDIA compatível, é possível executar todo o primeiro teste sem abrir vários scripts manualmente:

```powershell
.\scripts\windows\first-nvidia-test.ps1 `
  -ShortVideoPath "C:\caminho\video-curto.mp4" `
  -ShortAudioPath "C:\caminho\musica-curta.mp3" `
  -LongVideoPath "C:\caminho\video-4m17.mp4" `
  -LongAudioPath "C:\caminho\musica-4m17.mp3"
```

O script faz, nesta ordem:

1. verifica NVIDIA + Docker;
2. inicia e aguarda o GPU Worker;
3. executa o benchmark curto;
4. se os arquivos longos forem informados, executa o teste de 4:17;
5. deixa os relatórios em `reports/`.

Não é necessário iniciar o Next.js para esse primeiro teste: ele testa diretamente o backend GPU.
