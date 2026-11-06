# -*- coding: utf-8 -*-
"""online_menu.py - ecrã "Jogar online": criar um jogo (anfitrião) ou entrar num (convidado).

O ecrã só mostra e devolve ações; quem abre a ligação é o Game (ver online.py).
Fases do ecrã:
  "inicio"   escolher entre criar e entrar
  "criar"    anfitrião à espera do adversário (mostra o endereço deste PC)
  "entrar"   escrever o endereço do anfitrião
  "a_ligar"  convidado a ligar-se
  "espera"   convidado ligado, à espera que o anfitrião escolha as equipas
"""
import math

import pygame

from settings import WIDTH, HEIGHT
from componentes import texto, ListaBotoes, painel_vidro, COR_DESTAQUE, COR_TEXTO, COR_TEXTO_SUAVE
from graficos import luz, icone
from menu import BotaoMenu, _fundo_arena
from rede import PORTA

COR_ONLINE = (40, 200, 210)


class EcraOnline:
    def __init__(self, screen: pygame.Surface, arena=None, endereco: str = "", erro: str = ""):
        self.screen = screen
        self.arena = arena
        self.t = 0.0
        self.endereco = endereco          # o último endereço escrito (fica guardado)
        self.enderecos = []               # endereços deste PC (fase "criar")
        self.erro = erro
        self.caixa = pygame.Rect(WIDTH // 2 - 380, 150, 760, 440)
        self.r_campo = pygame.Rect(self.caixa.left + 50, self.caixa.top + 150, self.caixa.width - 100, 64)
        self.mudar_fase("inicio")

    # ------------------------------------------------------------------ #
    def mudar_fase(self, fase: str):
        self.fase = fase
        cx, base = WIDTH // 2, self.caixa.bottom - 80
        if fase == "inicio":
            x, bw = cx - 260, 520
            self.lista = ListaBotoes([
                BotaoMenu((x, self.caixa.top + 120, bw, 64), "CRIAR JOGO",
                          "Ficas à espera e o teu amigo liga-se a ti", "criar", (40, 190, 100), "casa"),
                BotaoMenu((x, self.caixa.top + 200, bw, 64), "ENTRAR NUM JOGO",
                          "Escreve o endereço do computador do teu amigo", "entrar", COR_ONLINE, "globo"),
                BotaoMenu((cx - 140, base, 280, 50), "VOLTAR", "", "voltar", (150, 110, 255), "casa",
                          seta=False, tamanho=18),
            ])
        elif fase == "entrar":
            self.lista = ListaBotoes([
                BotaoMenu((cx - 290, base, 280, 54), "LIGAR", "", "ligar", (40, 190, 100), "jogar",
                          seta=False, tamanho=20),
                BotaoMenu((cx + 10, base, 280, 54), "VOLTAR", "", "cancelar", (150, 110, 255), "casa",
                          seta=False, tamanho=18),
            ])
        else:   # criar, a_ligar, espera: só se pode cancelar
            self.lista = ListaBotoes([
                BotaoMenu((cx - 140, base, 280, 52), "CANCELAR", "", "cancelar", (230, 70, 70), "sair",
                          seta=False, tamanho=18),
            ])
        try:
            if fase == "entrar":
                pygame.key.start_text_input()
            else:
                pygame.key.stop_text_input()
        except pygame.error:
            pass

    # ------------------------------------------------------------------ #
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return "sair"
        if self.fase == "entrar":
            if event.type == pygame.TEXTINPUT:
                if len(self.endereco) < 60:
                    self.endereco += "".join(c for c in event.text if c.isprintable() and c != " ")
                    self.erro = ""
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    self.endereco = self.endereco[:-1]
                    return None
                if event.key == pygame.K_v and event.mod & pygame.KMOD_CTRL:
                    self._colar()
                    return None
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return ("ligar", self.endereco.strip())
                if event.key == pygame.K_ESCAPE:
                    return "cancelar"
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                    self.lista.foco = 1 - self.lista.foco
                    return None
                # As outras teclas (letras, números) são para o campo de texto, não para os botões
                if event.key not in (pygame.K_TAB,):
                    return None
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "voltar" if self.fase == "inicio" else "cancelar"
        acao = self.lista.handle_event(event)
        if acao == "ligar":
            return ("ligar", self.endereco.strip())
        return acao

    def _colar(self):
        """CTRL+V: cola o endereço que o amigo mandou (por exemplo pelo WhatsApp/Discord)."""
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            dados = pygame.scrap.get_text() or ""
        except (pygame.error, AttributeError, NotImplementedError):
            return
        dados = "".join(c for c in dados.strip() if c.isprintable() and c != " ")
        self.endereco = (self.endereco + dados)[:60]

    def update(self, dt: float):
        self.t += dt
        for i, b in enumerate(self.lista.botoes):
            b.animar(dt, i == self.lista.foco)

    # ------------------------------------------------------------------ #
    def draw(self):
        s = self.screen
        s.blit(_fundo_arena(self.arena), (0, 0))
        brilho = luz(900, 520, COR_ONLINE, 45)
        s.blit(brilho, brilho.get_rect(center=(WIDTH // 2, 360)), special_flags=pygame.BLEND_RGB_ADD)

        ic = icone("globo", 46, COR_ONLINE)
        s.blit(ic, ic.get_rect(center=(WIDTH // 2, 58)))
        texto(s, "JOGAR ONLINE", 36, COR_TEXTO, (WIDTH // 2, 108), sombra=True)

        caixa = self.caixa
        painel_vidro(s, caixa, 20, 230, (60, 130, 160))
        getattr(self, "_desenhar_" + self.fase)(s, caixa)
        self.lista.draw(s)

        if self.erro:
            texto(s, self.erro, 15, (255, 110, 100), (WIDTH // 2, caixa.bottom + 24))
        dicas = {"entrar": "Escreve o endereço     CTRL+V  colar     ENTER  ligar     ESC  voltar",
                 "inicio": "↑ ↓  escolher     ENTER  confirmar     ESC  voltar"}
        texto(s, dicas.get(self.fase, "ESC  cancelar"), 12, (120, 145, 195), (WIDTH // 2, HEIGHT - 22),
              negrito=False)

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

    def _desenhar_inicio(self, s, caixa):
        texto(s, "Joga contra um amigo noutro computador", 20, COR_DESTAQUE, (WIDTH // 2, caixa.top + 40))
        texto(s, "Um cria o jogo (joga com a equipa da casa) e o outro entra (joga com a equipa de fora).",
              14, COR_TEXTO_SUAVE, (WIDTH // 2, caixa.top + 74), negrito=False)
        linhas = ["Na mesma rede (casa, escola): basta o endereço que aparece a quem cria o jogo.",
                  "Pela internet: instalem os dois o Radmin VPN e entrem na mesma rede (ver o README)."]
        for i, l in enumerate(linhas):
            texto(s, l, 13, (150, 175, 215), (WIDTH // 2, caixa.top + 300 + i * 22), negrito=False)

    def _desenhar_criar(self, s, caixa):
        texto(s, "À espera do adversário" + self._pontos(), 24, COR_DESTAQUE, (WIDTH // 2, caixa.top + 42))
        self._roda(s, (WIDTH // 2, caixa.top + 92))
        texto(s, "Diz ao teu amigo para escrever este endereço em «ENTRAR NUM JOGO»:", 14, COR_TEXTO_SUAVE,
              (WIDTH // 2, caixa.top + 142), negrito=False)
        y = caixa.top + 186
        for i, ip in enumerate(self.enderecos[:3]):
            vpn = ip.startswith(("26.", "100."))
            if i == 0:
                r = pygame.Rect(0, 0, 420, 54)
                r.center = (WIDTH // 2, y)
                pygame.draw.rect(s, (8, 14, 30), r, border_radius=14)
                pygame.draw.rect(s, COR_ONLINE, r, 2, border_radius=14)
                texto(s, ip, 30, (255, 255, 255), r.center)
                nota = "rede VPN (internet)" if vpn else "rede local"
                texto(s, nota, 12, COR_ONLINE, (r.right + 12, r.centery), ancora="midleft", negrito=False)
                y += 50
            else:
                nota = "  (VPN)" if vpn else ""
                texto(s, f"ou  {ip}{nota}", 16, (200, 215, 240), (WIDTH // 2, y))
                y += 26
        texto(s, f"Porta {PORTA}  •  se o firewall do Windows perguntar, carrega em «Permitir».", 13,
              (150, 175, 215), (WIDTH // 2, caixa.bottom - 108), negrito=False)

    def _desenhar_entrar(self, s, caixa):
        texto(s, "Endereço do anfitrião", 20, COR_DESTAQUE, (WIDTH // 2, caixa.top + 42))
        texto(s, "É o número que aparece no ecrã de quem criou o jogo (por exemplo 26.12.34.56).", 14,
              COR_TEXTO_SUAVE, (WIDTH // 2, caixa.top + 76), negrito=False)
        texto(s, "Se usarem um túnel (ex.: playit.gg), escreve endereço:porta.", 13, (150, 175, 215),
              (WIDTH // 2, caixa.top + 102), negrito=False)
        r = self.r_campo
        pygame.draw.rect(s, (8, 14, 30), r, border_radius=14)
        pygame.draw.rect(s, COR_ONLINE, r, 2, border_radius=14)
        cursor = "|" if int(self.t * 2) % 2 == 0 else " "
        if self.endereco:
            texto(s, self.endereco + cursor, 28, (255, 255, 255), (r.left + 22, r.centery), ancora="midleft")
        else:
            texto(s, "ex.: 26.12.34.56" + cursor, 24, (100, 120, 165), (r.left + 22, r.centery),
                  ancora="midleft", negrito=False)

    def _desenhar_a_ligar(self, s, caixa):
        texto(s, "A ligar" + self._pontos(), 26, COR_DESTAQUE, (WIDTH // 2, caixa.top + 60))
        self._roda(s, (WIDTH // 2, caixa.top + 150))
        texto(s, self.endereco, 18, (220, 230, 250), (WIDTH // 2, caixa.top + 220))

    def _desenhar_espera(self, s, caixa):
        ok = icone("jogar", 40, (40, 210, 110))
        pygame.draw.circle(s, (12, 40, 30), (WIDTH // 2, caixa.top + 90), 40)
        pygame.draw.circle(s, (40, 210, 110), (WIDTH // 2, caixa.top + 90), 40, 3)
        s.blit(ok, ok.get_rect(center=(WIDTH // 2 + 3, caixa.top + 90)))
        texto(s, "Ligado!", 30, (90, 230, 140), (WIDTH // 2, caixa.top + 168))
        texto(s, "O anfitrião está a escolher as equipas" + self._pontos(), 18, COR_TEXTO,
              (WIDTH // 2, caixa.top + 214))
        texto(s, "Vais jogar com a equipa de fora, que começa do lado esquerdo do campo.", 14, COR_TEXTO_SUAVE,
              (WIDTH // 2, caixa.top + 250), negrito=False)
