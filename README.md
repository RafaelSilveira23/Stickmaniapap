# Stickmaniapap

Projeto PAP Rafael 2026/2027 — **StickMania**, um jogo de hóquei em patins 2D feito em Python com `pygame-ce`.

## Planeamento

O diagrama de Gantt do projeto está em **[docs/GANTT.md](docs/GANTT.md)** — o GitHub desenha-o a partir de
código Mermaid. É gerado pelo mesmo script da imagem do relatório (`docs/diagramas/gerar_gantt.py`).

## Como jogar

Requisitos: **Python 3.10 ou superior**.

```bash
pip install -r hockey_game/requirements.txt
python main.py
```

No Windows basta fazer duplo clique em `jogar.vbs`: o jogo abre **sem a janela preta da consola**.
Se faltar o Python ou o pygame-ce, abre o `jogar_com_consola.bat`, que mostra o que se passa e instala o pygame-ce
(também se pode abrir esse ficheiro diretamente para ver as mensagens do jogo). Se o jogo fechar com um erro,
aparece uma janela com a mensagem, que também fica gravada em `hockey_game/saves/erro.txt`.

## Controlos

| Tecla | Ação |
|---|---|
| W A S D / Setas | Mover o jogador |
| SHIFT | Sprint |
| C / TAB / ESPAÇO | Trocar para o jogador mais perto da bola (na carreira de jogador: pedir a bola) |
| Z | Passe |
| X | Remate na primeira pessoa: rato/setas apontam à baliza, manter X (ou o botão do rato) dá a força, largar remata |
| R | No MODO TESTE: novo remate noutro sítio |
| ESC / P | Pausa (ESC também cancela a mira) |
| F4 | Mudar a dificuldade da IA |
| F11 | Ecrã inteiro |
| F3 | Modo de depuração |

No **jogo online** os controlos são os mesmos, mas o `X` faz um remate direto à baliza (o ecrã do remate na
primeira pessoa pararia o jogo do outro jogador): carrega numa seta para cima ou para baixo ao mesmo tempo
para apontar a esse lado da baliza.

## Jogar online (contra um amigo noutro computador)

1. Os dois abrem o jogo e escolhem **JOGAR ONLINE** no menu principal.
2. Um escolhe **CRIAR JOGO** (é o *anfitrião* e joga com a equipa da casa). Aparece no ecrã o endereço do
   computador dele (por exemplo `192.168.1.20` ou `26.12.34.56`).
3. O outro escolhe **ENTRAR NUM JOGO**, escreve esse endereço e carrega em **LIGAR** (joga com a equipa de fora).
4. O anfitrião escolhe as duas equipas e começa a partida.

Na primeira vez o **Firewall do Windows** pergunta se o Python pode usar a rede: carrega em **Permitir**
(no computador do anfitrião). O jogo usa a porta **50555** (TCP).

**Na mesma rede** (casa, escola): funciona logo com o endereço que aparece ao anfitrião.

**Pela internet** os dois computadores têm de "se ver". A forma mais simples:

