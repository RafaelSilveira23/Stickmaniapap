# -*- coding: utf-8 -*-
"""carreira_jogador_menu.py - ecrãs da carreira de jogador.

  • EcraCriarJogador     - nome, número, posição e clube do jogador
  • EcraCarreiraJogador  - ficha do jogador (geral e atributos), próximo jogo, estatísticas da
                           época, classificação e, no fim da época, as propostas dos clubes

Como os outros menus: handle_event(event) -> ação, update(dt) e draw(). A classe Game decide.
"""
import math

import pygame

from settings import WIDTH, HEIGHT
from team import EQUIPAS_LISTA, obter_info_equipa, carregar_logo_equipa
from carreira import FORCA_EQUIPAS
from carreira_jogador import (POSICOES, NOME_POSICAO, GERAL_INICIAL, ATRIBUTOS, atributos)
from cores import kit_principal, misturar, cor_texto_sobre
from componentes import fonte, texto, sprite_equipamento, COR_DESTAQUE, COR_TEXTO, COR_TEXTO_SUAVE
from graficos import luz, icone
from menu import BotaoMenu, _fundo_arena
from carreira_menu import _vidro, _titulo_painel, _barra_forca
from sons import som

NOME_ATRIBUTO = {"velocidade": "VEL", "remate": "REM", "passe": "PAS", "defesa": "DEF"}
# Cor e ícone de cada tipo de evento da vida
CATEGORIA = {"hoquei": ((90, 200, 255), "jogar", "HÓQUEI"), "festa": ((255, 140, 190), "estrela", "AMIGOS"),
             "escola": ((120, 170, 255), "livro", "ESCOLA"), "dinheiro": ((110, 215, 140), "moeda", "DINHEIRO"),
             "familia": ((255, 185, 100), "casa", "FAMÍLIA"), "amor": ((255, 95, 130), "coracao", "AMOR"),
             "imprensa": ((255, 205, 60), "estrela", "FAMA"), "saude": ((240, 90, 90), "cruz", "SAÚDE")}
COR_PAPEL = {"mae": (255, 185, 100), "pai": (120, 170, 255), "amigo": (110, 215, 140), "namoro": (255, 95, 130)}
DESCRICAO_POSICAO = {"avancado": "Marca golos. Remate forte.",
                     "medio": "Liga o jogo. Passe certeiro.",
                     "defesa": "Recupera bolas. Duro a defender."}


def cor_nota(nota) -> tuple:
    """Vermelho (nota baixa) -> amarelo -> verde (nota alta)."""
    if nota is None:
        return (120, 135, 170)
    t = max(0.0, min(1.0, (nota - 5.0) / 3.0))
    return misturar((230, 80, 70), (90, 215, 120), t) if t > 0.5 else misturar((230, 80, 70), (240, 200, 70), t * 2)


def _barras_atributos(s, x, y, w, attrs, passo=30):
    for i, a in enumerate(ATRIBUTOS):
        v = attrs[a]
        yy = y + i * passo
        texto(s, NOME_ATRIBUTO[a], 13, COR_TEXTO_SUAVE, (x, yy), ancora="midleft")
        texto(s, str(v), 15, COR_TEXTO, (x + w, yy), ancora="midright")
        barra = pygame.Rect(x + 44, yy - 4, w - 84, 8)
        pygame.draw.rect(s, (25, 35, 65), barra, border_radius=4)
        t = max(0.0, min(1.0, (v - 40) / 59))
        pygame.draw.rect(s, misturar((230, 120, 60), (90, 215, 120), t),
                         (barra.x, barra.y, max(8, round(barra.w * t)), 8), border_radius=4)


def _circulo_geral(s, centro, geral, raio=42, t=0.0):
    pygame.draw.circle(s, (12, 18, 38), centro, raio)
    k = max(0.0, min(1.0, (geral - 40) / 59))
    cor = misturar((240, 200, 70), (90, 215, 120), k)
    ret = pygame.Rect(0, 0, raio * 2, raio * 2)
    ret.center = centro
    pygame.draw.arc(s, (40, 55, 90), ret, 0, 2 * math.pi, 6)
    pygame.draw.arc(s, cor, ret, math.pi / 2, math.pi / 2 + 2 * math.pi * k, 6)
    texto(s, f"{int(geral)}", 32, (255, 255, 255), (centro[0], centro[1] - 4))
    texto(s, "GERAL", 10, COR_TEXTO_SUAVE, (centro[0], centro[1] + 22))


