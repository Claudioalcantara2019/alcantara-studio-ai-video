# GPU Worker

Backend de processamento do Alcantara Studio AI Video.

Este serviço foi separado da aplicação Next.js porque a inferência do MuseTalk precisa de GPU.

## Contrato

POST /generate

Multipart:
- video: vídeo-base
- audio: música
- format: 16:9 ou 9:16

Resposta JSON com jobId.

GET /health verifica se o worker está ativo.

## Próxima etapa

O worker será conectado ao ambiente MuseTalk validado no Tesla T4.
