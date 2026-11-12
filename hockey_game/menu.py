# -*- coding: utf-8 -*-
"""menu.py - Ecrãs de menu do StickMania PAP.

  • MenuPrincipal   - ecrã inicial (Jogo rápido, Modo carreira, Controlos, Sair)
  • EcraEscolhaTeste - escolher o treino do modo teste (sozinho, com um colega, contra um adversário)
  • EcraControlos   - lista de teclas
  • TeamSelectMenu  - seleção das equipas, do equipamento e da dificuldade
  • MenuPausa       - pausa durante a partida
  • EcraFimJogo     - resultado final

Cada ecrã tem handle_event(event) -> ação (str) ou None, update(dt) e draw().
Quem decide o que fazer com a ação é a classe Game (game.py).
"""
import math
import random
import pygame
import fontes
from settings import WIDTH, HEIGHT, VERSAO_JOGO
import comando
from team import EQUIPAS_LISTA, COMPETICOES, competicao_da_equipa, obter_info_equipa, carregar_logo_equipa
from ai import DIFICULDADES
from cores import (definir_equipamentos, cor_linhas_campo, cor_visivel_em_escuro,
                   cor_texto_sobre, misturar, clarear, escurecer)
from componentes import (fonte, texto, painel, fundo_menu, Botao, ListaBotoes, painel_vidro, fundo_desfocado,
                         sprite_equipamento, amostra_cor, faixa_equipa, escurecer_ecra,
                         gradiente_vertical, COR_DESTAQUE, COR_TEXTO, COR_TEXTO_SUAVE, COR_PAINEL)
from graficos import (gradiente_radial, luz, cone_luz, sombra_suave, brilho_retangulo, vinheta,
                      icone, emblema_sticks, titulo_estilizado)


# ====================================================================== #
# Estatísticas da partida                                                #
# ====================================================================== #

def desenhar_estatisticas(s, game, centro_x: int, y: int, largura: int, passo: int = 26):
    """
    Estatísticas da partida (remates, defesas, posse e faltas), usadas na pausa e no fim do jogo.
    Cada linha tem o valor da casa à esquerda, o nome ao centro e o valor do visitante à direita,
    e por baixo uma barra dividida nas cores das duas equipas, proporcional aos valores.
    """
    cor_c = cor_visivel_em_escuro(game.kit_casa["principal"], 120)
    cor_f = cor_visivel_em_escuro(game.kit_fora["principal"], 120)
    x0 = centro_x - largura // 2
    for k, (nome, va, vv, ta, tv) in enumerate(game.estatisticas_jogo()):
        yy = y + k * passo
        texto(s, ta, 15, COR_TEXTO if va >= vv else COR_TEXTO_SUAVE, (x0, yy), ancora="midleft")
        texto(s, nome.upper(), 10, COR_TEXTO_SUAVE, (centro_x, yy))
        texto(s, tv, 15, COR_TEXTO if vv >= va else COR_TEXTO_SUAVE, (x0 + largura, yy), ancora="midright")
        barra = pygame.Rect(x0, yy + 9, largura, 4)
        total = va + vv
        meio = round(largura * (va / total if total else 0.5))
        pygame.draw.rect(s, (22, 32, 60), barra, border_radius=2)
        if total:
            if meio > 1:
                pygame.draw.rect(s, cor_c, (barra.left, barra.top, meio - 1, 4), border_radius=2)
            if largura - meio > 1:
                pygame.draw.rect(s, cor_f, (barra.left + meio + 1, barra.top, largura - meio - 1, 4),
                                 border_radius=2)


# ====================================================================== #
# Menu Principal                                                         #
# ====================================================================== #

class BotaoMenu:
    """
    Botão grande do menu principal: ícone num círculo, título e uma linha de descrição.
    Quando tem o foco acende-se na sua cor (com um halo) e desliza um pouco para a direita.
    Tem a mesma "interface" do Botao (rect, acao, por_cima, draw) para funcionar na ListaBotoes.
    """

    def __init__(self, rect, titulo: str, descricao: str, acao: str, cor, nome_icone: str,
                 seta: bool = True, tamanho: int = 22):
        self.rect = pygame.Rect(rect)
        self.seta = seta              # seta "▶" à direita quando tem o foco
        self.tamanho = tamanho        # tamanho do título quando não há descrição
        self.titulo = titulo
        self.descricao = descricao
        self.acao = acao
        self.cor = cor
        self.nome_icone = nome_icone
        self.k = 0.0          # 0 = normal, 1 = com foco (vai mudando aos poucos: transição suave)

    def por_cima(self, pos) -> bool:
        return self.rect.collidepoint(pos)

    def animar(self, dt: float, focado: bool):
        alvo = 1.0 if focado else 0.0
        self.k += (alvo - self.k) * min(1.0, dt * 12)

    def draw(self, surf, _mpos=None, focado: bool = False):
        # As cores usam o foco arredondado a 5 %: assim o fundo e o ícone ficam em cache
        # (antes o gradiente do fundo era redesenhado linha a linha em todos os frames)
        k = round(self.k * 20) / 20
        r = self.rect.move(round(8 * self.k), 0)
        raio = 16

        # Halo de luz quando tem o foco
        if k > 0.02:
            halo = brilho_retangulo(r.size, self.cor, raio, 22, 150).copy()
            halo.set_alpha(int(255 * k))
            surf.blit(halo, (r.x - 22, r.y - 22))

        surf.blit(_fundo_botao(r.size, self.cor, k, raio), (r.x, r.y))

        # Ícone dentro de um círculo
        cx, cy = r.x + 40, r.centery
        cor_circ = misturar(escurecer(self.cor, 0.3), (255, 255, 255), k)
        pygame.draw.circle(surf, misturar(cor_circ, (0, 0, 0), 0.5), (cx, cy + 2), 25)
        pygame.draw.circle(surf, cor_circ, (cx, cy), 25)
        pygame.draw.circle(surf, clarear(self.cor, 0.5), (cx, cy), 25, 2)
        cor_ic = misturar((255, 255, 255), self.cor, k)
        ic = icone(self.nome_icone, 26, cor_ic)
        surf.blit(ic, ic.get_rect(center=(cx, cy)))

        # Textos
        cor_tit = misturar((225, 232, 250), (255, 255, 255), k)
        cor_desc = misturar((130, 150, 195), (235, 240, 255), k)
        x_txt = r.x + 82
        if self.descricao:
            texto(surf, self.titulo, 24, cor_tit, (x_txt, cy - 10), ancora="midleft")
            texto(surf, self.descricao, 14, cor_desc, (x_txt, cy + 15), ancora="midleft", negrito=False)
        else:
            texto(surf, self.titulo, self.tamanho, cor_tit, (x_txt, cy), ancora="midleft")

        # Seta à direita quando tem o foco
        if k > 0.05 and self.seta:
            seta = icone("jogar", 16, (255, 255, 255)).copy()
            seta.set_alpha(int(255 * k))
            surf.blit(seta, seta.get_rect(center=(r.right - 30, cy)))


_cache_fundo_botao = {}


