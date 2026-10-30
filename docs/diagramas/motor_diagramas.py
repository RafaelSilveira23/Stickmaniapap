# -*- coding: utf-8 -*-
"""motor_diagramas.py - cria diagramas em formato draw.io (.drawio) e em imagem (.png).

Cada diagrama é descrito uma vez (caixas + setas com coordenadas) e daí saem:
  - o ficheiro .drawio, que se abre e edita em https://app.diagrams.net
  - a imagem .png, desenhada com pygame, para pôr no relatório
"""
import math
import os
from xml.sax.saxutils import escape

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

# Cores no estilo do draw.io: (preenchimento, contorno)
CORES = {
    "azul":    ("#DAE8FC", "#6C8EBF"),
    "verde":   ("#D5E8D4", "#82B366"),
    "amarelo": ("#FFF2CC", "#D6B656"),
    "vermelho": ("#F8CECC", "#B85450"),
    "roxo":    ("#E1D5E7", "#9673A6"),
    "cinza":   ("#F5F5F5", "#666666"),
    "laranja": ("#FFE6CC", "#D79B00"),
    "branco":  ("#FFFFFF", "#333333"),
    "preto":   ("#000000", "#000000"),
}

R = 4      # resolução interna do desenho (super-amostragem)
SAIDA = 2  # a imagem final fica com o dobro do tamanho do diagrama (boa para imprimir)


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class No:
    def __init__(self, id, x, y, w, h, texto, tipo, cor, tracejado, negrito, tam, linhas):
        self.id, self.x, self.y, self.w, self.h = id, x, y, w, h
        self.texto, self.tipo, self.cor = texto, tipo, cor
        self.tracejado, self.negrito, self.tam = tracejado, negrito, tam
        self.linhas = linhas  # para classes / tabelas: (titulo, [secções])

    @property
    def centro(self):
        return (self.x + self.w / 2, self.y + self.h / 2)

    def borda(self, de, para):
        """Ponto onde a reta de 'de' (dentro) para 'para' sai da forma."""
        cx, cy = de
        dx, dy = para[0] - cx, para[1] - cy
        if abs(dx) < 1e-9 and abs(dy) < 1e-9:
            return de
        hw, hh = self.w / 2, self.h / 2
        if self.tipo in ("elipse", "inicio", "fim"):
            t = 1 / math.sqrt((dx / hw) ** 2 + (dy / hh) ** 2)
        elif self.tipo == "losango":
            t = 1 / (abs(dx) / hw + abs(dy) / hh)
        else:
            tx = hw / abs(dx) if abs(dx) > 1e-9 else 1e9
            ty = hh / abs(dy) if abs(dy) > 1e-9 else 1e9
            t = min(tx, ty)
        # a reta parte do centro da forma (mesmo com desvio, o desvio é paralelo)
        return (cx + dx * t, cy + dy * t)


class Seta:
    def __init__(self, a, b, texto, tracejado, pontos, ambos, desvio, pos_texto, exato, ponta):
        self.a, self.b, self.texto = a, b, texto
        self.tracejado, self.pontos, self.ambos = tracejado, pontos or [], ambos
        self.desvio, self.pos_texto, self.exato, self.ponta = desvio, pos_texto, exato, ponta


