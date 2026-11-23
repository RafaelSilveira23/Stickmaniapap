# -*- coding: utf-8 -*-
"""online_menu.py - ecrã "Jogar online": jogo aleatório, criar uma sala privada ou entrar numa.

O ecrã só mostra e devolve ações; quem fala com o servidor é o Game (ver online.py).
Em cima mostra sempre quantas pessoas estão online e a jogar (o servidor envia de 2 em 2 s).
Fases do ecrã:
  "inicio"    escolher: JOGO ALEATÓRIO, CRIAR SALA PRIVADA ou ENTRAR NUMA SALA
  "procurar"  à procura de um adversário aleatório
  "criar"     sala privada criada: mostra o código para dar ao amigo
  "entrar"    escrever o código da sala do amigo
  "a_ligar"   a entrar na sala
  "espera"    emparelhado, à espera que o anfitrião comece o jogo
  "desafiar"  escrever a alcunha do amigo que se quer desafiar (precisa de conta)
  "desafio"   à espera que o amigo aceite
Se alguém nos desafia, aparece um aviso por cima (ENTER aceita, ESC recusa).
"""
import math

import pygame

from settings import WIDTH, HEIGHT
from componentes import texto, fonte, ListaBotoes, painel_vidro, COR_DESTAQUE, COR_TEXTO, COR_TEXTO_SUAVE
from graficos import luz, icone
from menu import BotaoMenu, _fundo_arena

COR_ONLINE = (40, 200, 210)
VERDE = (60, 220, 120)


