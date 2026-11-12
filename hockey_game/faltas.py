# -*- coding: utf-8 -*-
"""
faltas.py - o que acontece DEPOIS de uma falta (bolas paradas e cartões).

A falta é detetada em player.py (empurrar_separar) e assinalada em game.py (assinalar_falta).
Este módulo junta ao Game (como o OnlineMixin) o resto das regras:

  - LIVRE: o relógio pára, os adversários ficam a DIST_LIVRE da bola e só recomeça quando
    quem marca o livre joga a bola (a IA espera um instante antes de jogar).
  - PENÁLTI e LIVRE DIRETO: os outros jogadores ficam atrás de quem bate; se for a equipa
    do jogador, abre o remate na primeira pessoa contra o guarda-redes (sem defesas);
    se for a IA, remata no jogo 2D para um canto e o guarda-redes tenta defender.
  - CARTÕES: faltas graves podem dar cartão azul (fora CARTAO_AZUL_S segundos, ou até a
    equipa sofrer um golo) e as violentas cartão vermelho (expulso; a equipa joga com menos
    um durante CARTAO_VERMELHO_S segundos e depois entra um suplente). Dois azuis = vermelho.

No jogo online e no modo teste fica como antes (a falta só dá a posse da bola).
"""
import math
import random

import pygame

from ball import REMATE_FORCA
from remate_pov import RematePOV, MEIA_BOCA
from sons import som

DIST_LIVRE = 100            # distância mínima dos adversários à bola num livre (px)
DIST_PENALTI = 95           # marca de penálti, a partir da linha de golo
DIST_LIVRE_DIRETO = 135     # marca de livre direto (mais longe do que a de penálti)
PREPARAR_S = 1.6            # tempo com o jogo parado antes de bater o penálti / livre direto
LIMITE_LIVRE_S = 7.0        # se ninguém jogar a bola, o livre acaba sozinho
FORCA_PENALTI_IA = (1.0, 1.2)  # força do remate da IA (vezes a força normal de remate)
CANTO_PENALTI_IA = (0.55, 0.95)  # para onde a IA aponta (0 = meio da baliza, 1 = poste)
CARTAO_AZUL_S = 30.0        # tempo de jogo fora com cartão azul
CARTAO_VERMELHO_S = 60.0    # tempo com menos um depois de um vermelho (depois entra um suplente)


