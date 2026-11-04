# Stickmaniapap

Projeto PAP Rafael 2026/2027 — **StickMania**, um jogo de hóquei em patins 2D feito em Python com `pygame-ce`.

## Como jogar

Requisitos: **Python 3.10 ou superior**.

```bash
pip install -r hockey_game/requirements.txt
python main.py
```

No Windows também se pode fazer duplo clique em `jogar.bat`.

## Controlos

| Tecla | Ação |
|---|---|
| W A S D / Setas | Mover o jogador |
| SHIFT | Sprint |
| C / TAB / ESPAÇO | Trocar para o jogador mais perto da bola |
| Z | Passe |
| X | Remate na primeira pessoa: rato/setas apontam à baliza, manter X (ou o botão do rato) dá a força, largar remata |
| R | No MODO TESTE: novo remate noutro sítio |
| ESC / P | Pausa (ESC também cancela a mira) |
| F4 | Mudar a dificuldade da IA |
| F11 | Ecrã inteiro |
| F3 | Modo de depuração |

## Funcionalidades

- Menu principal com o pavilhão desfocado ao fundo e uma **engrenagem no canto** que abre as
  **Definições** (lista de controlos e ecrã inteiro, que fica gravado); menu de pausa e ecrã de fim de jogo
- **Gráficos melhorados**: piso desenhado com o dobro da resolução (linhas e emblema suaves),
  tábuas com veios e nós, reflexos das luzes no verniz, sombra junto às tabelas e sombras esbatidas
  nos jogadores e na bola; vsync para a imagem não "rasgar"
- **Modo carreira**: escolhes um clube e jogas um campeonato contra as outras 7 equipas (7 jornadas, os outros jogos são simulados), com classificação, calendário e várias épocas. O progresso fica gravado numa base de dados SQLite (`hockey_game/saves/carreira.db`)
  - Podes **simular** o teu jogo (botão SIMULAR ou tecla `S`) ou a **época toda**
  - Resultados realistas: força dos clubes, forma recente e "forma do dia", golos por distribuição binomial
    (validado em 600 épocas com `ferramentas/analise_simulacao.py`)
  - Classificação com a forma (últimos 5 jogos) e probabilidades de vitória/empate/derrota no próximo jogo
  - A força do clube também conta no jogo (os clubes fortes patinam um pouco mais depressa)
- **Estilo arcade** (liga/desliga nas Definições): "GOLO!" gigante com o nome do marcador, câmara lenta e
  confetes; nos impactos o jogo congela por um instante, o ecrã treme e saltam faíscas; textos de banda
  desenhada ("DEFESA!", "POSTE!", "ROUBO!"), rasto da bola e contorno nos jogadores (`hockey_game/efeitos.py`)
- **Sons** criados por síntese no código (sem ficheiros de fora): apito, tacadas, tabelas, postes,
  defesas, golo com buzina e público; volume dos efeitos e do público nas Definições
  - **Melhores marcadores**: cada golo fica com o nome de quem marcou (no jogo e nos jogos simulados),
    gravado nas tabelas `jogador` e `estatistica`; separador MARCADORES no ecrã do campeonato
- 8 equipas portuguesas com emblemas e **planteis reais**: 4 jogadores de campo + guarda-redes, como no
  hóquei em patins (formação em losango: avançado, dois médios e defesa)
- Os nomes aparecem no cartão do jogador, nas faltas, nos golos ("GOLO! FC PORTO • Hélder Nunes") e no fim do jogo
- **Equipamentos com as cores de cada clube**; se as cores das duas equipas forem parecidas, a equipa visitante joga com o equipamento alternativo
- **Linhas do ringue na cor da equipa da casa**, ajustadas automaticamente para se verem bem no piso de madeira
- IA com 3 níveis de dificuldade, sistema de faltas, livres diretos e penáltis
- **Remate na primeira pessoa**: a câmara passa para os olhos do jogador; apontas a qualquer ponto da baliza
  (também em altura) e escolhes a força — mais força é mais rápido mas menos preciso. O guarda-redes tem
  tempo de reação, mergulho e pode adivinhar o lado (`hockey_game/remate_pov.py`)
  - O jogador continua a patinar a 50 % enquanto carrega o remate (barra de velocidade)
  - Os defesas que estão entre ti e a baliza aparecem no ecrã e podem **bloquear** o remate
    (a mira fica vermelha com "LINHA TAPADA"); se passarem perto, tapam a vista ao guarda-redes
