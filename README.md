# StickMania — Hóquei em Patins

Projeto PAP 2026/2027 de **Rafael da Hora Silveira** e **Vasco Andreia**
(Curso Profissional de Técnico de Gestão e Programação de Sistemas Informáticos).

StickMania é um jogo de hóquei em patins para Windows, feito em **Python** com **pygame-ce**: jogo rápido,
modo carreira com duas divisões e Taça Europeia, carreira de jogador, jogo online com contas e ranking,
dois jogadores no mesmo computador e um tutorial para quem começa.

- **Site do jogo:** https://rafaelsilveira23.github.io/Stickmaniapap/
- **Descarregar:** [StickMania-Instalar.exe](https://github.com/RafaelSilveira23/Stickmaniapap/raw/main/download/StickMania-Instalar.exe)
- **Relatórios:** [docs/relatorio](docs/relatorio) (um relatório individual de cada aluno, em .docx e .pdf)

---

## 1. Jogar

**Com o instalador (recomendado):** abre o `StickMania-Instalar.exe`, carrega em **INSTALAR** e depois em
**JOGAR AGORA**. Não é preciso o Python nem permissões de administrador. Se o Windows mostrar
«O Windows protegeu o computador», carrega em *Mais informações* → *Executar mesmo assim* (o jogo não tem
assinatura digital paga).

**A partir do código:** precisa do Python 3.10 ou mais recente.

```bash
pip install -r jogo/requirements.txt
python main.py
```

No Windows também se pode fazer duplo clique em `jogar.vbs` (abre sem a janela da consola). Se faltar
o Python ou o pygame-ce, aparece uma janela a explicar o que instalar; se o jogo fechar com um erro, a
mensagem aparece numa janela e fica gravada em `jogo/saves/erro.txt`.

| Tecla | Ação | | Tecla | Ação |
|---|---|---|---|---|
| WASD / setas | Mover | | V | Finta |
| SHIFT | Acelerar | | F | Roleta |
| Z | Passe | | C | Trocar de jogador |
| X | Remate (na primeira pessoa) | | ESC | Pausa |

Também dá para jogar com um comando (Xbox, PlayStation ou compatível).

---

## 2. O que tem o jogo

| | |
|---|---|
| **Partida** | Física da bola e dos jogadores, IA com 3 níveis, guarda-redes que sai da baliza e se atira à bola, faltas com livres, penáltis, livres diretos e cartões, fintas e roleta, remate na primeira pessoa (stickada) |
| **Modos** | Jogo rápido, modo carreira (2 divisões, subidas e descidas, Taça Europeia, jogos simulados), carreira de jogador com a vida fora do rinque, modo teste, tutorial com 8 missões, dois jogadores no mesmo PC |
| **Online** | Jogo aleatório, sala privada com código e desafios pela alcunha; contas (alcunha + palavra-passe), carreiras guardadas na nuvem e ranking com pontos |
| **Apresentação** | Câmara em perspetiva como na televisão, marcador e estatísticas, estilo arcade, repetição dos golos em câmara lenta, sons e cânticos dos clubes criados no código |
| **Clubes** | 19 clubes (1.ª e 2.ª divisão portuguesas e 4 espanhóis) com emblemas, planteis e equipamentos com as cores de cada um |

---

## 3. Organização do projeto

```
stickmaniapap/
├── jogo/                  o jogo (Python + pygame-ce)
│   ├── main.py            ponto de entrada (mostra os erros numa janela)
│   ├── game.py            ciclo principal e estados do jogo (menus, partida, pausa, fim)
│   ├── settings.py        tamanhos, velocidades e cores
│   ├── caminhos.py        onde está cada pasta (junta as subpastas ao Python)
│   ├── partida/           o que acontece no rinque
│   ├── modos/             modo carreira, carreira de jogador, tutorial, dois jogadores
│   ├── clubes/            equipas, planteis, emblemas e cores
│   ├── ecras/             menus, painel do jogo e peças da interface
│   ├── multijogador/      jogo online e contas
│   ├── som/               efeitos sonoros e cânticos
│   └── recursos/          imagens, sons, emblemas e sprites
├── servidor/              servidor do jogo online (Render) e contas (base de dados na Neon)
├── site/                  site de download (publicado no GitHub Pages, ramo gh-pages)
├── ferramentas/
│   ├── construir/         cria o StickMania.exe, o instalador e o pacote da Microsoft Store
│   ├── analise/           testes da simulação e da jogabilidade (IA contra IA)
│   └── imagens/           preparar sprites, emblema e stick
├── docs/
│   ├── relatorio/         relatórios da PAP (o conjunto e os dois individuais)
│   ├── diagramas/         diagramas e Gantt (com os programas que os desenham)
│   ├── capturas/          capturas de ecrã do jogo
│   ├── loja/              guia e imagens para a Microsoft Store
│   └── GANTT.md           planeamento (o GitHub desenha-o)
├── download/              StickMania-Instalar.exe (o instalador pronto)
├── main.py, jogar.vbs     formas de abrir o jogo a partir do código
└── render.yaml            configuração do servidor no Render
```

### O código do jogo, por pasta

| Pasta | Ficheiros | O que faz |
|---|---|---|
| `partida/` | `ball.py`, `player.py`, `goalkeeper.py`, `ai.py` | Bola, jogadores, guarda-redes e inteligência artificial |
| | `faltas.py`, `fintas.py`, `remate_pov.py`, `pavilhao_pov.py` | Faltas e cartões, fintas, remate na primeira pessoa |
| | `rink.py`, `baliza.py`, `camera.py`, `animation.py` | Ringue, balizas, câmara em perspetiva e animações |
| | `efeitos.py`, `repeticao.py`, `comando.py` | Estilo arcade, repetição dos golos e comando |
| `modos/` | `carreira.py`, `carreira_menu.py` | Modo carreira (base de dados SQLite, simulação, Taça Europeia) |
| | `carreira_jogador.py`, `carreira_jogador_menu.py`, `vida.py` | Carreira de jogador e vida do jogador |
| | `tutorial.py`, `dois_jogadores.py` | Tutorial com missões e dois jogadores no mesmo PC |
| `clubes/` | `team.py`, `cores.py` | Clubes, planteis, emblemas e cores dos equipamentos |
| `ecras/` | `menu.py`, `ui.py`, `componentes.py`, `graficos.py`, `fontes.py` | Menus, painel do jogo, botões, ícones e fontes |
| `multijogador/` | `rede.py`, `online.py`, `online_menu.py` | Ligação ao servidor e jogo online |
| | `conta.py`, `conta_menu.py` | Conta do jogador, progresso na nuvem e ranking |
| `som/` | `sons.py`, `canticos.py` | Sons criados por síntese e cânticos dos clubes |

As subpastas são só para organizar: o `caminhos.py` junta-as ao caminho do Python, por isso cada ficheiro
importa os outros só pelo nome (por exemplo `import comando`).

---

## 4. Como funciona (resumo)

- **Ciclo do jogo** (`game.py`): 60 vezes por segundo lê as teclas, atualiza a física, a IA e as regras, e
  desenha tudo. Um "estado" diz em que ecrã se está (menu, partida, pausa, fim...).
- **Câmara**: a física e a IA usam um campo plano; só o desenho passa pela câmara em perspetiva.
- **Jogo online**: o anfitrião corre o jogo inteiro; o convidado envia as teclas e recebe o estado do jogo
  30 vezes por segundo, com previsão do próprio jogador e suavização dos outros. As mensagens passam pelo
  servidor (WebSocket), por isso não é preciso abrir portas.
- **Contas**: o servidor guarda a alcunha, a palavra-passe cifrada (PBKDF2), as carreiras e o ranking numa
  base de dados Postgres (Neon). Não se pede email.
- **Carreiras**: guardadas em SQLite no PC (`jogo/saves`, ou `%APPDATA%\StickMania` no programa instalado)
  e, com conta, também na nuvem.

---

## 5. Ferramentas

| Comando | O que faz |
|---|---|
| `python ferramentas/construir/construir_app.py` | Cria o `StickMania.exe` (PyInstaller) e o instalador em `download/` |
| `python ferramentas/construir/construir_msix.py` | Cria o pacote da Microsoft Store (ver `docs/loja`) |
| `python ferramentas/analise/analise_simulacao.py` | Simula 400 épocas e verifica se os resultados são realistas |
| `python ferramentas/analise/medir_jogabilidade.py jogo` | Joga partidas IA contra IA e conta golos, faltas e problemas |
| `python docs/relatorio/gerar_individuais.py --pdf` | Gera os dois relatórios individuais a partir do conjunto |
| `python servidor/servidor.py` | Servidor online no próprio PC (para testar: `set STICKMANIA_SERVIDOR=ws://localhost:8765`) |

---

## 6. Divisão do trabalho

| Quem | Partes |
|---|---|
| **Rafael da Hora Silveira** | Física da bola e dos jogadores, faltas e cartões, fintas, guarda-redes, gráficos e câmara, estilo arcade e repetição dos golos, remate na primeira pessoa e modo teste, comando e dois jogadores, jogo online, servidor e contas, aplicação para Windows e site |
| **Vasco Andreia** | Inteligência artificial, modo carreira e base de dados, menus, interface e tutorial, sons e cânticos, carreira de jogador e vida do jogador |
| **Os dois** | Ciclo principal do jogo, análise, testes e relatório |

O pormenor está na secção 5.4 de cada relatório individual e no diagrama de Gantt ([docs/GANTT.md](docs/GANTT.md)).

---

Os nomes e emblemas dos clubes pertencem aos respetivos clubes e são usados apenas neste projeto escolar.
