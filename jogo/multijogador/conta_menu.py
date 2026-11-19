# -*- coding: utf-8 -*-
"""
conta_menu.py - ecrã "A MINHA CONTA" (abre no botão da conta, no canto do menu principal).

Fases:
  "fora"       entrar (alcunha + palavra-passe)
  "criar"      criar conta (alcunha + palavra-passe duas vezes)
  "recuperar"  esqueci-me da palavra-passe (alcunha + código de recuperação + nova palavra-passe)
  "codigo"     mostra o código de recuperação depois de criar a conta (para escrever num papel)
  "dentro"     o perfil (pontos, lugar no ranking, jogos) e o progresso na nuvem
  "ranking"    os melhores jogadores e os últimos jogos online

O ecrã só desenha e devolve ações; quem fala com o servidor é o Game (conta.py).
"""

import pygame

from settings import WIDTH, HEIGHT
from componentes import texto, ListaBotoes, painel_vidro, COR_DESTAQUE, COR_TEXTO, COR_TEXTO_SUAVE
from graficos import icone, luz
from menu import BotaoMenu, _fundo_arena
from conta import FICHEIROS_SAVE, NOMES_SAVE, ContaLocal, data_curta

COR_CONTA = (255, 170, 60)


class Campo:
    def __init__(self, nome: str, rotulo: str, segredo: bool = False, maximo: int = 16):
        self.nome, self.rotulo, self.segredo, self.maximo = nome, rotulo, segredo, maximo
        self.valor = ""
        self.rect = pygame.Rect(0, 0, 0, 0)


FASES_CAMPOS = {
    "fora": [("alcunha", "Alcunha", False, 16), ("senha", "Palavra-passe", True, 64)],
    "criar": [("alcunha", "Alcunha (é o nome que os outros veem)", False, 16),
              ("senha", "Palavra-passe (pelo menos 6 caracteres)", True, 64),
              ("senha2", "Repete a palavra-passe", True, 64)],
    "recuperar": [("alcunha", "Alcunha", False, 16), ("codigo", "Código de recuperação (STK-....-....)", False, 14),
                  ("senha", "Nova palavra-passe", True, 64)],
}


