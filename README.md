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
- Limite padrão de upload: **2 GB por arquivo**.
- A duração do vídeo-base deve cobrir a duração da música.
- O worker mede as durações antes de ocupar a GPU.
- Jobs em andamento não continuam automaticamente depois de uma reinicialização do worker; eles são marcados como interrompidos para evitar jobs presos na fila.
- O job registra timestamps, tamanho dos arquivos e limites utilizados.
- Esses limites podem ser alterados por variáveis de ambiente.

Variáveis principais:

```text
GPU_CONCURRENCY=1
MAX_VIDEO_DURATION_SECONDS=900
MAX_UPLOAD_BYTES=2147483648
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

## Fluxo local no Windows
### Telemetria do processamento

O worker registra métricas para a primeira execução real em GPU:

- tempo total de processamento;
- tempo de normalização;
- tempo do MuseTalk;
- tempo do ajuste de duração, quando necessário;
- tempo da composição do cenário;
- tempo da finalização;
- GPU utilizada;
- pico de memória GPU alocada/reservada;
- duração e tamanho do resultado.

O objetivo é medir a execução real antes de alterar batch, limites de VRAM ou outras otimizações.

### Medição do primeiro teste de 4:17

Depois que um job terminar, as métricas ficam registradas no próprio job:

- tempo total de processamento;
- duração do MP4 final;
- tamanho do resultado;
- batch usado pelo MuseTalk.

No Windows, é possível consultar com:

```powershell
.\scripts\windows\show-job.ps1 -JobId SEU_JOB_ID
```

Esses dados serão usados para avaliar a primeira execução real de 4:17 e decidir ajustes de batch/VRAM antes de pensar em otimizações posteriores.

### Validação antes de usar

No Windows, existe um comando único para conferir a estrutura do projeto:

```powershell
.\scripts\windows\validate-project.ps1
```

Ele verifica a compilação Python, a configuração do Docker Compose, o build do Next.js e a presença dos arquivos essenciais. Ele **não executa o MuseTalk**, porque essa etapa depende de uma GPU NVIDIA.

### Primeiro início do worker GPU

O primeiro `docker compose up --build` pode demorar porque a imagem instala as dependências do MuseTalk e o script de inicialização baixa os modelos.

Os modelos ficam no volume Docker `musetalk-models`. O script de download foi preparado para ser **idempotente**: arquivos já existentes não são baixados novamente.

O worker também aceita:

```text
MUSETALK_BATCH_SIZE=4
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

O batch pode ser reduzido para `2` ou `1` em uma GPU com pouca VRAM.


O projeto agora inclui um fluxo explícito para desenvolvimento local no Windows:

```text
C:\Projetos\alcantara-studio-ai-video\
├── app\
├── gpu-worker\
├── lib\
├── scripts\windows\
├── docker-compose.gpu.yml
└── README.md
```

Scripts disponíveis:

- `scripts/windows/check-gpu.ps1` — diagnóstico da GPU e do acesso do Docker.
- `scripts/windows/start-gpu-worker.ps1` — constrói/inicia o worker GPU.
- `scripts/windows/start-web.ps1` — cria `.env.local` para o worker local e inicia o Next.js.
- `scripts/windows/README.md` — passo a passo do fluxo local.

Isso recoloca o projeto no fluxo de trabalho familiar do VS Code. O GitHub continua sendo o repositório central; a pasta local é a cópia usada para desenvolvimento e testes.

## Transferência de arquivos no modo web

Na versão web atual, a interface envia os arquivos para a API Next.js, que os encaminha ao GPU Worker.

O download do MP4 usa **streaming**: a API Next.js repassa o fluxo do arquivo sem carregar o vídeo inteiro em memória. Isso é importante para vídeos maiores.

A arquitetura final do aplicativo Windows poderá eliminar essa passagem intermediária e conectar a interface diretamente ao processamento local/GPU.

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
- limite de 2 GB por arquivo.

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

## Processamento sem GPU NVIDIA local

O projeto também possui um caminho de processamento via Kaggle, para que o computador local não precise ter uma GPU NVIDIA.

Arquivos:

- `kaggle/Alcantara_Studio_MuseTalk.ipynb` — notebook preparado para MuseTalk 1.5 + GPU do Kaggle.
- `kaggle/README.md` — instruções do fluxo.

Esse caminho usa a GPU gratuita disponibilizada pelo Kaggle dentro da quota e disponibilidade da conta. A quota é limitada e pode variar; portanto, não é tratada como GPU ilimitada. O processamento real no Kaggle ainda precisa ser executado para validação.

O fluxo local com Docker/NVIDIA continua disponível para uma máquina que tenha GPU compatível, mas **não é requisito para o notebook do Cláudio usar o projeto**.

## Estado atual

A interface inicial e a API de jobs estão implementadas. O backend GPU com MuseTalk 1.5 está estruturado em Docker/CUDA, com download automatizado dos modelos, volume persistente, healthcheck e reinício automático.

O pipeline possui uma camada separada de composição de cenário. A versão atual já executa quatro modos: original, estúdio, palco e cinematográfico. Os três últimos aplicam tratamentos visuais com FFmpeg depois do MuseTalk, sem modificar roupa, rosto ou áudio. A substituição real do fundo por outro cenário ainda será uma etapa separada de segmentação/recorte da pessoa.

## Requisitos de evolução

- Interface final simples para uso diário no computador.
- Upload de MP4 + MP3/WAV.
- Saída 16:9 e 9:16.
- Download direto do MP4.
- Seleção de tratamentos visuais sem alterar o núcleo do MuseTalk.
- Próxima etapa de composição: substituição real do fundo por cenário externo usando segmentação da pessoa.
- Arquitetura preparada para futuros elementos visuais, como microfone lateral.
- Possibilidade futura de empacotar a interface como aplicativo Windows.


> Observação: no modo web atual, o arquivo ainda atravessa a camada Next.js/Vercel. O limite do worker de 2 GB não elimina eventuais limites de upload da infraestrutura web. No aplicativo Windows final, o objetivo é evitar essa passagem pela Vercel e enviar o arquivo diretamente ao processamento local/GPU.
