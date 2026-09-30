# Alcantara Studio — caminho de processamento no Kaggle

Este diretório existe para separar o **processamento pesado** do computador do Cláudio.

O notebook `Alcantara_Studio_MuseTalk.ipynb` prepara o MuseTalk 1.5 em um Kaggle Notebook com GPU, recebe vídeo + música e produz o MP4 final.

## Por que isso existe?

O notebook do Cláudio não possui GPU NVIDIA adequada para a instalação Docker/CUDA local que foi construída inicialmente. Isso **não significa que o projeto precise de outro computador**.

O Kaggle oferece acesso gratuito a GPUs NVIDIA em Notebooks. A documentação atual informa quota semanal de GPU de 30 horas ou, em algumas situações, mais, e sessões de GPU com limite de duração. A disponibilidade pode variar. 

Portanto:

- **custo de geração:** R$ 0 dentro da quota gratuita;
- **GPU local:** não necessária;
- **computador local:** apenas navegador;
- **MuseTalk:** continua sendo o motor;
- **vídeo + música:** continuam sendo os mesmos arquivos usados no teste validado;
- **limitação:** a GPU gratuita do Kaggle não é garantida nem ilimitada.

## Uso

1. Abra o Kaggle.
2. Crie/importa um Notebook Python.
3. Selecione uma GPU nas configurações do Notebook.
4. Ative Internet.
5. Importe `Alcantara_Studio_MuseTalk.ipynb`.
6. Execute as células na ordem.
7. Na célula de upload, envie o vídeo-base e a música.
8. Baixe o MP4 produzido.

O primeiro ciclo instala dependências e baixa os modelos. Depois disso, o mesmo Notebook pode ser reutilizado enquanto o ambiente estiver disponível.

## Importante

O teste de 39 segundos já demonstrou que o MuseTalk consegue sincronizar o vídeo-base com outra música. Este Notebook transforma essa prova em um caminho reproduzível sem exigir NVIDIA no notebook local.

A execução real no Kaggle ainda precisa ser feita. O código foi preparado, mas não deve ser chamado de validado até rodar no ambiente Kaggle.
