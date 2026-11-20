# -*- coding: utf-8 -*-
"""
conquistas.py - medalhas que se ganham ao jogar («primeiro golo», «roleta que dá golo», «campeão»...).

  - CONQUISTAS: a lista (id, nome, como se ganha, ícone e, nas de contar, quantas vezes é preciso).
  - ConquistasLocal: o que está ganho, guardado em conquistas.json (na pasta dos jogos gravados).
    Com conta, este ficheiro vai para a nuvem como as carreiras (conta.py). Ao trazer da nuvem
    não se substitui: juntam-se as duas listas (uma conquista ganha num PC nunca se perde).
  - ConquistasMixin: junta ao Game os sítios onde se ganham e a mensagem «CONQUISTA DESBLOQUEADA».

Só contam os jogos a sério: o modo teste e o tutorial não dão conquistas de jogo (só a do tutorial).
"""
import json
import os
import time

import pygame

from carreira import PASTA_SAVES
from componentes import texto
from graficos import icone
from sons import som

CAMINHO_CONQUISTAS = os.path.join(PASTA_SAVES, "conquistas.json")

# id, nome, como se ganha, ícone, quantas vezes (só nas de contar)
CONQUISTAS = [
    ("tutorial", "Aluno aplicado", "Acaba o tutorial", "livro", None),
    ("primeiro_golo", "Primeiro golo", "Marca um golo com o teu jogador", "jogar", None),
    ("primeira_vitoria", "Primeira vitória", "Ganha um jogo", "trofeu", None),
    ("hat_trick", "Hat-trick", "Marca 3 golos no mesmo jogo", "estrela", None),
    ("golo_roleta", "Roleta mágica", "Marca golo logo a seguir a enganar um defesa com a roleta", "recomecar", None),
    ("golo_stickada", "Stickada certeira", "Marca golo num remate na primeira pessoa", "alvo", None),
    ("muralha", "Muralha", "Ganha um jogo sem sofrer golos", "escudo", None),
    ("goleada", "Goleada", "Ganha um jogo por 5 ou mais golos de diferença", "avancar", None),
    ("dificil", "Contra os melhores", "Ganha um jogo na dificuldade difícil", "coracao", None),
    ("dois_jogadores", "Joga com um amigo", "Acaba um jogo a dois no mesmo computador", "jogador", None),
    ("vitoria_online", "Vitória online", "Ganha um jogo online", "globo", None),
    ("estreia_cj", "Estreia profissional", "Joga o primeiro jogo da carreira de jogador", "jogador", None),
    ("subir_divisao", "Subida de divisão", "Ganha a 2.ª divisão e sobe no modo carreira", "avancar", None),
    ("campeao", "Campeão nacional", "Ganha a 1.ª divisão no modo carreira", "trofeu", None),
    ("taca_europeia", "Rei da Europa", "Ganha a Taça Europeia no modo carreira", "estrela", None),
    ("goleador", "Goleador", "Marca 50 golos com o teu jogador", "jogar", ("golos", 50)),
    ("veterano", "Veterano", "Acaba 25 jogos", "moeda", ("jogos", 25)),
]
POR_ID = {c[0]: c for c in CONQUISTAS}
SEGUNDOS_MENSAGEM = 3.6


