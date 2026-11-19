# -*- coding: utf-8 -*-
"""
tutorial.py - tutorial para quem joga pela primeira vez: missões curtas.

É uma variante do MODO TESTE (teste_variante = "tutorial"): o jogo corre sem tempo e só com os
jogadores que cada missão precisa (o jogador, um colega e um defesa). Cada missão põe os
jogadores no sítio, mostra o que fazer num painel em cima e verifica quando está cumprida.
Se correr mal (o defesa rouba a bola, o remate não entra), a missão recomeça.

Missões: patinar, passe, stickada, finta, roleta, livre (passar ou rematar), livre direto e,
no fim, a explicação dos cartões. Na pausa pode-se saltar uma missão e R recomeça-a.
Os textos mudam conforme se joga com teclado ou com comando.
"""
import math

import pygame

import comando
from componentes import texto
from sons import som

# (chave, título, texto com teclado, texto com comando)
MISSOES = [
    ("mexer", "PATINAR",
     "Patina até ao círculo amarelo com WASD ou as setas. Mantém SHIFT para acelerar.",
     "Patina até ao círculo amarelo com o stick. Mantém RB para acelerar."),
    ("passe", "PASSE",
     "Vira-te para o colega e passa-lhe a bola com Z.",
     "Vira-te para o colega e passa-lhe a bola com A."),
    ("remate", "STICKADA",
     "Carrega em X para rematar: aponta com o rato ou as setas, mantém X para ganhar força e larga. Marca golo!",
     "Carrega em B para rematar: aponta com o stick, mantém B para ganhar força e larga. Marca golo!"),
    ("finta", "FINTA",
     "O defesa vem aí. Faz uma finta com V (com uma seta escolhes o lado) e fica com a bola.",
     "O defesa vem aí. Faz uma finta com Y (com o stick escolhes o lado) e fica com a bola."),
    ("roleta", "ROLETA",
     "Deixa o defesa chegar perto e faz uma roleta com F: dás uma volta com a bola colada ao stick.",
     "Deixa o defesa chegar perto e faz uma roleta com LB: dás uma volta com a bola colada ao stick."),
    ("livre", "LIVRE",
     "Falta a teu favor! O jogo fica parado até bateres o livre: passa ao colega (Z) ou remata (X).",
     "Falta a teu favor! O jogo fica parado até bateres o livre: passa ao colega (A) ou remata (B)."),
    ("livre_direto", "LIVRE DIRETO",
     "Falta grave perto da baliza: livre direto. Só tu contra o guarda-redes. Marca golo!",
     "Falta grave perto da baliza: livre direto. Só tu contra o guarda-redes. Marca golo!"),
    ("cartoes", "CARTÕES", "", ""),
]
QUEM = {"mexer": (), "passe": ("colega",), "remate": (), "finta": ("defesa",), "roleta": ("defesa",),
        "livre": ("colega", "defesa"), "livre_direto": (), "cartoes": ()}
CARTOES = [((250, 210, 40), "AMARELO", "Um aviso. O jogador continua em jogo."),
           ((40, 120, 230), "AZUL", "O jogador sai 30 segundos (ou até a equipa sofrer um golo)."),
           ((220, 40, 40), "VERMELHO", "Expulso: a equipa joga com menos um durante 1 minuto.")]
ESPERA_OK = 1.3          # segundos com «missão cumprida» antes da missão seguinte
ESPERA_FALHA = 1.6