class EcraOnline:
    def __init__(self, screen: pygame.Surface, arena=None, servidor=None, erro: str = ""):
        self.screen = screen
        self.arena = arena
        self.servidor = servidor          # rede.Servidor: contagens, estado e código da sala
        self.modo = None                  # "aleatorio" ou "privado" (fase "espera")
        self.t = 0.0
        self.codigo = ""                  # o código que se está a escrever (fase "entrar")
        self.alcunha = ""                 # a alcunha do amigo (fase "desafiar")
        self.desafiado = ""
        self.erro = erro
        self.caixa = pygame.Rect(WIDTH // 2 - 380, 168, 760, 440)
        self.mudar_fase("inicio")

    # ------------------------------------------------------------------ #
    def mudar_fase(self, fase: str):
        self.fase = fase
        self.t_fase = 0.0
        cx, base = WIDTH // 2, self.caixa.bottom - 76
        if fase == "inicio":
            x, bw = cx - 270, 540
            self.lista = ListaBotoes([
                BotaoMenu((x, self.caixa.top + 30, bw, 62), "JOGO ALEATÓRIO",
                          "Joga contra outra pessoa que esteja à procura de jogo", "aleatorio", VERDE, "globo"),
                BotaoMenu((x, self.caixa.top + 100, bw, 62), "CRIAR SALA PRIVADA",
                          "Recebes um código para dar ao teu amigo", "criar", (240, 170, 40), "casa"),
                BotaoMenu((x, self.caixa.top + 170, bw, 62), "ENTRAR NUMA SALA",
                          "Escreve o código da sala do teu amigo", "entrar", COR_ONLINE, "avancar"),
                BotaoMenu((x, self.caixa.top + 240, bw, 62), "DESAFIAR UM AMIGO",
                          "Pela alcunha da conta dele (os dois precisam de conta)", "desafiar", (255, 120, 160),
                          "jogador"),
                BotaoMenu((cx - 140, base, 280, 50), "VOLTAR", "", "voltar", (150, 110, 255), "casa",
                          seta=False, tamanho=18),
            ])
        elif fase == "desafiar":
            self.lista = ListaBotoes([
                BotaoMenu((cx - 290, base, 280, 54), "DESAFIAR", "", "desafiar_ok", (40, 190, 100), "jogar",
                          seta=False, tamanho=20),
                BotaoMenu((cx + 10, base, 280, 54), "VOLTAR", "", "cancelar", (150, 110, 255), "casa",
                          seta=False, tamanho=18),
            ])
        elif fase == "entrar":
            self.codigo = ""
            self.lista = ListaBotoes([
                BotaoMenu((cx - 290, base, 280, 54), "ENTRAR", "", "ligar", (40, 190, 100), "jogar",
                          seta=False, tamanho=20),
                BotaoMenu((cx + 10, base, 280, 54), "VOLTAR", "", "cancelar", (150, 110, 255), "casa",
                          seta=False, tamanho=18),
            ])
        else:   # procurar, criar, a_ligar, espera: só se pode cancelar
            self.lista = ListaBotoes([
                BotaoMenu((cx - 140, base, 280, 52), "CANCELAR", "", "cancelar", (230, 70, 70), "sair",
                          seta=False, tamanho=18),
            ])
        try:
            if fase in ("entrar", "desafiar"):
                pygame.key.start_text_input()
            else:
                pygame.key.stop_text_input()
        except pygame.error:
            pass

    # ------------------------------------------------------------------ #
    def _convite(self):
        srv = self.servidor
        if srv is not None and srv.convites and self.fase in ("inicio", "procurar", "criar", "desafiar"):
            return srv.convites[0]
        return None

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return "sair"
        convite = self._convite()
        if convite is not None:
            # Um amigo desafiou-nos: ENTER (ou A no comando) aceita, ESC (ou B) recusa
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    return ("aceitar", convite)
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return ("recusar", convite)
                return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                sim, nao = self._botoes_convite()
                if sim.collidepoint(event.pos):
                    return ("aceitar", convite)
                if nao.collidepoint(event.pos):
                    return ("recusar", convite)
                return None
            if event.type == pygame.TEXTINPUT:
                return None
        if self.fase == "desafiar":
            if event.type == pygame.TEXTINPUT:
                self.alcunha = (self.alcunha + event.text)[:16]
                self.erro = ""
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    self.alcunha = self.alcunha[:-1]
                    return None
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return ("desafiar_ok", self.alcunha)
                if event.key == pygame.K_ESCAPE:
                    return "cancelar"
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                    self.lista.foco = 1 - self.lista.foco
                    return None
                if event.key not in (pygame.K_TAB,):
                    return None
            acao = self.lista.handle_event(event)
            return ("desafiar_ok", self.alcunha) if acao == "desafiar_ok" else acao
        if self.fase == "entrar":
            if event.type == pygame.TEXTINPUT:
                # Código: 4 letras/números, sempre em maiúsculas
                novo = "".join(c for c in event.text.upper() if c.isalnum())
                self.codigo = (self.codigo + novo)[:4]
                self.erro = ""
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    self.codigo = self.codigo[:-1]
                    return None
                if event.key == pygame.K_v and event.mod & pygame.KMOD_CTRL:
                    self._colar()
                    return None
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return ("ligar", self.codigo)
                if event.key == pygame.K_ESCAPE:
                    return "cancelar"
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                    self.lista.foco = 1 - self.lista.foco
                    return None
                # As outras teclas (letras, números) são para o código, não para os botões
                if event.key not in (pygame.K_TAB,):
                    return None
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "voltar" if self.fase == "inicio" else "cancelar"
        acao = self.lista.handle_event(event)
        if acao == "ligar":
            return ("ligar", self.codigo)
        return acao

    def _colar(self):
        """CTRL+V: cola o código que o amigo mandou (por exemplo pelo WhatsApp ou pelo Discord)."""
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            dados = pygame.scrap.get_text() or ""
        except (pygame.error, AttributeError, NotImplementedError):
            return
        self.codigo = "".join(c for c in dados.upper() if c.isalnum())[:4]

    def update(self, dt: float):
        self.t += dt
        self.t_fase += dt
        for i, b in enumerate(self.lista.botoes):
            b.animar(dt, i == self.lista.foco)

    # ------------------------------------------------------------------ #
    def draw(self):
        s = self.screen
        s.blit(_fundo_arena(self.arena), (0, 0))
        brilho = luz(900, 520, COR_ONLINE, 45)
        s.blit(brilho, brilho.get_rect(center=(WIDTH // 2, 360)), special_flags=pygame.BLEND_RGB_ADD)

        ic = icone("globo", 42, COR_ONLINE)
        s.blit(ic, ic.get_rect(center=(WIDTH // 2, 46)))
        texto(s, "JOGAR ONLINE", 34, COR_TEXTO, (WIDTH // 2, 92), sombra=True)
        self._desenhar_contagem(s, (WIDTH // 2, 136))

        caixa = self.caixa
        painel_vidro(s, caixa, 20, 230, (60, 130, 160))
        getattr(self, "_desenhar_" + self.fase)(s, caixa)
        self.lista.draw(s)

        if self.erro:
            texto(s, self.erro, 15, (255, 110, 100), (WIDTH // 2, caixa.bottom + 24))
        convite = self._convite()
        if convite is not None:
            self._desenhar_convite(s, convite)
        dicas = {"entrar": "Escreve o código     CTRL+V  colar     ENTER  entrar     ESC  voltar",
                 "desafiar": "Escreve a alcunha     ENTER  desafiar     ESC  voltar",
                 "inicio": "↑ ↓  escolher     ENTER  confirmar     ESC  voltar"}
        texto(s, dicas.get(self.fase, "ESC  cancelar"), 12, (120, 145, 195), (WIDTH // 2, HEIGHT - 22),
              negrito=False)

    def _desenhar_contagem(self, s, centro):
        """«● 12 jogadores online  •  4 a jogar», ou o estado da ligação ao servidor."""
        srv = self.servidor
        if srv is None or srv.estado == "erro":
            cor, txt = (255, 110, 100), "Sem ligação ao servidor do jogo"
        elif srv.estado == "a_ligar" or srv.online is None:
            cor = (240, 200, 90)
            txt = ("A acordar o servidor do jogo (pode demorar até 1 minuto)" + self._pontos()
                   if srv.a_acordar() else "A ligar ao servidor" + self._pontos())
        else:
            cor = VERDE
            n = srv.online
            txt = f"{n} jogador{'es' if n != 1 else ''} online  •  {srv.a_jogar} a jogar"
        r = pygame.Rect(0, 0, fonte(15).size(txt)[0] + 56, 34)
        r.center = centro
        pygame.draw.rect(s, (8, 14, 30), r, border_radius=17)
        pygame.draw.rect(s, cor, r, 1, border_radius=17)
        # Ponto a "pulsar" quando há ligação
        k = 0.6 + 0.4 * math.sin(self.t * 4) if cor == VERDE else 1.0
        pygame.draw.circle(s, tuple(int(c * k) for c in cor), (r.left + 20, r.centery), 6)
        texto(s, txt, 15, cor if cor != VERDE else (220, 240, 230), (r.left + 36, r.centery), ancora="midleft")

    def _pontos(self) -> str:
        return "." * (1 + int(self.t * 2.5) % 3)

    def _roda(self, s, centro, cor=COR_ONLINE):
        """Animação de espera: 8 pontos em círculo, um mais aceso a rodar."""
        for i in range(8):
            k = ((i - self.t * 8) % 8) / 8          # 0 = o ponto mais aceso
            x = centro[0] + 22 * math.cos(i * math.pi / 4)
            y = centro[1] + 22 * math.sin(i * math.pi / 4)
            c = tuple(int(v * (0.3 + 0.7 * (1 - k))) for v in cor)
            pygame.draw.circle(s, c, (round(x), round(y)), 5)

    def _caixas_codigo(self, s, y, letras: str, cursor: bool = False):
        """As 4 letras do código em caixas grandes."""
        larg, esp = 86, 18
        x0 = WIDTH // 2 - (4 * larg + 3 * esp) // 2
        for i in range(4):
            r = pygame.Rect(x0 + i * (larg + esp), y, larg, 100)
            ativa = cursor and i == len(letras)
            pygame.draw.rect(s, (8, 14, 30), r, border_radius=16)
            pygame.draw.rect(s, COR_ONLINE if (ativa or i < len(letras)) else (60, 80, 120), r, 3,
                             border_radius=16)
            if i < len(letras):
                texto(s, letras[i], 64, (255, 255, 255), r.center)
            elif ativa and int(self.t * 2) % 2 == 0:
                pygame.draw.rect(s, COR_ONLINE, (r.centerx - 18, r.bottom - 26, 36, 5), border_radius=2)

    def _botoes_convite(self):
        return botoes_convite()

    def _desenhar_convite(self, s, nome: str):
        desenhar_convite(s, nome)

    # ------------------------------------------------------------------ fases

    # ------------------------------------------------------------------ fases
    def _desenhar_inicio(self, s, caixa):
        texto(s, "Quem cria a sala (ou estava há mais tempo à procura) joga com a equipa da casa.", 13,
              (150, 175, 215), (WIDTH // 2, caixa.top + 332), negrito=False)

    def _desenhar_desafiar(self, s, caixa):
        texto(s, "Alcunha do teu amigo", 22, COR_DESTAQUE, (WIDTH // 2, caixa.top + 42))
        texto(s, "O teu amigo tem de ter conta e o jogo aberto (o convite aparece-lhe no menu).", 14, COR_TEXTO_SUAVE,
              (WIDTH // 2, caixa.top + 78), negrito=False)
        r = pygame.Rect(0, 0, 440, 64)
        r.center = (WIDTH // 2, caixa.top + 170)
        pygame.draw.rect(s, (8, 14, 30), r, border_radius=14)
        pygame.draw.rect(s, (255, 120, 160), r, 3, border_radius=14)
        t = texto(s, self.alcunha, 30, (255, 255, 255), r.center) if self.alcunha else pygame.Rect(r.centerx, r.centery, 0, 0)
        if int(self.t * 2) % 2 == 0:
            pygame.draw.line(s, (255, 120, 160), (t.right + 4, r.centery - 16), (t.right + 4, r.centery + 16), 3)

    def _desenhar_desafio(self, s, caixa):
        texto(s, f"Desafiaste {self.desafiado}", 26, COR_DESTAQUE, (WIDTH // 2, caixa.top + 60))
        self._roda(s, (WIDTH // 2, caixa.top + 150), (255, 120, 160))
        texto(s, "À espera que aceite" + self._pontos(), 18, (220, 230, 250), (WIDTH // 2, caixa.top + 220))

    def _desenhar_procurar(self, s, caixa):
        texto(s, "À procura de adversário" + self._pontos(), 26, COR_DESTAQUE, (WIDTH // 2, caixa.top + 60))
        self._roda(s, (WIDTH // 2, caixa.top + 140), VERDE)
        srv = self.servidor
        segundos = int(self.t_fase)
        texto(s, f"{segundos // 60}:{segundos % 60:02d}", 20, (220, 230, 250), (WIDTH // 2, caixa.top + 200))
        if srv is not None and srv.online is not None:
            outros = max(0, srv.online - 1)
            if outros == 0:
                linha = "Ainda não há mais ninguém online. Convida um amigo ou cria uma sala privada."
            else:
                linha = f"Há mais {outros} pessoa{'s' if outros != 1 else ''} online. Quando alguém procurar jogo, começa logo."
            texto(s, linha, 14, COR_TEXTO_SUAVE, (WIDTH // 2, caixa.top + 250), negrito=False)
        texto(s, "Quando encontrares adversário, cada um escolhe a sua equipa.", 13, (150, 175, 215),
              (WIDTH // 2, caixa.top + 280), negrito=False)

    def _desenhar_criar(self, s, caixa):
        codigo = self.servidor.codigo if self.servidor is not None else None
        if not codigo:
            texto(s, "A criar a sala" + self._pontos(), 24, COR_DESTAQUE, (WIDTH // 2, caixa.top + 60))
            self._roda(s, (WIDTH // 2, caixa.top + 150))
            return
        texto(s, "Sala privada criada", 24, COR_DESTAQUE, (WIDTH // 2, caixa.top + 40))
        texto(s, "O teu amigo escolhe JOGAR ONLINE  →  ENTRAR NUMA SALA e escreve este código:", 14,
              COR_TEXTO_SUAVE, (WIDTH // 2, caixa.top + 80), negrito=False)
        self._caixas_codigo(s, caixa.top + 108, codigo)
        self._roda(s, (WIDTH // 2, caixa.top + 258), (120, 140, 180))
        texto(s, "À espera do teu amigo" + self._pontos(), 16, (200, 215, 240), (WIDTH // 2, caixa.top + 300))

    def _desenhar_entrar(self, s, caixa):
        texto(s, "Código da sala", 22, COR_DESTAQUE, (WIDTH // 2, caixa.top + 42))
        texto(s, "São as 4 letras que aparecem no ecrã de quem criou a sala (por exemplo K7QZ).", 14,
              COR_TEXTO_SUAVE, (WIDTH // 2, caixa.top + 78), negrito=False)
        self._caixas_codigo(s, caixa.top + 120, self.codigo, cursor=True)

    def _desenhar_a_ligar(self, s, caixa):
        texto(s, "A entrar na sala" + self._pontos(), 26, COR_DESTAQUE, (WIDTH // 2, caixa.top + 60))
        self._roda(s, (WIDTH // 2, caixa.top + 150))
        texto(s, self.codigo, 30, (220, 230, 250), (WIDTH // 2, caixa.top + 220))

    def _desenhar_espera(self, s, caixa):
        ok = icone("jogar", 40, (40, 210, 110))
        pygame.draw.circle(s, (12, 40, 30), (WIDTH // 2, caixa.top + 90), 40)
        pygame.draw.circle(s, (40, 210, 110), (WIDTH // 2, caixa.top + 90), 40, 3)
        s.blit(ok, ok.get_rect(center=(WIDTH // 2 + 3, caixa.top + 90)))
        adv = self.servidor.adversario if self.servidor is not None else None
        if self.modo == "desafio":
            texto(s, f"Desafio aceite{' (' + adv + ')' if adv else ''}!", 30, (90, 230, 140), (WIDTH // 2, caixa.top + 168))
            texto(s, "A abrir a escolha das equipas" + self._pontos(), 18, COR_TEXTO,
                  (WIDTH // 2, caixa.top + 214))
        elif self.modo == "aleatorio":
            texto(s, f"Adversário encontrado{': ' + adv if adv else ''}!", 30, (90, 230, 140), (WIDTH // 2, caixa.top + 168))
            texto(s, "O jogo vai começar" + self._pontos(), 18, COR_TEXTO, (WIDTH // 2, caixa.top + 214))
        else:
            texto(s, "Entraste na sala!", 30, (90, 230, 140), (WIDTH // 2, caixa.top + 168))
            texto(s, "A abrir a escolha das equipas" + self._pontos(), 18, COR_TEXTO,
                  (WIDTH // 2, caixa.top + 214))
        texto(s, "Vais jogar com a equipa de fora, que começa do lado esquerdo do campo.", 14, COR_TEXTO_SUAVE,
              (WIDTH // 2, caixa.top + 250), negrito=False)


# ---------------------------------------------------------------------- convite de um amigo
def botoes_convite():
    sim = pygame.Rect(0, 0, 220, 50)
    sim.center = (WIDTH // 2 - 125, 400)
    return sim, sim.move(250, 0)


def desenhar_convite(s, nome: str):
    """Janela «X desafia-te para um jogo!» (no ecrã JOGAR ONLINE e no menu principal)."""
    sombra = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    sombra.fill((0, 0, 0, 150))
    s.blit(sombra, (0, 0))
    caixa = pygame.Rect(0, 0, 580, 220)
    caixa.center = (WIDTH // 2, 340)
    pygame.draw.rect(s, (12, 20, 44), caixa, border_radius=16)
    pygame.draw.rect(s, (255, 120, 160), caixa, 2, border_radius=16)
    texto(s, f"{nome} desafia-te para um jogo!", 26, (255, 170, 200), (WIDTH // 2, caixa.top + 46), sombra=True)
    texto(s, "Conta para o ranking. Cada um escolhe a sua equipa.", 14, COR_TEXTO_SUAVE,
          (WIDTH // 2, caixa.top + 84), negrito=False)
    mpos = pygame.mouse.get_pos()
    for r, txt, cor in zip(botoes_convite(), ("ACEITAR", "RECUSAR"), ((40, 190, 100), (230, 70, 70))):
        pygame.draw.rect(s, cor if r.collidepoint(mpos) or txt == "ACEITAR" else (30, 40, 70), r, border_radius=12)
        pygame.draw.rect(s, (255, 255, 255), r, 2, border_radius=12)
        texto(s, txt, 18, (255, 255, 255), r.center)
    texto(s, "ENTER aceitar     ESC recusar", 12, (150, 170, 215), (WIDTH // 2, caixa.bottom - 18), negrito=False)