class ConquistasLocal:
    def __init__(self, ficheiro: str = CAMINHO_CONQUISTAS):
        self.ficheiro = ficheiro
        self.ganhas = {}        # id -> quando foi ganha (segundos desde 1970)
        self.contadores = {}    # "golos", "jogos" -> número
        self.carregar()

    def carregar(self):
        self.ganhas, self.contadores = self._ler(self.ficheiro)

    @staticmethod
    def _ler(caminho: str):
        try:
            with open(caminho, encoding="utf-8") as f:
                d = json.load(f)
            ganhas = {k: int(v) for k, v in d.get("ganhas", {}).items() if k in POR_ID}
            contadores = {k: int(v) for k, v in d.get("contadores", {}).items()}
            return ganhas, contadores
        except (OSError, ValueError, AttributeError, TypeError):
            return {}, {}

    def gravar(self):
        try:
            os.makedirs(os.path.dirname(self.ficheiro), exist_ok=True)
            temp = self.ficheiro + ".novo"
            with open(temp, "w", encoding="utf-8") as f:
                json.dump({"ganhas": self.ganhas, "contadores": self.contadores}, f)
            os.replace(temp, self.ficheiro)
        except OSError:
            pass                 # não conseguir gravar não impede de jogar

    def tem(self, cid: str) -> bool:
        return cid in self.ganhas

    def ganhar(self, cid: str) -> bool:
        """Marca como ganha. Devolve True só se for a primeira vez."""
        if cid not in POR_ID or cid in self.ganhas:
            return False
        self.ganhas[cid] = int(time.time())
        self.gravar()
        return True

    def somar(self, contador: str, n: int = 1) -> list:
        """Soma a um contador e devolve as conquistas de contar que ficaram ganhas."""
        self.contadores[contador] = self.contadores.get(contador, 0) + n
        novas = [c[0] for c in CONQUISTAS if c[4] and c[4][0] == contador
                 and self.contadores[contador] >= c[4][1] and self.ganhar(c[0])]
        self.gravar()
        return novas

    def progresso(self, cid: str):
        """Nas conquistas de contar: (feito, preciso). Nas outras: None."""
        alvo = POR_ID[cid][4]
        if not alvo:
            return None
        return min(self.contadores.get(alvo[0], 0), alvo[1]), alvo[1]

    def juntar(self, outro_ficheiro: str) -> bool:
        """Junta as conquistas de outro ficheiro (as da nuvem). Devolve True se ficou alguma coisa nova."""
        ganhas, contadores = self._ler(outro_ficheiro)
        mudou = False
        for k, t in ganhas.items():
            if k not in self.ganhas or t < self.ganhas[k]:
                mudou = mudou or k not in self.ganhas
                self.ganhas[k] = t
        for k, v in contadores.items():
            if v > self.contadores.get(k, 0):
                self.contadores[k] = v
                mudou = True
        self.gravar()
        return mudou