class Diagrama:
    def __init__(self, nome, largura, altura, titulo=""):
        self.nome, self.W, self.H, self.titulo = nome, largura, altura, titulo
        self.nos, self.setas, self._ids = [], [], {}

    # ------------------------------------------------------------ construir
    def caixa(self, id, x, y, w, h, texto="", tipo="retangulo", cor="azul", tracejado=False,
              negrito=False, tam=13, linhas=None):
        n = No(id, x, y, w, h, texto, tipo, cor, tracejado, negrito, tam, linhas)
        self.nos.append(n)
        self._ids[id] = n
        return n

    def seta(self, a, b, texto="", tracejado=False, pontos=None, ambos=False, desvio=(0, 0),
             pos_texto=0.5, exato=False, ponta=True):
        """
        a, b      : ids das caixas (ou, com exato=True, a lista 'pontos' já tem o caminho todo)
        pontos    : pontos intermédios (cotovelos)
        desvio    : (dx, dy) para afastar setas paralelas (ida e volta)
        """
        self.setas.append(Seta(a, b, texto, tracejado, pontos, ambos, desvio, pos_texto, exato, ponta))

    # ------------------------------------------------------------ geometria
    def _caminho(self, s):
        if s.exato:
            return [tuple(p) for p in s.pontos]
        A, B = self._ids[s.a], self._ids[s.b]
        dx, dy = s.desvio
        ca = (A.centro[0] + dx, A.centro[1] + dy)
        cb = (B.centro[0] + dx, B.centro[1] + dy)
        meio = [tuple(p) for p in s.pontos]
        p0 = A.borda(ca, meio[0] if meio else cb)
        p1 = B.borda(cb, meio[-1] if meio else ca)
        return [p0] + meio + [p1]

    @staticmethod
    def _ponto_ao_longo(pts, f):
        comp = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
        alvo = sum(comp) * f
        for i, c in enumerate(comp):
            if alvo <= c or i == len(comp) - 1:
                t = 0 if c == 0 else min(1, alvo / c)
                return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t,
                        pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t)
            alvo -= c

    def _no_mais_proximo(self, p):
        """Para setas 'exatas': que caixa toca neste ponto (para o draw.io ligar a seta)."""
        for n in self.nos:
            if n.tipo == "grupo":
                continue
            if n.x - 2 <= p[0] <= n.x + n.w + 2 and n.y - 2 <= p[1] <= n.y + n.h + 2:
                return n
        return None

    # ------------------------------------------------------------ draw.io
    def _estilo(self, n):
        f, c = CORES[n.cor]
        base = f"whiteSpace=wrap;html=1;fillColor={f};strokeColor={c};fontSize={n.tam};fontFamily=Arial;"
        if n.tracejado:
            base += "dashed=1;"
        if n.negrito:
            base += "fontStyle=1;"
        return {
            "retangulo": "rounded=0;" + base,
            "arredondado": "rounded=1;arcSize=18;" + base,
            "terminal": "rounded=1;arcSize=50;" + base,
            "elipse": "ellipse;" + base,
            "losango": "rhombus;" + base,
            "ator": "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;outlineConnect=0;" + base,
            "inicio": "ellipse;fillColor=#000000;strokeColor=#000000;html=1;",
            "fim": "ellipse;shape=endState;fillColor=#000000;strokeColor=#000000;html=1;",
            "grupo": "rounded=1;arcSize=3;verticalAlign=top;fontStyle=1;spacingTop=4;" + base,
            "texto": "text;html=1;align=center;verticalAlign=middle;fontSize=%d;fontFamily=Arial;%s"
                     % (n.tam, "fontStyle=1;" if n.negrito else ""),
            "classe": "verticalAlign=top;align=left;overflow=fill;html=1;whiteSpace=wrap;fontFamily=Arial;"
                      f"fontSize={n.tam};fillColor={f};strokeColor={c};",
        }[n.tipo]

    def _valor(self, n):
        if n.tipo == "classe":
            titulo, seccoes = n.linhas
            html = f'<p style="margin:0px;margin-top:4px;text-align:center;"><b>{escape(titulo)}</b></p>'
            for sec in seccoes:
                html += '<hr size="1"/><p style="margin:0px;margin-left:6px;">'
                html += "<br/>".join(escape(l) for l in sec) + "</p>"
            return html
        return "<br>".join(escape(l) for l in n.texto.split("\n"))

    def guardar_drawio(self, pasta):
        cel = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
        for n in self.nos:
            cel.append(
                f'<mxCell id="{n.id}" value="{escape(self._valor(n), {chr(34): "&quot;"})}" '
                f'style="{self._estilo(n)}" vertex="1" parent="1">'
                f'<mxGeometry x="{n.x}" y="{n.y}" width="{n.w}" height="{n.h}" as="geometry"/></mxCell>')
        for i, s in enumerate(self.setas):
            pts = self._caminho(s)
            estilo = ("edgeStyle=none;html=1;rounded=0;fontSize=12;fontFamily=Arial;"
                      "labelBackgroundColor=#FFFFFF;strokeColor=#333333;")
            estilo += "endArrow=block;endFill=1;" if s.ponta else "endArrow=none;"
            if s.ambos:
                estilo += "startArrow=block;startFill=1;"
            if s.tracejado:
                estilo += "dashed=1;"
            A = self._ids.get(s.a) if not s.exato else self._no_mais_proximo(pts[0])
            B = self._ids.get(s.b) if not s.exato else self._no_mais_proximo(pts[-1])
            liga = ""
            if A is not None:
                estilo += "exitX=%.3f;exitY=%.3f;exitDx=0;exitDy=0;" % ((pts[0][0] - A.x) / A.w, (pts[0][1] - A.y) / A.h)
                liga += f' source="{A.id}"'
            if B is not None:
                estilo += "entryX=%.3f;entryY=%.3f;entryDx=0;entryDy=0;" % ((pts[-1][0] - B.x) / B.w, (pts[-1][1] - B.y) / B.h)
                liga += f' target="{B.id}"'
            meio = "".join(f'<mxPoint x="{p[0]:.1f}" y="{p[1]:.1f}"/>' for p in pts[1:-1])
            geo = (f'<mxGeometry x="{s.pos_texto * 2 - 1:.2f}" relative="1" as="geometry">'
                   f'<mxPoint x="{pts[0][0]:.1f}" y="{pts[0][1]:.1f}" as="sourcePoint"/>'
                   f'<mxPoint x="{pts[-1][0]:.1f}" y="{pts[-1][1]:.1f}" as="targetPoint"/>'
                   + (f'<Array as="points">{meio}</Array>' if meio else "") + '</mxGeometry>')
            cel.append(f'<mxCell id="e{i}" value="{escape(s.texto)}" style="{estilo}" edge="1" '
                       f'parent="1"{liga}>{geo}</mxCell>')
        xml = (f'<mxfile host="app.diagrams.net"><diagram name="{escape(self.titulo or self.nome)}" id="{self.nome}">'
               f'<mxGraphModel dx="{self.W}" dy="{self.H}" grid="1" gridSize="10" guides="1" tooltips="1" '
               f'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{self.W + 40}" '
               f'pageHeight="{self.H + 40}" math="0" shadow="0"><root>' + "".join(cel) +
               '</root></mxGraphModel></diagram></mxfile>')
        caminho = os.path.join(pasta, self.nome + ".drawio")
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(xml)
        return caminho

    # ------------------------------------------------------------ PNG
    def guardar_png(self, pasta):
        pygame.init()
        M = 20  # margem
        W, H = (self.W + 2 * M) * R, (self.H + 2 * M) * R
        surf = pygame.Surface((W, H))
        surf.fill((255, 255, 255))
        self._surf, self._m = surf, M
        fontes = {}

        def fonte(tam, negrito=False):
            k = (tam, negrito)
            if k not in fontes:
                fontes[k] = pygame.font.SysFont("arial", round(tam * R * 1.02), bold=negrito)
            return fontes[k]
        self._fonte = fonte

        for n in self.nos:
            self._desenhar_no(n)
        for s in self.setas:
            self._desenhar_seta(s)
        final = pygame.transform.smoothscale(surf, (W * SAIDA // R, H * SAIDA // R))
        caminho = os.path.join(pasta, self.nome + ".png")
        pygame.image.save(final, caminho)
        return caminho

    def _p(self, x, y):
        return (round((x + self._m) * R), round((y + self._m) * R))

    def _linha(self, a, b, cor, larg, tracejado):
        s = self._surf
        if not tracejado:
            pygame.draw.line(s, cor, self._p(*a), self._p(*b), larg)
            return
        comp = math.dist(a, b)
        passo, cheio = 8, 5
        k = 0
        while k < comp:
            t0, t1 = k / comp, min(comp, k + cheio) / comp
            p0 = (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0)
            p1 = (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)
            pygame.draw.line(s, cor, self._p(*p0), self._p(*p1), larg)
            k += passo

    def _contorno(self, pts, cor, larg, tracejado):
        for i in range(len(pts)):
            self._linha(pts[i], pts[(i + 1) % len(pts)], cor, larg, tracejado)

    def _texto(self, texto, rect, tam, negrito=False, cor=(20, 20, 20), alinhar="centro", topo=False):
        """Escreve texto com quebra de linha automática dentro de rect (coordenadas do diagrama)."""
        x, y, w, h = rect
        f = self._fonte(tam, negrito)
        largura_max = (w - 10) * R
        linhas = []
        for par in texto.split("\n"):
            atual = ""
            for pal in par.split(" "):
                tent = (atual + " " + pal).strip()
                if f.size(tent)[0] <= largura_max or not atual:
                    atual = tent
                else:
                    linhas.append(atual)
                    atual = pal
            linhas.append(atual)
        alt = f.get_linesize()
        total = alt * len(linhas)
        y0 = self._p(x, y)[1] + (6 * R if topo else (h * R - total) / 2)
        for i, l in enumerate(linhas):
            img = f.render(l, True, cor)
            if alinhar == "centro":
                px = self._p(x + w / 2, 0)[0] - img.get_width() / 2
            else:
                px = self._p(x + 6, 0)[0]
            self._surf.blit(img, (px, y0 + i * alt))

    def _desenhar_no(self, n):
        s = self._surf
        f, c = (_rgb(v) for v in CORES[n.cor])
        rect = pygame.Rect(*self._p(n.x, n.y), round(n.w * R), round(n.h * R))
        L = 2 * R // 2 + 1
        if n.tipo in ("retangulo", "arredondado", "terminal", "grupo", "classe"):
            raio = {"retangulo": 0, "classe": 0, "arredondado": round(min(n.w, n.h) * 0.18 * R),
                    "terminal": rect.h // 2, "grupo": 8 * R}[n.tipo]
            pygame.draw.rect(s, f, rect, border_radius=raio)
            if n.tracejado:
                self._contorno([(n.x, n.y), (n.x + n.w, n.y), (n.x + n.w, n.y + n.h), (n.x, n.y + n.h)], c, L, True)
            else:
                pygame.draw.rect(s, c, rect, L, border_radius=raio)
            if n.tipo == "grupo":
                self._texto(n.texto, (n.x, n.y, n.w, 26), n.tam, True, topo=True)
            elif n.tipo == "classe":
                titulo, seccoes = n.linhas
                ft = self._fonte(n.tam, True)
                img = ft.render(titulo, True, (20, 20, 20))
                s.blit(img, (rect.centerx - img.get_width() / 2, rect.top + 5 * R))
                yy = n.y + 6 + ft.get_linesize() / R + 4
                fn = self._fonte(n.tam - 1)
                alt = fn.get_linesize() / R
                for sec in seccoes:
                    self._linha((n.x, yy), (n.x + n.w, yy), c, L, False)
                    yy += 4
                    for l in sec:
                        s.blit(fn.render(l, True, (30, 30, 30)), self._p(n.x + 7, yy))
                        yy += alt
                    yy += 4
            else:
                self._texto(n.texto, (n.x, n.y, n.w, n.h), n.tam, n.negrito)
        elif n.tipo == "elipse":
            pygame.draw.ellipse(s, f, rect)
            if n.tracejado:
                pts = [(n.x + n.w / 2 + n.w / 2 * math.cos(a / 60 * math.tau),
                        n.y + n.h / 2 + n.h / 2 * math.sin(a / 60 * math.tau)) for a in range(60)]
                for i in range(0, 60, 2):
                    self._linha(pts[i], pts[(i + 1) % 60], c, L, False)
            else:
                pygame.draw.ellipse(s, c, rect, L)
            self._texto(n.texto, (n.x + n.w * 0.08, n.y, n.w * 0.84, n.h), n.tam, n.negrito)
        elif n.tipo == "losango":
            pts = [(n.x + n.w / 2, n.y), (n.x + n.w, n.y + n.h / 2), (n.x + n.w / 2, n.y + n.h), (n.x, n.y + n.h / 2)]
            pygame.draw.polygon(s, f, [self._p(*p) for p in pts])
            pygame.draw.polygon(s, c, [self._p(*p) for p in pts], L)
            self._texto(n.texto, (n.x + n.w * 0.15, n.y, n.w * 0.7, n.h), n.tam, n.negrito)
        elif n.tipo == "inicio":
            pygame.draw.ellipse(s, (0, 0, 0), rect)
        elif n.tipo == "fim":
            pygame.draw.ellipse(s, (0, 0, 0), rect, L)
            pygame.draw.ellipse(s, (0, 0, 0), rect.inflate(-rect.w * 0.45, -rect.h * 0.45))
        elif n.tipo == "ator":
            cx = n.x + n.w / 2
            r = n.w * 0.22
            pygame.draw.circle(s, f, self._p(cx, n.y + r), r * R)
            pygame.draw.circle(s, c, self._p(cx, n.y + r), r * R, L)
            corpo_fim = n.y + n.h * 0.62
            self._linha((cx, n.y + 2 * r), (cx, corpo_fim), c, L, False)
            self._linha((n.x + n.w * 0.05, n.y + n.h * 0.36), (n.x + n.w * 0.95, n.y + n.h * 0.36), c, L, False)
            self._linha((cx, corpo_fim), (n.x + n.w * 0.12, n.y + n.h), c, L, False)
            self._linha((cx, corpo_fim), (n.x + n.w * 0.88, n.y + n.h), c, L, False)
            self._texto(n.texto, (n.x - 60, n.y + n.h + 2, n.w + 120, 34), n.tam, True)
        elif n.tipo == "texto":
            self._texto(n.texto, (n.x, n.y, n.w, n.h), n.tam, n.negrito)

    def _ponta(self, de, para):
        ang = math.atan2(para[1] - de[1], para[0] - de[0])
        comp, abert = 11, 0.42
        p1 = (para[0] - comp * math.cos(ang - abert), para[1] - comp * math.sin(ang - abert))
        p2 = (para[0] - comp * math.cos(ang + abert), para[1] - comp * math.sin(ang + abert))
        pygame.draw.polygon(self._surf, (40, 40, 40), [self._p(*para), self._p(*p1), self._p(*p2)])

    def _desenhar_seta(self, s):
        pts = self._caminho(s)
        cor = (51, 51, 51)
        L = 2 * R // 2 + 1
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            # encurtar o último segmento para a ponta da seta não ficar tapada pela linha
            if s.ponta and i == len(pts) - 2:
                d = math.dist(a, b)
                if d > 8:
                    b = (b[0] - (b[0] - a[0]) * 6 / d, b[1] - (b[1] - a[1]) * 6 / d)
            if s.ambos and i == 0:
                d = math.dist(a, pts[1])
                if d > 8:
                    a = (a[0] + (pts[1][0] - a[0]) * 6 / d, a[1] + (pts[1][1] - a[1]) * 6 / d)
            self._linha(a, b, cor, L, s.tracejado)
        if s.ponta:
            self._ponta(pts[-2], pts[-1])
        if s.ambos:
            self._ponta(pts[1], pts[0])
        if s.texto:
            px, py = self._ponto_ao_longo(pts, s.pos_texto)
            f = self._fonte(12)
            linhas = s.texto.split("\n")
            imgs = [f.render(l, True, (20, 20, 20)) for l in linhas]
            w = max(i.get_width() for i in imgs) + 6 * R
            h = sum(i.get_height() for i in imgs) + 2 * R
            cx, cy = self._p(px, py)
            fundo = pygame.Rect(0, 0, w, h)
            fundo.center = (cx, cy)
            pygame.draw.rect(self._surf, (255, 255, 255), fundo)
            yy = fundo.top + R
            for img in imgs:
                self._surf.blit(img, (cx - img.get_width() / 2, yy))
                yy += img.get_height()

    def guardar(self, pasta):
        os.makedirs(pasta, exist_ok=True)
        return self.guardar_drawio(pasta), self.guardar_png(pasta)