class TutorialMixin:

    def _tut_ativo(self) -> bool:
        return self.modo_teste and getattr(self, "teste_variante", "") == "tutorial"

    def iniciar_tutorial(self):
        self.iniciar_partida(self.equipa_casa_id, self.equipa_fora_id)
        self.modo_teste = True
        self.teste_variante = "tutorial"
        h = self.jogador_humano
        ag_c = next((a for a in self.agentes_azul if a.jogador.papel == "medio"), self.agentes_azul[0])
        ag_d = next((a for a in self.agentes_vermelhos if a.jogador.papel == "defesa"), self.agentes_vermelhos[0])
        self._tut_atores = {"humano": h, "colega": ag_c.jogador, "defesa": ag_d.jogador, "ag_defesa": ag_d}
        self.tempo_restante = 1e9
        self.teste = {"remates": 0, "golos": 0, "defesas": 0, "fora": 0, "perdidas": 0, "missao": 1}
        self._tut = {"i": 0, "feito": False, "espera": 0.0, "aviso": None, "fim": False}
        self._marcar_tutorial_visto()
        self._msg_timer = 0.0
        self._tut_preparar()

    def _marcar_tutorial_visto(self):
        self._convite_tutorial = False
        if not getattr(self, "tutorial_visto", False):
            self.tutorial_visto = True
            self._gravar_definicoes()

    # ------------------------------------------------------------------ #
    # Preparar cada missão                                                 #
    # ------------------------------------------------------------------ #

    def _tut_chave(self) -> str:
        return MISSOES[min(self._tut["i"], len(MISSOES) - 1)][0]

    def _tut_preparar(self):
        """Põe tudo no sítio para a missão atual (ou passa à seguinte, se a atual já foi cumprida)."""
        t = self._tut
        if t["fim"]:
            return
        if not t["feito"] and self._tut_chave() in ("remate", "livre_direto") and self.golos_azul > t.get("golos0", 1e9):
            t["feito"] = True                     # o golo já tinha entrado (sem estilo arcade repõe-se logo)
        if t["feito"]:
            t["i"] += 1
            t["feito"] = False
            som.tocar("apito_curto")
        if t["i"] >= len(MISSOES):
            t["i"] = len(MISSOES) - 1
            return
        self.teste["missao"] = t["i"] + 1
        chave = self._tut_chave()
        a = self._tut_atores
        h, colega, defesa = a["humano"], a["colega"], a["defesa"]
        if self.jogador_humano is not h:
            self._trocar_humano(h)
        quem = QUEM[chave]
        self.equipa_azul.empty()
        self.equipa_azul.add(h, *([colega] if "colega" in quem else []))
        self.equipa_vermelha.empty()
        self.equipa_vermelha.add(*([defesa] if "defesa" in quem else []))
        self.todos_jogadores = pygame.sprite.Group(*self.equipa_azul, *self.equipa_vermelha)
        self.agentes_azul = []
        self.agentes_vermelhos = [a["ag_defesa"]] if chave in ("finta", "roleta") else []

        self._cancelar_mira()
        self.remate_pov = None
        self._bola_parada = None
        self._reposicao_pendente = None
        self._falta_ativa = False
        self._falta_timer = 0.0
        self._falta_cooldown = 0.0
        self._teste_espera = 0.0
        self._teste_arranque = 0.9            # o defesa espera um instante antes de atacar
        for j in (h, colega, defesa):
            j.cancelar_finta()
            j.tem_bola = False

        r = self.rink.rect
        gx, cx, cy = self.rink.linha_golo_esq_x, r.centerx, r.centery
        pos = {
            "mexer": {h: (cx + 180, cy + 40)},
            "passe": {h: (cx + 60, cy + 90), colega: (cx - 140, cy - 80)},
            "remate": {h: (gx + 250, cy + 50)},
            "finta": {h: (gx + 470, cy), defesa: (gx + 300, cy)},
            "roleta": {h: (gx + 470, cy + 30), defesa: (gx + 330, cy + 30)},
            "livre": {h: (cx - 60, cy + 40), colega: (gx + 200, cy - 110), defesa: (cx - 160, cy + 60)},
            "livre_direto": {h: (gx + 135, cy)},
            "cartoes": {h: (cx + 120, cy)},
        }[chave]
        for j, (x, y) in pos.items():
            j.pos_x, j.pos_y = float(x), float(y)
            j.vel_x = j.vel_y = 0.0
            j.set_target(0.0, 0.0)
            j.rect.center = (round(j.pos_x), round(j.pos_y))
        h.vetor_direcao = pygame.math.Vector2(-1, 0)
        h._olhar_para(h.vetor_direcao)
        self.gr_vermelho.repor()
        self.gr_vermelho.pos_y = float(cy)
        self.bola.repor((h.pos_x, h.pos_y))
        self.bola.definir_dono(h)
        h.tem_bola = True
        self.bola.seguir_jogador(h)

        t.update(golos0=self.golos_azul, remates0=self.teste["remates"], t=0.0, finta=None, espera=0.0,
                 remate_t=None, solta=0.0, alvo=(cx - 160, cy - 90), tinha_livre=False)
        if chave == "livre":
            self._bola_parada = {"tipo": "livre", "marcador": h, "pos": (h.pos_x, h.pos_y), "t": 0.0,
                                 "defesa": "vermelho", "espera": 1.0}
            self._afastar_adversarios((h.pos_x, h.pos_y), "vermelho")
            t["tinha_livre"] = True
        elif chave == "livre_direto":
            self._posicionar_para_penalti(h, (h.pos_x, h.pos_y))
            self._bola_parada = {"tipo": "livre_direto", "marcador": h, "pos": (h.pos_x, h.pos_y), "t": 0.0}

    # ------------------------------------------------------------------ #
    # Verificar as missões (no lugar do _update_teste)                     #
    # ------------------------------------------------------------------ #

    def _tut_update(self, dt: float):
        t = self._tut
        if t["aviso"] is not None:
            txt, cor, resta = t["aviso"]
            t["aviso"] = (txt, cor, resta - dt) if resta > dt else None
        if t["fim"]:
            t["espera"] -= dt
            if t["espera"] <= 0:
                self.ir_para_menu_principal()
            return
        chave = self._tut_chave()
        if not t["feito"] and chave in ("remate", "livre_direto") and self.golos_azul > t["golos0"]:
            self._tut_cumprida()               # o golo: a reposição depois da festa passa à seguinte
            return
        if self._reposicao_pendente is not None or self.remate_pov is not None:
            return
        if t["espera"] > 0:
            t["espera"] -= dt
            if t["espera"] <= 0:
                self._tut_preparar()
            return
        t["t"] += dt
        a = self._tut_atores
        h, b = a["humano"], self.bola

        if chave == "mexer":
            if math.hypot(h.pos_x - t["alvo"][0], h.pos_y - t["alvo"][1]) < 40:
                self._tut_cumprida()
        elif chave == "passe":
            if b.dono is a["colega"] or self.jogador_humano is a["colega"]:
                self._tut_cumprida()
            elif self._tut_bola_perdida(dt):
                self._tut_falhou("A bola não chegou ao colega. Tenta outra vez!")
        elif chave in ("remate", "livre_direto"):
            if self.teste["remates"] > t["remates0"]:
                t["remate_t"] = (t["remate_t"] or 0.0) + dt
                if t["remate_t"] > 2.2:
                    self._tut_falhou("Quase! Tenta outra vez.")
        elif chave in ("finta", "roleta"):
            if h._finta is not None:
                t["finta"] = h._finta.get("tipo", "corte")
            certa = "roleta" if chave == "roleta" else "corte"
            if b.dono is a["defesa"]:
                self._tut_falhou("O defesa ficou com a bola. Tenta outra vez!")
            elif t["finta"] == certa and h._finta is None and h.tem_bola:
                self._tut_cumprida()
            elif self._tut_bola_perdida(dt):
                self._tut_falhou("Perdeste a bola. Tenta outra vez!")
        elif chave == "livre":
            if self._bola_parada is None and b.dono is not h:
                self._tut_cumprida()

    def _tut_bola_perdida(self, dt) -> bool:
        b = self.bola
        if b.dono is None and b.vel.length() < 25:
            self._tut["solta"] += dt
        else:
            self._tut["solta"] = 0.0
        return self._tut["solta"] > 1.5

    def _tut_cumprida(self):
        t = self._tut
        t["feito"] = True
        t["espera"] = ESPERA_OK
        t["aviso"] = ("MISSÃO CUMPRIDA!", (90, 230, 120), ESPERA_OK + 0.3)
        som.tocar("apito_curto")

    def _tut_falhou(self, msg: str):
        t = self._tut
        t["espera"] = ESPERA_FALHA
        t["aviso"] = (msg, (255, 150, 90), ESPERA_FALHA + 0.3)

    def tut_saltar(self):
        """Saltar a missão (na pausa)."""
        self._tut["feito"] = True
        if self._tut_chave() == "cartoes":
            self._tut_terminar()
        else:
            self._tut_preparar()

    def _tut_terminar(self):
        t = self._tut
        t["fim"] = True
        t["espera"] = 4.0
        som.tocar("golo", 0.6)

    def _tut_evento(self, event) -> bool:
        """Teclas próprias do tutorial. True se tratou o evento."""
        if not self._tut_ativo() or event.type != pygame.KEYDOWN:
            return False
        t = self._tut
        if t["fim"]:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z, pygame.K_ESCAPE):
                self.ir_para_menu_principal()
            return True
        if self._tut_chave() == "cartoes" and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z,
                                                             pygame.K_KP_ENTER):
            self._tut_terminar()
            return True
        if event.key == pygame.K_r:
            self._tut["feito"] = False
            self._tut_preparar()
            return True
        return False

    # ------------------------------------------------------------------ #
    # Desenho                                                              #
    # ------------------------------------------------------------------ #

    def _desenhar_tutorial(self, s):
        if not self._tut_ativo():
            return
        t = self._tut
        if t["fim"]:
            self._tut_painel_fim(s)
            return
        chave, titulo, txt_teclado, txt_comando = MISSOES[t["i"]]
        if chave == "mexer" and not t["feito"]:
            cam = self.rink.camera
            sx, sy = cam.projetar(*t["alvo"])
            k = cam.escala(t["alvo"][1])
            pulso = 1 + 0.08 * math.sin(pygame.time.get_ticks() / 150)
            anel = pygame.Rect(0, 0, round(80 * k * pulso), round(30 * k * pulso))
            anel.center = (round(sx), round(sy))
            pygame.draw.ellipse(s, (255, 220, 60), anel, 4)
        if chave == "cartoes":
            self._tut_painel_cartoes(s)
        else:
            caixa = pygame.Rect(0, 0, 820, 74)
            caixa.midtop = (s.get_width() // 2, 134)
            fundo = pygame.Surface(caixa.size, pygame.SRCALPHA)
            pygame.draw.rect(fundo, (8, 14, 32, 225), fundo.get_rect(), border_radius=12)
            s.blit(fundo, caixa)
            pygame.draw.rect(s, (255, 205, 60), caixa, 2, border_radius=12)
            texto(s, f"MISSÃO {t['i'] + 1} DE {len(MISSOES)}  •  {titulo}", 17, (255, 215, 80),
                  (caixa.left + 20, caixa.top + 18), ancora="midleft")
            self._tut_pontos(s, caixa.right - 20, caixa.top + 18)
            texto(s, txt_comando if comando.ligado() else txt_teclado, 15, (230, 238, 255),
                  (caixa.left + 20, caixa.top + 48), ancora="midleft", negrito=False)
        if t["aviso"] is not None:
            msg, cor, _r = t["aviso"]
            texto(s, msg, 34, cor, (s.get_width() // 2, 262), sombra=True)
        texto(s, "R  recomeçar a missão     ESC  pausa (saltar a missão)", 12, (190, 205, 235),
              (s.get_width() // 2, 528), sombra=True, negrito=False)

    def _tut_pontos(self, s, direita, y):
        """Uma bolinha por missão: verdes as feitas, amarela a atual."""
        n = len(MISSOES)
        for k in range(n):
            x = direita - (n - 1 - k) * 18
            i = self._tut["i"]
            cor = (90, 220, 120) if k < i or (k == i and self._tut["feito"]) else (
                (255, 205, 60) if k == i else (60, 75, 110))
            pygame.draw.circle(s, cor, (x, y), 6)

    def _tut_painel_cartoes(self, s):
        caixa = pygame.Rect(0, 0, 720, 300)
        caixa.center = (s.get_width() // 2, 300)
        fundo = pygame.Surface(caixa.size, pygame.SRCALPHA)
        pygame.draw.rect(fundo, (8, 14, 32, 235), fundo.get_rect(), border_radius=16)
        s.blit(fundo, caixa)
        pygame.draw.rect(s, (255, 205, 60), caixa, 2, border_radius=16)
        texto(s, f"MISSÃO {len(MISSOES)} DE {len(MISSOES)}  •  CARTÕES", 18, (255, 215, 80),
              (caixa.centerx, caixa.top + 28))
        texto(s, "Cuidado com as faltas! Empurrar ou entrar por trás dá falta, e as mais graves dão cartão:",
              14, (220, 230, 250), (caixa.centerx, caixa.top + 60), negrito=False)
        for k, (cor, nome, desc) in enumerate(CARTOES):
            y = caixa.top + 104 + k * 50
            cartao = pygame.Rect(caixa.left + 50, y - 20, 28, 38)
            pygame.draw.rect(s, (10, 10, 10), cartao.move(2, 2), border_radius=4)
            pygame.draw.rect(s, cor, cartao, border_radius=4)
            texto(s, nome, 17, (255, 255, 255), (caixa.left + 100, y - 2), ancora="midleft")
            texto(s, desc, 14, (210, 222, 245), (caixa.left + 220, y - 2), ancora="midleft", negrito=False)
        tecla = "A" if comando.ligado() else "ENTER"
        texto(s, f"Carrega em {tecla} para acabar o tutorial", 16, (120, 230, 150), (caixa.centerx, caixa.bottom - 26))

    def _tut_painel_fim(self, s):
        caixa = pygame.Rect(0, 0, 640, 190)
        caixa.center = (s.get_width() // 2, 300)
        fundo = pygame.Surface(caixa.size, pygame.SRCALPHA)
        pygame.draw.rect(fundo, (8, 14, 32, 235), fundo.get_rect(), border_radius=16)
        s.blit(fundo, caixa)
        pygame.draw.rect(s, (90, 220, 120), caixa, 2, border_radius=16)
        texto(s, "TUTORIAL CONCLUÍDO!", 34, (90, 230, 120), (caixa.centerx, caixa.top + 48), sombra=True)
        texto(s, "Já sabes tudo. Agora experimenta um jogo rápido ou o modo carreira.", 15,
              (220, 230, 250), (caixa.centerx, caixa.top + 100), negrito=False)
        texto(s, "Os controlos estão sempre nas Definições.", 13, (170, 190, 230),
              (caixa.centerx, caixa.top + 130), negrito=False)
        self._tut_pontos(s, caixa.centerx + (len(MISSOES) - 1) * 9, caixa.bottom - 22)

    # ------------------------------------------------------------------ #
    # Convite na primeira vez (menu principal)                             #
    # ------------------------------------------------------------------ #

    def _convite_evento(self, event) -> bool:
        """Enquanto o convite está aberto, trata as teclas e cliques. True se tratou o evento."""
        if not getattr(self, "_convite_tutorial", False):
            return False
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.iniciar_tutorial()
            elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_n):
                self._marcar_tutorial_visto()
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            sim, nao = self._convite_botoes()
            if sim.collidepoint(event.pos):
                self.iniciar_tutorial()
            elif nao.collidepoint(event.pos):
                self._marcar_tutorial_visto()
            return True
        return event.type != pygame.QUIT

    def _convite_botoes(self):
        cx, cy = self.screen.get_width() // 2, self.screen.get_height() // 2
        sim = pygame.Rect(0, 0, 240, 50)
        sim.midtop = (cx - 130, cy + 34)
        nao = pygame.Rect(0, 0, 200, 50)
        nao.midtop = (cx + 130, cy + 34)
        return sim, nao

    def _desenhar_convite(self):
        if not getattr(self, "_convite_tutorial", False):
            return
        s = self.screen
        sombra = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        sombra.fill((0, 0, 0, 150))
        s.blit(sombra, (0, 0))
        cx, cy = s.get_width() // 2, s.get_height() // 2
        caixa = pygame.Rect(0, 0, 620, 230)
        caixa.center = (cx, cy)
        pygame.draw.rect(s, (12, 20, 44), caixa, border_radius=16)
        pygame.draw.rect(s, (255, 205, 60), caixa, 2, border_radius=16)
        texto(s, "É A TUA PRIMEIRA VEZ?", 28, (255, 215, 80), (cx, caixa.top + 40), sombra=True)
        texto(s, "Faz o tutorial: 8 missões curtas para aprender a patinar, passar,", 15, (225, 233, 252),
              (cx, caixa.top + 84), negrito=False)
        texto(s, "fintar, fazer a stickada e marcar livres. Demora uns 3 minutos.", 15, (225, 233, 252),
              (cx, caixa.top + 106), negrito=False)
        sim, nao = self._convite_botoes()
        mpos = pygame.mouse.get_pos()
        for r, nome, cor in ((sim, "FAZER O TUTORIAL", (40, 190, 100)), (nao, "AGORA NÃO", (90, 100, 140))):
            pygame.draw.rect(s, cor if r.collidepoint(mpos) or r is sim else (30, 40, 70), r, border_radius=12)
            pygame.draw.rect(s, (255, 255, 255) if r is sim else (120, 135, 180), r, 2, border_radius=12)
            texto(s, nome, 17, (255, 255, 255), r.center)
        tecla_sim, tecla_nao = ("A", "B") if comando.ligado() else ("ENTER", "ESC")
        texto(s, f"{tecla_sim}  fazer o tutorial      {tecla_nao}  agora não  (está sempre no MODO TESTE)", 12,
              (150, 170, 215), (cx, caixa.bottom - 18), negrito=False)