class ConquistasMixin:
    """Liga as conquistas ao Game (game.py). As mensagens aparecem por cima de qualquer ecrã."""

    def _cq_iniciar(self):
        self.conquistas = ConquistasLocal()
        self._cq_fila = []           # conquistas por mostrar
        self._cq_t = 0.0             # tempo da mensagem que está a aparecer
        self._cq_hat = 0             # golos do jogador humano neste jogo

    def cq_ganhar(self, *ids):
        for cid in ids:
            if self.conquistas.ganhar(cid):
                self._cq_fila.append(cid)

    def _cq_conta(self) -> bool:
        """Jogo que conta para as conquistas (não o modo teste nem o tutorial)."""
        return not self.modo_teste

    # ------------------------------------------------------------------ sítios onde se ganham
    def _cq_inicio_partida(self):
        self._cq_hat = 0

    def _cq_golo(self, equipa: str, marcador):
        """Chamado em cada golo (só no jogo que corre neste PC: offline ou anfitrião)."""
        if not self._cq_conta() or marcador is None or not getattr(marcador, "humano", False):
            return
        if equipa != "azul":
            return                   # golo do outro jogador humano (a dois, ou o convidado online)
        self._cq_hat += 1
        self.cq_ganhar("primeiro_golo")
        if self._cq_hat >= 3:
            self.cq_ganhar("hat_trick")
        if pygame.time.get_ticks() - getattr(marcador, "_roleta_ok_ms", -10 ** 9) < 5000:
            self.cq_ganhar("golo_roleta")
        if getattr(self, "_cq_golo_pov", False):
            self.cq_ganhar("golo_stickada")
        self._cq_fila.extend(self.conquistas.somar("golos"))

    def _cq_fim_jogo(self):
        """No fim de um jogo jogado até ao fim (não conta o jogo online: esse vê-se em _cq_fim_online)."""
        if not self._cq_conta() or self.online:
            return
        eu, ele = self.golos_azul, self.golos_vermelho
        if self.dois_jogadores:
            self.cq_ganhar("dois_jogadores")
        if self.modo_jogador:
            self.cq_ganhar("estreia_cj")
        if eu > ele and not self.dois_jogadores:
            self.cq_ganhar("primeira_vitoria")
            if ele == 0:
                self.cq_ganhar("muralha")
            if eu - ele >= 5:
                self.cq_ganhar("goleada")
            if self.dificuldade == "dificil":
                self.cq_ganhar("dificil")
        self._cq_fila.extend(self.conquistas.somar("jogos"))

    def _cq_fim_online(self, golos_casa: int, golos_fora: int):
        meus, deles = (golos_casa, golos_fora) if self.online == "anfitriao" else (golos_fora, golos_casa)
        if meus > deles:
            self.cq_ganhar("vitoria_online", "primeira_vitoria")
            if deles == 0:
                self.cq_ganhar("muralha")
            if meus - deles >= 5:
                self.cq_ganhar("goleada")
        self._cq_fila.extend(self.conquistas.somar("jogos"))

    def _cq_epoca(self, camp):
        """No ecrã do campeonato: se a época acabou, vê se o clube do jogador ganhou alguma coisa."""
        if camp is None or not camp.terminado:
            return
        r, eu = camp.resumo_epoca(), camp.equipa_jogador
        if r.get("sobe") == eu:
            self.cq_ganhar("subir_divisao")
        if r.get("campeao1") == eu:
            self.cq_ganhar("campeao")
        if r.get("europa") == eu:
            self.cq_ganhar("taca_europeia")

    # ------------------------------------------------------------------ mensagem
    def _cq_update(self, dt: float):
        if not self._cq_fila:
            return
        if self._cq_t == 0.0:
            som.tocar("conquista", 0.8)
        self._cq_t += dt
        if self._cq_t >= SEGUNDOS_MENSAGEM:
            self._cq_fila.pop(0)
            self._cq_t = 0.0

    def _cq_desenhar(self, s):
        if not self._cq_fila:
            return
        cid, nome, desc, ic, _ = POR_ID[self._cq_fila[0]]
        t = self._cq_t
        # Entra a descer e sai a subir
        k = min(1.0, t / 0.35, max(0.0, (SEGUNDOS_MENSAGEM - t) / 0.35))
        k = 1 - (1 - k) ** 3
        caixa = pygame.Rect(0, 0, 470, 72)
        caixa.midtop = (s.get_width() // 2, round(-80 + 150 * k))
        fundo = pygame.Surface(caixa.size, pygame.SRCALPHA)
        pygame.draw.rect(fundo, (14, 20, 40, 240), fundo.get_rect(), border_radius=18)
        s.blit(fundo, caixa)
        pygame.draw.rect(s, (255, 200, 60), caixa, 2, border_radius=18)
        centro = (caixa.left + 40, caixa.centery)
        pygame.draw.circle(s, (120, 80, 20), centro, 25)
        pygame.draw.circle(s, (255, 205, 70), centro, 25, 2)
        img = icone(ic, 28, (255, 220, 110))
        s.blit(img, img.get_rect(center=centro))
        texto(s, "CONQUISTA DESBLOQUEADA", 13, (255, 205, 70), (caixa.left + 80, caixa.top + 18), ancora="midleft")
        texto(s, nome, 20, (255, 255, 255), (caixa.left + 80, caixa.top + 39), ancora="midleft")
        texto(s, desc, 12, (175, 190, 225), (caixa.left + 80, caixa.top + 58), ancora="midleft", negrito=False)
