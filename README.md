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
| X | Abrir a mira de remate; X ou clique para rematar |
| ESC / P | Pausa (ESC também cancela a mira) |
| F4 | Mudar a dificuldade da IA |
| F3 | Modo de depuração |

## Funcionalidades

- Menu principal, ecrã de controlos, menu de pausa e ecrã de fim de jogo
- 8 equipas portuguesas com emblemas
- **Equipamentos com as cores de cada clube**; se as cores das duas equipas forem parecidas, a equipa visitante joga com o equipamento alternativo
- **Linhas do ringue na cor da equipa da casa**, ajustadas automaticamente para se verem bem no piso de madeira
- IA com 3 níveis de dificuldade, sistema de faltas, livres diretos e penáltis
- Mira de remate com barra de força
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
| `hockey_game/componentes.py` | Botões, painéis e fundos reutilizáveis da interface |
| `hockey_game/cores.py` | Cores dos equipamentos, contraste e recoloração dos sprites |
| `hockey_game/team.py` | Dados das equipas (nome, sigla, cores, emblema) |
| `hockey_game/player.py`, `goalkeeper.py`, `ai.py` | Jogadores, guarda-redes e inteligência artificial |
| `hockey_game/ball.py`, `rink.py` | Física da bola e desenho do ringue |
| `hockey_game/camera.py` | Câmara em perspetiva (converte campo plano <-> ecrã) |
| `hockey_game/baliza.py` | Desenho das balizas (camada de fundo e da frente) |
| `hockey_game/animation.py` | Carregamento de animações (redução suave e alinhamento pelos patins) |
| `hockey_game/ui.py` | HUD (marcador, mini-mapa, cartão do jogador) |

Para mudar as cores de uma equipa, edita `cor_primaria`, `cor_secundaria` e `padrao` (`"liso"` ou `"riscas"`) em `hockey_game/team.py`.

## Créditos

Os nomes e emblemas dos clubes pertencem aos respetivos clubes e são usados apenas neste projeto escolar.