class FaltasMixin:

    # ------------------------------------------------------------------ #
    # Estado                                                               #
    # ------------------------------------------------------------------ #

    def _faltas_reiniciar(self):
        """No início de cada partida."""
        self._bola_parada = None      # livre, penálti ou livre direto a decorrer
        self._suspensos = []          # jogadores fora por cartão
        self._falta_cartao = None     # cor do cartão da última falta (para o aviso)
        self._azuis = {}              # jogador -> cartões azuis nesta partida
        self._amarelos = {}           # jogador -> cartões amarelos (aviso) nesta partida

    def _faltas_completas(self) -> bool:
        return not self.online and not self.modo_teste

    # ------------------------------------------------------------------ #
    # Depois do apito                                                      #
    # ------------------------------------------------------------------ #

    def _depois_da_falta(self, infrator, vitima, cartao, pos_bola):
        """
        Chamado no fim de assinalar_falta (a bola já está no sítio e com a equipa certa).
        cartao: None, "amarelo", "azul" ou "vermelho" (decidido antes, em _decidir_cartao).
        """
        if cartao == "amarelo":
            # Amarelo = aviso: o jogador continua em jogo
            self._amarelos[infrator] = self._amarelos.get(infrator, 0) + 1
            self._falta_cartao = "amarelo"
            self._falta_timer = 3.0
            self._msg_falta_sub = f"CARTÃO AMARELO para {infrator.nome} (aviso)  •  " + self._msg_falta_sub
        elif cartao and self._dar_cartao(infrator, cartao):
            self._falta_cartao = cartao
            self._falta_timer = 3.0
            nome = "CARTÃO VERMELHO" if cartao == "vermelho" else "CARTÃO AZUL"
            fora = "expulso" if cartao == "vermelho" else f"{int(CARTAO_AZUL_S)} s fora"
            self._msg_falta_sub = f"{nome} para {infrator.nome} ({fora})"

        marcador = self.bola.dono
        if marcador is None:
            return
        if self._falta_tipo == "livre":
            self._bola_parada = {"tipo": "livre", "marcador": marcador, "pos": tuple(pos_bola), "t": 0.0,
                                 "defesa": infrator.equipa,
                                 "espera": 0.0 if marcador.humano else random.uniform(0.8, 1.4)}
        else:
            self._posicionar_para_penalti(marcador, pos_bola)
            self._bola_parada = {"tipo": self._falta_tipo, "marcador": marcador, "pos": tuple(pos_bola),
                                 "t": 0.0}

    def _posicionar_para_penalti(self, marcador, pos_bola):
        """Os outros jogadores de campo ficam atrás de quem bate (longe da baliza)."""
        r = self.rink.rect
        o = 1 if marcador.equipa == "azul" else -1      # para longe da baliza atacada
        outros = [j for j in self.todos_jogadores if j is not marcador]
        n = max(1, len(outros) - 1)
        for i, j in enumerate(outros):
            x = pos_bola[0] + o * (175 + (i % 2) * 55)
            y = r.centery - 150 + i * 300 / n
            j.pos_x = float(max(r.left + 30, min(r.right - 30, x)))
            j.pos_y = float(max(r.top + 30, min(r.bottom - 30, y)))
            j.vel_x = j.vel_y = 0.0
            j.rect.center = (round(j.pos_x), round(j.pos_y))
            j.set_target(0.0, 0.0)
        marcador.vel_x = marcador.vel_y = 0.0

    # ------------------------------------------------------------------ #
    # Cartões                                                              #
    # ------------------------------------------------------------------ #

    def _decidir_cartao(self, infrator, gravidade: str, penalti: bool = False):
        """
        Amarelo = aviso; azul = fora 30 s; vermelho = expulso.
        2.º amarelo = azul e 2.º azul = vermelho (na mesma partida).
        """
        sorte = random.random()
        if gravidade == "violenta":
            cartao = "vermelho" if sorte < 0.30 else "azul"
        elif gravidade == "grave":
            cartao = "azul" if sorte < 0.35 else ("amarelo" if sorte < 0.85 else None)
        else:
            cartao = "amarelo" if sorte < (0.30 if penalti else 0.14) else None
        if cartao == "amarelo" and self._amarelos.get(infrator, 0) >= 1:
            cartao = "azul"
        if cartao == "azul" and self._azuis.get(infrator, 0) >= 1:
            cartao = "vermelho"
        if cartao in ("azul", "vermelho"):
            equipa = self.equipa_azul if infrator.equipa == "azul" else self.equipa_vermelha
            if len(equipa) <= 2 or (self.modo_jogador and infrator is getattr(self, "_cj_jogador", None)):
                cartao = "amarelo"   # não se tira mais ninguém (nem o teu jogador, na carreira de jogador)
        return cartao

    def _dar_cartao(self, j, cor: str) -> bool:
        """Tira o jogador do rinque. Devolve False se não deu (a equipa ficaria com muito poucos)."""
        equipa = self.equipa_azul if j.equipa == "azul" else self.equipa_vermelha
        if j not in equipa or len(equipa) <= 2:
            return False
        if j is self.jogador_humano:
            colegas = [c for c in equipa if c is not j]
            if not colegas or self.modo_jogador:
                return False
            novo = min(colegas, key=lambda c: math.hypot(c.pos_x - j.pos_x, c.pos_y - j.pos_y))
            self._trocar_humano(novo)
        agentes = self.agentes_azul if j.equipa == "azul" else self.agentes_vermelhos
        agente = next((a for a in agentes if a.jogador is j), None)
        if agente is not None:
            agentes.remove(agente)
        if self.bola.dono is j:
            self.bola.libertar(pygame.math.Vector2(0, 0), dono_anterior=j)
        j.tem_bola = False
        equipa.remove(j)
        self.todos_jogadores.remove(j)
        j.selecionado = False
        if cor == "azul":
            self._azuis[j] = self._azuis.get(j, 0) + 1
        self._suspensos.append({"jogador": j, "agente": agente, "cor": cor,
                                "t": CARTAO_AZUL_S if cor == "azul" else CARTAO_VERMELHO_S})
        return True

    def _atualizar_suspensos(self, dt: float):
        """Conta o tempo de jogo (o relógio a andar) de quem está fora."""
        for s in list(self._suspensos):
            s["t"] -= dt
            if s["t"] <= 0:
                self._voltar_ao_jogo(s)

    def _faltas_golo(self, equipa_que_marcou: str):
        """Quem sofre um golo com um jogador fora por cartão azul recupera-o logo (como nas regras)."""
        sofreu = "vermelho" if equipa_que_marcou == "azul" else "azul"
        for s in list(self._suspensos):
            if s["cor"] == "azul" and s["jogador"].equipa == sofreu:
                self._voltar_ao_jogo(s)

    def _voltar_ao_jogo(self, s):
        j = s["jogador"]
        self._suspensos.remove(s)
        if s["cor"] == "vermelho":
            # O expulso não volta: entra um suplente para o lugar dele
            j.nome = "Suplente"
            self._azuis.pop(j, None)
        r = self.rink.rect
        # Entra pela linha lateral, no meio-campo da própria equipa
        j.pos_x = float(r.centerx + (80 if j.equipa == "azul" else -80))
        j.pos_y = float(r.top + 30)
        j.vel_x = j.vel_y = 0.0
        j.tem_bola = False
        j.rect.center = (round(j.pos_x), round(j.pos_y))
        j.set_target(0.0, 0.0)
        (self.equipa_azul if j.equipa == "azul" else self.equipa_vermelha).add(j)
        self.todos_jogadores.add(j)
        if s["agente"] is not None:
            (self.agentes_azul if j.equipa == "azul" else self.agentes_vermelhos).append(s["agente"])
        self._msg_texto = f"{j.nome} entra em jogo"
        self._msg_timer = 1.8

    # ------------------------------------------------------------------ #
    # Bolas paradas                                                        #
    # ------------------------------------------------------------------ #

    def _agente_espera(self, agente) -> bool:
        """True se este agente da IA vai marcar o livre e ainda está à espera de jogar."""
        bp = self._bola_parada
        return (bp is not None and bp["tipo"] == "livre" and agente.jogador is bp["marcador"]
                and bp["t"] < bp["espera"])

    def _atualizar_bola_parada(self, dt: float) -> bool:
        """
        Corre antes do resto do jogo. Devolve True se o jogo está parado neste frame
        (penálti / livre direto a preparar), e o resto do update não corre.
        """
        bp = self._bola_parada
        bp["t"] += dt
        if bp["tipo"] == "livre":
            return False

        # Penálti ou livre direto: todos parados, à espera do apito
        marcador = bp["marcador"]
        for j in self.todos_jogadores:
            humano = j.humano
            j.humano = False
            j.set_target(0.0, 0.0)
            j.vel_x = j.vel_y = 0.0
            j.update(dt, self.rink.rect, self.bola, self.rink)
            j.humano = humano
        self.gr_azul.update(dt, self.bola)
        self.gr_vermelho.update(dt, self.bola)
        if marcador.tem_bola:
            self.bola.seguir_jogador(marcador)
        if bp["t"] < PREPARAR_S:
            return True

        self._bola_parada = None
        som.tocar("apito_curto")
        if not marcador.tem_bola:
            return True
        # Equipa do jogador: remate na primeira pessoa (quem bate passa a ser o jogador controlado)
        if marcador.equipa == "azul":
            self._trocar_humano(marcador)
            if self.jogador_humano is marcador:
                self._cj_contar("remates")
                self.remate_pov = RematePOV(self.screen, self.rink, marcador, self.gr_vermelho, self.dificuldade,
                                            limite_tempo=6.0, cor_linhas=self.rink.cor_linhas, defensores=[],
                                            velocidade=(0.0, 0.0), placar=self._placar_pov())
                return True
        # IA: o resultado decide-se como na stickada (a física pura quase nunca deixava marcar:
        # a baliza é estreita e o guarda-redes, ao centro, tapava-a) e aplica-se no jogo 2D
        p_golo = (0.48 if bp["tipo"] == "penalti" else 0.38) + (getattr(marcador, "stat_remate", 80) - 80) / 200
        p_golo -= {"facil": -0.08, "normal": 0.0, "dificil": 0.08}.get(self.dificuldade, 0.0)             if marcador.equipa == "azul" else 0.0
        sorte = random.random()
        if sorte < p_golo:
            resultado = "golo"
        elif sorte < p_golo + 0.08:
            resultado = random.choice(("poste", "fora"))
        else:
            resultado = "defesa"
        lado = random.choice((-1, 1))
        u = lado * random.uniform(*CANTO_PENALTI_IA) * MEIA_BOCA
        if resultado == "fora":
            u = lado * (MEIA_BOCA + random.uniform(6, 20))
        res = {"resultado": resultado, "u": u, "u_gr": u * 0.8, "velocidade": REMATE_FORCA * random.uniform(*FORCA_PENALTI_IA),
               "pos": (marcador.pos_x, marcador.pos_y), "vel": (0.0, 0.0)}
        self._aplicar_remate(res, j=marcador, baliza="esq" if marcador.equipa == "azul" else "dir")
        return True

    def _restricoes_livre(self):
        """Depois de os jogadores se mexerem: num livre, os adversários ficam afastados da bola."""
        bp = self._bola_parada
        if bp is None or bp["tipo"] != "livre":
            return
        px, py = bp["pos"]
        marcador = bp["marcador"]
        if marcador.tem_bola and bp["t"] < bp["espera"]:
            marcador.pos_x, marcador.pos_y = px, py
            marcador.vel_x = marcador.vel_y = 0.0
            marcador.rect.center = (round(px), round(py))
            self.bola.seguir_jogador(marcador)
        marcador._cooldown_desarme = max(marcador._cooldown_desarme, 0.3)
        r = self.rink.rect
        for j in self.todos_jogadores:
            if j.equipa != bp["defesa"]:
                continue
            d = math.hypot(j.pos_x - px, j.pos_y - py)
            if d < DIST_LIVRE:
                if d < 0.1:
                    nx, ny = (1.0 if j.equipa == "azul" else -1.0), 0.0
                else:
                    nx, ny = (j.pos_x - px) / d, (j.pos_y - py) / d
                j.pos_x = max(r.left + 20, min(r.right - 20, px + nx * DIST_LIVRE))
                j.pos_y = max(r.top + 20, min(r.bottom - 20, py + ny * DIST_LIVRE))
                j.rect.center = (round(j.pos_x), round(j.pos_y))
        # O livre acaba quando a bola é jogada (sai do sítio ou muda de dono) ou ao fim de um tempo
        bola = self.bola
        if (bola.dono is not marcador or math.hypot(bola.pos_x - px, bola.pos_y - py) > 30
                or bp["t"] > LIMITE_LIVRE_S):
            self._bola_parada = None

    # ------------------------------------------------------------------ #
    # Desenho                                                              #
    # ------------------------------------------------------------------ #

    def _desenhar_suspensos(self, screen):
        """Por baixo do marcador: quem está fora por cartão e quanto tempo falta."""
        if not self._suspensos:
            return
        from componentes import texto
        n = {"azul": 0, "vermelho": 0}
        for s in self._suspensos:
            j = s["jogador"]
            lado = j.equipa
            # Lado a lado, para fora do marcador (não fica por cima do aviso da falta)
            cx = 640 + (-1 if lado == "azul" else 1) * (150 + n[lado] * 206)
            y = 76
            n[lado] += 1
            if s["cor"] == "vermelho":
                txt = f"{j.nome}  •  menos um {int(math.ceil(s['t']))} s"
            else:
                txt = f"{j.nome}  •  {int(math.ceil(s['t']))} s"
            caixa = pygame.Rect(0, 0, 200, 20)
            caixa.center = (cx, y)
            fundo = pygame.Surface(caixa.size, pygame.SRCALPHA)
            pygame.draw.rect(fundo, (10, 16, 34, 220), fundo.get_rect(), border_radius=10)
            screen.blit(fundo, caixa)
            cor = (60, 140, 255) if s["cor"] == "azul" else (230, 50, 50)
            pygame.draw.rect(screen, cor, (caixa.left + 8, caixa.top + 3, 10, 14), border_radius=2)
            texto(screen, txt, 11, (230, 238, 255), (caixa.left + 26, caixa.centery), ancora="midleft",
                  negrito=False)