- **MODO TESTE** no menu principal: só tu contra o guarda-redes, para treinar remates (golos / remates no marcador)
- **Animações de patinagem melhoradas**: o jogador vira-se para o lado para onde patina,
  inclina-se ao acelerar e para trás ao travar, balança a cada passada, tem sombra no chão
  e larga raspas dos patins nas travagens e nas viragens rápidas
- **Balizas desenhadas no código** (vista 3/4, rede em malha, sombra), em duas camadas:
  a bola fica por baixo da rede quando entra e o guarda-redes fica à frente da baliza
- Jogadores desenhados por ordem de profundidade (quem está mais abaixo no ecrã fica à frente)
- **Câmara em perspetiva (vista de TV)**: o campo aparece em trapézio, os jogadores do fundo
  ficam mais pequenos, as tabelas têm altura e publicidade, e há bancadas com público
  nas cores da equipa da casa. A física e a IA continuam num campo plano; só o desenho
  passa pela câmara (`hockey_game/camera.py`)

## Estrutura

| Ficheiro | Função |
|---|---|
| `hockey_game/game.py` | Ciclo principal e estados do jogo (menus, partida, pausa, fim) |
| `hockey_game/menu.py` | Ecrãs de menu |
| `hockey_game/carreira.py` | Modo carreira: calendário, jogos simulados, classificação e base de dados SQLite |
| `hockey_game/carreira_menu.py` | Ecrãs do modo carreira (escolha da equipa e campeonato) |
| `hockey_game/componentes.py` | Botões, painéis e fundos reutilizáveis da interface |
| `hockey_game/graficos.py` | Efeitos gráficos: luzes, sombras suaves, ícones e título desenhados no código |
| `hockey_game/remate_pov.py` | Remate na primeira pessoa (perspetiva, mira, força e modelo do guarda-redes) |
| `hockey_game/efeitos.py` | Estilo arcade (tremer, pausa nos impactos, partículas, festa do golo) |
| `hockey_game/sons.py` | Síntese e reprodução dos sons (os `.wav` ficam em `hockey_game/assets/sounds`) |
| `ferramentas/analise_simulacao.py` | Verifica se os resultados simulados do modo carreira fazem sentido |
| `hockey_game/cores.py` | Cores dos equipamentos, contraste e recoloração dos sprites |
| `hockey_game/team.py` | Dados das equipas (nome, sigla, cores, emblema) |
| `hockey_game/player.py`, `goalkeeper.py`, `ai.py` | Jogadores, guarda-redes e inteligência artificial |
| `hockey_game/ball.py`, `rink.py` | Física da bola e desenho do ringue |
| `hockey_game/camera.py` | Câmara em perspetiva (converte campo plano <-> ecrã) |
| `hockey_game/baliza.py` | Desenho das balizas (camada de fundo e da frente) |
| `hockey_game/animation.py` | Carregamento de animações (redução suave e alinhamento pelos patins) |
| `hockey_game/ui.py` | HUD (marcador, mini-mapa, cartão do jogador) |

Para mudar as cores de uma equipa, edita `cor_primaria`, `cor_secundaria` e `padrao` (`"liso"` ou `"riscas"`) em `hockey_game/team.py`.
Para mudar os jogadores, edita `PLANTEIS` no mesmo ficheiro (guarda-redes + 4 jogadores de campo, pela ordem avançado, médio, médio, defesa).

## Créditos

Os nomes e emblemas dos clubes pertencem aos respetivos clubes e são usados apenas neste projeto escolar.
