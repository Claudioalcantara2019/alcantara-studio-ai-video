# GO NVIDIA — primeiro teste real

Use este comando antes de iniciar o MuseTalk:

```powershell
.\scripts\windows\go-nvidia.ps1
```

Ele faz somente o pré-voo:

- confirma Docker;
- confirma `nvidia-smi`;
- mostra GPU, VRAM e driver;
- executa `nvidia-smi` dentro de um container CUDA 11.8;
- interrompe o fluxo imediatamente se a GPU não estiver acessível.

Se todos os testes passarem:

```powershell
.\scripts\windows\start-gpu-worker.ps1
```

Depois:

```powershell
.\scripts\windows\start-web.ps1
```

E então fazemos primeiro um vídeo curto. Somente depois do curto passar partimos para o vídeo de **4:17**.

## Regra desta etapa

Não vamos mexer em otimização, cenários novos ou empacotamento Windows antes de confirmar o pipeline real:

**GPU → Docker → MuseTalk → MP4 → áudio → sincronização.**

Isso evita gastar tempo tentando diagnosticar várias camadas ao mesmo tempo.