class EcraConta:
    def __init__(self, screen: pygame.Surface, arena=None, conta=None):
        self.screen = screen
        self.arena = arena
        self.conta = conta
        self.servidor = None
        self.t = 0.0
        self.erro = ""
        self.info = ""
        self.ocupado = False           # à espera de uma resposta do servidor
        self.escolher = False          # nuvem e PC com progresso: o jogador escolhe
        self.versoes_nuvem = {}
        self.codigo_rec = ""
        self.ranking = None
        self.eu = None
        self.historico = None
        self.caixa = pygame.Rect(WIDTH // 2 - 400, 132, 800, 500)
        self.campos = []
        self.foco_campo = 0
        self.mudar_fase("dentro" if conta is not None and conta.ligada else "fora")

    # ------------------------------------------------------------------ #
    def limpar_campos(self):
        for c in self.campos:
            c.valor = ""

    def mudar_fase(self, fase: str):
        guardados = {c.nome: c.valor for c in self.campos if not c.segredo}
        self.fase = fase
        self.erro = self.info = "" if fase not in ("dentro",) else self.info
        cx, cx0 = WIDTH // 2, self.caixa.left
        base = self.caixa.bottom - 70
        self.campos = []
        for i, (nome, rot, seg, mx) in enumerate(FASES_CAMPOS.get(fase, [])):
            c = Campo(nome, rot, seg, mx)
            c.valor = guardados.get(nome, "")
            c.rect = pygame.Rect(cx - 220, self.caixa.top + 108 + i * 78, 440, 44)
            self.campos.append(c)
        self.foco_campo = 0 if self.campos else None
        if fase == "fora":
            botoes = [BotaoMenu((cx - 290, base, 280, 54), "ENTRAR", "", "ok", (40, 190, 100), "jogar",
                                seta=False, tamanho=20),
                      BotaoMenu((cx + 10, base, 280, 54), "VOLTAR", "", "voltar", (150, 110, 255), "casa",
                                seta=False, tamanho=18)]
        elif fase in ("criar", "recuperar"):
            nome = "CRIAR CONTA" if fase == "criar" else "MUDAR A PALAVRA-PASSE"
            botoes = [BotaoMenu((cx - 290, base, 280, 54), nome, "", "ok", (40, 190, 100), "jogar",
                                seta=False, tamanho=18),
                      BotaoMenu((cx + 10, base, 280, 54), "VOLTAR", "", "voltar_fora", (150, 110, 255), "casa",
                                seta=False, tamanho=18)]
        elif fase == "codigo":
            botoes = [BotaoMenu((cx - 170, base, 340, 54), "JÁ ESCREVI O CÓDIGO", "", "continuar", (40, 190, 100),
                                "jogar", seta=False, tamanho=18)]
        elif fase == "ranking":
            botoes = [BotaoMenu((cx - 140, base + 6, 280, 50), "VOLTAR", "", "voltar_dentro", (150, 110, 255), "casa",
                                seta=False, tamanho=18)]
        else:   # dentro
            x, bw = cx0 + 420, 350
            botoes = [BotaoMenu((x, self.caixa.top + 210, bw, 56), "GUARDAR NA NUVEM", "Envia o progresso deste PC",
                                "enviar_nuvem", (40, 190, 100), "globo"),
                      BotaoMenu((x, self.caixa.top + 274, bw, 56), "TRAZER DA NUVEM", "Usa neste PC o progresso guardado",
                                "trazer_nuvem", (40, 200, 210), "avancar"),
                      BotaoMenu((x, self.caixa.top + 338, bw, 56), "RANKING", "Os melhores jogadores online",
                                "ranking", (255, 175, 40), "trofeu"),
                      BotaoMenu((cx0 + 30, base, 240, 50), "SAIR DA CONTA", "", "sair_conta", (230, 70, 70), "sair",
                                seta=False, tamanho=17),
                      BotaoMenu((cx + 140, base, 240, 50), "VOLTAR", "", "voltar", (150, 110, 255), "casa",
                                seta=False, tamanho=17)]
        self.lista = ListaBotoes(botoes)
        self.lista.foco = 0
        try:
            if self.campos:
                pygame.key.start_text_input()
            else:
                pygame.key.stop_text_input()
        except pygame.error:
            pass

    # ------------------------------------------------------------------ #
    def _acao_ok(self):
        v = {c.nome: c.valor.strip() if not c.segredo else c.valor for c in self.campos}
        if any(not c.valor for c in self.campos):
            self.erro = "Preenche todos os campos."
            return None
        if self.fase == "fora":
            return ("entrar", v["alcunha"], v["senha"])
        if self.fase == "criar":
            return ("criar", v["alcunha"], v["senha"], v["senha2"])
        return ("recuperar", v["alcunha"], v["codigo"], v["senha"])

    def _links(self):
        """Ligações de texto da fase "fora": criar conta e esqueci-me da palavra-passe."""
        y = self.caixa.top + 290
        criar = pygame.Rect(0, 0, 300, 26)
        criar.center = (WIDTH // 2, y)
        rec = pygame.Rect(0, 0, 300, 26)
        rec.center = (WIDTH // 2, y + 34)
        return criar, rec

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return "sair"
        if self.fase == "dentro" and self.escolher:
            r_env, r_tra = self._botoes_escolher()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if r_env.collidepoint(event.pos):
                    return "enviar_nuvem"
                if r_tra.collidepoint(event.pos):
                    return "trazer_nuvem"
        if self.campos and self.foco_campo is not None:
            campo = self.campos[self.foco_campo]
            if event.type == pygame.TEXTINPUT:
                if len(campo.valor) < campo.maximo:
                    campo.valor += event.text[:campo.maximo - len(campo.valor)]
                self.erro = ""
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    campo.valor = campo.valor[:-1]
                    return None
                if event.key in (pygame.K_TAB, pygame.K_DOWN):
                    if self.foco_campo + 1 < len(self.campos):
                        self.foco_campo += 1
                    elif event.key == pygame.K_DOWN:
                        self.foco_campo = None            # passa para os botões
                    else:
                        self.foco_campo = 0
                    return None
                if event.key == pygame.K_UP:
                    self.foco_campo = max(0, self.foco_campo - 1)
                    return None
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if self.foco_campo + 1 < len(self.campos) and not self.campos[self.foco_campo + 1].valor:
                        self.foco_campo += 1
                        return None
                    return self._acao_ok()
                if event.key == pygame.K_ESCAPE:
                    return "voltar" if self.fase == "fora" else self._voltar_fora()
                if event.key == pygame.K_v and event.mod & pygame.KMOD_CTRL:
                    self._colar(campo)
                    return None
                return None                                 # letras: são para o campo
        elif self.campos and event.type == pygame.KEYDOWN and event.key == pygame.K_UP and self.lista.foco == 0:
            self.foco_campo = len(self.campos) - 1
            return None
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return {"fora": "voltar", "dentro": "voltar", "ranking": "voltar_dentro",
                    "codigo": "continuar"}.get(self.fase, self._voltar_fora())
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, c in enumerate(self.campos):
                if c.rect.collidepoint(event.pos):
                    self.foco_campo = i
                    return None
            if self.fase == "fora":
                criar, rec = self._links()
                if criar.collidepoint(event.pos):
                    self.mudar_fase("criar")
                    return None
                if rec.collidepoint(event.pos):
                    self.mudar_fase("recuperar")
                    return None
        if self.fase == "fora" and event.type == pygame.KEYDOWN and self.foco_campo is None:
            if event.key == pygame.K_c:
                self.mudar_fase("criar")
                return None
        acao = self.lista.handle_event(event)
        if acao == "ok":
            return self._acao_ok()
        if acao == "voltar_fora":
            return self._voltar_fora()
        return acao

    def _voltar_fora(self):
        self.mudar_fase("fora")
        return None

    def _colar(self, campo: Campo):
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            dados = (pygame.scrap.get_text() or "").strip()
        except (pygame.error, AttributeError, NotImplementedError):
            return
        campo.valor = (campo.valor + dados)[:campo.maximo]

    def update(self, dt: float):
        self.t += dt
        for i, b in enumerate(self.lista.botoes):
            b.animar(dt, i == self.lista.foco and self.foco_campo is None)

    # ------------------------------------------------------------------ #
    def draw(self):
        s = self.screen
        s.blit(_fundo_arena(self.arena), (0, 0))
        brilho = luz(900, 520, COR_CONTA, 40)
        s.blit(brilho, brilho.get_rect(center=(WIDTH // 2, 360)), special_flags=pygame.BLEND_RGB_ADD)
        ic = icone("jogador", 42, COR_CONTA)
        s.blit(ic, ic.get_rect(center=(WIDTH // 2, 46)))
        titulos = {"fora": "ENTRAR NA CONTA", "criar": "CRIAR CONTA", "recuperar": "RECUPERAR A CONTA",
                   "codigo": "CÓDIGO DE RECUPERAÇÃO", "dentro": "A MINHA CONTA", "ranking": "RANKING ONLINE"}
        texto(s, titulos[self.fase], 34, COR_TEXTO, (WIDTH // 2, 94), sombra=True)
        painel_vidro(s, self.caixa, 20, 230, (150, 110, 60))
        getattr(self, "_desenhar_" + self.fase)(s, self.caixa)
        for c in self.campos:
            self._desenhar_campo(s, c, self.campos.index(c) == self.foco_campo)
        self.lista.draw(s)
        y = self.caixa.bottom + 22
        if self.ocupado:
            txt = "A falar com o servidor" + "." * (1 + int(self.t * 2.5) % 3)
            if self.servidor is not None and self.servidor.a_acordar():
                txt = "A acordar o servidor do jogo (pode demorar até 1 minuto)" + "." * (1 + int(self.t * 2.5) % 3)
            texto(s, txt, 15, (240, 200, 90), (WIDTH // 2, y))
        elif self.erro:
            texto(s, self.erro, 15, (255, 110, 100), (WIDTH // 2, y))
        elif self.info:
            texto(s, self.info, 15, (110, 230, 150), (WIDTH // 2, y))
        dica = ("TAB  próximo campo     ENTER  confirmar     CTRL+V  colar     ESC  voltar" if self.campos
                else "↑ ↓  escolher     ENTER  confirmar     ESC  voltar")
        texto(s, dica, 12, (120, 145, 195), (WIDTH // 2, HEIGHT - 18), negrito=False)

    def _desenhar_campo(self, s, c: Campo, focado: bool):
        texto(s, c.rotulo, 14, (200, 215, 245), (c.rect.left + 4, c.rect.top - 14), ancora="midleft", negrito=False)
        pygame.draw.rect(s, (8, 14, 30), c.rect, border_radius=10)
        pygame.draw.rect(s, COR_CONTA if focado else (70, 90, 130), c.rect, 2, border_radius=10)
        mostrar = "•" * len(c.valor) if c.segredo else c.valor
        r = texto(s, mostrar, 20, (255, 255, 255), (c.rect.left + 16, c.rect.centery), ancora="midleft",
                  negrito=False) if mostrar else pygame.Rect(c.rect.left + 16, c.rect.centery, 0, 0)
        if focado and int(self.t * 2) % 2 == 0:
            x = (r.right if mostrar else c.rect.left + 16) + 3
            pygame.draw.line(s, COR_CONTA, (x, c.rect.centery - 11), (x, c.rect.centery + 11), 2)

    # ------------------------------------------------------------------ fases
    def _desenhar_fora(self, s, caixa):
        texto(s, "Com uma conta, as tuas carreiras ficam guardadas na nuvem e os jogos online contam para o ranking.",
              14, COR_TEXTO_SUAVE, (WIDTH // 2, caixa.top + 36), negrito=False)
        texto(s, "Não pedimos email nem dados pessoais: só uma alcunha e uma palavra-passe.", 13,
              (150, 175, 215), (WIDTH // 2, caixa.top + 60), negrito=False)
        criar, rec = self._links()
        mpos = pygame.mouse.get_pos()
        texto(s, "Ainda não tens conta?  CRIAR CONTA  (C)", 16,
              (255, 220, 120) if criar.collidepoint(mpos) else COR_CONTA, criar.center)
        texto(s, "Esqueci-me da palavra-passe", 14,
              (255, 255, 255) if rec.collidepoint(mpos) else (170, 190, 230), rec.center, negrito=False)

    def _desenhar_criar(self, s, caixa):
        texto(s, "Escolhe uma alcunha e uma palavra-passe. Não precisas de email.", 14, COR_TEXTO_SUAVE,
              (WIDTH // 2, caixa.top + 40), negrito=False)

    def _desenhar_recuperar(self, s, caixa):
        texto(s, "Usa o código que o jogo te mostrou quando criaste a conta.", 14, COR_TEXTO_SUAVE,
              (WIDTH // 2, caixa.top + 40), negrito=False)

    def _desenhar_codigo(self, s, caixa):
        texto(s, "Escreve este código num papel e guarda-o bem.", 18, COR_TEXTO, (WIDTH // 2, caixa.top + 60))
        texto(s, "É a única forma de recuperar a conta se te esqueceres da palavra-passe.", 15,
              COR_TEXTO_SUAVE, (WIDTH // 2, caixa.top + 92), negrito=False)
        r = pygame.Rect(0, 0, 520, 110)
        r.center = (WIDTH // 2, caixa.top + 210)
        pygame.draw.rect(s, (8, 14, 30), r, border_radius=18)
        pygame.draw.rect(s, COR_CONTA, r, 3, border_radius=18)
        texto(s, self.codigo_rec, 54, (255, 255, 255), r.center)
        texto(s, "Ninguém da equipa do jogo te vai pedir este código.", 13, (150, 175, 215),
              (WIDTH // 2, caixa.top + 300), negrito=False)

    def _botoes_escolher(self):
        a = pygame.Rect(0, 0, 175, 38)
        a.topleft = (self.caixa.left + 40, self.caixa.top + 400)
        b = a.move(188, 0)
        return a, b

    def _desenhar_dentro(self, s, caixa):
        p = (self.servidor.perfil if self.servidor is not None and self.servidor.perfil else None) \
            or (self.conta.perfil if self.conta else None) or {}
        x = caixa.left + 40
        texto(s, (self.conta.alcunha or "") if self.conta else "", 34, COR_CONTA, (x, caixa.top + 46), ancora="midleft")
        if p:
            texto(s, f"{p.get('pontos', 1000)} pontos  •  {p.get('posicao', '?')}.º lugar no ranking", 18,
                  COR_TEXTO, (x, caixa.top + 86), ancora="midleft")
            texto(s, f"Jogos online: {p.get('jogos', 0)}  ({p.get('vitorias', 0)} V  {p.get('empates', 0)} E  "
                     f"{p.get('derrotas', 0)} D)   •   golos: {p.get('golos_marcados', 0)}", 14, COR_TEXTO_SUAVE,
                  (x, caixa.top + 114), ancora="midleft", negrito=False)
        texto(s, "PROGRESSO DAS CARREIRAS", 15, COR_DESTAQUE, (x, caixa.top + 160), ancora="midleft")
        sinc = self.conta.estado_sinc() if self.conta and self.conta.ligada else {"versoes": {}}
        for i, tipo in enumerate(FICHEIROS_SAVE):
            y = caixa.top + 196 + i * 72
            texto(s, NOMES_SAVE[tipo], 16, COR_TEXTO, (x, y), ancora="midleft")
            local = data_curta(ContaLocal.mtime(tipo)) if ContaLocal.existe(tipo) else "sem progresso"
            nuvem = data_curta(self.versoes_nuvem.get(tipo)) if self.versoes_nuvem.get(tipo) else "nada guardado"
            texto(s, f"Neste PC: {local}", 13, COR_TEXTO_SUAVE, (x + 14, y + 22), ancora="midleft", negrito=False)
            texto(s, f"Na nuvem: {nuvem}", 13, COR_TEXTO_SUAVE, (x + 14, y + 42), ancora="midleft", negrito=False)
        if self.escolher:
            texto(s, "Este PC e a nuvem têm progresso diferente.", 14, (255, 210, 120),
                  (x, caixa.top + 350), ancora="midleft")
            texto(s, "Qual queres manter?", 14, (255, 210, 120), (x, caixa.top + 374), ancora="midleft")
            mpos = pygame.mouse.get_pos()
            for r, nome in zip(self._botoes_escolher(), ("FICA O DESTE PC", "FICA O DA NUVEM")):
                pygame.draw.rect(s, (40, 70, 120) if r.collidepoint(mpos) else (20, 34, 66), r, border_radius=10)
                pygame.draw.rect(s, (255, 210, 120), r, 2, border_radius=10)
                texto(s, nome, 15, (255, 255, 255), r.center)
        elif sinc.get("ok"):
            texto(s, "O progresso deste PC vai sozinho para a nuvem", 13,
                  (120, 220, 160), (x, caixa.top + 356), ancora="midleft", negrito=False)
            texto(s, "depois de cada jogo das carreiras.", 13,
                  (120, 220, 160), (x, caixa.top + 376), ancora="midleft", negrito=False)

    def _desenhar_ranking(self, s, caixa):
        x0 = caixa.left + 30
        texto(s, "OS MELHORES", 15, COR_DESTAQUE, (x0, caixa.top + 28), ancora="midleft")
        if self.ranking is None:
            texto(s, "A carregar" + "." * (1 + int(self.t * 2.5) % 3), 16, COR_TEXTO_SUAVE, (x0, caixa.top + 70),
                  ancora="midleft")
        else:
            cab = caixa.top + 56
            for txt, dx in (("#", 0), ("ALCUNHA", 40), ("PONTOS", 250), ("V-E-D", 330), ("GOLOS", 420)):
                texto(s, txt, 12, (150, 175, 215), (x0 + dx, cab), ancora="midleft")
            minha = self.eu["id"] if self.eu else None
            for i, j in enumerate(self.ranking[:14]):
                y = cab + 24 + i * 24
                cor = COR_CONTA if j.get("id") == minha else COR_TEXTO
                texto(s, f"{i + 1}.", 14, cor, (x0, y), ancora="midleft")
                texto(s, j["alcunha"], 14, cor, (x0 + 40, y), ancora="midleft")
                texto(s, str(j["pontos"]), 14, cor, (x0 + 250, y), ancora="midleft")
                texto(s, f"{j['vitorias']}-{j['empates']}-{j['derrotas']}", 14, cor, (x0 + 330, y), ancora="midleft",
                      negrito=False)
                texto(s, str(j["golos_marcados"]), 14, cor, (x0 + 420, y), ancora="midleft", negrito=False)
            if not self.ranking:
                texto(s, "Ainda ninguém jogou online com conta.", 14, COR_TEXTO_SUAVE, (x0, cab + 30), ancora="midleft")
            if self.eu:
                texto(s, f"Tu: {self.eu['pontos']} pontos  •  {self.eu['posicao']}.º lugar", 15, COR_CONTA,
                      (x0, caixa.bottom - 110), ancora="midleft")
        x1 = caixa.left + 510
        texto(s, "OS MEUS ÚLTIMOS JOGOS", 15, COR_DESTAQUE, (x1, caixa.top + 28), ancora="midleft")
        if self.historico:
            for i, h in enumerate(self.historico[:12]):
                y = caixa.top + 64 + i * 26
                cor = (110, 230, 150) if h["eu"] > h["ele"] else ((255, 130, 110) if h["eu"] < h["ele"] else COR_TEXTO)
                texto(s, f"{h['eu']}-{h['ele']}  vs {h['adversario']}", 14, cor, (x1, y), ancora="midleft")
                d = h["pontos"]
                texto(s, f"{'+' if d > 0 else ''}{d}", 14, cor, (caixa.right - 30, y), ancora="midright")
        elif self.historico is not None:
            texto(s, "Ainda não jogaste online com a conta.", 14, COR_TEXTO_SUAVE, (x1, caixa.top + 64), ancora="midleft",
                  negrito=False)
        texto(s, "Só contam os jogos online em que os dois jogadores têm conta.", 12, (150, 175, 215),
              (WIDTH // 2, caixa.bottom - 84), negrito=False)


class BotaoConta:
    """Botão do canto do menu principal: «ENTRAR» ou a alcunha e os pontos."""

    def __init__(self, conta, topo_esq=(24, 22)):
        self.conta = conta
        self.acao = "conta"
        self.k = 0.0
        self.rect = pygame.Rect(topo_esq, (230, 52))

    def por_cima(self, pos) -> bool:
        return self.rect.collidepoint(pos)

    def animar(self, dt: float, focado: bool):
        self.k += ((1.0 if focado else 0.0) - self.k) * min(1.0, dt * 12)

    def draw(self, surf, _mpos=None, focado: bool = False):
        r, k = self.rect, self.k
        pygame.draw.rect(surf, (0, 0, 0), r.move(2, 3), border_radius=26)
        fundo = tuple(int(a + (b - a) * k) for a, b in zip((18, 28, 56), (120, 80, 30)))
        pygame.draw.rect(surf, fundo, r, border_radius=26)
        pygame.draw.rect(surf, COR_CONTA if k > 0.3 else (130, 110, 80), r, 2, border_radius=26)
        pygame.draw.circle(surf, (40, 30, 15), (r.left + 26, r.centery), 18)
        ic = icone("jogador", 24, COR_CONTA)
        surf.blit(ic, ic.get_rect(center=(r.left + 26, r.centery)))
        if self.conta is not None and self.conta.ligada:
            texto(surf, self.conta.alcunha or "", 16, (255, 255, 255), (r.left + 54, r.centery - 9), ancora="midleft")
            p = self.conta.perfil or {}
            texto(surf, f"{p.get('pontos', 1000)} pontos", 12, (255, 210, 140), (r.left + 54, r.centery + 11),
                  ancora="midleft", negrito=False)
        else:
            texto(surf, "ENTRAR / CRIAR CONTA", 14, (255, 255, 255), (r.left + 54, r.centery), ancora="midleft")