def _jogador_em_palco(s, kit, nome, numero, centro_chao, tamanho=230, t=0.0):
    """Sprite do jogador com o equipamento, um foco de luz e a camisola com o nome e o número."""
    cx, chao = centro_chao
    brilho = luz(tamanho + 80, 90, (255, 240, 200), 110)
    s.blit(brilho, brilho.get_rect(center=(cx, chao - 4)), special_flags=pygame.BLEND_RGB_ADD)
    img = sprite_equipamento(kit, tamanho, t)
    s.blit(img, img.get_rect(midbottom=(cx, chao)))
    placa = pygame.Rect(0, 0, 200, 40)
    placa.midtop = (cx, chao + 8)
    pygame.draw.rect(s, kit["principal"], placa, border_radius=10)
    pygame.draw.rect(s, (255, 255, 255), placa, 2, border_radius=10)
    cor_txt = cor_texto_sobre(kit["principal"])
    texto(s, f"{numero}", 22, cor_txt, (placa.left + 26, placa.centery))
    pygame.draw.line(s, cor_txt, (placa.left + 46, placa.top + 8), (placa.left + 46, placa.bottom - 8), 2)
    nome_curto = (nome or "?").split()[-1].upper()[:12]
    texto(s, nome_curto, 17, cor_txt, (placa.left + 46 + (placa.width - 46) // 2, placa.centery))


# ====================================================================== #
# Criar o jogador                                                        #
# ====================================================================== #

class EcraCriarJogador:
    def __init__(self, screen, arena=None, nome: str = "", equipa_id: str = "riba_dave"):
        self.screen = screen
        self.arena = arena
        self.t = 0.0
        self.nome = nome
        self.numero = 10
        self.posicao = "avancado"
        self.equipa = equipa_id if equipa_id in EQUIPAS_LISTA else EQUIPAS_LISTA[-1]
        self.erro = ""
        self.r_nome = pygame.Rect(40, 128, 590, 58)
        self.r_num_menos = pygame.Rect(40, 224, 58, 58)
        self.r_num_mais = pygame.Rect(232, 224, 58, 58)
        self.r_pos = [pygame.Rect(40 + i * 200, 326, 190, 118) for i in range(3)]
        self.r_clubes = [pygame.Rect(40 + (i % 4) * 149, 486 + (i // 4) * 70, 141, 62)
                         for i in range(len(EQUIPAS_LISTA))]
        self.btn_comecar = BotaoMenu((700, 620, 540, 64), "COMEÇAR CARREIRA", "Primeira época no clube escolhido",
                                     "comecar", (40, 190, 100), "jogar")
        self.btn_voltar = BotaoMenu((40, 648, 230, 50), "VOLTAR", "", "voltar", (150, 110, 255), "casa",
                                    seta=False, tamanho=18)
        try:
            pygame.key.start_text_input()
        except pygame.error:
            pass

    def _mudar_numero(self, d):
        self.numero = (self.numero - 1 + d) % 99 + 1
        som.ui("mover")

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return "sair"
        if event.type == pygame.TEXTINPUT:
            if event.text.isprintable() and len(self.nome) < 22:
                self.nome += event.text
                self.erro = ""
            return None
        if event.type == pygame.KEYDOWN:
            k = event.key
            if k == pygame.K_ESCAPE:
                return "voltar"
            if k in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return self._comecar()
            if k == pygame.K_BACKSPACE:
                self.nome = self.nome[:-1]
            elif k == pygame.K_UP:
                self.posicao = POSICOES[(POSICOES.index(self.posicao) - 1) % 3]
                som.ui("mover")
            elif k == pygame.K_DOWN:
                self.posicao = POSICOES[(POSICOES.index(self.posicao) + 1) % 3]
                som.ui("mover")
            elif k in (pygame.K_LEFT, pygame.K_RIGHT):
                d = 1 if k == pygame.K_RIGHT else -1
                self.equipa = EQUIPAS_LISTA[(EQUIPAS_LISTA.index(self.equipa) + d) % len(EQUIPAS_LISTA)]
                som.ui("mover")
            elif k in (pygame.K_PAGEUP, pygame.K_KP_PLUS):
                self._mudar_numero(1)
            elif k in (pygame.K_PAGEDOWN, pygame.K_KP_MINUS):
                self._mudar_numero(-1)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            p = event.pos
            if self.btn_comecar.por_cima(p):
                return self._comecar()
            if self.btn_voltar.por_cima(p):
                return "voltar"
            if self.r_num_menos.collidepoint(p):
                self._mudar_numero(-1)
            elif self.r_num_mais.collidepoint(p):
                self._mudar_numero(1)
            for i, r in enumerate(self.r_pos):
                if r.collidepoint(p):
                    self.posicao = POSICOES[i]
                    som.ui("mover")
            for i, r in enumerate(self.r_clubes):
                if r.collidepoint(p):
                    self.equipa = EQUIPAS_LISTA[i]
                    som.ui("mover")
        elif event.type == pygame.MOUSEWHEEL:
            if pygame.Rect(40, 224, 250, 58).collidepoint(pygame.mouse.get_pos()):
                self._mudar_numero(1 if event.y > 0 else -1)
        return None

    def _comecar(self):
        if not self.nome.strip():
            self.erro = "Escreve o nome do teu jogador"
            som.ui("mover")
            return None
        try:
            pygame.key.stop_text_input()
        except pygame.error:
            pass
        return "comecar"

    def update(self, dt):
        self.t += dt
        mpos = pygame.mouse.get_pos()
        self.btn_comecar.animar(dt, True)
        self.btn_voltar.animar(dt, self.btn_voltar.por_cima(mpos))

    def draw(self):
        s = self.screen
        info = obter_info_equipa(self.equipa)
        kit = kit_principal(self.equipa)
        s.blit(_fundo_arena(self.arena), (0, 0))
        brilho = luz(700, 500, info["cor_primaria"], 55)
        s.blit(brilho, brilho.get_rect(center=(970, 330)), special_flags=pygame.BLEND_RGB_ADD)

        texto(s, "CRIAR JOGADOR", 32, COR_TEXTO, (40, 46), ancora="midleft", sombra=True)
        texto(s, "Na carreira de jogador só controlas o teu jogador. Os colegas são da IA.", 14,
              COR_TEXTO_SUAVE, (40, 80), ancora="midleft", negrito=False)

        # Nome
        texto(s, "NOME", 13, COR_DESTAQUE, (40, 114), ancora="midleft")
        _vidro(s, self.r_nome, 12, 230, COR_DESTAQUE)
        mostrar = self.nome or ""
        cursor = "|" if int(self.t * 2) % 2 == 0 else " "
        if mostrar:
            texto(s, mostrar + cursor, 26, (255, 255, 255), (self.r_nome.left + 20, self.r_nome.centery),
                  ancora="midleft")
        else:
            texto(s, "Escreve o nome..." + cursor, 22, (110, 130, 175), (self.r_nome.left + 20, self.r_nome.centery),
                  ancora="midleft", negrito=False)
        if self.erro:
            texto(s, self.erro, 13, (255, 110, 100), (self.r_nome.right, 114), ancora="midright")

        # Número
        texto(s, "NÚMERO", 13, COR_DESTAQUE, (40, 210), ancora="midleft")
        caixa_num = pygame.Rect(104, 224, 122, 58)
        _vidro(s, caixa_num, 12, 230)
        texto(s, str(self.numero), 30, (255, 255, 255), caixa_num.center)
        for r, sinal in ((self.r_num_menos, "−"), (self.r_num_mais, "+")):
            _vidro(s, r, 12, 230)
            texto(s, sinal, 28, COR_TEXTO, r.center)

        # Posição
        texto(s, "POSIÇÃO", 13, COR_DESTAQUE, (40, 312), ancora="midleft")
        for pos, r in zip(POSICOES, self.r_pos):
            escolhido = pos == self.posicao
            _vidro(s, r, 12, 235, COR_DESTAQUE if escolhido else (60, 90, 150))
            if escolhido:
                pygame.draw.rect(s, COR_DESTAQUE, r, 3, border_radius=12)
            texto(s, NOME_POSICAO[pos].upper(), 18, (255, 255, 255) if escolhido else COR_TEXTO,
                  (r.centerx, r.top + 22))
            texto(s, DESCRICAO_POSICAO[pos], 11, COR_TEXTO_SUAVE, (r.centerx, r.top + 44), negrito=False)
            at = atributos(GERAL_INICIAL, pos)
            for j, a in enumerate(ATRIBUTOS):
                x = r.left + 16 + j * 42
                texto(s, NOME_ATRIBUTO[a], 10, COR_TEXTO_SUAVE, (x + 14, r.top + 72))
                texto(s, str(at[a]), 17, (255, 255, 255) if at[a] >= 68 else COR_TEXTO, (x + 14, r.top + 94))

        # Clube
        texto(s, "CLUBE", 13, COR_DESTAQUE, (40, 472), ancora="midleft")
        for eq, r in zip(EQUIPAS_LISTA, self.r_clubes):
            escolhido = eq == self.equipa
            _vidro(s, r, 10, 235, COR_DESTAQUE if escolhido else (60, 90, 150))
            if escolhido:
                pygame.draw.rect(s, COR_DESTAQUE, r, 3, border_radius=10)
            logo = carregar_logo_equipa(eq, (42, 42))
            if logo:
                s.blit(logo, logo.get_rect(center=(r.left + 30, r.centery)))
            texto(s, obter_info_equipa(eq)["sigla"], 15, (255, 255, 255) if escolhido else COR_TEXTO,
                  (r.left + 58, r.top + 22), ancora="midleft")
            _barra_forca(s, r.left + 58, r.top + 38, 70, FORCA_EQUIPAS.get(eq, 75))

        # Pré-visualização do jogador
        caixa = pygame.Rect(700, 100, 540, 500)
        _vidro(s, caixa, 16, 215)
        _jogador_em_palco(s, kit, self.nome or "?", self.numero, (caixa.left + 160, caixa.top + 360), 250, self.t)
        _circulo_geral(s, (caixa.right - 120, caixa.top + 90), GERAL_INICIAL)
        _barras_atributos(s, caixa.right - 220, caixa.top + 170, 190, atributos(GERAL_INICIAL, self.posicao))
        logo = carregar_logo_equipa(self.equipa, (70, 70))
        if logo:
            s.blit(logo, logo.get_rect(center=(caixa.right - 120, caixa.top + 330)))
        texto(s, info["nome"], 17, COR_TEXTO, (caixa.right - 120, caixa.top + 382))
        texto(s, NOME_POSICAO[self.posicao], 14, COR_TEXTO_SUAVE, (caixa.right - 120, caixa.top + 404),
              negrito=False)
        from team import obter_plantel
        sai = next((n for n, p, _ in obter_plantel(self.equipa)["jogadores"] if p == self.posicao), None)
        if sai:
            texto(s, f"Entras no plantel no lugar de {sai}", 12, (130, 150, 195),
                  (caixa.centerx, caixa.bottom - 24), negrito=False)

        self.btn_comecar.draw(s)
        self.btn_voltar.draw(s)
        texto(s, "Escreve o nome     ↑ ↓ posição     ← → clube     PgUp / PgDn número     ENTER começar     ESC voltar",
              12, (120, 145, 195), (WIDTH // 2, 708), negrito=False)


# ====================================================================== #
# Painel da carreira                                                     #
# ====================================================================== #

class EcraCarreiraJogador:
    """
    cj    : CarreiraJogador (com cj.vida)
    aviso : resumo do último jogo (de CarreiraJogador.registar_jogo / simular_jogo), mostrado num cartão

    Além do painel, este ecrã tem janelas por cima ("modais"):
      evento     - um acontecimento da vida com escolhas (aparece sozinho depois de uma jornada)
      atividades - o que fazer nesta semana (uma atividade por jornada)
      resultado  - o que aconteceu depois de uma escolha (com os efeitos)
      diario     - as últimas entradas do diário
    As escolhas são aplicadas logo na classe Vida (vida.py); o resto (jogar, simular) é decidido pela Game.
    """

    def __init__(self, screen, cj, arena=None, aviso: dict | None = None):
        self.screen = screen
        self.cj = cj
        self.arena = arena
        self.t = 0.0
        self.aviso = aviso
        self._aviso_fechado = False
        self._confirmar = None
        self.modal = None              # None ou {"tipo": "evento" | "atividades" | "resultado" | "diario", ...}
        self._opcoes = []              # retângulos das opções do modal (para o rato)
        self._hover = -1
        self._ler_dados()
        self._criar_botoes()

    def _ler_dados(self):
        cj, camp = self.cj, self.cj.camp
        self.atleta = dict(cj.atleta)
        self.vida = cj.vida.estado
        self.mod = cj.vida.modificador()
        self.pode_jogar, self.motivo = cj.vida.pode_jogar()
        mod_r = round(self.mod)
        self.attrs = {k: max(40, min(99, v + mod_r)) for k, v in cj.atributos().items()}
        self.est = cj.estatisticas_epoca()
        self.notas = cj.ultimas_notas(5)
        self.tabela = list(camp.classificacao())
        self.marcadores = list(camp.melhores_marcadores(3))
        self.terminado = camp.terminado
        self.proximo = None if self.terminado else camp.proximo_jogo()
        self.propostas = cj.propostas() if self.terminado else []
        self.posicao_equipa = camp.posicao_do_jogador()
        self.epoca = camp.info["epoca"]
        self.jornada = camp.jornada_atual
        self.total_jornadas = camp.total_jornadas
        self.jogadas = camp.ultima_jornada_jogada()
        self.ultimo_diario = cj.vida.diario(1)

    def _criar_botoes(self):
        self.botoes_principais = []
        if self.terminado:
            y = 312
            for eq in self.propostas:
                nome = obter_info_equipa(eq)["nome"]
                self.botoes_principais.append(BotaoMenu((450, y, 380, 58), f"ASSINAR: {nome.upper()}",
                                                        "Proposta para a próxima época", f"assinar:{eq}",
                                                        (40, 190, 100), "jogar"))
                y += 64
            atual = obter_info_equipa(self.atleta["equipa_id"])["nome"]
            self.botoes_principais.append(BotaoMenu((450, y, 380, 58), "FICAR NO CLUBE", f"Nova época no {atual}",
                                                    "ficar", (50, 140, 255), "casa"))
        elif not self.pode_jogar:
            self.botoes_principais = [
                BotaoMenu((450, 312, 380, 64), "SIMULAR JORNADA", self.motivo.capitalize(), "simular",
                          (230, 90, 70), "avancar")]
        else:
            self.botoes_principais = [
                BotaoMenu((450, 312, 214, 64), "JOGAR", "Só com o teu jogador", "jogar", (40, 190, 100), "jogar"),
                BotaoMenu((672, 312, 158, 64), "SIMULAR", "", "simular", (255, 175, 40), "avancar", seta=False,
                          tamanho=17),
            ]
        self.btn_epoca = None if self.terminado else BotaoMenu(
            (330, 646, 270, 50), "SIMULAR ÉPOCA", "", "simular_epoca", (255, 175, 40), "avancar", seta=False, tamanho=18)
        self.btn_nova = BotaoMenu((40, 646, 270, 50), "NOVA CARREIRA", "", "nova_carreira", (255, 120, 60),
                                  "recomecar", seta=False, tamanho=18)
        self.btn_ativ = BotaoMenu((620, 646, 330, 50), "ATIVIDADES DA SEMANA", "", "atividades", (255, 110, 160),
                                  "jogador", seta=False, tamanho=18)
        self.btn_menu = BotaoMenu((WIDTH - 310, 646, 270, 50), "MENU PRINCIPAL", "", "menu", (150, 110, 255),
                                  "casa", seta=False, tamanho=18)
        self.r_pilulas = {k: pygame.Rect(470 + i * 116, 590, 108, 26)
                          for i, k in enumerate(("pessoas", "diario", "conquistas"))}
        self.foco = 0

    @property
    def _todos_botoes(self):
        return self.botoes_principais + [b for b in (self.btn_epoca, self.btn_nova, self.btn_ativ, self.btn_menu) if b]

    def _pedir_confirmacao(self, botao, texto_original) -> bool:
        if self._confirmar is botao:
            return True
        if self._confirmar is not None:
            self._confirmar.titulo = self._confirmar._titulo_original
        botao._titulo_original = texto_original
        botao.titulo = "TENS A CERTEZA?"
        self._confirmar = botao
        som.ui("mover")
        return False

    @property
    def _aviso_visivel(self) -> bool:
        return bool(self.aviso) and not self._aviso_fechado and self.t < 6.0

    # ------------------------------------------------------------------ #
    # Modais                                                              #
    # ------------------------------------------------------------------ #
    def _abrir_evento_se_houver(self) -> bool:
        ev = self.cj.vida.evento_atual()
        if ev and self.modal is None:
            self.modal = {"tipo": "evento", "evento": ev}
            som.ui("mover")
            return True
        return False

    def _escolher(self, i):
        m = self.modal
        if m["tipo"] == "evento":
            if not m["evento"]["possivel"][i]:
                return
            res = self.cj.vida.escolher(i)
        elif m["tipo"] == "atividades":
            at = m["lista"][i]
            if not at["possivel"]:
                return
            res = self.cj.vida.fazer_atividade(at["id"])
        elif m["tipo"] == "pessoas":
            acoes = self._acoes_pessoas()
            if i >= len(acoes) or not acoes[i][3]:
                return
            p, ac, _info, _ok = acoes[i]
            res = self.cj.vida.interagir(p["papel"], ac)
            res["voltar"] = "pessoas"
        else:
            return
        som.ui("confirmar")
        self.modal = {"tipo": "resultado", "res": res}
        self._ler_dados()
        self._criar_botoes()

    def _evento_modal(self, event):
        m = self.modal
        n = len(self._opcoes)
        if event.type == pygame.KEYDOWN:
            if m["tipo"] in ("resultado", "diario", "conquistas"):
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_ESCAPE):
                    self._fechar_modal()
                return None
            if event.key == pygame.K_ESCAPE and m["tipo"] in ("atividades", "pessoas"):
                self.modal = None
            elif pygame.K_1 <= event.key <= pygame.K_9 and event.key - pygame.K_1 < n:
                self._escolher(event.key - pygame.K_1)
            elif event.key in (pygame.K_UP, pygame.K_w) and n:
                self._hover = (self._hover - 1) % n
            elif event.key in (pygame.K_DOWN, pygame.K_s) and n:
                self._hover = (self._hover + 1) % n
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and 0 <= self._hover < n:
                self._escolher(self._hover)
        elif event.type == pygame.MOUSEMOTION:
            self._hover = next((i for i, r in enumerate(self._opcoes) if r.collidepoint(event.pos)), self._hover)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if m["tipo"] in ("resultado", "diario", "conquistas"):
                self._fechar_modal()
                return None
            for i, r in enumerate(self._opcoes):
                if r.collidepoint(event.pos):
                    self._escolher(i)
                    return None
            if m["tipo"] in ("atividades", "pessoas"):
                self.modal = None
        return None

    def _fechar_modal(self):
        """Fecha a janela; depois de interagir com alguém volta à janela das pessoas."""
        voltar = self.modal.get("res", {}).get("voltar") if self.modal["tipo"] == "resultado" else None
        self.modal = None
        if voltar:
            self._abrir_modal(voltar)
        else:
            self._abrir_evento_se_houver()

    # ------------------------------------------------------------------ #
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return "sair"
        if self._aviso_visivel and (event.type == pygame.KEYDOWN or
                                    (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)):
            self._aviso_fechado = True
            self._abrir_evento_se_houver()
            return None
        if self.modal is not None:
            return self._evento_modal(event)
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self._acao_principal(self.botoes_principais[self.foco].acao)
            if event.key == pygame.K_ESCAPE:
                return "menu"
            if event.key == pygame.K_v:
                self._abrir_atividades()
            if event.key == pygame.K_l:
                self._abrir_modal("diario")
            if event.key == pygame.K_p:
                self._abrir_modal("pessoas")
            if event.key == pygame.K_c:
                self._abrir_modal("conquistas")
            if event.key in (pygame.K_LEFT, pygame.K_UP, pygame.K_a, pygame.K_w):
                self.foco = (self.foco - 1) % len(self.botoes_principais)
                som.ui("mover")
            if event.key in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_d, pygame.K_s):
                self.foco = (self.foco + 1) % len(self.botoes_principais)
                som.ui("mover")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            p = event.pos
            for b in self.botoes_principais:
                if b.por_cima(p):
                    return self._acao_principal(b.acao)
            if self.btn_menu.por_cima(p):
                return "menu"
            if self.btn_ativ.por_cima(p):
                self._abrir_atividades()
                return None
            for k, r in self.r_pilulas.items():
                if r.collidepoint(p):
                    self._abrir_modal(k)
                    return None
            if self.btn_nova.por_cima(p):
                return "nova_carreira" if self._pedir_confirmacao(self.btn_nova, "NOVA CARREIRA") else None
            if self.btn_epoca is not None and self.btn_epoca.por_cima(p):
                return "simular_epoca" if self._pedir_confirmacao(self.btn_epoca, "SIMULAR ÉPOCA") else None
        elif event.type == pygame.MOUSEMOTION:
            for i, b in enumerate(self.botoes_principais):
                if b.por_cima(event.pos):
                    self.foco = i
        return None

    def _acao_principal(self, acao):
        # Antes de jogar é preciso responder ao evento da semana
        if acao in ("jogar", "simular") and self._abrir_evento_se_houver():
            return None
        return acao

    def _abrir_modal(self, tipo):
        if tipo == "pessoas":
            self.modal = {"tipo": "pessoas"}
        else:
            self.modal = {"tipo": tipo}
        self._hover = -1
        som.ui("mover")

    def _acoes_pessoas(self):
        """Lista (pessoa, ação, possível) para a janela das pessoas."""
        from vida import ACOES_PESSOA
        dinheiro = self.cj.vida.estado["dinheiro"]
        lista = []
        for p in self.cj.vida.pessoas():
            for ac, info in ACOES_PESSOA.items():
                lista.append((p, ac, info, not p["interagiu"] and dinheiro >= info.get("custo", 0)))
        return lista

    def _abrir_atividades(self):
        if self.terminado:
            return
        self.modal = {"tipo": "atividades", "lista": self.cj.vida.atividades()}
        self._hover = -1
        som.ui("mover")

    def update(self, dt):
        self.t += dt
        mpos = pygame.mouse.get_pos()
        for i, b in enumerate(self.botoes_principais):
            b.animar(dt, i == self.foco and self.modal is None)
        for b in (self.btn_epoca, self.btn_nova, self.btn_ativ, self.btn_menu):
            if b:
                b.animar(dt, (b.por_cima(mpos) or b is self._confirmar) and self.modal is None)
        # Sem cartão do jogo à vista, o evento da semana abre sozinho
        if not self._aviso_visivel and self.modal is None and self.t > 0.3:
            self._abrir_evento_se_houver()

    # ------------------------------------------------------------------ #
    def draw(self):
        s = self.screen
        a = self.atleta
        eu = a["equipa_id"]
        info = obter_info_equipa(eu)
        kit = kit_principal(eu)
        s.blit(_fundo_arena(self.arena), (0, 0))
        brilho = luz(600, 480, info["cor_primaria"], 55)
        s.blit(brilho, brilho.get_rect(center=(230, 360)), special_flags=pygame.BLEND_RGB_ADD)

        self._cabecalho(info)
        self._ficha(pygame.Rect(40, 100, 390, 530), kit)
        self._centro(pygame.Rect(450, 100, 380, 196))
        self._painel_vida(pygame.Rect(450, 390, 380, 240))
        self._classificacao(pygame.Rect(850, 100, 390, 530))

        for b in self._todos_botoes:
            b.draw(s)
        dica = "ENTER  escolher     ← →  mudar" if self.terminado else "ENTER  jogar     ← →  jogar / simular"
        texto(s, dica + "     V  atividades     P  pessoas     L  diário     C  conquistas     ESC  menu", 12, (120, 145, 195),
              (WIDTH // 2, 710), negrito=False)
        if self._aviso_visivel:
            self._mostrar_aviso()
        elif self.modal is not None:
            self._desenhar_modal()

    def _cabecalho(self, info):
        s = self.screen
        a = self.atleta
        texto(s, a["nome"].upper(), 30, COR_TEXTO, (40, 40), ancora="midleft", sombra=True)
        texto(s, f"N.º {a['numero']}   •   {NOME_POSICAO[a['posicao']]}   •   {info['nome']}   •   "
                 f"{self.vida['idade']} anos   •   Época {self.epoca}",
              14, COR_TEXTO_SUAVE, (40, 74), ancora="midleft", negrito=False)
        r = pygame.Rect(WIDTH - 330, 22, 290, 58)
        _vidro(s, r, 12, 220, COR_DESTAQUE)
        etiqueta = "ÉPOCA TERMINADA" if self.terminado else f"JORNADA {self.jornada} DE {self.total_jornadas}"
        texto(s, etiqueta, 15, COR_DESTAQUE, (r.centerx, r.top + 18))
        total = max(1, self.total_jornadas)
        larg = (r.width - 40 - (total - 1) * 6) / total
        for i in range(total):
            seg = pygame.Rect(round(r.left + 20 + i * (larg + 6)), r.top + 36, round(larg), 8)
            cor = COR_DESTAQUE if i < self.jogadas else (45, 60, 95)
            pygame.draw.rect(s, cor, seg, border_radius=4)

    def _ficha(self, caixa, kit):
        s = self.screen
        a = self.atleta
        _vidro(s, caixa, 16, 220)
        _titulo_painel(s, caixa, "O TEU JOGADOR")
        _jogador_em_palco(s, kit, a["nome"], a["numero"], (caixa.left + 120, caixa.top + 270), 200, self.t)
        _circulo_geral(s, (caixa.right - 90, caixa.top + 100), a["geral"])
        _barras_atributos(s, caixa.right - 175, caixa.top + 175, 150, self.attrs, passo=28)
        if abs(self.mod) >= 0.5:
            cor = (90, 215, 120) if self.mod > 0 else (230, 90, 80)
            texto(s, f"Forma e moral: {round(self.mod):+d} nos atributos", 11, cor,
                  (caixa.right - 88, caixa.top + 290))
        y = caixa.top + 372
        texto(s, "ÚLTIMAS NOTAS", 13, COR_DESTAQUE, (caixa.left + 20, y), ancora="midleft")
        for i in range(5):
            r = pygame.Rect(caixa.left + 20 + i * 72, y + 18, 62, 40)
            if i < len(self.notas):
                n = self.notas[i]
                pygame.draw.rect(s, cor_nota(n), r, border_radius=8)
                texto(s, f"{n:.1f}".replace(".", ","), 18, (15, 20, 35), r.center)
            else:
                pygame.draw.rect(s, (45, 60, 95), r, 2, border_radius=8)
        y = caixa.top + 460
        est = self.est
        nota = "–" if est["nota"] is None else f"{est['nota']:.2f}".replace(".", ",")
        for i, (rot, val) in enumerate((("JOGOS", est["jogos"]), ("GOLOS", est["golos"]),
                                        ("ASSIST.", est["assistencias"]), ("NOTA", nota))):
            x = caixa.left + 20 + i * 90
            texto(s, str(val), 24, (255, 255, 255), (x + 40, y))
            texto(s, rot, 11, COR_TEXTO_SUAVE, (x + 40, y + 24))

    def _centro(self, caixa):
        s = self.screen
        _vidro(s, caixa, 16, 220)
        if self.terminado:
            pos = self.posicao_equipa
            _titulo_painel(s, caixa, "FIM DA ÉPOCA")
            texto(s, "CAMPEÃO!" if pos == 1 else f"{pos}.º LUGAR", 34,
                  COR_DESTAQUE if pos == 1 else (255, 255, 255), (caixa.centerx, caixa.top + 78), sombra=True)
            nota = self.est["nota"] or 0
            texto(s, f"Nota média {nota:.2f}".replace(".", ",") +
                  f"   •   {self.est['golos']} golos   •   {self.est['assistencias']} assist.", 14, COR_TEXTO,
                  (caixa.centerx, caixa.top + 122), negrito=False)
            msg = (f"{len(self.propostas)} clube(s) querem-te!" if self.propostas
                   else "Sem propostas: precisas de mais nota ou de mais fama")
            texto(s, msg, 15, (120, 230, 150) if self.propostas else COR_TEXTO_SUAVE,
                  (caixa.centerx, caixa.top + 160))
            return
        p = self.proximo
        eu = self.atleta["equipa_id"]
        _titulo_painel(s, caixa, f"PRÓXIMO JOGO  •  JORNADA {p['jornada']}")
        for eq, cx in ((p["casa_id"], caixa.left + 90), (p["fora_id"], caixa.right - 90)):
            logo = carregar_logo_equipa(eq, (74, 74))
            if logo:
                s.blit(logo, logo.get_rect(center=(cx, caixa.top + 96)))
            texto(s, obter_info_equipa(eq)["sigla"], 16, (255, 255, 255) if eq == eu else COR_TEXTO,
                  (cx, caixa.top + 150))
        texto(s, "VS", 30, COR_DESTAQUE, (caixa.centerx, caixa.top + 92))
        texto(s, "EM CASA" if p["casa_id"] == eu else "FORA", 13, COR_TEXTO_SUAVE,
              (caixa.centerx, caixa.top + 124))
        if not self.pode_jogar:
            texto(s, self.motivo, 12, (255, 120, 100), (caixa.centerx, caixa.bottom - 18))

    def _painel_vida(self, r):
        """A MINHA VIDA: dinheiro, os cinco valores em barras e a última linha do diário."""
        s = self.screen
        v = self.vida
        _vidro(s, r, 16, 220, (190, 90, 140))
        texto(s, "A MINHA VIDA", 15, (255, 140, 190), (r.left + 20, r.top + 22), ancora="midleft")
        dinheiro = f"{v['dinheiro']:,} €".replace(",", " ")
        texto(s, dinheiro, 15, (130, 230, 150), (r.left + 210, r.top + 22), ancora="midleft")
        texto(s, f"{v['idade']} anos", 13, COR_TEXTO_SUAVE, (r.right - 20, r.top + 22), ancora="midright")
        mpos = pygame.mouse.get_pos()
        for k, rr in self.r_pilulas.items():
            hover = rr.collidepoint(mpos)
            pygame.draw.rect(s, (110, 50, 85) if hover else (60, 40, 70), rr, border_radius=13)
            pygame.draw.rect(s, (255, 140, 190), rr, 1, border_radius=13)
            nome = {"pessoas": "PESSOAS (P)", "diario": "DIÁRIO (L)", "conquistas": "CONQUISTAS (C)"}[k]
            texto(s, nome, 11, (255, 210, 230), rr.center)
        for i, k in enumerate(("forma", "moral", "treinador", "fama", "estudos")):
            y = r.top + 48 + i * 24
            texto(s, {"treinador": "Treinador"}.get(k, k.capitalize()), 13, COR_TEXTO_SUAVE,
                  (r.left + 20, y), ancora="midleft")
            barra = pygame.Rect(r.left + 110, y - 5, 210, 10)
            pygame.draw.rect(s, (25, 35, 65), barra, border_radius=5)
            t = v[k] / 100
            cor = misturar((230, 80, 70), (90, 215, 120), t) if k != "fama" else misturar((90, 120, 200), (255, 205, 60), t)
            pygame.draw.rect(s, cor, (barra.x, barra.y, max(6, round(barra.w * t)), 10), border_radius=5)
            texto(s, str(v[k]), 13, COR_TEXTO, (r.right - 20, y), ancora="midright")
        y = r.top + 174
        if not self.pode_jogar:
            texto(s, self.motivo, 13, (255, 120, 100), (r.left + 20, y), ancora="midleft")
        elif v["atividade_feita"]:
            texto(s, "Já fizeste a atividade desta semana", 12, COR_TEXTO_SUAVE, (r.left + 20, y), ancora="midleft",
                  negrito=False)
        else:
            texto(s, "Ainda podes fazer uma atividade esta semana", 12, (255, 170, 210), (r.left + 20, y),
                  ancora="midleft", negrito=False)

    def _classificacao(self, caixa):
        s = self.screen
        _vidro(s, caixa, 16, 220)
        _titulo_painel(s, caixa, "CLASSIFICAÇÃO")
        eu = self.atleta["equipa_id"]
        texto(s, "J", 12, COR_TEXTO_SUAVE, (caixa.right - 120, caixa.top + 22))
        texto(s, "DG", 12, COR_TEXTO_SUAVE, (caixa.right - 78, caixa.top + 22))
        texto(s, "PTS", 12, COR_TEXTO_SUAVE, (caixa.right - 32, caixa.top + 22))
        for i, l in enumerate(self.tabela):
            y = caixa.top + 60 + i * 44
            meu = l["equipa_id"] == eu
            if meu:
                pygame.draw.rect(s, (40, 80, 150), (caixa.left + 10, y - 19, caixa.width - 20, 38), border_radius=10)
            texto(s, f"{i + 1}", 15, COR_DESTAQUE if i == 0 else COR_TEXTO_SUAVE, (caixa.left + 30, y))
            logo = carregar_logo_equipa(l["equipa_id"], (30, 30))
            if logo:
                s.blit(logo, logo.get_rect(center=(caixa.left + 68, y)))
            texto(s, l["nome"], 14, (255, 255, 255) if meu else COR_TEXTO, (caixa.left + 92, y), ancora="midleft",
                  negrito=meu)
            texto(s, str(l["jogos"]), 13, COR_TEXTO_SUAVE, (caixa.right - 120, y))
            texto(s, f"{l['diferenca']:+d}", 13, COR_TEXTO_SUAVE, (caixa.right - 78, y))
            texto(s, str(l["pontos"]), 16, (255, 255, 255), (caixa.right - 32, y))
        y0 = caixa.top + 420
        texto(s, "MELHORES MARCADORES", 13, COR_DESTAQUE, (caixa.left + 20, y0), ancora="midleft")
        if not self.marcadores:
            texto(s, "Ainda não há golos nesta época", 12, COR_TEXTO_SUAVE, (caixa.centerx, y0 + 40), negrito=False)
        for i, m in enumerate(self.marcadores):
            y = y0 + 26 + i * 26
            meu = m["nome"] == self.atleta["nome"] and m["equipa_id"] == eu
            if meu:
                pygame.draw.rect(s, (40, 80, 150), (caixa.left + 10, y - 12, caixa.width - 20, 24), border_radius=8)
            texto(s, f"{i + 1}. {m['nome']}", 13, (255, 255, 255) if meu else COR_TEXTO, (caixa.left + 20, y),
                  ancora="midleft", negrito=meu)
            texto(s, obter_info_equipa(m["equipa_id"])["sigla"], 12, COR_TEXTO_SUAVE, (caixa.right - 70, y))
            texto(s, str(m["golos"]), 15, COR_DESTAQUE, (caixa.right - 26, y))

    # ------------------------------------------------------------------ #
    def _fundo_modal(self, w, h):
        s = self.screen
        escuro = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        escuro.fill((5, 8, 20, 185))
        s.blit(escuro, (0, 0))
        caixa = pygame.Rect(0, 0, w, h)
        caixa.center = (WIDTH // 2, HEIGHT // 2)
        _vidro(s, caixa, 18, 248, (255, 140, 190))
        return caixa

    def _texto_quebrado(self, txt, tamanho, cor, x, y, largura, negrito=False, passo=None):
        f = fonte(tamanho, negrito)
        palavras, linha = txt.split(), ""
        for p in palavras:
            prox = (linha + " " + p).strip()
            if f.size(prox)[0] > largura and linha:
                texto(self.screen, linha, tamanho, cor, (x, y), ancora="midleft", negrito=negrito)
                y += passo or tamanho + 8
                linha = p
            else:
                linha = prox
        if linha:
            texto(self.screen, linha, tamanho, cor, (x, y), ancora="midleft", negrito=negrito)
            y += passo or tamanho + 8
        return y

    def _chips(self, efeitos, x, y):
        """Efeitos como etiquetas coloridas: verde = bom, vermelho = mau."""
        from vida import NOME_VALOR
        for k, d in efeitos.items():
            if not d:
                continue
            if k == "dinheiro":
                txt = f"{d:+,} €".replace(",", " ")
            elif k == "lesao":
                txt = f"Lesão {d:+d} jorn."
            elif k == "geral":
                txt = f"Geral {d:+.1f}".replace(".", ",")
            else:
                txt = f"{NOME_VALOR.get(k, k)} {d:+d}"
            bom = d < 0 if k == "lesao" else d > 0
            f = fonte(13)
            w = f.size(txt)[0] + 18
            r = pygame.Rect(x, y, w, 26)
            pygame.draw.rect(self.screen, (40, 120, 70) if bom else (140, 45, 50), r, border_radius=13)
            texto(self.screen, txt, 13, (255, 255, 255), r.center)
            x += w + 8

    def _desenhar_modal(self):
        m = self.modal
        s = self.screen
        self._opcoes = []
        if m["tipo"] == "evento":
            ev = m["evento"]
            n = len(ev["opcoes"])
            caixa = self._fundo_modal(660, 176 + n * 62)
            cor, nome_icone, nome_cat = CATEGORIA.get(ev.get("categoria"), CATEGORIA["hoquei"])
            pygame.draw.rect(s, cor, (caixa.left + 18, caixa.top + 10, caixa.width - 36, 4), border_radius=2)
            centro = (caixa.left + 58, caixa.top + 58)
            halo = luz(120, 120, cor, 90)
            s.blit(halo, halo.get_rect(center=centro), special_flags=pygame.BLEND_RGB_ADD)
            pygame.draw.circle(s, cor, centro, 28)
            ic = icone(nome_icone, 30, (20, 20, 30))
            s.blit(ic, ic.get_rect(center=centro))
            texto(s, nome_cat + ("  •  CONSEQUÊNCIA" if ev.get("seguimento") else ""), 12, cor,
                  (caixa.left + 100, caixa.top + 38), ancora="midleft")
            texto(s, ev["titulo"], 25, (255, 255, 255), (caixa.left + 100, caixa.top + 70), ancora="midleft")
            y = self._texto_quebrado(ev["texto"], 15, COR_TEXTO, caixa.left + 30, caixa.top + 112, caixa.width - 60)
            y += 6
            for i, op in enumerate(ev["opcoes"]):
                r = pygame.Rect(caixa.left + 30, y + i * 62, caixa.width - 60, 52)
                self._opcoes.append(r)
                ok = ev["possivel"][i]
                hover = i == self._hover
                pygame.draw.rect(s, (70, 40, 80) if hover else (30, 34, 60), r, border_radius=12)
                pygame.draw.rect(s, (255, 140, 190) if hover else (80, 90, 130), r, 2, border_radius=12)
                texto(s, f"{i + 1}", 18, (255, 170, 210), (r.left + 24, r.centery))
                texto(s, op["texto"] + ("" if ok else "   (não tens dinheiro)"), 17,
                      (255, 255, 255) if ok else (120, 120, 140), (r.left + 50, r.centery), ancora="midleft")
        elif m["tipo"] == "atividades":
            lista = m["lista"]
            caixa = self._fundo_modal(700, 130 + len(lista) * 56)
            texto(s, "ATIVIDADES DA SEMANA", 24, (255, 255, 255), (caixa.left + 30, caixa.top + 36), ancora="midleft")
            texto(s, "Só podes fazer uma por jornada.  ESC fecha.", 13, COR_TEXTO_SUAVE,
                  (caixa.left + 30, caixa.top + 64), ancora="midleft", negrito=False)
            for i, at in enumerate(lista):
                r = pygame.Rect(caixa.left + 30, caixa.top + 90 + i * 56, caixa.width - 60, 48)
                self._opcoes.append(r)
                hover = i == self._hover and at["possivel"]
                pygame.draw.rect(s, (70, 40, 80) if hover else (30, 34, 60), r, border_radius=10)
                pygame.draw.rect(s, (255, 140, 190) if hover else (80, 90, 130), r, 2, border_radius=10)
                cor = (255, 255, 255) if at["possivel"] else (110, 115, 140)
                texto(s, f"{i + 1}", 16, (255, 170, 210), (r.left + 20, r.centery))
                texto(s, at["nome"], 16, cor, (r.left + 42, r.top + 16), ancora="midleft")
                texto(s, at["descricao"], 11, COR_TEXTO_SUAVE, (r.left + 42, r.top + 34), ancora="midleft",
                      negrito=False)
                if at["possivel"]:
                    self._chips(at["efeitos"], r.left + 330, r.top + 11)
        elif m["tipo"] == "resultado":
            res = m["res"]
            caixa = self._fundo_modal(640, 300)
            texto(s, res["titulo"].upper(), 13, (255, 170, 210), (caixa.left + 30, caixa.top + 30), ancora="midleft")
            texto(s, res["escolha"], 22, (255, 255, 255), (caixa.left + 30, caixa.top + 66), ancora="midleft")
            y = self._texto_quebrado(res["texto"], 15, COR_TEXTO, caixa.left + 30, caixa.top + 110, caixa.width - 60)
            self._chips(res["efeitos"], caixa.left + 30, max(y + 10, caixa.top + 190))
            for k, nome in enumerate(res.get("conquistas", [])[:2]):
                self._selo_conquista(caixa.left + 30, caixa.top + 228 + k * 30, nome)
            texto(s, "Carrega numa tecla para continuar", 12, (120, 145, 195), (caixa.centerx, caixa.bottom - 22),
                  negrito=False)
        elif m["tipo"] == "pessoas":
            self._desenhar_pessoas()
        elif m["tipo"] == "conquistas":
            self._desenhar_conquistas()
        elif m["tipo"] == "diario":
            linhas = self.cj.vida.diario(10)
            caixa = self._fundo_modal(760, 560)
            texto(s, "DIÁRIO", 24, (255, 255, 255), (caixa.left + 30, caixa.top + 36), ancora="midleft")
            y = caixa.top + 76
            for l in linhas:
                quando = f"J{l['jornada']}" if l["jornada"] else "Início"
                texto(s, f"Época {l['epoca']} • {quando}", 11, (255, 170, 210), (caixa.left + 30, y),
                      ancora="midleft")
                y = self._texto_quebrado(l["texto"], 13, COR_TEXTO, caixa.left + 150, y, caixa.width - 180,
                                         passo=18) + 4
                if y > caixa.bottom - 50:
                    break
            texto(s, "Carrega numa tecla para fechar", 12, (120, 145, 195), (caixa.centerx, caixa.bottom - 22),
                  negrito=False)

    def _selo_conquista(self, x, y, nome):
        """Etiqueta dourada "CONQUISTA: ..." (com uma estrela)."""
        s = self.screen
        txt = f"CONQUISTA: {nome.upper()}"
        w = fonte(13).size(txt)[0] + 52
        r = pygame.Rect(x, y, w, 26)
        pygame.draw.rect(s, (70, 55, 10), r, border_radius=13)
        pygame.draw.rect(s, COR_DESTAQUE, r, 2, border_radius=13)
        ic = icone("estrela", 16, COR_DESTAQUE)
        s.blit(ic, ic.get_rect(center=(r.left + 18, r.centery)))
        texto(s, txt, 13, COR_DESTAQUE, (r.left + 34, r.centery), ancora="midleft")

    def _desenhar_pessoas(self):
        """As pessoas da vida do jogador: relação e o que se pode fazer com cada uma esta semana."""
        from vida import NOME_PAPEL
        s = self.screen
        acoes = self._acoes_pessoas()
        pessoas = []
        for p, *_r in acoes:
            if p["id"] not in [q["id"] for q in pessoas]:
                pessoas.append(p)
        caixa = self._fundo_modal(860, 120 + len(pessoas) * 112)
        texto(s, "AS PESSOAS DA TUA VIDA", 24, (255, 255, 255), (caixa.left + 30, caixa.top + 36), ancora="midleft")
        texto(s, "Uma vez por semana podes estar com cada pessoa. Boas relações dão moral.   ESC fecha.", 13,
              COR_TEXTO_SUAVE, (caixa.left + 30, caixa.top + 64), ancora="midleft", negrito=False)
        mpos = pygame.mouse.get_pos()
        for j, p in enumerate(pessoas):
            linha = pygame.Rect(caixa.left + 24, caixa.top + 90 + j * 112, caixa.width - 48, 100)
            pygame.draw.rect(s, (24, 28, 52), linha, border_radius=14)
            cor = COR_PAPEL[p["papel"]]
            centro = (linha.left + 46, linha.top + 50)
            pygame.draw.circle(s, cor, centro, 30)
            letra = p["nome"][0].upper()
            texto(s, letra, 26, (20, 20, 30), centro)
            nome = NOME_PAPEL[p["papel"]] if p["papel"] in ("mae", "pai") else p["nome"]
            texto(s, nome, 18, (255, 255, 255), (linha.left + 92, linha.top + 24), ancora="midleft")
            papel = "" if p["papel"] in ("mae", "pai") else NOME_PAPEL[p["papel"]]
            if papel:
                texto(s, papel, 12, cor, (linha.left + 92 + fonte(18).size(nome)[0] + 12, linha.top + 25),
                      ancora="midleft")
            barra = pygame.Rect(linha.left + 92, linha.top + 46, 170, 10)
            pygame.draw.rect(s, (40, 45, 75), barra, border_radius=5)
            t = p["relacao"] / 100
            pygame.draw.rect(s, misturar((230, 80, 70), (90, 215, 120), t),
                             (barra.x, barra.y, max(6, round(barra.w * t)), 10), border_radius=5)
            texto(s, f"Relação {p['relacao']}", 12, COR_TEXTO_SUAVE, (barra.right + 12, barra.centery),
                  ancora="midleft")
            if p["interagiu"]:
                texto(s, "Já estiveste com esta pessoa esta semana", 12, (150, 160, 190),
                      (linha.left + 92, linha.top + 76), ancora="midleft", negrito=False)
            # Botões das ações
            x = linha.left + 360
            for i, (q, ac, info, ok) in enumerate(acoes):
                if q["id"] != p["id"]:
                    continue
                w = fonte(12).size(info["nome"])[0] + 20
                r = pygame.Rect(x, linha.top + 32, w, 36)
                while len(self._opcoes) < i:
                    self._opcoes.append(pygame.Rect(0, 0, 0, 0))
                self._opcoes.append(r)
                hover = (r.collidepoint(mpos) or i == self._hover) and ok
                pygame.draw.rect(s, (90, 45, 80) if hover else (34, 38, 66), r, border_radius=10)
                pygame.draw.rect(s, cor if ok else (60, 65, 90), r, 2 if hover else 1, border_radius=10)
                texto(s, info["nome"], 12, (255, 255, 255) if ok else (100, 105, 130), r.center)
                x += w + 8

    def _desenhar_conquistas(self):
        s = self.screen
        lista = self.cj.vida.conquistas()
        feitas = sum(c["feita"] for c in lista)
        caixa = self._fundo_modal(860, 520)
        texto(s, "CONQUISTAS", 24, (255, 255, 255), (caixa.left + 30, caixa.top + 36), ancora="midleft")
        texto(s, f"{feitas} de {len(lista)}", 15, COR_DESTAQUE, (caixa.right - 30, caixa.top + 36), ancora="midright")
        for i, c in enumerate(lista):
            col, lin = i % 2, i // 2
            r = pygame.Rect(caixa.left + 24 + col * 410, caixa.top + 70 + lin * 60, 398, 52)
            pygame.draw.rect(s, (60, 48, 14) if c["feita"] else (26, 30, 52), r, border_radius=12)
            pygame.draw.rect(s, COR_DESTAQUE if c["feita"] else (55, 60, 90), r, 2 if c["feita"] else 1,
                             border_radius=12)
            ic = icone("trofeu" if c["feita"] else "estrela", 26, COR_DESTAQUE if c["feita"] else (80, 85, 115))
            s.blit(ic, ic.get_rect(center=(r.left + 30, r.centery)))
            texto(s, c["nome"], 15, (255, 255, 255) if c["feita"] else (130, 135, 160), (r.left + 56, r.top + 17),
                  ancora="midleft")
            texto(s, c["descricao"], 11, COR_TEXTO_SUAVE if c["feita"] else (100, 105, 130),
                  (r.left + 56, r.top + 36), ancora="midleft", negrito=False)
        texto(s, "Carrega numa tecla para fechar", 12, (120, 145, 195), (caixa.centerx, caixa.bottom - 20),
              negrito=False)

    def _mostrar_aviso(self):
        """Cartão do último jogo: resultado, nota, evolução e o que mudou na vida."""
        s = self.screen
        av = self.aviso
        k = min(1.0, self.t / 0.25)
        escuro = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        escuro.fill((5, 8, 20, int(170 * k)))
        s.blit(escuro, (0, 0))
        caixa = pygame.Rect(0, 0, 580, 410)
        caixa.center = (WIDTH // 2, HEIGHT // 2 + round(30 * (1 - k)))
        _vidro(s, caixa, 18, 245, COR_DESTAQUE)
        g_eu, g_adv = av["g_eu"], av["g_adv"]
        res = "VITÓRIA" if g_eu > g_adv else ("DERROTA" if g_eu < g_adv else "EMPATE")
        cor = (90, 215, 120) if g_eu > g_adv else ((230, 80, 80) if g_eu < g_adv else (240, 200, 70))
        tipo = "JOGO SIMULADO" if av.get("simulado") else "JOGO JOGADO"
        texto(s, f"JORNADA {av['jornada']}  •  {tipo}", 13, COR_TEXTO_SUAVE, (caixa.centerx, caixa.top + 26))
        casa, fora = obter_info_equipa(av["casa"]), obter_info_equipa(av["fora"])
        eu_casa = av["casa"] == self.atleta["equipa_id"]
        gc, gf = (g_eu, g_adv) if eu_casa else (g_adv, g_eu)
        texto(s, f"{casa['sigla']}  {gc} - {gf}  {fora['sigla']}", 30, (255, 255, 255), (caixa.centerx, caixa.top + 66))
        texto(s, res, 18, cor, (caixa.centerx, caixa.top + 100))
        if av.get("ausente"):
            texto(s, "Não jogaste: " + av["ausente"].lower(), 17, (255, 130, 110), (caixa.centerx, caixa.top + 170))
        else:
            nota = av["nota"]
            circ = (caixa.left + 120, caixa.top + 186)
            pygame.draw.circle(s, cor_nota(nota), circ, 54)
            pygame.draw.circle(s, (255, 255, 255), circ, 54, 3)
            texto(s, f"{nota:.1f}".replace(".", ","), 38, (15, 20, 35), (circ[0], circ[1] - 6))
            texto(s, "NOTA", 12, (15, 20, 35), (circ[0], circ[1] + 24))
            x = caixa.left + 210
            texto(s, f"Golos: {av['golos']}     Assistências: {av['assistencias']}", 16, COR_TEXTO,
                  (x, caixa.top + 158), ancora="midleft")
            d = av["geral_depois"] - av["geral_antes"]
            texto(s, f"Geral: {av['geral_antes']:.1f} → {av['geral_depois']:.1f}".replace(".", ","), 16, COR_TEXTO,
                  (x, caixa.top + 190), ancora="midleft")
            texto(s, f"{d:+.2f}".replace(".", ","), 16, (90, 215, 120) if d >= 0 else (230, 80, 80),
                  (caixa.right - 30, caixa.top + 190), ancora="midright")
            if int(av["geral_depois"]) > int(av["geral_antes"]):
                texto(s, "SUBISTE DE NÍVEL!", 15, COR_DESTAQUE, (x, caixa.top + 222), ancora="midleft")
        y = caixa.top + 262
        for frase in av.get("vida", [])[:4]:
            if frase.startswith("Conquista: "):
                w = fonte(13).size("CONQUISTA: " + frase[11:].upper())[0] + 52
                self._selo_conquista(caixa.centerx - w // 2, y - 13, frase[11:])
                y += 30
                continue
            cor_f = (255, 130, 110) if ("Lesion" in frase or "banco" in frase or "acabou" in frase) else (130, 230, 150)
            texto(s, frase, 14, cor_f, (caixa.centerx, y))
            y += 24
        texto(s, "Carrega numa tecla para continuar", 12, (120, 145, 195), (caixa.centerx, caixa.bottom - 20),
              negrito=False)