- **Radmin VPN** (grátis, feito para jogos): instalem os dois o [Radmin VPN](https://www.radmin-vpn.com/),
  um cria uma rede (*Network → Create network*, com nome e palavra-passe) e o outro entra nela
  (*Network → Join network*). O endereço a usar no jogo é o que começa por **26.** (o jogo mostra-o primeiro).
- Alternativas iguais: **ZeroTier** ou **Tailscale** (endereços `100.x.x.x`).
- Sem VPN: o anfitrião pode abrir a porta 50555 no router (*port forwarding*) ou usar um túnel como o
  **playit.gg**; nesse caso o amigo escreve `endereço:porta` (por exemplo `exemplo.playit.gg:12345`).

Como funciona: só o computador do anfitrião corre o jogo (física, IA, golos). O convidado envia as teclas que
carrega e recebe 30 vezes por segundo o estado do jogo (posições, bola, resultado, sons e efeitos), que desenha
com suavização para não se ver aos saltos (`hockey_game/rede.py` e `hockey_game/online.py`).

## Funcionalidades

- Menu principal com o pavilhão desfocado ao fundo e uma **engrenagem no canto** que abre as
  **Definições** (lista de controlos e ecrã inteiro, que fica gravado); menu de pausa e ecrã de fim de jogo
- Todos os menus com o mesmo estilo (painéis de vidro e botões com ícones); na **pausa** e no **fim de jogo**
  o jogo fica desfocado por trás, e no fim cada equipa aparece com as suas cores, o vencedor destacado e confetes
- **Transições suaves** (fade) entre todos os ecrãs
- **Gráficos melhorados**: piso desenhado com o dobro da resolução (linhas e emblema suaves),
  tábuas com veios e nós, reflexos das luzes no verniz, sombra junto às tabelas e sombras esbatidas
  nos jogadores e na bola; vsync para a imagem não "rasgar"
- **Modo carreira**: escolhes um clube e jogas um campeonato contra as outras 7 equipas (7 jornadas, os outros jogos são simulados), com classificação, calendário e várias épocas. O progresso fica gravado numa base de dados SQLite (`hockey_game/saves/carreira.db`)
  - Podes **simular** o teu jogo (botão SIMULAR ou tecla `S`) ou a **época toda**
  - Resultados realistas: força dos clubes, forma recente e "forma do dia", golos por distribuição binomial
    (validado em 600 épocas com `ferramentas/analise_simulacao.py`)
  - Classificação com a forma (últimos 5 jogos) e probabilidades de vitória/empate/derrota no próximo jogo
  - A força do clube também conta no jogo (os clubes fortes patinam um pouco mais depressa)
- **Carreira de jogador**: crias o teu jogador (nome, número, posição e clube) e nos jogos **só controlas esse jogador**;
  os colegas são da IA e passam-te a bola quando a pedes (`C`, `TAB`, `ESPAÇO` ou `Z` sem bola)
  - Nota de 0 a 10 em cada jogo (golos, assistências, passes certos, bolas recuperadas e perdidas, resultado),
    com um cartão que a mostra ao vivo durante o jogo
  - O geral e os atributos evoluem com as notas; no fim da época, com nota média 6,8 ou mais, há propostas de
    clubes mais fortes
  - Gravado à parte em `hockey_game/saves/carreira_jogador.db` (tabelas `atleta` e `atuacao`)
  - **Vida do jogador** (ao estilo dos jogos de simulação de vida): idade, dinheiro, forma, moral, confiança do
    treinador, fama e estudos. Depois de cada jornada há um **evento com escolhas** (festa na véspera do jogo,
    teste na escola, patrocínio, polémica nas redes, convocatória da seleção, ...) e em cada semana uma
    **atividade** (`V`): treino extra, ginásio, descansar, sair com os amigos, estudar, ... Tudo fica no **diário** (`L`)
  - As escolhas mexem no hóquei: forma e moral somam-se aos atributos, pouca forma dá **lesões**, sem a
    confiança do treinador vais para o **banco**, e a fama ajuda a ter propostas (`hockey_game/vida.py`)
  - **Pessoas** (`P`): mãe, pai, melhor amigo e um namoro que pode começar nos eventos; cada uma tem uma relação
    que desce se não lhe ligares; uma vez por semana podes passar tempo, conversar, pedir conselho ou dar uma prenda
  - **42 eventos**, alguns com **consequências** mais tarde (a polémica nas redes dá um processo disciplinar,
    o primeiro encontro pode dar um namoro, ...), **bens** (carta, carro, casa própria, agente, braçadeira de capitão)
    e **14 conquistas** (`C`)
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
  - Os defesas têm sempre o tamanho certo em perspetiva (crescem ao aproximar-te, já não encolhem nem desaparecem), com sprites HD nas cores do clube; quem tapa a linha do remate fica com contorno vermelho e o nome por cima
- **MODO TESTE** no menu principal: só tu contra o guarda-redes, para treinar remates (golos / remates no marcador)
- **Animações de patinagem melhoradas**: o jogador vira-se para o lado para onde patina,
  inclina-se ao acelerar e para trás ao travar, balança a cada passada, tem sombra no chão
  e larga raspas dos patins nas travagens e nas viragens rápidas
- **Balizas desenhadas no código** (vista 3/4, rede em malha, sombra), em duas camadas:
  a bola fica por baixo da rede quando entra e o guarda-redes fica à frente da baliza
- Jogadores desenhados por ordem de profundidade (quem está mais abaixo no ecrã fica à frente)
- **Jogar online**: dois jogadores em computadores diferentes, um em cada equipa (ver em cima)
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
| `hockey_game/carreira_jogador.py` | Carreira de jogador: jogador criado, nota, evolução, propostas e base de dados |
| `hockey_game/carreira_jogador_menu.py` | Ecrãs da carreira de jogador (criar o jogador e painel da carreira) |
| `hockey_game/vida.py` | Vida do jogador: valores, eventos com escolhas, atividades, lesões, banco e diário |
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
| `hockey_game/fontes.py` | Fontes do sistema com cache (cada fonte é criada uma só vez) |
| `hockey_game/rede.py` | Ligação TCP entre os dois computadores (anfitrião e convidado), em threads |
| `hockey_game/online.py` | Jogo online: o anfitrião corre o jogo e envia o estado; o convidado envia as teclas |
| `hockey_game/online_menu.py` | Ecrã "Jogar online" (criar jogo, escrever o endereço, à espera) |
| `jogar.vbs` / `jogar_com_consola.bat` | Arrancar o jogo sem consola / com consola (e instalar o pygame-ce) |
| `sprites_v2/` | Sprites usados pelo jogo (jogadores, guarda-redes, bola e público) |

Para mudar as cores de uma equipa, edita `cor_primaria`, `cor_secundaria` e `padrao` (`"liso"` ou `"riscas"`) em `hockey_game/team.py`.
Para mudar os jogadores, edita `PLANTEIS` no mesmo ficheiro (guarda-redes + 4 jogadores de campo, pela ordem avançado, médio, médio, defesa).

## Créditos

Os nomes e emblemas dos clubes pertencem aos respetivos clubes e são usados apenas neste projeto escolar.
