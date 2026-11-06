"""navegador.py - ajustes só para a versão do browser (pygbag).

O pygbag não suporta bem ecrãs com zoom (portáteis a 125-200 %, telemóveis): a posição do rato
que chega ao pygame fica desviada quando o jogo não está encostado ao canto da página, e os
cliques acertavam no botão de baixo. Aqui o jogo passa a ler a posição do rato diretamente do
browser (JavaScript) e converte-a para as coordenadas do jogo (1280×720):

    x_jogo = (x_rato − esquerda_do_jogo) × 1280 / largura_do_jogo_no_ecrã
    y_jogo = (y_rato − topo_do_jogo)     ×  720 / altura_do_jogo_no_ecrã

Depois substitui a posição nos eventos do rato e em pygame.mouse.get_pos(), por isso o resto do
jogo não precisa de mudar nada.
"""
import json

import pygame

from settings import WIDTH, HEIGHT

_JS = r"""
(function () {
  if (window.stickRato) return;
  const R = window.stickRato = {x: 0, y: 0};
  function guardar(e) {
    const c = document.getElementById("canvas");
    if (!c || e.clientX === undefined) return;
    const r = c.getBoundingClientRect();
    R.x = Math.round((e.clientX - r.left) * %W% / r.width);
    R.y = Math.round((e.clientY - r.top) * %H% / r.height);
  }
  for (const t of ["mousemove", "mousedown", "mouseup", "pointermove", "pointerdown", "pointerup"])
    window.addEventListener(t, guardar, true);          // "true": antes de o pygame tratar o evento
  for (const t of ["touchstart", "touchmove"])
    window.addEventListener(t, function (ev) { if (ev.touches.length) guardar(ev.touches[0]); }, true);
})();
""".replace("%W%", str(WIDTH)).replace("%H%", str(HEIGHT))

_TIPOS_RATO = (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP)


def preparar():
    import platform          # no pygbag, platform.window é a janela do browser
    import random
    platform.window.eval(_JS)
    # No browser o gerador de números aleatórios do Python começava sempre igual (o mesmo código de
    # sala para todos os jogos online, a mesma "sorte" nos jogos): baralha-se com o relógio e o
    # gerador do próprio browser.
    random.seed(str(platform.window.eval("String(Date.now()) + String(Math.random())")))

    obter_eventos = pygame.event.get

    def posicao():
        x, y = json.loads(str(platform.window.eval("JSON.stringify([stickRato.x, stickRato.y])")))
        return max(0, min(WIDTH - 1, x)), max(0, min(HEIGHT - 1, y))

    def eventos(*args, **kwargs):
        lista = obter_eventos(*args, **kwargs)
        if any(e.type in _TIPOS_RATO for e in lista):
            p = posicao()
            lista = [pygame.event.Event(e.type, {**e.__dict__, "pos": p}) if e.type in _TIPOS_RATO else e
                     for e in lista]
        return lista

    pygame.event.get = eventos
    pygame.mouse.get_pos = posicao
