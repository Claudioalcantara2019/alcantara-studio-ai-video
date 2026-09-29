# GPU Worker

Worker FastAPI que recebe vídeo + música, executa MuseTalk 1.5 e devolve o MP4.

## API

GET /health

POST /generate
- video: MP4
- audio: MP3/WAV
- format: 16:9 ou 9:16

GET /jobs/{jobId}

GET /jobs/{jobId}/result

## Modelos

Os pesos não ficam no GitHub nem dentro do código-fonte. Eles devem existir no diretório models da instalação do MuseTalk no ambiente GPU.

A configuração segue a instalação oficial do MuseTalk 1.5: Python 3.10, PyTorch 2.0.1 com CUDA 11.8 e os pacotes MMLab exigidos pelo projeto.

O código oficial usa scripts/inference.py para a inferência normal.

## Observação

O Dockerfile instala o código e as dependências do MuseTalk, mas o download dos pesos é separado para permitir armazenamento persistente e evitar reconstruir uma imagem de vários gigabytes a cada alteração do código.
