# -*- coding: utf-8 -*-
"""
conquistas_menu.py - ecrã CONQUISTAS (abre no botão da taça, por baixo da engrenagem do menu principal)
e esse botão redondo, com o número de conquistas ganhas.
"""
import math
import time

import pygame

from settings import WIDTH, HEIGHT
from componentes import texto, fonte, ListaBotoes, painel_vidro, COR_TEXTO, COR_TEXTO_SUAVE
from graficos import icone, luz, gradiente_radial
from cores import misturar
from menu import BotaoMenu, _fundo_arena
from conquistas import CONQUISTAS

DOURADO = (255, 200, 60)


class EcraConquistas:
    def __init__(self, screen: pygame.Surface, conquistas, arena=None, com_conta: bool = False):
        self.screen = screen
        self.cq = conquistas
        self.arena = arena
        self.com_conta = com_conta
        self.t = 0.0
        self.caixa = pygame.Rect(WIDTH // 2 - 520, 120, 1040, 520)
        self.lista = ListaBotoes([BotaoMenu((WIDTH // 2 - 140, HEIGHT - 70, 280, 50), "VOLTAR", "", "voltar",
                                            (150, 110, 255), "casa", seta=False, tamanho=18)])
        self.lista.foco = 0

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return "sair"
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            return "voltar"
        return self.lista.handle_event(event)

    def update(self, dt: float):
        self.t += dt
        for i, b in enumerate(self.lista.botoes):
            b.animar(dt, i == self.lista.foco)

    def _cartao(self, i: int) -> pygame.Rect:
        col, lin = i % 2, i // 2
        return pygame.Rect(self.caixa.left + 24 + col * 504, self.caixa.top + 70 + lin * 48, 492, 42)

    def draw(self):
        s = self.screen
        s.blit(_fundo_arena(self.arena), (0, 0))
        brilho = luz(900, 520, DOURADO, 34)
        s.blit(brilho, brilho.get_rect(center=(WIDTH // 2, 360)), special_flags=pygame.BLEND_RGB_ADD)
        ic = icone("trofeu", 40, DOURADO)
        s.blit(ic, ic.get_rect(center=(WIDTH // 2, 40)))
        texto(s, "CONQUISTAS", 34, COR_TEXTO, (WIDTH // 2, 88), sombra=True)
        painel_vidro(s, self.caixa, 20, 230, (150, 120, 50))

        ganhas, total = len(self.cq.ganhas), len(CONQUISTAS)
        c = self.caixa
        texto(s, f"{ganhas} de {total} ganhas", 18, DOURADO, (c.left + 30, c.top + 32), ancora="midleft")
        barra = pygame.Rect(c.left + 220, c.top + 25, 420, 14)
        pygame.draw.rect(s, (25, 32, 58), barra, border_radius=7)
        if ganhas:
            pygame.draw.rect(s, DOURADO, (barra.x, barra.y, max(14, round(barra.w * ganhas / total)), barra.h),
                             border_radius=7)
        nota = ("Com a tua conta, ficam guardadas na nuvem." if self.com_conta
                else "Entra na tua conta para as guardares na nuvem.")
        texto(s, nota, 13, COR_TEXTO_SUAVE, (c.right - 30, c.top + 32), ancora="midright", negrito=False)

        for i, (cid, nome, desc, ic_nome, contar) in enumerate(CONQUISTAS):
            r = self._cartao(i)
            ganha = self.cq.tem(cid)
            fundo = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(fundo, (255, 200, 60, 28) if ganha else (255, 255, 255, 8), fundo.get_rect(),
                             border_radius=12)
            s.blit(fundo, r)
            pygame.draw.rect(s, (200, 160, 60) if ganha else (60, 72, 105), r, 1, border_radius=12)
            centro = (r.left + 24, r.centery)
            pygame.draw.circle(s, (120, 80, 20) if ganha else (30, 36, 58), centro, 16)
            img = icone(ic_nome if ganha else "cadeado", 18, (255, 220, 110) if ganha else (110, 120, 150))
            s.blit(img, img.get_rect(center=centro))
            texto(s, nome, 15, (255, 255, 255) if ganha else (170, 180, 205), (r.left + 50, r.top + 13),
                  ancora="midleft")
            texto(s, desc, 12, (190, 200, 230) if ganha else (120, 132, 165), (r.left + 50, r.top + 30),
                  ancora="midleft", negrito=False)
            if ganha:
                quando = time.strftime("%d/%m/%Y", time.localtime(self.cq.ganhas[cid]))
                texto(s, quando, 11, (220, 185, 100), (r.right - 12, r.top + 13), ancora="midright", negrito=False)
            elif contar:
                feito, preciso = self.cq.progresso(cid)
                b = pygame.Rect(r.right - 92, r.top + 9, 80, 8)
                pygame.draw.rect(s, (25, 32, 58), b, border_radius=4)
                if feito:
                    pygame.draw.rect(s, (150, 130, 80), (b.x, b.y, max(8, round(b.w * feito / preciso)), b.h),
                                     border_radius=4)
                texto(s, f"{feito}/{preciso}", 11, (150, 160, 190), (r.right - 52, r.top + 28), negrito=False)

        self.lista.draw(s)
        texto(s, "ENTER / ESC  voltar", 12, (120, 145, 195), (WIDTH // 2, HEIGHT - 12), negrito=False)


class BotaoConquistas:
    """Botão redondo com uma taça, por baixo da engrenagem. Mostra quantas conquistas estão ganhas."""

    def __init__(self, conquistas, centro=(WIDTH - 50, 116), raio: int = 28):
        self.cq = conquistas
        self.centro = centro
        self.raio = raio
        self.rect = pygame.Rect(0, 0, raio * 2, raio * 2)
        self.rect.center = centro
        self.acao = "conquistas"
        self.k = 0.0

    def por_cima(self, pos) -> bool:
        return math.dist(pos, self.centro) <= self.raio + 4

    def animar(self, dt: float, focado: bool):
        self.k += ((1.0 if focado else 0.0) - self.k) * min(1.0, dt * 12)

    def draw(self, surf, _mpos=None, focado: bool = False):
        k = self.k
        cx, cy = self.centro
        if k > 0.02:
            halo = gradiente_radial(self.raio * 4, self.raio * 4, DOURADO, int(110 * k))
            surf.blit(halo, halo.get_rect(center=self.centro))
        pygame.draw.circle(surf, (0, 0, 0), (cx + 2, cy + 4), self.raio)
        pygame.draw.circle(surf, misturar((18, 28, 56), (150, 105, 30), k), self.centro, self.raio)
        pygame.draw.circle(surf, misturar((150, 125, 70), (255, 225, 140), k), self.centro, self.raio, 2)
        ic = icone("trofeu", 30, misturar((240, 205, 120), (255, 255, 255), k))
        surf.blit(ic, ic.get_rect(center=(cx, cy - 1)))
        # Número de conquistas ganhas (bolinha no canto)
        n = len(self.cq.ganhas)
        if n:
            b = (cx + self.raio - 6, cy - self.raio + 6)
            pygame.draw.circle(surf, (230, 70, 70), b, 11)
            pygame.draw.circle(surf, (255, 255, 255), b, 11, 1)
            texto(surf, str(n), 12, (255, 255, 255), b)
        if k > 0.05:
            img = fonte(14).render("CONQUISTAS", True, (255, 255, 255))
            caixa = pygame.Rect(0, 0, img.get_width() + 24, 30)
            caixa.midright = (cx - self.raio - 10 + round(10 * (1 - k)), cy)
            etiqueta = pygame.Surface(caixa.size, pygame.SRCALPHA)
            pygame.draw.rect(etiqueta, (60, 44, 16, 230), etiqueta.get_rect(), border_radius=15)
            pygame.draw.rect(etiqueta, (230, 190, 90, 255), etiqueta.get_rect(), 1, border_radius=15)
            etiqueta.set_alpha(int(255 * k))
            surf.blit(etiqueta, caixa)
            img.set_alpha(int(255 * k))
            surf.blit(img, img.get_rect(center=caixa.center))
