# Primeiro teste NVIDIA — Alcantara Studio

1. Abra o projeto no VS Code.
2. Confirme que existe uma GPU NVIDIA compatível e que `nvidia-smi` funciona.
3. Execute `scripts/windows/check-gpu.ps1`.
4. Execute `scripts/windows/start-gpu-worker.ps1`.
5. Espere o worker responder em `http://127.0.0.1:8000/health` com GPU pronta.
6. Execute `scripts/windows/start-web.ps1`.
7. Abra `http://localhost:3000`.
8. Use primeiro um vídeo curto para validar o pipeline completo.
9. Depois teste o vídeo de 4:17 com uma música de 4:17.
10. Registre tempo de processamento, duração final e tamanho do MP4 antes de qualquer otimização.

## Critério de passagem

O teste é considerado funcional quando o MP4 final:

- abre normalmente;
- mantém a imagem sincronizada com a música nova;
- contém áudio no arquivo final;
- respeita 16:9 ou 9:16;
- termina aproximadamente na duração da música;
- pode ser baixado pela interface.

## Importante

A Vercel não fornece a GPU do processamento. O teste real desta etapa deve ocorrer no computador com GPU NVIDIA e Docker configurados.
