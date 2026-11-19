# Pôr o StickMania na Microsoft Store (grátis)

Na Store é a Microsoft que assina o jogo, por isso deixa de ser preciso desligar o Controlo Inteligente
de Aplicações e desaparece o aviso «O Windows protegeu o computador».

## 1. Criar a conta de programador (grátis)

1. Vai a **https://storedeveloper.microsoft.com** e carrega em criar conta como **Individual**
   (para pessoas individuais é grátis).
2. Entra com uma conta Microsoft (Outlook/Hotmail) e preenche os dados.
3. A Microsoft pede para confirmar a identidade (foto do Cartão de Cidadão e uma selfie). Pode demorar
   desde alguns minutos até um ou dois dias.

## 2. Reservar o nome

1. No **Partner Center** (https://partner.microsoft.com/dashboard) vai a **Apps e jogos → Nova aplicação**.
2. Escreve **StickMania** e carrega em reservar. Se já estiver ocupado, experimenta «StickMania Hóquei».

## 3. Copiar a identidade do pacote

1. Na aplicação, vai a **Gestão de produtos → Identidade do produto**.
2. Copia estes três valores para o ficheiro `ferramentas/loja.json`:

```json
{
  "Name": "valor de Package/Identity/Name",
  "Publisher": "valor de Package/Identity/Publisher (começa por CN=)",
  "PublisherDisplayName": "valor de Package/Properties/PublisherDisplayName"
}
```

## 4. Criar o pacote

Na pasta do projeto:

```
python ferramentas/construir_app.py
python ferramentas/construir_msix.py
```

O pacote fica em `build_app/StickMania_1.<versão>.0.0_x64.msix`. O `makeappx.exe` tem de estar em
`build_app/sdk` (vem do pacote NuGet Microsoft.Windows.SDK.BuildTools, pasta `bin/<versão>/x64`).

## 5. Preencher a submissão

No Partner Center, carrega em **Iniciar a submissão** e preenche:

| Secção | O que pôr |
|---|---|
| Preços e disponibilidade | Grátis, todos os mercados (ou só Portugal) |
| Propriedades | Categoria **Jogos → Desporto**. Política de privacidade: https://rafaelsilveira23.github.io/Stickmaniapap/privacidade.html . Site: https://rafaelsilveira23.github.io/Stickmaniapap/ |
| Classificação etária | Responde ao questionário (sem violência, sem compras, tem jogo online com desconhecidos mas sem chat) |
| Pacotes | Arrasta o ficheiro `.msix` |
| Listagem da Store (Português) | Descrição e capturas de ecrã (ver abaixo) |
| Opções de submissão → Notas para a certificação | O texto abaixo |

**Descrição:**

> StickMania é um jogo de hóquei em patins. Joga uma partida rápida contra o computador, desafia um
> amigo online com uma sala privada, leva o teu clube ao título no modo carreira, com duas divisões e
> uma Taça Europeia, ou cria o teu próprio jogador e decide a vida dele dentro e fora do ringue.
> Tem faltas, cartões, livres diretos, penáltis, fintas e remates na primeira pessoa. Dá para jogar
> com teclado ou com comando.

**Capturas de ecrã:** as imagens `*_1920x1080.png` desta pasta (a Store pede pelo menos 1366×768).
**Logótipos:** `logo_1x1_1080.png` (1:1) e `poster_2x3_720x1080.png` (2:3).

**Notas para a certificação:**

> Desktop game written in Python (pygame) and packaged as MSIX. It needs runFullTrust because it is a
> classic Win32 desktop application. Online mode connects to our own WebSocket server
> (stickmania-eu.onrender.com); the free server may take up to a minute to wake up the first time.

## 6. Enviar

Carrega em **Submeter para a Store**. A verificação da Microsoft costuma demorar até 3 dias úteis.
Depois de aprovado, o jogo aparece na Store e o link pode ir para o site.

Para publicar uma versão nova: muda a versão do jogo, volta a correr os dois scripts do passo 4 e faz
uma nova submissão só com o pacote novo.