def _fundo_botao(tamanho, cor, k, raio):
    """Sombra, vidro com gradiente, reflexo e borda de um BotaoMenu (feito uma vez por cor e foco)."""
    chave = (tamanho, tuple(cor), k, raio)
    img = _cache_fundo_botao.get(chave)
    if img is None:
        w, h = tamanho
        img = pygame.Surface((w + 3, h + 6), pygame.SRCALPHA)
        pygame.draw.rect(img, (0, 0, 0, 110), (3, 6, w, h), border_radius=raio)          # sombra
        topo = misturar((22, 32, 62), clarear(cor, 0.05), k * 0.85)
        base = misturar((12, 18, 38), escurecer(cor, 0.35), k * 0.85)
        camada = pygame.Surface((w, h), pygame.SRCALPHA)
        gradiente_vertical(camada, camada.get_rect(), topo, base, raio=raio)
        camada.set_alpha(int(215 + 40 * k))
        img.blit(camada, (0, 0))
        reflexo = pygame.Surface((w - 8, h // 2 - 4), pygame.SRCALPHA)                  # reflexo de vidro
        pygame.draw.rect(reflexo, (255, 255, 255, int(14 + 16 * k)), reflexo.get_rect(), border_radius=raio - 4)
        img.blit(reflexo, (4, 4))
        pygame.draw.rect(img, misturar((70, 95, 150), clarear(cor, 0.45), k), (0, 0, w, h), 2, border_radius=raio)
        if len(_cache_fundo_botao) > 400:
            _cache_fundo_botao.clear()
        _cache_fundo_botao[chave] = img
    return img


class BotaoEngrenagem:
    """Botão redondo com uma engrenagem (abre as definições). Roda quando tem o foco."""

    def __init__(self, centro, raio: int = 28, acao: str = "definicoes"):
        self.centro = centro
        self.raio = raio
        self.rect = pygame.Rect(0, 0, raio * 2, raio * 2)
        self.rect.center = centro
        self.acao = acao
        self.k = 0.0
        self.angulo = 0.0

    def por_cima(self, pos) -> bool:
        return math.dist(pos, self.centro) <= self.raio + 4

    def animar(self, dt: float, focado: bool):
        self.k += ((1.0 if focado else 0.0) - self.k) * min(1.0, dt * 12)
        self.angulo -= dt * (25 + 120 * self.k)

    def draw(self, surf, _mpos=None, focado: bool = False):
        k = self.k
        cx, cy = self.centro
        if k > 0.02:
            halo = gradiente_radial(self.raio * 4, self.raio * 4, (120, 180, 255), int(110 * k))
            surf.blit(halo, halo.get_rect(center=self.centro))
        pygame.draw.circle(surf, (0, 0, 0), (cx + 2, cy + 4), self.raio)
        fundo = misturar((18, 28, 56), (50, 110, 230), k)
        pygame.draw.circle(surf, fundo, self.centro, self.raio)
        pygame.draw.circle(surf, misturar((80, 110, 170), (190, 220, 255), k), self.centro, self.raio, 2)
        eng = icone("engrenagem", 34, misturar((200, 215, 245), (255, 255, 255), k))
        eng = pygame.transform.rotozoom(eng, self.angulo, 1.0)
        surf.blit(eng, eng.get_rect(center=self.centro))
        # Etiqueta "DEFINIÇÕES" que aparece ao lado
        if k > 0.05:
            f = fonte(14)
            img = f.render("DEFINIÇÕES", True, (255, 255, 255))
            caixa = pygame.Rect(0, 0, img.get_width() + 24, 30)
            caixa.midright = (cx - self.raio - 10 + round(10 * (1 - k)), cy)
            etiqueta = pygame.Surface(caixa.size, pygame.SRCALPHA)
            pygame.draw.rect(etiqueta, (20, 34, 70, 230), etiqueta.get_rect(), border_radius=15)
            pygame.draw.rect(etiqueta, (110, 160, 240, 255), etiqueta.get_rect(), 1, border_radius=15)
            etiqueta.blit(img, img.get_rect(center=(caixa.width // 2, caixa.height // 2)))
            etiqueta.set_alpha(int(255 * k))
            surf.blit(etiqueta, caixa)


_fundo_arena_cache = {}


def _fundo_arena(arena: pygame.Surface | None) -> pygame.Surface:
    """O pavilhão do jogo desfocado e escurecido (fundo do menu principal)."""
    chave = id(arena)
    if chave in _fundo_arena_cache:
        return _fundo_arena_cache[chave]
    fundo = pygame.Surface((WIDTH, HEIGHT))
    if arena is None:
        fundo_menu(fundo, 0.0)
    else:
        fundo.fill((10, 14, 28))
        # Desfocar numa imagem mais pequena é muito mais rápido e o resultado é o mesmo
        peq = pygame.transform.smoothscale(arena.convert(), (WIDTH // 2, HEIGHT // 2))
        peq = pygame.transform.gaussian_blur(peq, 5)
        fundo.blit(pygame.transform.smoothscale(peq, (WIDTH, HEIGHT)), (0, 0))
    # Escurecer, mais em cima (para o título se ler bem) e em baixo
    escuro = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        a = 200 - 70 * math.sin(t * math.pi)
        pygame.draw.line(escuro, (8, 12, 30, int(a)), (0, y), (WIDTH, y))
    fundo.blit(escuro, (0, 0))
    fundo.blit(vinheta(WIDTH, HEIGHT, 190), (0, 0))
    _fundo_arena_cache.clear()
    _fundo_arena_cache[chave] = fundo
    return fundo


class MenuPrincipal:
    def __init__(self, screen: pygame.Surface, casa_id: str = "fc_porto", fora_id: str = "riba_dave",
                 arena: pygame.Surface | None = None):
        self.screen = screen
        self.casa_id = casa_id
        self.fora_id = fora_id
        self.t = 0.0
        self.arena = arena
        bw, x = 460, WIDTH // 2 - 230
        self.engrenagem = BotaoEngrenagem((WIDTH - 50, 48))
        self.lista = ListaBotoes([
            BotaoMenu((x, 242, bw, 60), "JOGO RÁPIDO", "Escolhe dois clubes e joga uma partida",
                      "jogar", (40, 190, 100), "jogar"),
            BotaoMenu((x, 310, bw, 60), "JOGAR ONLINE", "Jogo aleatório ou sala privada com um amigo",
                      "online", (40, 200, 210), "globo"),
            BotaoMenu((x, 378, bw, 60), "MODO CARREIRA", "Duas divisões, Taça Europeia e subidas de divisão",
                      "carreira", (255, 175, 40), "trofeu"),
            BotaoMenu((x, 446, bw, 60), "CARREIRA DE JOGADOR", "Cria o teu jogador e joga só com ele",
                      "carreira_jogador", (255, 110, 160), "jogador"),
            BotaoMenu((x, 514, bw, 60), "MODO TESTE", "Treina remates, passes e jogadas contra um defesa",
                      "teste", (80, 170, 255), "alvo"),
            BotaoMenu((x + 90, 584, bw - 180, 44), "SAIR", "", "sair", (230, 70, 70), "sair", seta=False, tamanho=19),
            self.engrenagem,
        ])
        # Posição final de cada botão (entram a deslizar, um a seguir ao outro, quando o menu abre)
        self._y_botoes = [b.rect.y for b in self.lista.botoes]
        self._cone = cone_luz(360, 470)
        self._feixe = cone_luz(240, 760, (190, 215, 255), 6, 26)
        fonte_titulo = fontes.SysFont("Arial Black", 86)
        self._titulo = titulo_estilizado("STICKMANIA", fonte_titulo, (255, 255, 255), (170, 200, 255),
                                         contorno=5, cor_brilho=(60, 120, 255))
        self._mascara_titulo = fonte_titulo.render("STICKMANIA", True, (255, 255, 255))
        # Partículas de pó a flutuar na luz dos projetores (sempre as mesmas)
        rnd = random.Random(3)
        self._po = [(rnd.uniform(0, WIDTH), rnd.uniform(0, HEIGHT), rnd.uniform(6, 22),
                     rnd.uniform(1.0, 2.4), rnd.uniform(0, 6.28)) for _ in range(55)]

    def handle_event(self, event) -> str | None:
        if event.type == pygame.QUIT:
            return "sair"
        return self.lista.handle_event(event)

    def update(self, dt: float):
        self.t += dt
        for i, b in enumerate(self.lista.botoes):
            b.animar(dt, i == self.lista.foco)

    # ------------------------------------------------------------------ #
    def _desenhar_fundo(self, s):
        s.blit(_fundo_arena(self.arena), (0, 0))
        # Dois projetores a varrer o pavilhão devagar
        for x0, fase in ((150, 0.0), (WIDTH - 150, 2.2)):
            ang = 22 * math.sin(self.t * 0.35 + fase)
            # O feixe é uma luz esbatida: rodar sem suavização (rotate) dá o mesmo aspeto e é muito
            # mais rápido do que rotozoom
            feixe = pygame.transform.rotate(self._feixe, round(ang, 1))
            # O topo do feixe fica preso ao projetor (por cima do ecrã)
            dx = math.sin(math.radians(ang)) * 380
            s.blit(feixe, feixe.get_rect(center=(x0 - dx, -60 + 380 * math.cos(math.radians(ang)))),
                   special_flags=pygame.BLEND_RGB_ADD)
        # Pó a brilhar na luz
        for x, y, vel, tam, fase in self._po:
            yy = (y - self.t * vel) % HEIGHT
            xx = x + 10 * math.sin(self.t * 0.6 + fase)
            a = int(60 + 50 * math.sin(self.t * 1.3 + fase))
            pygame.draw.circle(s, (a, a, int(a * 1.1)), (xx, yy), tam / 2)

    def _desenhar_titulo(self, s):
        cx = WIDTH // 2
        emb = emblema_sticks(124)
        flutuar = 3 * math.sin(self.t * 1.8)
        brilho = luz(300, 200, (255, 210, 150), 70)
        s.blit(brilho, brilho.get_rect(center=(cx, 68)), special_flags=pygame.BLEND_RGB_ADD)
        s.blit(emb, emb.get_rect(center=(cx, 60 + flutuar)))

        tr = self._titulo.get_rect(center=(cx, 158))
        s.blit(self._titulo, tr)
        # Reflexo de luz que atravessa o título de vez em quando
        ciclo = (self.t % 5.0) / 1.2
        if ciclo < 1.0:
            m = self._mascara_titulo
            faixa = pygame.Surface(m.get_size(), pygame.SRCALPHA)
            x = -120 + (m.get_width() + 240) * ciclo
            pygame.draw.polygon(faixa, (255, 255, 255, 150),
                                [(x, 0), (x + 50, 0), (x + 10, m.get_height()), (x - 40, m.get_height())])
            brilho_txt = m.copy()
            brilho_txt.blit(faixa, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            s.blit(brilho_txt, brilho_txt.get_rect(center=(cx, 158)))

        # Subtítulo dourado com riscas dos lados
        y = 216
        r = texto(s, "H Ó Q U E I   E M   P A T I N S", 17, COR_DESTAQUE, (cx, y))
        for sinal in (-1, 1):
            xa = cx + sinal * (r.width // 2 + 18)
            pygame.draw.line(s, COR_DESTAQUE, (xa, y), (xa + sinal * 70, y), 2)
            pygame.draw.circle(s, COR_DESTAQUE, (xa + sinal * 76, y), 3)

    def _desenhar_jogador(self, s, kit, eq_id, cx, virar):
        chao = 572
        # Projetor de palco por cima do jogador
        s.blit(self._cone, self._cone.get_rect(midbottom=(cx, chao + 30)), special_flags=pygame.BLEND_RGB_ADD)
        mancha = luz(300, 70, (255, 240, 200), 120)
        s.blit(mancha, mancha.get_rect(center=(cx, chao - 4)), special_flags=pygame.BLEND_RGB_ADD)
        sombra = sombra_suave(150, 30, 170)
        s.blit(sombra, sombra.get_rect(center=(cx, chao - 4)))
        img = sprite_equipamento(kit, 220, self.t, virar=virar)
        s.blit(img, img.get_rect(midbottom=(cx, chao)))
        # Emblema com um halo
        logo = carregar_logo_equipa(eq_id, (66, 66))
        ly = 318 + 4 * math.sin(self.t * 1.6 + cx)
        halo = luz(150, 150, kit["principal"], 90)
        s.blit(halo, halo.get_rect(center=(cx, ly)), special_flags=pygame.BLEND_RGB_ADD)
        if logo:
            s.blit(logo, logo.get_rect(center=(cx, ly)))
        # Nome numa etiqueta
        nome = obter_info_equipa(eq_id)["nome"]
        f = fonte(15)
        img_n = f.render(nome.upper(), True, (255, 255, 255))
        caixa = pygame.Rect(0, 0, img_n.get_width() + 30, 30)
        caixa.center = (cx, 606)
        etiqueta = pygame.Surface(caixa.size, pygame.SRCALPHA)
        pygame.draw.rect(etiqueta, (*escurecer(kit["principal"], 0.35), 220), etiqueta.get_rect(), border_radius=15)
        pygame.draw.rect(etiqueta, (*clarear(kit["principal"], 0.4), 255), etiqueta.get_rect(), 2, border_radius=15)
        s.blit(etiqueta, caixa)
        s.blit(img_n, img_n.get_rect(center=caixa.center))

    def draw(self):
        s = self.screen
        kit_casa, kit_fora = definir_equipamentos(self.casa_id, self.fora_id)
        self._desenhar_fundo(s)
        self._desenhar_titulo(s)

        for kit, eq_id, cx, virar in ((kit_casa, self.casa_id, 200, False),
                                      (kit_fora, self.fora_id, WIDTH - 200, True)):
            self._desenhar_jogador(s, kit, eq_id, cx, virar)

        # Entrada: cada botão sobe para o seu lugar, 0,05 s depois do anterior
        for i, (b, y_final) in enumerate(zip(self.lista.botoes, self._y_botoes)):
            if b is self.engrenagem:
                continue
            k = max(0.0, min(1.0, (self.t - 0.05 * i) / 0.32))
            b.rect.y = y_final + round(46 * (1 - k) ** 3)
        if self.t < 0.75:
            # Enquanto entram, os botões são desenhados numa camada que vai ficando opaca
            camada = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            self.lista.draw(camada)
            camada.set_alpha(int(255 * min(1.0, self.t / 0.45)))
            s.blit(camada, (0, 0))
        else:
            self.lista.draw(s)

        texto(s, "↑ ↓  escolher     ENTER  confirmar", 12, (120, 145, 195),
              (WIDTH // 2, 652), negrito=False)
        # Rodapé
        pygame.draw.line(s, (40, 60, 105), (WIDTH // 2 - 220, HEIGHT - 42), (WIDTH // 2 + 220, HEIGHT - 42), 1)
        texto(s, "Projeto PAP  •  Vasco Andreia e Rafael Silveira  •  2026/2027", 13, (110, 130, 175),
              (WIDTH // 2, HEIGHT - 24), negrito=False)
        texto(s, f"v{VERSAO_JOGO}", 12, (80, 100, 145), (18, HEIGHT - 24), ancora="midleft")


# ====================================================================== #
# Escolha do Modo Teste                                                  #
# ====================================================================== #

# (ação, título, descrição, cor, ícone)
MODOS_TESTE = [
    ("teste_sozinho", "SOZINHO", "Só tu contra o guarda-redes: treina os remates",
     (80, 170, 255), "alvo"),
    ("teste_colega", "COM UM COLEGA", "Tu e um colega da tua equipa: treina os passes",
     (40, 190, 100), "jogador"),
    ("teste_adversario", "CONTRA UM ADVERSÁRIO", "Um defesa tenta tirar-te a bola antes do remate",
     (255, 110, 90), "escudo"),
]


class EcraEscolhaTeste:
    """Ecrã que abre no MODO TESTE do menu principal: escolher um dos 3 treinos."""

    def __init__(self, screen: pygame.Surface, arena: pygame.Surface | None = None):
        self.screen = screen
        self.arena = arena
        self.t = 0.0
        bw, x = 560, WIDTH // 2 - 280
        botoes = [BotaoMenu((x, 210 + i * 78, bw, 62), titulo, desc, acao, cor, ic)
                  for i, (acao, titulo, desc, cor, ic) in enumerate(MODOS_TESTE)]
        botoes.append(BotaoMenu((x + 140, 470, bw - 280, 46), "VOLTAR", "", "voltar", (150, 110, 255), "casa",
                                seta=False, tamanho=19))
        self.lista = ListaBotoes(botoes)

    def handle_event(self, event) -> str | None:
        if event.type == pygame.QUIT:
            return "sair"
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            return "voltar"
        return self.lista.handle_event(event)

    def update(self, dt: float):
        self.t += dt
        for i, b in enumerate(self.lista.botoes):
            b.animar(dt, i == self.lista.foco)

    def draw(self):
        s = self.screen
        s.blit(_fundo_arena(self.arena), (0, 0))
        alvo = icone("alvo", 40, COR_DESTAQUE)
        r_tit = texto(s, "MODO TESTE", 44, COR_TEXTO, (WIDTH // 2 + 26, 110), sombra=True)
        s.blit(alvo, alvo.get_rect(center=(r_tit.left - 32, 110)))
        pygame.draw.rect(s, COR_DESTAQUE, (WIDTH // 2 - 90, 142, 180, 4), border_radius=2)
        texto(s, "Sem tempo e sem limite de remates  •  R = nova jogada", 15, COR_TEXTO_SUAVE,
              (WIDTH // 2, 172), negrito=False)
        self.lista.draw(s)
        texto(s, "↑ ↓  escolher     ENTER  confirmar     ESC  voltar", 13, (130, 155, 205),
              (WIDTH // 2, HEIGHT - 40), negrito=False)


# ====================================================================== #
# Ecrã de Controlos                                                      #
# ====================================================================== #

CONTROLOS = [
    ("MOVIMENTO", [
        ("W A S D  /  Setas", "Mover o jogador"),
        ("SHIFT", "Sprint (correr mais rápido)"),
        ("C  /  TAB  /  ESPAÇO", "Trocar de jogador (carreira de jogador: pedir a bola)"),
    ]),
    ("COM A BOLA", [
        ("Z  /  Clique no colega", "Passe (escolhe o tipo nas definições)"),
        ("X", "Remate na primeira pessoa"),
        ("Rato  /  Setas", "Apontar à baliza (no remate)"),
        ("Manter X  /  Clique", "Força do remate (larga para rematar)"),
    ]),
    ("JOGO", [
        ("ESC  /  P", "Pausa (no ecrã do remate, ESC cancela o remate)"),
        ("F4", "Mudar a dificuldade da IA"),
        ("F11", "Ecrã inteiro"),
        ("F3", "Modo de depuração (FPS)"),
    ]),
]

# Com um comando ligado, o ecrã das definições mostra os botões dele (nomes da Xbox)
CONTROLOS_COMANDO = [
    ("MOVIMENTO", [
        ("Stick esquerdo  /  Setas", "Mover o jogador"),
        ("RB  /  RT", "Sprint (correr mais rápido)"),
        ("X  /  Y  /  LB", "Trocar de jogador (carreira de jogador: pedir a bola)"),
    ]),
    ("COM A BOLA", [
        ("A", "Passe"),
        ("B", "Remate na primeira pessoa"),
        ("Stick esquerdo", "Apontar à baliza (no remate)"),
        ("Manter B", "Força do remate (larga para rematar)"),
    ]),
    ("JOGO E MENUS", [
        ("START", "Pausa"),
        ("BACK", "Pausa (no ecrã do remate, cancela o remate)"),
        ("A  /  B", "Confirmar  /  voltar, nos menus"),
        ("LB  /  RB", "Mudar de separador, nos menus"),
    ]),
]


def _interruptor(surf, centro, ligado: bool, k_foco: float):
    """Interruptor (ligado/desligado) como nos telemóveis."""
    r = pygame.Rect(0, 0, 64, 32)
    r.center = centro
    if k_foco > 0.02:
        halo = brilho_retangulo(r.size, (90, 160, 255), 16, 12, 140).copy()
        halo.set_alpha(int(255 * k_foco))
        surf.blit(halo, (r.x - 12, r.y - 12))
    fundo = (40, 190, 100) if ligado else (52, 64, 96)
    pygame.draw.rect(surf, fundo, r, border_radius=16)
    pygame.draw.rect(surf, clarear(fundo, 0.35), r, 2, border_radius=16)
    bx = r.right - 16 if ligado else r.left + 16
    pygame.draw.circle(surf, (0, 0, 0), (bx + 1, r.centery + 2), 12)
    pygame.draw.circle(surf, (255, 255, 255), (bx, r.centery), 12)
    return r


class EcraControlos:
    """
    Ecrã de DEFINIÇÕES (abre na engrenagem do menu principal e nas «Definições» da pausa):
    à esquerda a lista de teclas, à direita o ecrã inteiro, o estilo arcade e o volume do som.
    """
    # Itens que podem ter o foco (setas ↑ ↓)
    ITENS = ("ecra", "arcade", "passe", "efeitos", "publico", "voltar")

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.t = 0.0
        self.ecra_inteiro = False          # o Game atualiza isto antes de desenhar
        self.estilo_arcade = True
        self.tipo_passe = "z"               # "z" (tecla Z) ou "clique" (clicar no colega)
        self.vol_efeitos = 0.8              # 0.0 a 1.0 (o Game lê e grava)
        self.vol_publico = 0.5
        self.arena = None                   # fundo (pavilhão desfocado), dado pelo Game
        self.btn_voltar = Botao((WIDTH // 2 - 140, HEIGHT - 84, 280, 52), "VOLTAR", "voltar",
                                cor=(50, 140, 255), icone="◄")
        self.foco = self.ITENS.index("voltar")
        self._k_foco = [0.0] * len(self.ITENS)
        self._a_arrastar = None             # barra de volume que está a ser arrastada com o rato
        self.rect_painel_teclas = pygame.Rect(70, 118, 730, 500)
        p = self.rect_painel_ecra = pygame.Rect(830, 118, 380, 500)
        self.linhas = {
            "ecra": pygame.Rect(p.left + 16, p.top + 50, p.width - 32, 48),
            "arcade": pygame.Rect(p.left + 16, p.top + 100, p.width - 32, 48),
            "passe": pygame.Rect(p.left + 16, p.top + 150, p.width - 32, 48),
            "efeitos": pygame.Rect(p.left + 16, p.top + 246, p.width - 32, 48),
            "publico": pygame.Rect(p.left + 16, p.top + 296, p.width - 32, 48),
        }
        # Seletor do tipo de passe: duas metades, "Z" e "CLIQUE"
        self.rect_seletor_passe = pygame.Rect(0, 0, 132, 32)
        self.rect_seletor_passe.midright = (p.right - 30, self.linhas["passe"].centery)
        self.rect_interruptor = pygame.Rect(0, 0, 64, 32)
        self.rect_interruptor.center = (p.right - 62, self.linhas["ecra"].centery)
        self.rect_interruptor_arcade = self.rect_interruptor.copy()
        self.rect_interruptor_arcade.centery = self.linhas["arcade"].centery
        self.barras = {k: pygame.Rect(p.left + 150, self.linhas[k].centery - 4, 190, 8)
                       for k in ("efeitos", "publico")}

    # ------------------------------------------------------------------ #
    def _mudar_volume(self, qual: str, valor: float) -> str:
        valor = round(max(0.0, min(1.0, valor)) * 20) / 20       # passos de 5 %
        if qual == "efeitos":
            self.vol_efeitos = valor
        else:
            self.vol_publico = valor
        return "volume_" + qual

    def _valor_do_rato(self, qual: str, x: int) -> float:
        b = self.barras[qual]
        return (x - b.left) / b.width

    def handle_event(self, event) -> str | None:
        """Devolve 'voltar', 'ecra_inteiro', 'estilo_arcade', 'tipo_passe', 'volume_efeitos',
        'volume_publico', 'sair' ou None."""
        if event.type == pygame.QUIT:
            return "sair"
        item = self.ITENS[self.foco]
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                return "voltar"
            if event.key in (pygame.K_UP, pygame.K_w):
                self.foco = (self.foco - 1) % len(self.ITENS)
                return "mover"
            if event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_TAB):
                self.foco = (self.foco + 1) % len(self.ITENS)
                return "mover"
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                if item == "ecra":
                    return "ecra_inteiro"
                if item == "arcade":
                    return "estilo_arcade"
                if item == "passe":
                    return "tipo_passe"
                if item == "voltar":
                    return "voltar"
            if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d):
                passo = 0.1 if event.key in (pygame.K_RIGHT, pygame.K_d) else -0.1
                if item == "ecra":
                    return "ecra_inteiro"
                if item == "arcade":
                    return "estilo_arcade"
                if item == "passe":
                    return "tipo_passe"
                if item in ("efeitos", "publico"):
                    atual = self.vol_efeitos if item == "efeitos" else self.vol_publico
                    return self._mudar_volume(item, atual + passo)
        if event.type == pygame.MOUSEMOTION:
            if self._a_arrastar:
                return self._mudar_volume(self._a_arrastar, self._valor_do_rato(self._a_arrastar, event.pos[0]))
            for i, k in enumerate(self.ITENS):
                r = self.btn_voltar.rect if k == "voltar" else self.linhas[k]
                if r.collidepoint(event.pos):
                    self.foco = i
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._a_arrastar = None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_voltar.por_cima(event.pos):
                return "voltar"
            if self.linhas["ecra"].collidepoint(event.pos):
                self.foco = 0
                return "ecra_inteiro"
            if self.linhas["arcade"].collidepoint(event.pos):
                self.foco = 1
                return "estilo_arcade"
            if self.linhas["passe"].collidepoint(event.pos):
                self.foco = self.ITENS.index("passe")
                return "tipo_passe"
            for k in ("efeitos", "publico"):
                if self.linhas[k].collidepoint(event.pos):
                    self.foco = self.ITENS.index(k)
                    self._a_arrastar = k
                    return self._mudar_volume(k, self._valor_do_rato(k, event.pos[0]))
        return None

    def update(self, dt: float):
        self.t += dt
        for i in range(len(self.ITENS)):
            alvo = 1.0 if i == self.foco else 0.0
            self._k_foco[i] += (alvo - self._k_foco[i]) * min(1.0, dt * 12)

    # ------------------------------------------------------------------ #
    def _destaque(self, s, rect, k):
        if k > 0.02:
            destaque = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(destaque, (60, 110, 220, int(70 * k)), destaque.get_rect(), border_radius=10)
            s.blit(destaque, rect)

    def _barra_volume(self, s, qual: str, valor: float, k: float):
        b = self.barras[qual]
        pygame.draw.rect(s, (30, 44, 80), b, border_radius=4)
        cheio = b.copy()
        cheio.width = max(0, round(b.width * valor))
        if cheio.width:
            gradiente_vertical(s, cheio, (90, 200, 255), (40, 120, 230), raio=4)
        pygame.draw.rect(s, (80, 110, 170), b, 1, border_radius=4)
        x = b.left + round(b.width * valor)
        raio = 10 + round(2 * k)
        pygame.draw.circle(s, (0, 0, 0), (x + 1, b.centery + 2), raio)
        pygame.draw.circle(s, (255, 255, 255), (x, b.centery), raio)
        pygame.draw.circle(s, (60, 140, 255), (x, b.centery), raio, 2)
        texto(s, f"{round(valor * 100)}%", 13, COR_TEXTO_SUAVE, (b.right + 26, b.centery))

    def _seletor_passe(self, s, k: float):
        """Duas metades lado a lado ("Z" | "CLIQUE"); a escolhida fica acesa."""
        r = self.rect_seletor_passe
        if k > 0.02:
            halo = brilho_retangulo(r.size, (90, 160, 255), 16, 12, 140).copy()
            halo.set_alpha(int(255 * k))
            s.blit(halo, (r.x - 12, r.y - 12))
        pygame.draw.rect(s, (30, 44, 80), r, border_radius=16)
        metade = r.width // 2
        for i, (valor, nome) in enumerate((("z", "Z"), ("clique", "CLIQUE"))):
            parte = pygame.Rect(r.left + i * metade, r.top, metade, r.height)
            escolhido = self.tipo_passe == valor
            if escolhido:
                pygame.draw.rect(s, (40, 190, 100), parte.inflate(-4, -4), border_radius=14)
            texto(s, nome, 13, (255, 255, 255) if escolhido else COR_TEXTO_SUAVE, parte.center)
        pygame.draw.rect(s, (80, 110, 170), r, 2, border_radius=16)

    def draw(self, por_cima_do_jogo: bool = False):
        s = self.screen
        if por_cima_do_jogo:
            escurecer_ecra(s, 210)
        else:
            s.blit(_fundo_arena(self.arena), (0, 0))

        # Título com a engrenagem
        eng = pygame.transform.rotozoom(icone("engrenagem", 38, COR_DESTAQUE), -self.t * 20, 1.0)
        r_tit = texto(s, "DEFINIÇÕES", 40, COR_TEXTO, (WIDTH // 2 + 24, 62), sombra=True)
        s.blit(eng, eng.get_rect(center=(r_tit.left - 30, 62)))
        pygame.draw.rect(s, COR_DESTAQUE, (WIDTH // 2 - 90, 92, 180, 4), border_radius=2)

        # ── Painel dos controlos ─────────────────────────────────────────
        caixa = self.rect_painel_teclas
        painel(s, caixa, alpha=228)
        com_comando = comando.ligado()
        texto(s, "CONTROLOS  •  COMANDO" if com_comando else "CONTROLOS", 18, COR_TEXTO,
              (caixa.left + 30, caixa.top + 28), ancora="midleft")
        y = caixa.top + 62
        for secao, linhas in (CONTROLOS_COMANDO if com_comando else CONTROLOS):
            texto(s, secao, 13, COR_DESTAQUE, (caixa.left + 30, y), ancora="midleft")
            pygame.draw.line(s, (40, 65, 120), (caixa.left + 130, y), (caixa.right - 30, y), 1)
            y += 27
            for tecla, descricao in linhas:
                # "Tecla" desenhada como uma tecla de teclado
                f = fonte(13)
                img = f.render(tecla, True, (255, 255, 255))
                tecla_r = pygame.Rect(caixa.left + 30, y - 13, img.get_width() + 22, 26)
                pygame.draw.rect(s, (12, 20, 40), tecla_r.move(0, 3), border_radius=6)
                gradiente_vertical(s, tecla_r, (44, 66, 118), (28, 44, 86), raio=6)
                pygame.draw.rect(s, (90, 130, 210), tecla_r, 1, border_radius=6)
                s.blit(img, img.get_rect(center=tecla_r.center))
                texto(s, descricao, 14, (210, 225, 250), (caixa.left + 270, y), ancora="midleft", negrito=False)
                y += 29
            y += 6

        # ── Painel do ecrã e do som ──────────────────────────────────────
        caixa = self.rect_painel_ecra
        painel(s, caixa, alpha=228)
        texto(s, "JOGO", 16, COR_DESTAQUE, (caixa.left + 30, caixa.top + 28), ancora="midleft")
        linha = self.linhas["ecra"]
        self._destaque(s, linha, self._k_foco[0])
        texto(s, "Ecrã inteiro", 16, COR_TEXTO, (caixa.left + 30, linha.centery - 8), ancora="midleft")
        texto(s, "Atalho: F11", 12, COR_TEXTO_SUAVE, (caixa.left + 30, linha.centery + 12),
              ancora="midleft", negrito=False)
        _interruptor(s, self.rect_interruptor.center, self.ecra_inteiro, self._k_foco[0])
        linha = self.linhas["arcade"]
        self._destaque(s, linha, self._k_foco[1])
        texto(s, "Estilo arcade", 16, COR_TEXTO, (caixa.left + 30, linha.centery - 8), ancora="midleft")
        texto(s, "golos e impactos com mais energia", 11, COR_TEXTO_SUAVE, (caixa.left + 30, linha.centery + 12),
              ancora="midleft", negrito=False)
        _interruptor(s, self.rect_interruptor_arcade.center, self.estilo_arcade, self._k_foco[1])
        i_passe = self.ITENS.index("passe")
        linha = self.linhas["passe"]
        self._destaque(s, linha, self._k_foco[i_passe])
        texto(s, "Tipo de passe", 16, COR_TEXTO, (caixa.left + 30, linha.centery - 8), ancora="midleft")
        texto(s, "tecla Z ou clicar no colega", 11, COR_TEXTO_SUAVE, (caixa.left + 30, linha.centery + 12),
              ancora="midleft", negrito=False)
        self._seletor_passe(s, self._k_foco[i_passe])

        y = caixa.top + 206
        pygame.draw.line(s, (40, 65, 120), (caixa.left + 30, y), (caixa.right - 30, y), 1)
        texto(s, "SOM", 16, COR_DESTAQUE, (caixa.left + 30, y + 22), ancora="midleft")
        for i, (k, nome, desc, valor) in enumerate((
                ("efeitos", "Efeitos", "apito, bola, golos", self.vol_efeitos),
                ("publico", "Público", "ambiente do pavilhão", self.vol_publico)), start=self.ITENS.index("efeitos")):
            r = self.linhas[k]
            self._destaque(s, r, self._k_foco[i])
            texto(s, nome, 16, COR_TEXTO, (caixa.left + 30, r.centery - 8), ancora="midleft")
            texto(s, desc, 11, COR_TEXTO_SUAVE, (caixa.left + 30, r.centery + 11), ancora="midleft", negrito=False)
            self._barra_volume(s, k, valor, self._k_foco[i])

        # Sobre o jogo
        y = caixa.top + 356
        pygame.draw.line(s, (40, 65, 120), (caixa.left + 30, y), (caixa.right - 30, y), 1)
        texto(s, "SOBRE", 16, COR_DESTAQUE, (caixa.left + 30, y + 22), ancora="midleft")
        emb = emblema_sticks(56)
        s.blit(emb, emb.get_rect(center=(caixa.left + 70, y + 86)))
        texto(s, "STICKMANIA", 20, COR_TEXTO, (caixa.left + 112, y + 66), ancora="midleft")
        texto(s, f"Hóquei em patins 2D  •  versão {VERSAO_JOGO}", 12, COR_TEXTO_SUAVE, (caixa.left + 112, y + 90),
              ancora="midleft", negrito=False)
        texto(s, "Projeto PAP  •  2026/2027", 12, COR_TEXTO_SUAVE, (caixa.left + 112, y + 108),
              ancora="midleft", negrito=False)
        texto(s, "Python + pygame-ce", 12, COR_TEXTO_SUAVE, (caixa.left + 112, y + 126),
              ancora="midleft", negrito=False)

        self.btn_voltar.draw(s, (-1, -1), focado=self.ITENS[self.foco] == "voltar")
        texto(s, "↑ ↓  escolher     ← →  ajustar     ENTER  confirmar     ESC  voltar", 12, (120, 145, 195),
              (WIDTH // 2, HEIGHT - 16), negrito=False)


# ====================================================================== #
# Seleção de Equipas                                                     #
# ====================================================================== #

class TeamSelectMenu:
    def __init__(self, screen: pygame.Surface, casa_id: str = "fc_porto",
                 fora_id: str = "riba_dave", dificuldade: str = "normal", arena: pygame.Surface | None = None):
        self.screen = screen
        self.arena = arena                  # pavilhão do jogo (fundo desfocado, como no menu principal)
        self.casa_idx = EQUIPAS_LISTA.index(casa_id) if casa_id in EQUIPAS_LISTA else 0
        self.fora_idx = EQUIPAS_LISTA.index(fora_id) if fora_id in EQUIPAS_LISTA else 1
        if self.fora_idx == self.casa_idx:
            self.fora_idx = (self.casa_idx + 1) % len(EQUIPAS_LISTA)
        self.dificuldade = dificuldade if dificuldade in DIFICULDADES else "normal"
        self.anim_t = 0.0
        # Separador da grelha: 1.ª divisão, 2.ª divisão ou Europa (começa no da equipa da casa)
        self.aba = competicao_da_equipa(EQUIPAS_LISTA[self.casa_idx])
        self._setup_rects()

    # ------------------------------------------------------------------ #
    def _setup_rects(self):
        self.btn_voltar = Botao((24, 18, 130, 40), "VOLTAR", "voltar", cor=(50, 140, 255),
                                tamanho_texto=15, icone="◄")

        self.rect_casa = pygame.Rect(130, 96, 420, 252)
        self.rect_fora = pygame.Rect(WIDTH - 130 - 420, 96, 420, 252)
        for nome, card in (("casa", self.rect_casa), ("fora", self.rect_fora)):
            prev = pygame.Rect(card.left + 12, card.top + 104, 34, 46)
            nxt = pygame.Rect(card.right - 46, card.top + 104, 34, 46)
            setattr(self, f"btn_{nome}_prev", prev)
            setattr(self, f"btn_{nome}_next", nxt)

        # Separadores das competições, por cima da grelha
        aw, ag = 150, 10
        x0 = (WIDTH - (len(COMPETICOES) * aw + (len(COMPETICOES) - 1) * ag)) // 2
        self.rects_abas = [pygame.Rect(x0 + i * (aw + ag), 352, aw, 26) for i in range(len(COMPETICOES))]
        self._montar_grelha()

        # Dificuldade
        cx = WIDTH // 2
        self.botoes_dif = [
            Botao((cx - 222, 512, 140, 38), "FÁCIL", "facil", cor=(40, 180, 90), tamanho_texto=17),
            Botao((cx - 70, 512, 140, 38), "NORMAL", "normal", cor=(50, 140, 255), tamanho_texto=17),
            Botao((cx + 82, 512, 140, 38), "DIFÍCIL", "dificil", cor=(230, 70, 70), tamanho_texto=17),
        ]
        self.btn_jogar = Botao((WIDTH // 2 - 160, 596, 320, 56), "INICIAR PARTIDA", "iniciar",
                               cor=(40, 190, 100), tamanho_texto=22, icone="►")

    def _montar_grelha(self):
        """Grelha com as equipas do separador escolhido: (id, índice em EQUIPAS_LISTA, retângulo)."""
        equipas = COMPETICOES[self.aba][1]
        card_w, card_h, gap = 118, 88, 14
        total_w = len(equipas) * card_w + (len(equipas) - 1) * gap
        start_x = (WIDTH - total_w) // 2
        self.grid_rects = []
        for i, eq_id in enumerate(equipas):
            r = pygame.Rect(start_x + i * (card_w + gap), 384, card_w, card_h)
            self.grid_rects.append((eq_id, EQUIPAS_LISTA.index(eq_id), r))

    def mudar_aba(self, aba: int):
        if aba != self.aba:
            self.aba = aba % len(COMPETICOES)
            self._montar_grelha()

    # ------------------------------------------------------------------ #
    # Lógica                                                             #
    # ------------------------------------------------------------------ #
    def mudar_casa(self, delta: int):
        self.casa_idx = (self.casa_idx + delta) % len(EQUIPAS_LISTA)
        if self.casa_idx == self.fora_idx:
            self.casa_idx = (self.casa_idx + delta) % len(EQUIPAS_LISTA)
        self.mudar_aba(competicao_da_equipa(EQUIPAS_LISTA[self.casa_idx]))   # a grelha acompanha a escolha

    def mudar_fora(self, delta: int):
        self.fora_idx = (self.fora_idx + delta) % len(EQUIPAS_LISTA)
        if self.fora_idx == self.casa_idx:
            self.fora_idx = (self.fora_idx + delta) % len(EQUIPAS_LISTA)

    def escolher_casa(self, idx: int):
        """Escolhe a equipa da casa; se for a mesma da visitante, a visitante passa à seguinte."""
        self.casa_idx = idx
        if self.fora_idx == self.casa_idx:
            self.fora_idx = (self.casa_idx + 1) % len(EQUIPAS_LISTA)

    def escolher_fora(self, idx: int):
        self.fora_idx = idx
        if self.casa_idx == self.fora_idx:
            self.casa_idx = (self.fora_idx + 1) % len(EQUIPAS_LISTA)

    def get_equipas(self) -> tuple[str, str]:
        return EQUIPAS_LISTA[self.casa_idx], EQUIPAS_LISTA[self.fora_idx]

    def get_dificuldade(self) -> str:
        return self.dificuldade

    def ciclar_dificuldade(self):
        ordem = ["facil", "normal", "dificil"]
        idx = ordem.index(self.dificuldade) if self.dificuldade in ordem else 1
        self.dificuldade = ordem[(idx + 1) % len(ordem)]

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Devolve 'iniciar', 'voltar', 'sair' ou None."""
        if event.type == pygame.QUIT:
            return "sair"

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                return "iniciar"
            elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                return "voltar"
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self.mudar_casa(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.mudar_casa(1)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.mudar_fora(-1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.mudar_fora(1)
            elif event.key == pygame.K_TAB:
                self.ciclar_dificuldade()
            elif event.key in (pygame.K_f, pygame.K_F1):
                self.dificuldade = "facil"
            elif event.key in (pygame.K_n, pygame.K_F2):
                self.dificuldade = "normal"
            elif event.key in (pygame.K_g, pygame.K_F3):
                self.dificuldade = "dificil"
            elif event.key in (pygame.K_q, pygame.K_e, pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                self.mudar_aba(self.aba + (1 if event.key in (pygame.K_e, pygame.K_PAGEDOWN) else -1))
            elif pygame.K_1 <= event.key <= pygame.K_8:
                k = event.key - pygame.K_1          # número do cartão no separador
                if 0 <= k < len(self.grid_rects):
                    self.escolher_casa(self.grid_rects[k][1])

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
            mpos = event.pos
            if event.button == 1:
                if self.btn_jogar.por_cima(mpos):
                    return "iniciar"
                if self.btn_voltar.por_cima(mpos):
                    return "voltar"
                for b in self.botoes_dif:
                    if b.por_cima(mpos):
                        self.dificuldade = b.acao
                        return None
                for i, r in enumerate(self.rects_abas):
                    if r.collidepoint(mpos):
                        self.mudar_aba(i)
                        return None
                if self.btn_casa_prev.collidepoint(mpos):
                    self.mudar_casa(-1)
                elif self.btn_casa_next.collidepoint(mpos):
                    self.mudar_casa(1)
                elif self.btn_fora_prev.collidepoint(mpos):
                    self.mudar_fora(-1)
                elif self.btn_fora_next.collidepoint(mpos):
                    self.mudar_fora(1)

            for eq_id, idx, r in self.grid_rects:
                if r.collidepoint(mpos):
                    if event.button == 1:
                        self.escolher_casa(idx)     # clique esquerdo = casa
                    else:
                        self.escolher_fora(idx)     # clique direito = visitante
                    break
        return None

    def update(self, dt: float):
        self.anim_t += dt

    # ------------------------------------------------------------------ #
    # Desenho                                                            #
    # ------------------------------------------------------------------ #
    def draw(self):
        s = self.screen
        id_casa, id_fora = self.get_equipas()
        info_casa, info_fora = obter_info_equipa(id_casa), obter_info_equipa(id_fora)
        kit_casa, kit_fora = definir_equipamentos(id_casa, id_fora)
        mpos = pygame.mouse.get_pos()

        if self.arena is not None:
            # O pavilhão desfocado, com a luz das cores de cada equipa do seu lado
            s.blit(_fundo_arena(self.arena), (0, 0))
            for kit, x in ((kit_casa, 340), (kit_fora, WIDTH - 340)):
                halo = luz(620, 460, cor_visivel_em_escuro(kit["principal"], 110), 70)
                s.blit(halo, halo.get_rect(center=(x, 230)), special_flags=pygame.BLEND_RGB_ADD)
        else:
            fundo_menu(s, self.anim_t, kit_casa["principal"], kit_fora["principal"])

        # Cabeçalho
        texto(s, "SELEÇÃO DE EQUIPAS", 34, COR_TEXTO, (WIDTH // 2, 34), sombra=True)
        texto(s, "Escolhe a tua equipa e o adversário  •  as cores do equipamento e do ringue mudam com a escolha",
              14, COR_TEXTO_SUAVE, (WIDTH // 2, 68), negrito=False)
        self.btn_voltar.draw(s, mpos)

        # Cartões principais
        self._desenhar_card(self.rect_casa, "A TUA EQUIPA  •  CASA", info_casa, kit_casa,
                            self.btn_casa_prev, self.btn_casa_next, virar=False)
        self._desenhar_card(self.rect_fora, "ADVERSÁRIO  •  VISITANTE (IA)", info_fora, kit_fora,
                            self.btn_fora_prev, self.btn_fora_next, virar=True)

        # VS + pré-visualização do ringue
        self._desenhar_centro(info_casa)

        # Separadores e grelha
        for i, (r, (nome, equipas)) in enumerate(zip(self.rects_abas, COMPETICOES)):
            ativa = i == self.aba
            tem_escolhida = any(EQUIPAS_LISTA.index(e) in (self.casa_idx, self.fora_idx) for e in equipas)
            pygame.draw.rect(s, (40, 80, 150) if ativa else (20, 32, 62), r, border_radius=8)
            borda = (110, 170, 255) if ativa else ((90, 120, 190) if r.collidepoint(mpos) else (45, 70, 130))
            pygame.draw.rect(s, borda, r, 1, border_radius=8)
            texto(s, nome, 13, COR_TEXTO if ativa else COR_TEXTO_SUAVE, r.center)
            if tem_escolhida and not ativa:
                pygame.draw.circle(s, (255, 205, 60), (r.right - 10, r.top + 7), 4)   # há uma equipa escolhida aqui
        texto(s, "clique esquerdo = casa  •  direito = visitante", 11, (140, 170, 220),
              (self.rects_abas[-1].right + 16, self.rects_abas[-1].centery), ancora="midleft", negrito=False)
        for k, (eq_id, idx, r) in enumerate(self.grid_rects):
            self._desenhar_mini_card(eq_id, idx, r, mpos, k)

        # Dificuldade
        texto(s, "DIFICULDADE DA IA", 14, (200, 220, 255), (WIDTH // 2, 496))
        for b in self.botoes_dif:
            b.ativo = (b.acao == self.dificuldade)
            b.draw(s, mpos)
        desc = DIFICULDADES.get(self.dificuldade, {}).get("descricao", "")
        texto(s, desc, 13, (160, 195, 240), (WIDTH // 2, 568), negrito=False)

        # Botão principal (pulsa ligeiramente para chamar a atenção)
        self.btn_jogar.draw(s, mpos, focado=(math.sin(self.anim_t * 3) > 0.6))

        texto(s, "[A/D] casa   [W/S] visitante   [Q/E] divisão   [1-8] escolher casa   [TAB] dificuldade   "
                 "[ENTER] começar   [ESC] voltar",
              12, (110, 140, 190), (WIDTH // 2, 682), negrito=False)

    def _desenhar_card(self, rect, titulo, info, kit, btn_prev, btn_next, virar: bool):
        s = self.screen
        cor = info.get("cor_primaria", (20, 50, 120))
        mpos = pygame.mouse.get_pos()

        painel_vidro(s, rect, 12, 225, misturar(cor_visivel_em_escuro(cor), (255, 255, 255), 0.2))
        faixa_equipa(s, (rect.left, rect.top, rect.width, 38), cor)
        texto(s, titulo, 14, cor_texto_sobre(cor), (rect.centerx, rect.top + 19))

        # Emblema (esquerda) e jogador com o equipamento (direita)
        logo = carregar_logo_equipa(info["id"], (104, 104))
        if logo:
            s.blit(logo, logo.get_rect(center=(rect.left + 140, rect.top + 108)))
        cx_kit = rect.right - 140
        foco = luz(150, 46, (255, 240, 210), 90)
        s.blit(foco, foco.get_rect(center=(cx_kit, rect.top + 162)), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.ellipse(s, (6, 10, 22), (cx_kit - 34, rect.top + 156, 68, 12))
        jogador = sprite_equipamento(kit, 136, self.anim_t, virar=virar)
        s.blit(jogador, jogador.get_rect(midbottom=(cx_kit, rect.top + 166)))

        # Nome e detalhes
        texto(s, info["nome"], 24, COR_TEXTO, (rect.centerx, rect.top + 190))
        linha = f"{info['sigla']}   •   EQUIPAMENTO {'ALTERNATIVO' if kit['alternativo'] else 'PRINCIPAL'}"
        cor_linha = COR_DESTAQUE if kit["alternativo"] else (150, 185, 240)
        texto(s, linha, 12, cor_linha, (rect.centerx, rect.top + 216))

        # Amostras de cor: camisola e detalhes
        x0 = rect.centerx - 26
        amostra_cor(s, kit["principal"], (x0, rect.top + 228, 22, 14))
        amostra_cor(s, kit["secundaria"], (x0 + 30, rect.top + 228, 22, 14))

        for btn, seta in ((btn_prev, "◄"), (btn_next, "►")):
            hover = btn.collidepoint(mpos)
            pygame.draw.rect(s, (35, 65, 130) if hover else (22, 38, 76), btn, border_radius=8)
            pygame.draw.rect(s, (110, 160, 255) if hover else (45, 80, 160), btn, 1, border_radius=8)
            texto(s, seta, 18, (255, 255, 255), btn.center)

    def _desenhar_centro(self, info_casa):
        s = self.screen
        cx = WIDTH // 2
        cy = 150
        pulso = 1.0 + 0.05 * math.sin(self.anim_t * 4.0)
        raio = int(36 * pulso)
        pygame.draw.circle(s, (22, 38, 76), (cx, cy), raio + 5)
        pygame.draw.circle(s, COR_DESTAQUE, (cx, cy), raio, 3)
        texto(s, "VS", 30, (255, 225, 70), (cx, cy))

        # Mini ringue com as linhas na cor da equipa da casa
        r = pygame.Rect(cx - 78, 222, 156, 88)
        cor_l = cor_linhas_campo(info_casa.get("cor_primaria", (30, 95, 210)))
        pygame.draw.rect(s, (235, 238, 245), r.inflate(8, 8), border_radius=18)
        pygame.draw.rect(s, (224, 178, 122), r, border_radius=14)
        for y in range(r.top + 6, r.bottom, 8):
            pygame.draw.line(s, (210, 165, 110), (r.left + 6, y), (r.right - 6, y), 1)
        pygame.draw.line(s, cor_l, (r.centerx, r.top + 2), (r.centerx, r.bottom - 2), 2)
        pygame.draw.circle(s, cor_l, r.center, 16, 2)
        pygame.draw.rect(s, cor_l, (r.left + 14, r.centery - 24, 26, 48), 2)
        pygame.draw.rect(s, cor_l, (r.right - 40, r.centery - 24, 26, 48), 2)
        texto(s, "RINGUE DA CASA", 11, (170, 200, 255), (cx, r.bottom + 18))

    def _desenhar_mini_card(self, eq_id, idx, r, mpos, k: int = 0):
        s = self.screen
        info = obter_info_equipa(eq_id)
        e_casa, e_fora = idx == self.casa_idx, idx == self.fora_idx
        hover = r.collidepoint(mpos)

        if e_casa:
            bg, borda, bw = (20, 50, 110), (80, 170, 255), 3
        elif e_fora:
            bg, borda, bw = (80, 20, 30), (255, 90, 100), 3
        elif hover:
            bg, borda, bw = (25, 40, 75), (140, 190, 255), 2
        else:
            bg, borda, bw = None, (45, 70, 120), 1

        sobe = -3 if hover else 0
        rr = r.move(0, sobe)
        if bg is None:
            painel_vidro(s, rr, 10, 215, borda)
        else:
            pygame.draw.rect(s, bg, rr, border_radius=10)
            if e_casa or e_fora:
                brilho = luz(rr.width + 40, rr.height + 30, borda, 60)
                s.blit(brilho, brilho.get_rect(center=rr.center), special_flags=pygame.BLEND_RGB_ADD)
        # Faixa inferior com as cores do clube
        cor_p, cor_s = info.get("cor_primaria", (40, 40, 40)), info.get("cor_secundaria", (255, 255, 255))
        pygame.draw.rect(s, cor_p, (rr.left + 10, rr.bottom - 7, rr.width // 2 - 10, 3))
        pygame.draw.rect(s, cor_s, (rr.centerx, rr.bottom - 7, rr.width // 2 - 10, 3))
        pygame.draw.rect(s, borda, rr, bw, border_radius=10)

        logo = carregar_logo_equipa(eq_id, (42, 42))
        if logo:
            s.blit(logo, logo.get_rect(center=(rr.centerx, rr.top + 28)))
        texto(s, info["sigla"], 12, (255, 255, 255), (rr.centerx, rr.bottom - 32))

        if e_casa:
            etiqueta, cor_et = "CASA", (110, 200, 255)
        elif e_fora:
            etiqueta, cor_et = "FORA", (255, 130, 130)
        else:
            etiqueta, cor_et = f"#{k + 1}", (90, 120, 170)
        texto(s, etiqueta, 11, cor_et, (rr.centerx, rr.bottom - 17))


# ====================================================================== #
# Menu de Pausa                                                          #
# ====================================================================== #

class MenuPausa:
    """
    Pausa: o jogo fica desfocado por trás, com um painel de vidro, o resultado e o tempo
    num marcador pequeno e botões grandes com ícones (os mesmos do menu principal).
    """

    def __init__(self, screen: pygame.Surface, modo_carreira: bool = False, modo_teste: bool = False,
                 modo_online: bool = False):
        self.screen = screen
        self.t = 0.0
        self.modo_carreira = modo_carreira
        self.modo_teste = modo_teste
        self.modo_online = modo_online
        self._fundo = None                     # imagem desfocada do jogo (feita no primeiro desenho)
        if modo_online:
            # Online o jogo não pára (o outro jogador continua a jogar): só se pode voltar ou sair
            itens = [("CONTINUAR", "continuar", (40, 190, 100), "jogar"),
                     ("ABANDONAR O JOGO", "menu", (150, 110, 255), "casa"),
                     ("SAIR DO JOGO", "sair", (230, 70, 70), "sair")]
        elif modo_teste:
            itens = [("CONTINUAR", "continuar", (40, 190, 100), "jogar"),
                     ("DEFINIÇÕES", "controlos", (50, 140, 255), "engrenagem"),
                     ("MENU PRINCIPAL", "menu", (150, 110, 255), "casa"),
                     ("SAIR DO JOGO", "sair", (230, 70, 70), "sair")]
        elif modo_carreira:
            # No modo carreira não há "reiniciar": desistir volta ao campeonato e o jogo não conta
            itens = [("CONTINUAR", "continuar", (40, 190, 100), "jogar"),
                     ("DEFINIÇÕES", "controlos", (50, 140, 255), "engrenagem"),
                     ("DESISTIR DO JOGO", "desistir", (255, 180, 40), "recomecar"),
                     ("MENU PRINCIPAL", "menu", (150, 110, 255), "casa"),
                     ("SAIR DO JOGO", "sair", (230, 70, 70), "sair")]
        else:
            itens = [("CONTINUAR", "continuar", (40, 190, 100), "jogar"),
                     ("REINICIAR PARTIDA", "reiniciar", (255, 180, 40), "recomecar"),
                     ("DEFINIÇÕES", "controlos", (50, 140, 255), "engrenagem"),
                     ("MENU PRINCIPAL", "menu", (150, 110, 255), "casa"),
                     ("SAIR DO JOGO", "sair", (230, 70, 70), "sair")]
        n = len(itens)
        # No modo teste não há estatísticas da partida (só os remates, que já aparecem em cima)
        self.com_stats = not modo_teste
        extra = 104 if self.com_stats else 0
        altura = 178 + extra + n * 58
        self.caixa = pygame.Rect(WIDTH // 2 - 230, (HEIGHT - altura) // 2 - 10, 460, altura)
        y0 = self.caixa.top + 164 + extra
        self.lista = ListaBotoes([BotaoMenu((WIDTH // 2 - 195, y0 + i * 58, 390, 50), titulo, "", acao, cor, ic,
                                            seta=(i == 0), tamanho=19)
                                  for i, (titulo, acao, cor, ic) in enumerate(itens)])
        self._titulo = titulo_estilizado("PAUSA", fontes.SysFont("Arial Black", 44), (255, 255, 255),
                                         (170, 200, 255), contorno=4)

    def handle_event(self, event) -> str | None:
        if event.type == pygame.QUIT:
            return "sair"
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
            return "continuar"
        return self.lista.handle_event(event)

    def update(self, dt: float):
        self.t += dt
        for i, b in enumerate(self.lista.botoes):
            b.animar(dt, i == self.lista.foco)

    def draw(self, game):
        s = self.screen
        if self.modo_online:
            # O jogo continua por trás: desfoca-se o frame atual (não uma imagem parada)
            escurecer_ecra(s, 150)
        else:
            if self._fundo is None:
                self._fundo = fundo_desfocado(s)
            s.blit(self._fundo, (0, 0))
        caixa = self.caixa
        painel_vidro(s, caixa, 20, 238, (90, 130, 210))
        s.blit(self._titulo, self._titulo.get_rect(center=(WIDTH // 2, caixa.top + 46)))

        # Marcador pequeno: emblemas, resultado e tempo
        info_c = obter_info_equipa(game.equipa_casa_id)
        info_f = obter_info_equipa(game.equipa_fora_id)
        pilula = pygame.Rect(0, 0, 330, 46)
        pilula.center = (WIDTH // 2, caixa.top + 104)
        pygame.draw.rect(s, (8, 12, 26), pilula, border_radius=23)
        pygame.draw.rect(s, (70, 100, 160), pilula, 1, border_radius=23)
        for eq, x in ((game.equipa_casa_id, pilula.left + 28), (game.equipa_fora_id, pilula.right - 28)):
            logo = carregar_logo_equipa(eq, (32, 32))
            if logo:
                s.blit(logo, logo.get_rect(center=(x, pilula.centery)))
        if self.modo_teste:
            t = game.teste
            pct = round(100 * t["golos"] / t["remates"]) if t["remates"] else 0
            texto(s, f"{t['golos']} golos  /  {t['remates']} remates", 17, COR_DESTAQUE, pilula.center)
            texto(s, f"MODO TESTE  •  {pct}% de golos  •  defesas {t['defesas']}  •  fora/poste {t['fora']}", 12,
                  COR_TEXTO_SUAVE, (WIDTH // 2, caixa.top + 140), negrito=False)
        else:
            mins, segs = divmod(max(0, int(game.tempo_restante)), 60)
            texto(s, f"{info_c['sigla']}   {game.golos_azul}  -  {game.golos_vermelho}   {info_f['sigla']}", 19,
                  (255, 255, 255), pilula.center)
            texto(s, f"{game.parte}.ª parte  •  faltam {mins:02d}:{segs:02d}", 12, COR_TEXTO_SUAVE,
                  (WIDTH // 2, caixa.top + 140), negrito=False)
        if self.com_stats:
            pygame.draw.line(s, (45, 65, 115), (caixa.left + 40, caixa.top + 156), (caixa.right - 40, caixa.top + 156))
            desenhar_estatisticas(s, game, WIDTH // 2, caixa.top + 172, 300, 23)

        self.lista.draw(s)
        if self.modo_carreira:
            texto(s, "Se desistires, o jogo não conta e podes jogá-lo outra vez.", 12, COR_TEXTO_SUAVE,
                  (WIDTH // 2, caixa.bottom + 18), negrito=False)
        elif self.modo_online:
            texto(s, "Jogo online: o jogo não pára enquanto estás neste menu.", 12, COR_TEXTO_SUAVE,
                  (WIDTH // 2, caixa.bottom + 18), negrito=False)
        texto(s, "↑ ↓  escolher     ENTER  confirmar     ESC  continuar", 12, (120, 145, 195),
              (WIDTH // 2, HEIGHT - 22), negrito=False)


# ====================================================================== #
# Fim de Jogo                                                            #
# ====================================================================== #

class EcraFimJogo:
    """
    Fim do jogo: o jogo desfocado por trás, cada equipa do seu lado com as suas cores,
    o resultado ao centro, "VENCEDOR" por cima de quem ganhou e confetes quando ganhas.
    """

    def __init__(self, screen: pygame.Surface, modo_carreira: bool = False, jornada: int | None = None,
                 jogador: dict | None = None, online: str | None = None):
        self.screen = screen
        self.t = 0.0
        self.modo_carreira = modo_carreira
        self.jornada = jornada
        self.jogador = jogador          # carreira de jogador: {"nome", "nota", "golos", "assistencias", ...}
        self.online = online            # None, "anfitriao" ou "convidado"
        self._fundo = None
        self._confetes = None
        self.caixa = pygame.Rect(WIDTH // 2 - 460, 62, 920, 586)
        y, bh = self.caixa.bottom - 84, 58
        cx = WIDTH // 2
        if online == "convidado":
            # Quem decide se se joga outra vez é o anfitrião; o convidado só pode sair
            self.lista = ListaBotoes([
                BotaoMenu((cx - 210, y, 420, bh), "SAIR DO JOGO ONLINE", "", "menu", (150, 110, 255), "casa",
                          seta=False, tamanho=19)])
        elif modo_carreira:
            # O resultado conta para o campeonato: só se pode continuar
            self.lista = ListaBotoes([
                BotaoMenu((cx - 210, y, 420, bh), "CONTINUAR", f"O resultado conta  •  {jornada}",
                          "continuar", (40, 190, 100), "jogar")])
        else:
            bw = 270
            self.lista = ListaBotoes([
                BotaoMenu((cx - bw - bw // 2 - 14, y, bw, bh), "JOGAR DE NOVO", "", "reiniciar", (40, 190, 100),
                          "recomecar", seta=False, tamanho=19),
                BotaoMenu((cx - bw // 2, y, bw, bh), "MUDAR EQUIPAS", "", "equipas", (50, 140, 255), "jogador",
                          seta=False, tamanho=19),
                BotaoMenu((cx + bw // 2 + 14, y, bw, bh), "MENU PRINCIPAL", "", "menu", (150, 110, 255), "casa",
                          seta=False, tamanho=19),
            ])
        self._titulo = titulo_estilizado("FIM DO JOGO", fontes.SysFont("Arial Black", 46), (255, 255, 255),
                                         (170, 200, 255), contorno=4)

    def handle_event(self, event) -> str | None:
        if event.type == pygame.QUIT:
            return "sair"
        if event.type == pygame.KEYDOWN and self.online == "convidado":
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                return "menu"
            return None
        if event.type == pygame.KEYDOWN and self.modo_carreira:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_ESCAPE):
                return "continuar"
            return None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                return "reiniciar"
            if event.key == pygame.K_ESCAPE:
                return "menu"
            # Botões estão lado a lado: esquerda/direita também navegam
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.lista.foco = (self.lista.foco - 1) % len(self.lista.botoes)
                return None
            if event.key in (pygame.K_RIGHT, pygame.K_d):
                self.lista.foco = (self.lista.foco + 1) % len(self.lista.botoes)
                return None
        return self.lista.handle_event(event)

    def update(self, dt: float):
        self.t += dt
        for i, b in enumerate(self.lista.botoes):
            b.animar(dt, i == self.lista.foco)
        if self._confetes:
            for c in self._confetes:
                c[1] += c[2] * dt
                c[0] += math.sin(self.t * 2 + c[4]) * 30 * dt
                if c[1] > HEIGHT + 10:
                    c[1] = -10

    def _criar_confetes(self, cores):
        rnd = random.Random(5)
        self._confetes = [[rnd.uniform(0, WIDTH), rnd.uniform(-HEIGHT, 0), rnd.uniform(60, 150),
                           rnd.choice(cores), rnd.uniform(0, 6.3), rnd.choice((6, 8, 10))] for _ in range(120)]

    def _lado(self, s, game, equipa, info, kit, cx, virar, venceu, perdeu):
        caixa = self.caixa
        cor = kit["principal"]
        zona = pygame.Rect(0, 0, 320, 330)
        zona.center = (cx, caixa.top + 268)
        # Luz com a cor da equipa por trás (mais forte em quem ganhou)
        halo = luz(420, 380, cor_visivel_em_escuro(cor, 120), 130 if venceu else 80)
        s.blit(halo, halo.get_rect(center=zona.center), special_flags=pygame.BLEND_RGB_ADD)
        if venceu:
            fita = pygame.Rect(0, 0, 150, 30)
            fita.center = (cx, caixa.top + 128)
            pygame.draw.rect(s, COR_DESTAQUE, fita, border_radius=15)
            texto(s, "VENCEDOR", 15, (30, 22, 5), fita.center)
        logo = carregar_logo_equipa(info["id"], (118, 118))
        dx = -48 if not virar else 48
        if logo:
            s.blit(logo, logo.get_rect(center=(cx + dx, caixa.top + 220)))
        pygame.draw.ellipse(s, (4, 6, 14), (cx - dx - 34, caixa.top + 272, 68, 12))
        jog = sprite_equipamento(kit, 140, self.t, virar=virar)
        s.blit(jog, jog.get_rect(midbottom=(cx - dx, caixa.top + 280)))
        texto(s, info["nome"], 24, COR_TEXTO, (cx, caixa.top + 312), sombra=True)
        # Marcadores da equipa (nome e minuto), os golos do mesmo jogador juntos
        por_jogador = {}
        for m in getattr(game, "marcadores", []):
            if m["equipa"] == equipa:
                por_jogador.setdefault(m["nome"] or "Golo", []).append(f"{m['minuto']}'")
        for k, (nome, minutos) in enumerate(list(por_jogador.items())[:4]):
            texto(s, f"{nome}  {', '.join(minutos)}", 13, COR_TEXTO_SUAVE, (cx, caixa.top + 340 + k * 19),
                  negrito=False)
        if perdeu:
            # Quem perdeu fica um pouco mais escuro
            zona_s = pygame.Rect(0, 0, 330, 290)
            zona_s.center = (cx, caixa.top + 262)
            sombra = pygame.Surface(zona_s.size, pygame.SRCALPHA)
            pygame.draw.rect(sombra, (5, 8, 20, 60), sombra.get_rect(), border_radius=24)
            s.blit(sombra, zona_s)

    def draw(self, game):
        s = self.screen
        if self._fundo is None:
            self._fundo = fundo_desfocado(s, 120)
            # Confetes quando ganhas (online, o convidado joga com a equipa de fora)
            if self.online == "convidado":
                ganhei, kit = game.golos_vermelho > game.golos_azul, game.kit_fora
            else:
                ganhei, kit = game.golos_azul > game.golos_vermelho, game.kit_casa
            if ganhei:
                self._criar_confetes([kit["principal"], kit["secundaria"], COR_DESTAQUE, (255, 255, 255)])
        s.blit(self._fundo, (0, 0))
        caixa = self.caixa
        painel_vidro(s, caixa, 22, 236, (90, 130, 210))
        s.blit(self._titulo, self._titulo.get_rect(center=(WIDTH // 2, caixa.top + 46)))

        info_c = obter_info_equipa(game.equipa_casa_id)
        info_f = obter_info_equipa(game.equipa_fora_id)
        kit_c, kit_f = game.kit_casa, game.kit_fora
        ga, gv = game.golos_azul, game.golos_vermelho
        self._lado(s, game, "azul", info_c, kit_c, caixa.left + 200, False, ga > gv, ga < gv)
        self._lado(s, game, "vermelho", info_f, kit_f, caixa.right - 200, True, gv > ga, gv < ga)

        # Resultado ao centro, com um brilho por trás
        brilho = luz(300, 200, (120, 160, 255), 60)
        s.blit(brilho, brilho.get_rect(center=(WIDTH // 2, caixa.top + 228)), special_flags=pygame.BLEND_RGB_ADD)
        texto(s, f"{ga}", 78, (255, 255, 255), (WIDTH // 2 - 62, caixa.top + 222), sombra=True)
        texto(s, "-", 60, COR_TEXTO_SUAVE, (WIDTH // 2, caixa.top + 218))
        texto(s, f"{gv}", 78, (255, 255, 255), (WIDTH // 2 + 62, caixa.top + 222), sombra=True)

        if ga > gv:
            msg, cor = f"VITÓRIA DO {info_c['nome'].upper()}!", cor_visivel_em_escuro(kit_c["principal"], 140)
        elif gv > ga:
            msg, cor = f"VITÓRIA DO {info_f['nome'].upper()}!", cor_visivel_em_escuro(kit_f["principal"], 140)
        else:
            msg, cor = "EMPATE!", COR_DESTAQUE
        texto(s, msg, 28, cor, (WIDTH // 2, caixa.top + 442), sombra=True)
        # Estatísticas da partida entre as duas equipas
        desenhar_estatisticas(s, game, WIDTH // 2, caixa.top + 300, 172, 29)

        if self.jogador:
            j = self.jogador
            from carreira_jogador_menu import cor_nota
            nota = f"{j['nota']:.1f}".replace(".", ",")
            linha = (f"{j['nome']}  •  NOTA {nota}  •  {j['golos']} golo(s)  •  "
                     f"{j['assistencias']} assist.  •  {j['passes']} passes certos")
            pil = pygame.Rect(0, 0, fonte(15).size(linha)[0] + 40, 32)
            pil.center = (WIDTH // 2, caixa.top + 96)
            pygame.draw.rect(s, (8, 12, 26), pil, border_radius=16)
            pygame.draw.rect(s, cor_nota(j["nota"]), pil, 2, border_radius=16)
            texto(s, linha, 15, cor_nota(j["nota"]), pil.center)
        elif self.modo_carreira:
            texto(s, f"MODO CARREIRA  •  {self.jornada}", 14, COR_DESTAQUE, (WIDTH // 2, caixa.top + 96))
        elif self.online:
            pontos = "." * (1 + int(self.t * 2) % 3)
            msg = (f"JOGO ONLINE  •  à espera que o anfitrião recomece{pontos}" if self.online == "convidado"
                   else "JOGO ONLINE  •  escolhe se jogam outra vez")
            texto(s, msg, 14, COR_DESTAQUE, (WIDTH // 2, caixa.top + 96))

        self.lista.draw(s)
        if self.online == "convidado":
            dica = "ENTER  sair do jogo online"
        elif self.modo_carreira:
            dica = "ENTER  continuar"
        else:
            dica = "← →  escolher     ENTER  confirmar     R  jogar de novo     ESC  menu principal"
        texto(s, dica, 12, (120, 145, 195), (WIDTH // 2, HEIGHT - 22), negrito=False)
        if self._confetes:
            for x, y, _v, cor, fase, tam in self._confetes:
                larg = max(2, abs(round(tam * math.cos(self.t * 5 + fase))))
                pygame.draw.rect(s, cor, (int(x), int(y), larg, tam))
