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

## 3. Subir o worker

Na raiz do projeto:

```powershell
.\scripts\windows\start-gpu-worker.ps1
```

O script chama o Docker Compose e deixa o worker na porta 8000.

## 4. Rodar a interface

Em outro terminal:

```powershell
.\scripts\windows\start-web.ps1
```

A interface Next.js ficará disponível localmente.

## 5. Diagnóstico

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
