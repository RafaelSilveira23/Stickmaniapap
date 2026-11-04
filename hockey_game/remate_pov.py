# -*- coding: utf-8 -*-
"""remate_pov.py - remate na primeira pessoa.

Quando o jogador carrega em X com a bola, a câmara passa para os olhos do jogador, virada
para a baliza (como num penálti). O jogador:
  • aponta com o rato ou com as setas para qualquer ponto da baliza (também em altura);
  • mantém X (ou o botão do rato) carregado para encher a barra de força e larga para rematar.
Mais força = a bola chega mais depressa (o guarda-redes tem menos tempo), mas o remate fica
menos preciso (o círculo da mira fica maior).

Fase de remate em movimento:
  • o jogador não para: continua a patinar a 50 % da velocidade que trazia, e a câmara avança com ele;
  • os adversários que estão entre o jogador e a baliza aparecem no ecrã, nas posições que tinham
    no campo quando se carregou em X;
  • a linha da bola até ao ponto apontado é testada contra o corpo de cada defesa (um cilindro):
    se o cruzar abaixo da altura do corpo, o remate é BLOQUEADO; se passar perto, o defesa
    tapa a vista ao guarda-redes, que tem mais dificuldade em adivinhar o lado.

Como se desenha a vista na primeira pessoa (projeção em perspetiva):
  A câmara está no jogador e olha para o centro da baliza. Para cada ponto do campo
  (x, y no chão e uma altura h) calculamos:
      z = distância à frente da câmara      (produto escalar com a direção "em frente")
      x = distância para o lado             (produto escalar com a direção "direita")
      ecrã_x = centro + F · x / z           (o que está longe fica mais perto do centro)
      ecrã_y = horizonte + F · (olhos − h) / z
  Os pontos atrás da câmara (z muito pequeno) são cortados ("clipping").

O resultado (golo, defesa, poste ou fora) é decidido com um modelo simples do guarda-redes:
tempo de reação, velocidade de mergulho, alcance (menor nos cantos de cima) e se "lê" ou não
o lado do remate. Depois o jogo 2D continua com a bola no sítio certo.
"""
import math
import os
import random

import pygame

from settings import WIDTH, HEIGHT
from graficos import titulo_estilizado, luz
from componentes import texto, fonte
from sons import som
from team import obter_info_equipa
import pavilhao_pov

F = 1000           # distância focal (quanto maior, mais "zoom")
HORIZONTE = 330    # y do horizonte no ecrã
OLHOS = 30         # altura dos olhos do jogador (unidades do campo)
PERTO = 8          # plano de corte: o que está mais perto do que isto não se desenha
CX = WIDTH // 2

ALTURA_BALIZA = 41      # a baliza de hóquei em patins tem 1,05 m de altura e 1,70 m de largura
MEIA_BOCA = 33
PROF_BALIZA = 38
RAIO_BOLA = 5.5
PX_POR_METRO = 1140 / 40      # o rinque tem 40 m de comprimento e 1140 px
REDUCAO_VELOCIDADE = 0.5      # a carregar o remate, o jogador patina a 50 % da velocidade
RAIO_DEFESA = 14              # "cilindro" do corpo de um defesa (px do campo)
ALTURA_DEFESA = 52            # altura do corpo de um defesa (px do campo)
DIST_MINIMA = 95              # o jogador não avança para mais perto da baliza do que isto
DIST_TRAVAR = 80              # trava a ~2,8 m de um defesa que esteja mesmo à frente


def kmh(px_por_segundo: float) -> float:
    return px_por_segundo / PX_POR_METRO * 3.6

# Guarda-redes por dificuldade: reação (s), velocidade de mergulho, alcance (baixo, meio, alto), leitura
# (valores afinados simulando milhares de remates: ver o relatório, secção 4.2)
GR_PERFIL = {
    "facil":   (0.28, 135, (21, 16, 11), 0.38),
    "normal":  (0.20, 160, (24, 19, 14), 0.47),
    "dificil": (0.15, 210, (26, 21, 16), 0.68),
}


def erro_remate(forca: float, distancia: float, precisao: float = 1.0) -> float:
    """Desvio típico do remate (px): cresce muito com a força (força³) e com a distância."""
    return (1.0 + 6 * forca ** 3) * (distancia / 230) * precisao

ALTURA_TABELA_POV = 30       # no ecrã do remate as tabelas/placas têm ~1 m (como num pavilhão a sério)
_PASTA_UI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ui")
# Stick e bola desenhados por cima de tudo (como nos jogos na primeira pessoa). Valores em píxeis do ecrã.
# O stick (sprite «SUPER / AZEMAD.») vem de cima à direita e a pá fica em baixo à esquerda.
BOLA_ECRA = (470, 592)       # ponto onde a bola parada toca na pá
RAIO_BOLA_ECRA = 40
ANCORA_STICK = (128, 480)    # ponto da imagem stick_pov.png onde a bola assenta (em cima da pá)
ESCALA_STICK = 1.0
LADO_STICK = 1               # +1: o cabo está à direita da bola (o "puxar atrás" vai para a direita)
# Animação da stickada: o stick roda à volta das mãos (no punho preto)
PIVO_STICK = (790, 72)       # ponto da imagem stick_pov.png onde estão as mãos
ANG_PREPARAR = 34            # graus que o stick vem para trás (para o jogador) com a força toda
ANG_ACOMPANHAR = 26          # graus que o stick segue para a frente (para a baliza) depois do golpe
DUR_GOLPE = (0.15, 0.08)     # duração da descida do stick até à bola: fraco -> forte (segundos)

_PASTA_GR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sprites_v2", "hd", "frames",
                         "guarda_redes")
_cache = {}


def _img_gr(nome: str) -> pygame.Surface:
    if nome not in _cache:
        _cache[nome] = pygame.image.load(os.path.join(_PASTA_GR, nome + ".png")).convert_alpha()
    return _cache[nome]


# Defesas no ecrã do remate: sprites HD (128 px) com as cores do clube, em vez da imagem
# pequena (52 px) do jogo visto de cima, que ficava pixelizada quando era ampliada.
_POSES_DEFESA = {"parado": ["parado_01", "parado_02", "parado_03", "parado_02"]}


def _frames_defesa(jogador) -> dict:
    """Frames HD de um defesa (pintados com o equipamento dele), já recortados pelo corpo."""
    from animation import load_animation_from_names
    from cores import recolorir_frames, escurecer_stick, chave_kit
    kit = getattr(jogador, "kit", None)
    equipa = getattr(jogador, "equipa", "vermelho")
    chave = ("defesa_pov", chave_kit(kit) if kit else equipa)
    if chave in _cache:
        return _cache[chave]
    pasta = os.path.join(os.path.dirname(_PASTA_GR), "azul" if kit else equipa)
    poses = {}
    for pose, nomes in _POSES_DEFESA.items():
        frames = load_animation_from_names(pasta, nomes, alinhar=True).frames
        frames = escurecer_stick(("defesa_pov", pose), frames)
        if kit:
            frames = recolorir_frames(("defesa_pov", pose), frames, kit)
        poses[pose] = frames
    # Recorte comum a todos os frames (para o boneco não "saltar" ao trocar de frame)
    caixa = None
    for frames in poses.values():
        for f in frames:
            r = f.get_bounding_rect()
            caixa = r if caixa is None else caixa.union(r)
    poses = {p: [f.subsurface(caixa).copy() for f in fs] for p, fs in poses.items()}
    _cache[chave] = poses
    return poses


def _img_ui(nome: str, escala: float = 1.0):
    """Imagens do ecrã do remate (stick e bola, feitas com ferramentas/preparar_stick.py)."""
    chave = ("ui", nome, escala)
    if chave not in _cache:
        caminho = os.path.join(_PASTA_UI, nome)
        if not os.path.exists(caminho):
            _cache[chave] = None
        else:
            img = pygame.image.load(caminho).convert_alpha()
            if escala != 1.0:
                img = pygame.transform.smoothscale(img, (round(img.get_width() * escala),
                                                         round(img.get_height() * escala)))
            _cache[chave] = img
    return _cache[chave]


def decidir_remate(u_alvo: float, h_alvo: float, forca: float, distancia: float, u_gr: float,
                   dificuldade: str, rnd=random, precisao: float = 1.0, tapado: bool = False) -> dict:
    """
    Decide o que acontece a um remate. É uma função à parte (sem desenho) para se poder testar.
      u_alvo, h_alvo : ponto apontado na baliza (u = de lado, 0 = meio; h = altura)
      forca          : 0 a 1 (barra de força)
      distancia      : distância à baliza (px do campo)
      u_gr           : onde está o guarda-redes no início
    Devolve {"resultado", "u", "h", "u_gr", "velocidade", "tempo", "erro"}.
    """
    velocidade = 320 + 560 * forca
    erro = erro_remate(forca, distancia, precisao)
    u = u_alvo + rnd.gauss(0, erro)
    h = max(0.0, h_alvo + rnd.gauss(0, erro * 0.7))
    tempo = distancia / velocidade

    reacao, vel_gr, alcances, leitura = GR_PERFIL.get(dificuldade, GR_PERFIL["normal"])
    # Antes do remate, o guarda-redes já se inclina um pouco para o lado para onde o jogador aponta
    u_gr = u_gr + max(-12.0, min(12.0, u_alvo * 0.15))
    movimento = max(0.0, tempo - reacao) * vel_gr
    # Quanto mais tempo a bola demora a chegar, mais fácil é "ler" o lado do remate
    leitura *= min(1.0, max(0.2, (tempo - 0.12) / 0.45))
    if tapado:
        leitura *= 0.5          # um defesa à frente tapa a vista ao guarda-redes
    if rnd.random() < leitura:
        destino = u
    else:
        destino = u_gr + rnd.choice((-1, 1)) * rnd.uniform(5, 25)
    u_gr_final = u_gr + max(-movimento, min(movimento, destino - u_gr))
    u_gr_final = max(-MEIA_BOCA, min(MEIA_BOCA, u_gr_final))
    alcance = alcances[0] if h < 13 else (alcances[1] if h < 27 else alcances[2])

    if abs(u) > MEIA_BOCA + 3 or h > ALTURA_BALIZA + 3:
        resultado = "fora"
    elif abs(abs(u) - MEIA_BOCA) <= 3 or abs(h - ALTURA_BALIZA) <= 3:
        resultado = "poste"
    elif abs(u - u_gr_final) <= alcance:
        resultado = "defesa"
    else:
        resultado = "golo"
    return {"resultado": resultado, "u": u, "h": h, "u_gr": u_gr_final, "u_gr_inicio": u_gr,
            "velocidade": velocidade, "tempo": tempo, "erro": erro}


class RematePOV:
    """
    Ecrã do remate na primeira pessoa. O Game chama handle_event, update e draw; quando
    'terminado' fica True, lê 'resultado' (ou None se o jogador cancelou com ESC).
    """

    def __init__(self, screen, rink, jogador, gr, dificuldade: str, limite_tempo: float | None = 5.0,
                 cor_linhas=(30, 95, 210), defensores=(), velocidade=(0.0, 0.0), placar=None):
        self.screen = screen
        self.rink = rink
        self.jogador = jogador
        self.gr = gr
        self.dificuldade = dificuldade
        self.limite = limite_tempo
        self.tempo_restante = limite_tempo or 0.0
        self.cor_linhas = cor_linhas
        self.placar = placar                  # (sigla casa, golos, sigla fora, golos, tempo) para o marcador
        self.terminado = False
        self.resultado = None
        self.t = 0.0

        r = rink.rect
        self.gx = rink.linha_golo_esq_x          # o jogador (equipa azul) ataca a baliza da esquerda
        self.cy = r.centery
        self.fora_dir = -1                        # "atrás da baliza" é para a esquerda (x menor)
        self.bx = r.left                          # tabela atrás da baliza
        # O jogador continua a patinar, a 50 % da velocidade que trazia
        self.pos = [float(jogador.pos_x), float(jogador.pos_y)]
        self.vel_corrida = math.hypot(*velocidade)
        self.vel = (velocidade[0] * REDUCAO_VELOCIDADE, velocidade[1] * REDUCAO_VELOCIDADE)
        # Fotografia dos adversários no momento em que se carregou em X
        self.defensores = [{"jogador": d, "x": d.pos_x, "y": d.pos_y, "img": d.image.copy(),
                            "fase": random.uniform(0, 4)} for d in defensores]
        for d in self.defensores:
            try:
                d["poses"] = _frames_defesa(d["jogador"])
            except (pygame.error, FileNotFoundError, ValueError):
                d["poses"] = None              # sem os sprites HD usa-se a imagem do jogo
        self._definir_camera()

        self.u, self.h = 0.0, 12.0                # mira começa no meio, a meia altura baixa
        self.u_gr0 = max(-22.0, min(22.0, gr.pos_y - self.cy))
        self.u_gr = self.u_gr0
        self.a_carregar = False
        self.forca = 0.0
        self._sentido_forca = 1
        self.estado = "mirar"                     # mirar -> golpe -> voo -> resultado
        self._ang = 0.0                           # ângulo do stick (graus): + = para trás (para o jogador), − = para a frente
        self._ang_inicio = 0.0
        self._golpe_t = 0.0
        self._golpe_dur = 0.1
        self._rasto = []                          # ângulos anteriores do stick (rasto de velocidade)
        self._impacto_t = -1.0                    # tempo desde o contacto com a bola (clarão)
        self._cache_stick = {}
        self._rato_ant = pygame.mouse.get_pos()
        self._decisao = None
        self._voo_t = 0.0
        self._voo_dur = 0.4
        self._res_t = 0.0
        self._fundo = self._criar_fundo()
        self._cena = None             # parte fixa da imagem: refeita só quando a câmara anda
        self._frente = None
        self._pos_cena = None
        self._cache_texto = {}

    def _definir_camera(self):
        """Câmara nos olhos do jogador, virada para o centro da baliza."""
        px, py = self.pos
        dx, dy = self.gx - px, self.cy - py
        self.distancia = max(40.0, math.hypot(dx, dy))
        dist_cam = max(self.distancia, 115.0)     # muito perto, a câmara recua um pouco (vê-se a baliza toda)
        self.fx, self.fy = dx / self.distancia, dy / self.distancia
        self.rx, self.ry = -self.fy, self.fx
        self.cx_mundo = self.gx - self.fx * dist_cam
        self.cy_mundo = self.cy - self.fy * dist_cam
        self.z_baliza = self._cam(self.gx, self.cy)[1]
        # Lado do ecrã para onde vai o +u (para as setas andarem para o lado certo)
        a, b = self._proj(self.gx, self.cy, 10), self._proj(self.gx, self.cy + 1, 10)
        self.sinal_u = 1 if (a and b and b[0] > a[0]) else -1
        # Bola na pá do stick. Há duas posições:
        #  • bola_ini   - onde a bola está mesmo (20 px à frente do jogador): é daqui que sai o remate
        #                 e que se testa se algum defesa está no caminho;
        #  • bola_vista - onde se DESENHA a bola parada com o stick (em baixo, à direita, como nos jogos
        #                 na primeira pessoa). No voo, a bola passa suavemente de uma para a outra.
        self.bola_ini = (self.pos[0] + self.fx * 20, self.pos[1] + self.fy * 20, 0.0)
        self.bola_vista = (BOLA_ECRA[0], BOLA_ECRA[1], F * RAIO_BOLA / RAIO_BOLA_ECRA)
        # Ponto do chão que está por baixo da bola desenhada (projeção ao contrário): é daqui que a
        # animação do remate parte, para a bola sair da pá sem saltos nem crescer
        z = F * OLHOS / max(1.0, BOLA_ECRA[1] - HORIZONTE)
        xc = (BOLA_ECRA[0] - CX) * z / F
        self.bola_anim = (self.cx_mundo + self.fx * z + self.rx * xc,
                          self.cy_mundo + self.fy * z + self.ry * xc, 0.0)

    # ------------------------------------------------------------------ #
    # Projeção                                                           #
    # ------------------------------------------------------------------ #
    def _cam(self, wx, wy):
        vx, vy = wx - self.cx_mundo, wy - self.cy_mundo
        return vx * self.rx + vy * self.ry, vx * self.fx + vy * self.fy       # (x, z)

    def _proj(self, wx, wy, h=0.0):
        x, z = self._cam(wx, wy)
        if z < PERTO:
            return None
        return CX + F * x / z, HORIZONTE + F * (OLHOS - h) / z, z

    def _proj_cam(self, x, z, h):
        return CX + F * x / z, HORIZONTE + F * (OLHOS - h) / z

    def _segmento(self, s, p1, p2, cor, largura_mundo=1.5, larg_min=1):
        """Linha entre dois pontos do mundo (x, y, h), cortada se passar para trás da câmara."""
        (x1, z1), (x2, z2) = self._cam(p1[0], p1[1]), self._cam(p2[0], p2[1])
        h1, h2 = p1[2], p2[2]
        if z1 < PERTO and z2 < PERTO:
            return
        if z1 < PERTO or z2 < PERTO:
            k = (PERTO - z1) / (z2 - z1)
            xm, hm = x1 + (x2 - x1) * k, h1 + (h2 - h1) * k
            if z1 < PERTO:
                x1, z1, h1 = xm, PERTO, hm
            else:
                x2, z2, h2 = xm, PERTO, hm
        a, b = self._proj_cam(x1, z1, h1), self._proj_cam(x2, z2, h2)
        larg = max(larg_min, round(F * largura_mundo / ((z1 + z2) / 2)))
        if larg <= 1:
            pygame.draw.aaline(s, cor, a, b)
        else:
            pygame.draw.line(s, cor, a, b, larg)

    def _poligono(self, pontos_mundo):
        """Corta um polígono (pontos x, y, h do mundo) pelo plano z = PERTO e projeta-o."""
        cam = [(*self._cam(x, y), h) for x, y, h in pontos_mundo]
        out = []
        n = len(cam)
        for i in range(n):
            a, b = cam[i], cam[(i + 1) % n]
            dentro_a, dentro_b = a[1] >= PERTO, b[1] >= PERTO
            if dentro_a:
                out.append(a)
            if dentro_a != dentro_b:
                k = (PERTO - a[1]) / (b[1] - a[1])
                out.append((a[0] + (b[0] - a[0]) * k, PERTO, a[2] + (b[2] - a[2]) * k))
        return [self._proj_cam(x, z, h) for x, z, h in out]

    def _mira_do_rato(self, sx, sy):
        """Converte a posição do rato no ponto (u, h) da baliza (inverso da projeção)."""
        x0, z0 = self._cam(self.gx, self.cy)
        x1, z1 = self._cam(self.gx, self.cy + 1)
        xu, zu = x1 - x0, z1 - z0
        dxs = sx - CX
        den = F * xu - dxs * zu
        if abs(den) < 1e-6:
            return
        u = (dxs * z0 - F * x0) / den
        z = z0 + u * zu
        h = OLHOS - (sy - HORIZONTE) * z / F
        self.u = max(-58.0, min(58.0, u))
        self.h = max(0.0, min(60.0, h))

    # ------------------------------------------------------------------ #
    # Eventos e lógica                                                   #
    # ------------------------------------------------------------------ #
    def handle_event(self, event):
        if self.estado != "mirar":
            # Depois do remate, qualquer tecla salta a animação do resultado
            if self.estado == "resultado" and event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                self._res_t = 99
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE and not self.a_carregar:
                self.terminado, self.resultado = True, None
            elif event.key in (pygame.K_x, pygame.K_SPACE, pygame.K_RETURN):
                self._comecar_carga()
        elif event.type == pygame.KEYUP and event.key in (pygame.K_x, pygame.K_SPACE, pygame.K_RETURN):
            if self.a_carregar:
                self._rematar()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._comecar_carga()
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.a_carregar:
            self._rematar()
        elif event.type == pygame.MOUSEMOTION:
            self._mira_do_rato(*event.pos)

    def _avancar(self, dt: float):
        """O jogador continua a patinar (a 50 %) enquanto aponta e carrega o remate."""
        if self.vel == (0.0, 0.0):
            return
        nx, ny = self.pos[0] + self.vel[0] * dt, self.pos[1] + self.vel[1] * dt
        r = self.rink.rect
        perto = math.hypot(self.gx - nx, self.cy - ny) < DIST_MINIMA or nx < self.gx + 40
        fora = not (r.left + 20 < nx < r.right - 20 and r.top + 20 < ny < r.bottom - 20)
        # Trava antes de um defesa que esteja mesmo à frente (senão ficava encostado a ele e o
        # defesa tapava o ecrã todo); os que estão ao lado só travam se houver contacto
        fx, fy = self.gx - nx, self.cy - ny
        n = math.hypot(fx, fy) or 1.0
        fx, fy = fx / n, fy / n

        def no_caminho(d):
            vx, vy = d["x"] - nx, d["y"] - ny
            frente, lado = vx * fx + vy * fy, abs(vx * fy - vy * fx)
            return (0 < frente < DIST_TRAVAR and lado < 30) or math.hypot(vx, vy) < 30
        choca = any(no_caminho(d) for d in self.defensores)
        if perto or fora or choca:
            self.vel = (0.0, 0.0)               # parou (baliza, tabela ou um defesa à frente)
            return
        self.pos = [nx, ny]
        self._definir_camera()

    # ------------------------------------------------------------------ #
    # Bloqueio pelos defesas (raycasting)                                #
    # ------------------------------------------------------------------ #
    def _linha_bloqueada(self, u: float, h: float):
        """
        Segue a linha da bola (do stick até ao ponto (u, h) da baliza) e devolve o primeiro
        defesa que a corta: (índice, t) com t = fração do caminho; ou None.
        Também devolve se algum defesa passa perto da linha (tapa a vista ao guarda-redes).
        O corpo de cada defesa é um cilindro de raio RAIO_DEFESA e altura ALTURA_DEFESA.
        """
        x0, y0, h0 = self.bola_ini
        x1, y1, h1 = self.gx, self.cy + u, h
        vx, vy = x1 - x0, y1 - y0
        comp2 = vx * vx + vy * vy
        primeiro, tapado = None, False
        for i, d in enumerate(self.defensores):
            # Ponto do caminho (no chão) mais perto do centro do defesa
            t = max(0.0, min(1.0, ((d["x"] - x0) * vx + (d["y"] - y0) * vy) / comp2))
            if not 0.02 < t < 0.98:
                continue
            dist = math.hypot(x0 + vx * t - d["x"], y0 + vy * t - d["y"])
            altura = h0 + (h1 - h0) * t
            if dist < RAIO_DEFESA + RAIO_BOLA and altura < ALTURA_DEFESA:
                if primeiro is None or t < primeiro[1]:
                    primeiro = (i, t)
            elif dist < 38 and t > 0.3:
                tapado = True
        return primeiro, tapado

    def _comecar_carga(self):
        if not self.a_carregar:
            self.a_carregar = True
            self.forca = 0.0
            self._sentido_forca = 1

    def _angulo_stick(self, dt: float) -> float:
        """
        Ângulo do stick em cada fase (o stick roda à volta das mãos):
          • mirar  - parado balança um pouco; a carregar vem para trás (para o jogador) conforme a força;
          • golpe  - varre cada vez mais depressa até à bola (aceleração: ângulo × (1 − k²));
          • depois - segue para a frente, em direção à baliza (acompanhamento), e volta um pouco.
        """
        if self.estado == "mirar":
            alvo = ANG_PREPARAR * self.forca if self.a_carregar else 1.2 * math.sin(self.t * 2.2)
            return self._ang + (alvo - self._ang) * min(1.0, dt * 16)
        if self.estado == "golpe":
            k = min(1.0, self._golpe_t / self._golpe_dur)
            return self._ang_inicio * (1 - k * k)
        tt = self._voo_t if self.estado == "voo" else self._voo_dur + self._res_t
        forca = self._decisao.get("forca", 0.5) if self._decisao else 0.5
        ida = ANG_ACOMPANHAR * (0.45 + 0.55 * forca) * (1 - math.exp(-tt * 14))
        volta = 0.4 * min(1.0, max(0.0, (tt - 0.45) / 0.6))
        return -ida * (1 - volta)

    def update(self, dt: float):
        self.t += dt
        self._ang = self._angulo_stick(dt)
        self._rasto = ([self._ang] + self._rasto)[:4]
        if self._impacto_t >= 0:
            self._impacto_t += dt
        if self.estado == "golpe":
            self._golpe_t += dt
            if self._golpe_t >= self._golpe_dur:
                # Contacto com a bola: só agora a bola sai
                self.estado = "voo"
                self._voo_t = 0.0
                self._impacto_t = 0.0
                self._ang = 0.0
                som.tocar("remate", 0.6 + 0.4 * self._decisao.get("forca", 0.5))
            return
        if self.estado == "mirar":
            teclas = pygame.key.get_pressed()
            du = (teclas[pygame.K_RIGHT] or teclas[pygame.K_d]) - (teclas[pygame.K_LEFT] or teclas[pygame.K_a])
            dh = (teclas[pygame.K_UP] or teclas[pygame.K_w]) - (teclas[pygame.K_DOWN] or teclas[pygame.K_s])
            self.u = max(-58.0, min(58.0, self.u + du * self.sinal_u * 70 * dt))
            self.h = max(0.0, min(60.0, self.h + dh * 50 * dt))
            # O guarda-redes inclina-se um pouco para o lado para onde estás a apontar
            self.u_gr = self.u_gr0 + max(-12.0, min(12.0, self.u * 0.15))
            self._avancar(dt)
            if self.a_carregar:
                # A barra sobe e desce: é preciso largar no momento certo
                self.forca += self._sentido_forca * dt / 0.9
                if self.forca >= 1.0:
                    self.forca, self._sentido_forca = 1.0, -1
                elif self.forca <= 0.0:
                    self.forca, self._sentido_forca = 0.0, 1
            if self.limite:
                self.tempo_restante -= dt
                if self.tempo_restante <= 0:
                    # Acabou o tempo: remata como estiver (fraco, se nem começou a carregar)
                    if not self.a_carregar:
                        self.forca = 0.3
                    self._rematar()
        elif self.estado == "voo":
            self._voo_t += dt
            k = min(1.0, self._voo_t / self._voo_dur)
            d = self._decisao
            # O guarda-redes só começa a mexer-se depois do tempo de reação
            reacao = GR_PERFIL.get(self.dificuldade, GR_PERFIL["normal"])[0]
            kr = max(0.0, min(1.0, (k * d["tempo"] - reacao) / max(0.05, d["tempo"] - reacao)))
            ini = d["u_gr_inicio"]
            self.u_gr = ini + (d["u_gr"] - ini) * (1 - (1 - kr) ** 2)
            if d["resultado"] == "bloqueado":
                # A bola só vai até ao defesa: a animação dura a parte do caminho até lá
                k = min(1.0, self._voo_t / max(0.12, self._voo_dur * d["t_bloqueio"]))
            if k >= 1.0:
                self.estado = "resultado"
                self._res_t = 0.0
                r = d["resultado"]
                if r == "bloqueado":
                    som.tocar("defesa", 1.0)
                    som.tocar("publico_uh", 0.6)
                elif r == "defesa":
                    som.tocar("defesa", 0.9)
                    som.tocar("publico_uh", 0.7)
                elif r == "poste":
                    som.tocar("poste", 1.0)
                    som.tocar("publico_uh", 0.8)
                elif r == "fora":
                    som.tocar("tabela", 0.6)
        elif self.estado == "resultado":
            self._res_t += dt
            if self._res_t > 1.1:
                self.terminado = True
                self.resultado = self._decisao

    def _rematar(self):
        self.a_carregar = False
        precisao = 1.15 - getattr(self.jogador, "stat_remate", 80) / 400
        _b, tapado = self._linha_bloqueada(self.u, self.h)
        self._decisao = decidir_remate(self.u, self.h, self.forca, self.distancia, self.u_gr0,
                                       self.dificuldade, precisao=precisao, tapado=tapado)
        self._decisao["forca"] = self.forca
        self._decisao["tapado"] = tapado
        self._decisao["pos"] = tuple(self.pos)
        self._decisao["vel"] = self.vel
        self._decisao["bola_ini"] = self.bola_ini
        self._decisao["bola_vista"] = self.bola_vista
        self._decisao["bola_anim"] = self.bola_anim
        # A linha REAL do remate (já com o erro) pode bater num defesa
        bloqueio, _t = self._linha_bloqueada(self._decisao["u"], self._decisao["h"])
        if bloqueio is not None:
            i, t = bloqueio
            d = self.defensores[i]
            self._decisao.update(resultado="bloqueado", t_bloqueio=t, bloqueador=d["jogador"],
                                 pos_bloqueio=(d["x"], d["y"]))
            self._decisao["u_gr"] = self._decisao["u_gr_inicio"]
        # A animação dura mais do que o voo real, para se perceber o que aconteceu
        self._voo_dur = max(0.3, min(0.75, self._decisao["tempo"] * 1.7))
        self._voo_t = 0.0
        # Tempo em que a bola passa do canto do ecrã (onde está desenhada) para o caminho real
        voo_real = self._voo_dur * self._decisao.get("t_bloqueio", 1.0)
        self._mistura = max(0.06, min(0.22, 0.8 * voo_real))
        # Primeiro o stick desce até à bola (mais força = desce mais depressa); a bola sai no contacto
        self.estado = "golpe"
        self._golpe_t = 0.0
        self._golpe_dur = DUR_GOLPE[0] + (DUR_GOLPE[1] - DUR_GOLPE[0]) * self.forca
        self._ang_inicio = max(self._ang, 6.0)      # mesmo sem carregar, há um pequeno balanço

    # ------------------------------------------------------------------ #
    # Desenho                                                            #
    # ------------------------------------------------------------------ #
    def _criar_fundo(self):
        """Fundo: a bancada do pavilhão (com cadeiras e adeptos), as faixas e o marcador eletrónico."""
        fundo = pygame.Surface((WIDTH, HEIGHT))
        fundo.fill((40, 44, 52))
        cor_casa = obter_info_equipa(self.rink.equipa_casa).get("cor_primaria", (30, 80, 180))
        fundo.blit(pavilhao_pov.bancada(HORIZONTE + 40, cor_casa), (0, 0))
        pavilhao_pov.marcador(fundo, CX, self.placar)
        for x in (300, 980):                           # luzes do teto
            l = luz(460, 200, (255, 245, 225), 40)
            fundo.blit(l, l.get_rect(center=(x, 30)), special_flags=pygame.BLEND_RGB_ADD)
        return fundo

    def _desenhar_campo(self, s):
        r = self.rink.rect
        # Piso de madeira
        piso = self._poligono([(r.left, r.top, 0), (r.right, r.top, 0), (r.right, r.bottom, 0), (r.left, r.bottom, 0)])
        if len(piso) >= 3:
            pygame.draw.polygon(s, (170, 98, 54), piso)          # madeira envernizada (mais escura)
            # Mais escuro ao longe (perto do horizonte)
            sombra = self._buffer("sombra")
            for y in range(HORIZONTE - 60, HORIZONTE + 160, 4):
                a = max(0, int(90 * (1 - (y - HORIZONTE + 60) / 220)))
                pygame.draw.rect(sombra, (60, 30, 10, a), (0, y, WIDTH, 4))
            mascara = self._buffer("mascara")
            pygame.draw.polygon(mascara, (255, 255, 255, 255), piso)
            sombra.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            s.blit(sombra, (0, 0))
        # Tábuas: linhas paralelas às tabelas laterais
        for y in range(r.top + 16, r.bottom, 16):
            self._segmento(s, (r.left, y, 0), (r.right, y, 0), (138, 76, 40) if (y // 16) % 2 else (190, 116, 66), 0.4)
        # Linhas do campo: grande área, linha de golo e marcas de penálti
        a_y0, a_y1 = self.cy - 125, self.cy + 125
        gx, cor = self.gx, self.cor_linhas
        ax = gx + 150
        for p1, p2 in (((gx, a_y0), (ax, a_y0)), ((ax, a_y0), (ax, a_y1)), ((ax, a_y1), (gx, a_y1)),
                       ((gx, a_y0), (gx, a_y1))):
            self._segmento(s, (*p1, 0), (*p2, 0), cor, 2.0, 2)
        self._segmento(s, (gx, self.cy - MEIA_BOCA, 0), (gx, self.cy + MEIA_BOCA, 0), (220, 40, 40), 2.2, 2)
        for dx, rr in ((85, 2.5), (130, 2.0)):
            p = self._proj(gx + dx, self.cy)
            if p:
                pygame.draw.ellipse(s, cor, pygame.Rect(0, 0, max(2, F * rr * 2 / p[2]),
                                                         max(2, F * rr / p[2])).move(p[0] - F * rr / p[2], p[1] - F * rr / 2 / p[2]))

    def _reflexos(self, s):
        """O verniz reflete as luzes e as placas: manchas de luz somadas às cores do piso."""
        p = self._proj(self.bx, self.cy, 0)
        if not p:
            return
        yb = p[1]
        faixa = luz(int(WIDTH * 1.1), 70, (255, 235, 210), 45)
        s.blit(faixa, faixa.get_rect(center=(CX, yb + 18)), special_flags=pygame.BLEND_RGB_ADD)
        for x in (300, 640, 980):
            l = luz(150, 420, (255, 230, 200), 30, 1.2)
            s.blit(l, l.get_rect(midtop=(x, yb + 4)), special_flags=pygame.BLEND_RGB_ADD)

    def _placa(self, s, a, b, alt, tex):
        """
        Cola uma placa de publicidade numa tabela em perspetiva: a placa é cortada em tiras
        verticais e cada tira é esticada para a altura certa naquele ponto da tabela.
        """
        pa, pb = self._proj(a[0], a[1], 0), self._proj(b[0], b[1], 0)
        if not pa or not pb:
            return
        if pb[0] < pa[0]:                      # para o texto ficar sempre da esquerda para a direita
            a, b, pa, pb = b, a, pb, pa
        n = max(2, min(40, int((pb[0] - pa[0]) / 10)))
        tw, th = tex.get_size()
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            p0 = (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0)
            p1 = (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)
            b0, c0 = self._proj(p0[0], p0[1], 0), self._proj(p0[0], p0[1], alt)
            b1, c1 = self._proj(p1[0], p1[1], 0), self._proj(p1[0], p1[1], alt)
            if not (b0 and b1 and c0 and c1):
                continue
            x0, x1 = b0[0], b1[0]
            topo, base = (c0[1] + c1[1]) / 2, (b0[1] + b1[1]) / 2
            w, h = math.ceil(abs(x1 - x0)) + 1, math.ceil(base - topo)
            if w < 1 or h < 1 or w > 600:
                continue
            u0, u1 = int(t0 * tw), max(int(t0 * tw) + 1, int(t1 * tw))
            tira = tex.subsurface((u0, 0, min(u1, tw) - u0, th))
            s.blit(pygame.transform.scale(tira, (w, h)), (min(x0, x1), topo))

    def _desenhar_tabelas(self, s):
        """Tabelas com placas de publicidade (atrás da baliza e dos lados, perto dela)."""
        r = self.rink.rect
        alt = ALTURA_TABELA_POV
        for quad in (
            [(self.bx, r.top, 0), (self.bx, r.bottom, 0), (self.bx, r.bottom, alt), (self.bx, r.top, alt)],
            [(self.bx, r.top, 0), (r.right, r.top, 0), (r.right, r.top, alt), (self.bx, r.top, alt)],
            [(self.bx, r.bottom, 0), (r.right, r.bottom, 0), (r.right, r.bottom, alt), (self.bx, r.bottom, alt)],
        ):
            pts = self._poligono(quad)
            if len(pts) >= 3:
                pygame.draw.polygon(s, (226, 230, 238), pts)
        seg = (r.bottom - r.top) / 4
        for i in range(4):                                         # atrás da baliza
            self._placa(s, (self.bx, r.top + i * seg), (self.bx, r.top + (i + 1) * seg), alt,
                        pavilhao_pov.textura_placa(i))
        for i in range(4):                                         # nos lados, perto da baliza
            x0 = self.bx + i * 130
            self._placa(s, (x0, r.top), (x0 + 130, r.top), alt, pavilhao_pov.textura_placa(i + 4))
            self._placa(s, (x0, r.bottom), (x0 + 130, r.bottom), alt, pavilhao_pov.textura_placa(i + 2))
        # Corrimão na cor da equipa da casa e rodapé
        for p1, p2 in (((self.bx, r.top), (self.bx, r.bottom)), ((self.bx, r.top), (r.right, r.top)),
                       ((self.bx, r.bottom), (r.right, r.bottom))):
            self._segmento(s, (*p1, alt), (*p2, alt), self.cor_linhas, 2.0, 2)
            self._segmento(s, (*p1, 0), (*p2, 0), (40, 30, 24), 1.0, 1)

    def _desenhar_tabelas_simples(self, s):
        r = self.rink.rect
        alt = 13
        # Tabela atrás da baliza e tabelas dos lados
        for quad in (
            [(self.bx, r.top, 0), (self.bx, r.bottom, 0), (self.bx, r.bottom, alt), (self.bx, r.top, alt)],
            [(self.bx, r.top, 0), (r.right, r.top, 0), (r.right, r.top, alt), (self.bx, r.top, alt)],
            [(self.bx, r.bottom, 0), (r.right, r.bottom, 0), (r.right, r.bottom, alt), (self.bx, r.bottom, alt)],
        ):
            pts = self._poligono(quad)
            if len(pts) >= 3:
                pygame.draw.polygon(s, (226, 230, 238), pts)
        # Corrimão na cor da equipa da casa
        for p1, p2 in (((self.bx, r.top), (self.bx, r.bottom)), ((self.bx, r.top), (r.right, r.top)),
                       ((self.bx, r.bottom), (r.right, r.bottom))):
            self._segmento(s, (*p1, alt), (*p2, alt), self.cor_linhas, 3.0, 3)
            self._segmento(s, (*p1, 0), (*p2, 0), (80, 86, 104), 1.0, 1)

    def _desenhar_baliza(self, s, frente: bool):
        """frente=False: rede (atrás do guarda-redes); frente=True: postes e barra (à frente)."""
        gx, cy, o = self.gx, self.cy, self.fora_dir
        H, M, P = ALTURA_BALIZA, MEIA_BOCA, PROF_BALIZA
        trasx = gx + o * P
        if not frente:
            rede = self._buffer("rede")
            cor_rede = (235, 240, 250, 150)
            for k in range(0, 2 * M + 1, 6):                         # rede de trás: verticais
                y = cy - M + k
                self._segmento(rede, (trasx, y, 0), (trasx, y, H * 0.8), cor_rede, 0.35)
            for hh in range(0, int(H * 0.8) + 1, 6):                 # rede de trás: horizontais
                self._segmento(rede, (trasx, cy - M, hh), (trasx, cy + M, hh), cor_rede, 0.35)
            for lado in (-1, 1):                                     # redes dos lados
                for k in range(0, P + 1, 6):
                    x = gx + o * k
                    self._segmento(rede, (x, cy + lado * M, 0), (x, cy + lado * M, H - (H * 0.2) * k / P), cor_rede, 0.35)
            for k in range(0, 2 * M + 1, 6):                         # rede de cima
                y = cy - M + k
                self._segmento(rede, (gx, y, H), (trasx, y, H * 0.8), cor_rede, 0.35)
            s.blit(rede, (0, 0))
            for lado in (-1, 1):                                     # postes de trás
                self._segmento(s, (trasx, cy + lado * M, 0), (trasx, cy + lado * M, H * 0.8), (170, 40, 40), 1.6, 2)
            self._segmento(s, (trasx, cy - M, H * 0.8), (trasx, cy + M, H * 0.8), (170, 40, 40), 1.6, 2)
        else:
            for lado in (-1, 1):
                self._segmento(s, (gx, cy + lado * M, 0), (gx, cy + lado * M, H), (25, 10, 10), 3.4, 3)
                self._segmento(s, (gx, cy + lado * M, 0), (gx, cy + lado * M, H), (220, 45, 45), 2.6, 2)
                self._segmento(s, (gx, cy + lado * M, H), (trasx, cy + lado * M, H * 0.8), (220, 45, 45), 2.0, 2)
            self._segmento(s, (gx, cy - M, H), (gx, cy + M, H), (25, 10, 10), 3.4, 3)
            self._segmento(s, (gx, cy - M, H), (gx, cy + M, H), (220, 45, 45), 2.6, 2)

    def _desenhar_ondulacao(self, s):
        """A rede abana onde a bola entrou (só no golo)."""
        trasx = self.gx + self.fora_dir * PROF_BALIZA
        p = self._proj(trasx, self.cy + self._decisao["u"], self._decisao["h"])
        if not p:
            return
        for i in range(3):
            rr = F * (4 + 7 * i + 10 * self._res_t) / p[2]
            a = max(0, int(200 - 160 * self._res_t - 40 * i))
            if a <= 0 or rr < 1:
                continue
            camada = pygame.Surface((round(rr * 2) + 4, round(rr * 1.4) + 4), pygame.SRCALPHA)
            pygame.draw.ellipse(camada, (255, 255, 255, a), camada.get_rect().inflate(-2, -2), 2)
            s.blit(camada, camada.get_rect(center=(p[0], p[1])))

    def _desenhar_gr(self, s):
        x = self.gx - self.fora_dir * 6                 # um pouco à frente da linha de golo
        p = self._proj(x, self.cy + self.u_gr, 0)
        if not p:
            return
        mergulho = self.u_gr - self.u_gr0
        if self.estado == "mirar":
            img = _img_gr("mover_baixo")
            ang, levanta = 0, 0
        else:
            img = _img_gr("defender_01" if int(self.t * 8) % 2 == 0 else "defender_02")
            # Inclina para o lado do mergulho; nos remates altos o corpo sobe
            lado_ecra = 1 if (mergulho * self.sinal_u) > 0 else -1
            ang = -lado_ecra * min(55, abs(mergulho) * 2.2)
            levanta = min(14, self._decisao["h"] * 0.35) * min(1.0, abs(mergulho) / 12)
            if lado_ecra < 0:
                img = pygame.transform.flip(img, True, False)
        alt = F * 62 / p[2]                              # 62 = altura da imagem no campo (o boneco ocupa ~70 %)
        img = pygame.transform.scale(img, (max(2, round(alt)), max(2, round(alt))))
        # O boneco não está ao centro da imagem: centramos pela parte visível
        caixa = img.get_bounding_rect()
        desvio = img.get_width() / 2 - caixa.centerx
        if ang:
            img = pygame.transform.rotate(img, ang)
        sombra = pygame.Surface((round(alt * 0.7), round(alt * 0.16)), pygame.SRCALPHA)
        pygame.draw.ellipse(sombra, (20, 10, 0, 90), sombra.get_rect())
        s.blit(sombra, sombra.get_rect(center=(p[0], p[1])))
        # O centro do corpo fica a ~35 % da altura da imagem acima dos patins (também quando roda)
        centro = (p[0] + desvio, p[1] - alt * 0.36 - F * levanta / p[2])
        s.blit(img, img.get_rect(center=centro))

    def _defesa_destacado(self):
        """Índice do defesa que tapa a linha do remate (a apontar) ou que bloqueou a bola."""
        if self.estado == "mirar":
            bloqueio, _t = self._linha_bloqueada(self.u, self.h)
            return bloqueio[0] if bloqueio else None
        d = self._decisao
        if d and d["resultado"] == "bloqueado":
            for i, df in enumerate(self.defensores):
                if df["jogador"] is d["bloqueador"]:
                    return i
        return None

    def _blit_escalado(self, s, src, rect, alpha=255):
        """
        Desenha 'src' esticada até 'rect', mas só a parte que cabe no ecrã: um defesa mesmo à
        frente pode ter milhares de píxeis de altura e não vale a pena ampliar o que não se vê.
        """
        vis = rect.clip(s.get_rect())
        if vis.w <= 0 or vis.h <= 0:
            return
        kx, ky = src.get_width() / rect.w, src.get_height() / rect.h
        x0, y0 = int((vis.x - rect.x) * kx), int((vis.y - rect.y) * ky)
        x1 = min(src.get_width(), math.ceil((vis.right - rect.x) * kx))
        y1 = min(src.get_height(), math.ceil((vis.bottom - rect.y) * ky))
        if x1 <= x0 or y1 <= y0:
            return
        # Volta a converter o recorte para o ecrã (assim os píxeis ficam no sítio certo)
        dx, dy = rect.x + x0 / kx, rect.y + y0 / ky
        w, h = max(1, round((x1 - x0) / kx)), max(1, round((y1 - y0) / ky))
        parte = pygame.transform.scale(src.subsurface((x0, y0, x1 - x0, y1 - y0)), (w, h))
        if alpha < 255:
            parte.set_alpha(alpha)
        s.blit(parte, (round(dx), round(dy)))

    def _silhueta(self, img, cor):
        """Silhueta de uma cor só (para o contorno do defesa destacado)."""
        chave = ("silhueta", id(img), cor)
        if chave not in _cache:
            _cache[chave] = pygame.mask.from_surface(img).to_surface(setcolor=(*cor, 255),
                                                                     unsetcolor=(0, 0, 0, 0))
        return _cache[chave]

    def _desenhar_defensores(self, s, perto_de: float, longe_de: float):
        """
        Desenha os defesas com z entre perto_de e longe_de (do mais longe para o mais perto).
        O tamanho segue SEMPRE a perspetiva (F · altura / z): quanto mais perto, maior, sem limite.
        Antes havia um limite de 380 px e os defesas desapareciam a menos de 40 px; ao avançar
        deixavam de crescer enquanto o campo à volta crescia, e pareciam encolher.
        """
        lista = []
        for i, d in enumerate(self.defensores):
            _x, z = self._cam(d["x"], d["y"])
            if z < PERTO + 6 or not (perto_de <= z < longe_de) or z > self.z_baliza - 2:
                continue
            lista.append((z, i, d))
        destaque = self._defesa_destacado()
        for z, i, d in sorted(lista, key=lambda e: -e[0]):
            self._desenhar_defesa(s, d, z, i == destaque)

    def _desenhar_defesa(self, s, d, z, destacado):
        p = self._proj(d["x"], d["y"], 0)
        if not p:
            return
        bloqueou = destacado and self.estado == "resultado"
        if d["poses"]:
            frames = d["poses"]["parado"]
            img = frames[0] if bloqueou else frames[int((self.t + d["fase"]) * 3) % len(frames)]
            if p[0] > CX:                       # os sprites olham para a direita: viram-se para o meio
                chave = ("espelho", id(img))
                if chave not in _cache:
                    _cache[chave] = pygame.transform.flip(img, True, False)
                img = _cache[chave]
            alt = F * ALTURA_DEFESA / z
        else:
            img = d["img"]
            alt = F * 58 / z
        larg = alt * img.get_width() / img.get_height()
        x = p[0]
        if bloqueou:                            # a bola bate-lhe no corpo: abana
            x += math.sin(self._res_t * 70) * alt * 0.025 * max(0.0, 1 - self._res_t / 0.4)
        # Muito perto ficam meio transparentes, para não taparem a baliza toda
        alpha = 255 if z >= 140 else int(110 + 145 * max(0.0, (z - 60) / 80))
        # Sombra no chão
        sombra = pygame.Surface((max(2, round(alt * 0.55)), max(2, round(alt * 0.12))), pygame.SRCALPHA)
        pygame.draw.ellipse(sombra, (20, 10, 0, int(110 * alpha / 255)), sombra.get_rect())
        s.blit(sombra, sombra.get_rect(center=(x, p[1])))
        rect = pygame.Rect(round(x - larg / 2), round(p[1] - alt), max(1, round(larg)), max(1, round(alt)))
        if destacado:
            # Anel e contorno vermelhos: é este defesa que está no caminho da bola
            anel = pygame.Rect(0, 0, max(4, round(alt * 0.7)), max(3, round(alt * 0.16)))
            anel.center = (round(x), round(p[1]))
            pygame.draw.ellipse(s, (255, 70, 60), anel, max(2, round(alt * 0.012)))
            if alpha == 255:
                # (meio transparente não leva contorno: as várias cópias somavam-se numa mancha)
                sil = self._silhueta(img, (255, 70, 60))
                e = max(2, min(6, round(alt * 0.012)))
                for ox, oy in ((-e, 0), (e, 0), (0, -e), (0, e), (-e, -e), (e, -e), (-e, e), (e, e)):
                    self._blit_escalado(s, sil, rect.move(ox, oy))
        self._blit_escalado(s, img, rect, alpha)
        if bloqueou and self._res_t < 0.3:
            # A bola bate-lhe no corpo: pisca a branco
            self._blit_escalado(s, self._silhueta(img, (255, 255, 255)), rect, int(200 * (1 - self._res_t / 0.3)))
        if destacado and self.estado == "mirar":
            nome = getattr(d["jogador"], "nome", "")
            txt = fonte(14).render(nome, True, (255, 255, 255))
            caixa = txt.get_rect(center=(round(x), max(112, rect.top - 18))).inflate(16, 8)
            pygame.draw.rect(s, (200, 40, 40), caixa, border_radius=8)
            pygame.draw.rect(s, (255, 200, 190), caixa, 1, border_radius=8)
            s.blit(txt, txt.get_rect(center=caixa.center))

    def _pos_bola(self):
        """Posição da bola no mundo (x, y, h) durante a animação do remate."""
        d = self._decisao
        bx0, by0, bh0 = d["bola_anim"]
        if d["resultado"] == "bloqueado":
            t = d["t_bloqueio"]
            rx0, ry0, _rh = d["bola_ini"]          # o ponto do bloqueio é o da linha real
            cx, cy_, ch = rx0 + (self.gx - rx0) * t, ry0 + (self.cy + d["u"] - ry0) * t, d["h"] * t
            if self.estado == "voo":
                k = min(1.0, self._voo_t / max(0.12, self._voo_dur * t))
                return bx0 + (cx - bx0) * k, by0 + (cy_ - by0) * k, ch * k
            # Ressalto no defesa: volta para trás e para o lado
            k2 = min(1.0, self._res_t / 0.5)
            lado = 1 if d["u"] >= 0 else -1
            return (cx - self.fx * 45 * k2 + self.rx * lado * 30 * k2,
                    cy_ - self.fy * 45 * k2 + self.ry * lado * 30 * k2,
                    max(0.0, ch + 14 * math.sin(math.pi * k2) - ch * k2))
        gx, cy = self.gx, self.cy
        alvo = (gx, cy + d["u"], d["h"])
        k = min(1.0, self._voo_t / self._voo_dur) if self.estado == "voo" else 1.0
        if self.estado == "resultado":
            k2 = min(1.0, self._res_t / 0.5)
            r = d["resultado"]
            if r == "golo":
                return (gx + self.fora_dir * 30 * (1 - (1 - k2) ** 2), cy + d["u"], max(0, d["h"] - 15 * k2))
            if r == "defesa":
                lado = 1 if d["u"] >= d["u_gr"] else -1
                return (gx - self.fora_dir * 70 * k2, cy + d["u"] + lado * 40 * k2,
                        max(0.0, d["h"] + 20 * math.sin(math.pi * k2) - d["h"] * k2))
            if r == "poste":
                lado = 1 if d["u"] >= 0 else -1
                return (gx - self.fora_dir * 50 * k2, cy + d["u"] + lado * 50 * k2, max(0.0, d["h"] * (1 - k2)))
            return (gx + self.fora_dir * 60 * k2, cy + d["u"] * (1 + 0.3 * k2), d["h"])
        x = bx0 + (alvo[0] - bx0) * k
        y = by0 + (alvo[1] - by0) * k
        h = bh0 + (alvo[2] - bh0) * k + 6 * math.sin(math.pi * k) * (1 - d["forca"])
        return x, y, h

    def _bola_no_ecra(self, pos):
        """(x, y, raio, y_sombra) da bola no ecrã; no início do voo mistura com a posição «vista»."""
        p = self._proj(*pos)
        chao = self._proj(pos[0], pos[1], 0)
        if not p or not chao:
            return None
        x, y, r, ys = p[0], p[1], max(2, F * RAIO_BOLA / p[2]), chao[1]
        if self.estado == "voo" and self.bola_vista:
            k = min(1.0, self._voo_t / getattr(self, "_mistura", 0.14))
            k = k * k * (3 - 2 * k)
            vx, vy, vz = self.bola_vista
            vr = F * RAIO_BOLA / vz
            x, y, r, ys = vx + (x - vx) * k, vy + (y - vy) * k, vr + (r - vr) * k, vy + (ys - vy) * k
        return x, y, r, ys

    def _desenhar_bola(self, s, pos):
        e = self._bola_no_ecra(pos)
        if e:
            self._desenhar_bola_ecra(s, *e)

    def _desenhar_bola_ecra(self, s, x, y, r, y_sombra):
        p = (x, y)
        sombra = pygame.Surface((round(r * 2.4), round(r * 0.9)), pygame.SRCALPHA)
        pygame.draw.ellipse(sombra, (20, 10, 0, 100), sombra.get_rect())
        s.blit(sombra, sombra.get_rect(center=(x, y_sombra)))
        img = _img_ui("bola_pov.png")
        if img is not None:
            lado = max(2, round(2 * r))
            chave = ("bola", lado)
            if chave not in _cache:
                _cache[chave] = pygame.transform.smoothscale(img, (lado, lado))
            s.blit(_cache[chave], _cache[chave].get_rect(center=(x, y - r)))
            return
        # Bola preta de hóquei em patins, com um reflexo de luz
        pygame.draw.circle(s, (0, 0, 0), (p[0], p[1] - r), r + max(1, r * 0.1))
        pygame.draw.circle(s, (28, 28, 32), (p[0], p[1] - r), r)
        pygame.draw.circle(s, (55, 55, 62), (p[0] - r * 0.25, p[1] - r * 1.25), r * 0.55)
        pygame.draw.circle(s, (150, 150, 160), (p[0] - r * 0.38, p[1] - r * 1.4), max(1, r * 0.18))

    def _texto_rodado(self, txt, tam, cor, ang):
        chave = (txt, tam, cor, round(ang))
        if chave not in self._cache_texto:
            f = pygame.font.SysFont("Arial Black", tam, italic=True)
            img = f.render(txt, True, cor)
            self._cache_texto[chave] = pygame.transform.rotozoom(img, round(ang), 1.0)
        return self._cache_texto[chave]

    def _desenhar_stick(self, s):
        """Stick «SUPER / AZEMAD.» (imagem): puxa atrás ao carregar e vai à frente no remate."""
        img = _img_ui("stick_pov.png", ESCALA_STICK)
        if img is None:
            return self._desenhar_stick_desenhado(s)
        # As mãos (pivô) ficam no mesmo sítio do ecrã; o stick roda à volta delas
        pivo_img = pygame.math.Vector2(PIVO_STICK[0] * ESCALA_STICK, PIVO_STICK[1] * ESCALA_STICK)
        pivo_ecra = pygame.math.Vector2(BOLA_ECRA[0] - ANCORA_STICK[0] * ESCALA_STICK,
                                        BOLA_ECRA[1] - ANCORA_STICK[1] * ESCALA_STICK) + pivo_img
        centro_img = pygame.math.Vector2(img.get_width() / 2, img.get_height() / 2)
        v = pivo_img - centro_img

        def escala(ang):
            """Para trás o stick vem para perto da câmara (maior); para a frente afasta-se (mais pequeno)."""
            if ang >= 0:
                return 1.0 + 0.14 * ang / ANG_PREPARAR
            return 1.0 - 0.12 * (-ang) / ANG_ACOMPANHAR

        def desenhar(ang, alpha=255):
            # As imagens rodadas ficam guardadas: o rasto usa os ângulos dos frames anteriores,
            # que já estão na cache (rodar uma imagem deste tamanho demora ~4,6 ms)
            chave = round(ang * 4) / 4
            if abs(chave) < 0.05:
                rod, chave = img, 0.0
            else:
                rod = self._cache_stick.get(chave)
                if rod is None:
                    rod = pygame.transform.rotozoom(img, chave, escala(chave))
                    if len(self._cache_stick) > 12:
                        self._cache_stick.pop(next(iter(self._cache_stick)))
                    self._cache_stick[chave] = rod
            centro = pivo_ecra - (v * escala(chave)).rotate(-chave)
            if alpha < 255:
                rod.set_alpha(alpha)
            s.blit(rod, rod.get_rect(center=(round(centro.x), round(centro.y))))
            if alpha < 255:
                rod.set_alpha(None)

        # Rasto de velocidade: cópias meio transparentes dos ângulos anteriores (só quando anda depressa)
        if self.estado in ("golpe", "voo") and len(self._rasto) > 1:
            depressa = abs(self._rasto[0] - self._rasto[-1]) > 4
            if depressa:
                for i, ang in enumerate(reversed(self._rasto[1:])):
                    desenhar(ang, 40 + 25 * i)
        desenhar(self._ang)

    def _desenhar_impacto(self, s):
        """Clarão e raios no sítio onde o stick bateu na bola (dura 0,15 s)."""
        t = self._impacto_t
        if not 0 <= t < 0.15:
            return
        k = t / 0.15
        x, y = BOLA_ECRA[0], BOLA_ECRA[1] - RAIO_BOLA_ECRA
        r = 30 + 70 * k
        camada = pygame.Surface((int(r * 2.6), int(r * 2.6)), pygame.SRCALPHA)
        c = camada.get_width() / 2
        a = int(230 * (1 - k))
        pygame.draw.circle(camada, (255, 250, 220, a // 2), (c, c), r * 0.6)
        pygame.draw.circle(camada, (255, 255, 255, a), (c, c), r, 4)
        for i in range(10):
            ang = i * math.pi / 5 + 0.3
            pygame.draw.line(camada, (255, 230, 150, a), (c + math.cos(ang) * r * 0.7, c + math.sin(ang) * r * 0.7),
                             (c + math.cos(ang) * r * 1.25, c + math.sin(ang) * r * 1.25), 4)
        s.blit(camada, camada.get_rect(center=(x, y)))

    def _desenhar_stick_desenhado(self, s):
        """
        Stick em primeira pessoa (modelo «SUPER» / «AZEMAD.»): o cabo vem do canto de cima à esquerda
        e a pá curva fica por baixo da bola. Ao carregar puxa para trás; no remate vai à frente.
        """
        bola = self.bola_vista if self.estado == "mirar" else self._decisao["bola_vista"]
        if not bola:
            return
        bx, by = bola[0], bola[1]
        rb = F * RAIO_BOLA / bola[2]
        if self.estado == "mirar":
            ang = -0.22 * self.forca if self.a_carregar else 0.0
        else:
            ang = 0.30 * min(1.0, (self._voo_t if self.estado == "voo" else 1.0) / 0.12)
        cabo = (bx - 900, by - 360)                  # ponta do cabo (fora do ecrã)

        def rodar(p):
            dx, dy = p[0] - cabo[0], p[1] - cabo[1]
            c, sn = math.cos(ang), math.sin(ang)
            return (cabo[0] + dx * c - dy * sn, cabo[1] + dx * sn + dy * c)

        calcanhar = rodar((bx - 70, by + rb * 0.9))
        ponta = rodar((bx + 150, by - 26))
        ctrl = rodar((bx + 70, by + rb * 1.7))
        # Pá: curva (Bézier quadrática) do calcanhar à ponta, com espessura
        curva = []
        for i in range(13):
            t = i / 12
            x = (1 - t) ** 2 * calcanhar[0] + 2 * (1 - t) * t * ctrl[0] + t * t * ponta[0]
            y = (1 - t) ** 2 * calcanhar[1] + 2 * (1 - t) * t * ctrl[1] + t * t * ponta[1]
            curva.append((x, y))
        cima, baixo = [], []
        for i, (x, y) in enumerate(curva):
            x2, y2 = curva[min(i + 1, 12)]
            x1, y1 = curva[max(i - 1, 0)]
            nx, ny = -(y2 - y1), x2 - x1
            n = math.hypot(nx, ny) or 1
            esp = 19 - 5 * i / 12
            cima.append((x + nx / n * esp, y + ny / n * esp))
            baixo.append((x - nx / n * esp, y - ny / n * esp))
        pa = cima + baixo[::-1]
        # Cabo: quadrilátero que engrossa um pouco até ao calcanhar
        dxs, dys = calcanhar[0] - cabo[0], calcanhar[1] - cabo[1]
        n = math.hypot(dxs, dys)
        px_, py_ = -dys / n, dxs / n
        cabo_poli = [(cabo[0] + px_ * 17, cabo[1] + py_ * 17), (calcanhar[0] + px_ * 20, calcanhar[1] + py_ * 20),
                     (calcanhar[0] - px_ * 20, calcanhar[1] - py_ * 20), (cabo[0] - px_ * 17, cabo[1] - py_ * 17)]
        madeira, claro, escuro = (214, 172, 118), (240, 208, 160), (24, 16, 10)
        for poli in (cabo_poli, pa):
            pygame.draw.polygon(s, madeira, poli)
        # Veio claro ao longo do cabo e da pá
        pygame.draw.line(s, claro, (cabo[0] + px_ * 8, cabo[1] + py_ * 8),
                         (calcanhar[0] + px_ * 10, calcanhar[1] + py_ * 10), 5)
        pygame.draw.lines(s, claro, False, [(x * 0.6 + cx * 0.4, y * 0.6 + cy * 0.4) for (x, y), (cx, cy) in zip(cima, curva)], 3)
        for poli in (cabo_poli, pa):
            pygame.draw.polygon(s, escuro, poli, 4)
        # Letras: «SUPER» no cabo e «AZEMAD.» na pá
        ang_cabo = -math.degrees(math.atan2(dys, dxs))
        sup = self._texto_rodado("SUPER", 30, escuro, ang_cabo)
        meio = (cabo[0] + dxs * 0.82, cabo[1] + dys * 0.82)
        s.blit(sup, sup.get_rect(center=meio))
        mx, my = curva[6]
        ax, ay = curva[8][0] - curva[4][0], curva[8][1] - curva[4][1]
        aze = self._texto_rodado("AZEMAD.", 22, escuro, -math.degrees(math.atan2(ay, ax)))
        s.blit(aze, aze.get_rect(center=(mx, my)))
        tx, ty = curva[11]
        pygame.draw.polygon(s, escuro, [(tx - 8, ty + 6), (tx + 8, ty + 2), (tx - 4, ty - 8)])

    def _desenhar_mira(self, s):
        p = self._proj(self.gx, self.cy + self.u, self.h)
        if not p:
            return
        precisao = 1.15 - getattr(self.jogador, "stat_remate", 80) / 400
        erro = erro_remate(self.forca, self.distancia, precisao)
        r = max(8, F * 2 * erro / p[2])
        pulso = 1 + 0.06 * math.sin(self.t * 8)
        bloqueio, tapado = self._linha_bloqueada(self.u, self.h)
        if bloqueio is not None:
            cor = (255, 70, 60)
        else:
            cor = (255, 230, 80) if self.a_carregar else (255, 255, 255)
        lado = int(2 * (r * pulso + 18))
        c = lado / 2
        camada = pygame.Surface((lado, lado), pygame.SRCALPHA)
        pygame.draw.circle(camada, (*cor, 50), (c, c), r * pulso)
        pygame.draw.circle(camada, (*cor, 230), (c, c), r * pulso, 2)
        for a in range(4):
            ang = a * math.pi / 2 + self.t
            pygame.draw.line(camada, (*cor, 255), (c + math.cos(ang) * (r + 4), c + math.sin(ang) * (r + 4)),
                             (c + math.cos(ang) * (r + 14), c + math.sin(ang) * (r + 14)), 3)
        pygame.draw.circle(camada, (255, 60, 60, 255), (c, c), 4)
        s.blit(camada, (p[0] - c, p[1] - c))
        if bloqueio is not None:
            texto(s, "LINHA TAPADA", 13, (255, 90, 80), (p[0], p[1] - r - 26), sombra=True)
        elif tapado:
            texto(s, "GR TAPADO", 13, (120, 230, 140), (p[0], p[1] - r - 26), sombra=True)

    def _desenhar_interface(self, s):
        # Barra de força (à direita)
        barra = pygame.Rect(WIDTH - 92, 200, 40, 340)
        pygame.draw.rect(s, (14, 16, 26), barra.inflate(10, 10), border_radius=14)
        cheio = round(barra.height * self.forca)
        for i in range(barra.height):
            k = i / barra.height
            cor = (int(50 + 190 * k), int(110 - 60 * k), int(250 - 190 * k))       # azul (baixo) -> vermelho (cima)
            if i > cheio:
                cor = tuple(int(c * 0.35) for c in cor)                             # parte ainda vazia: escurecida
            pygame.draw.line(s, cor, (barra.left + 3, barra.bottom - i), (barra.right - 4, barra.bottom - i))
        pygame.draw.rect(s, (235, 240, 250), barra, 3, border_radius=10)
        if self.forca > 0:
            yk = barra.bottom - cheio
            pygame.draw.line(s, (255, 255, 255), (barra.left - 6, yk), (barra.right + 5, yk), 3)
        texto(s, "FORÇA", 14, (230, 236, 255), (barra.centerx, barra.bottom + 22))
        pct = pygame.Rect(0, 0, 58, 24)
        pct.center = (barra.centerx, barra.top - 20)
        pygame.draw.rect(s, (14, 16, 26), pct, border_radius=8)
        texto(s, f"{round(self.forca * 100)}%", 15, (255, 255, 255), pct.center)
        # Informação em cima (em painéis escuros, para se ler por cima das faixas do pavilhão)
        dist_m = self.distancia / PX_POR_METRO
        for caixa in (pygame.Rect(14, 12, 360, 82 if self.defensores else 60), pygame.Rect(WIDTH - 334, 12, 320, 36)):
            painel_hud = pygame.Surface(caixa.size, pygame.SRCALPHA)
            pygame.draw.rect(painel_hud, (8, 12, 26, 215), painel_hud.get_rect(), border_radius=10)
            pygame.draw.rect(painel_hud, (90, 120, 180, 255), painel_hud.get_rect(), 1, border_radius=10)
            s.blit(painel_hud, caixa)
        texto(s, f"REMATE  •  {self.jogador.nome}", 20, (255, 255, 255), (30, 30), ancora="midleft", sombra=True)
        texto(s, f"Distância à baliza: {dist_m:.1f} m", 14, (200, 215, 245), (30, 56), ancora="midleft",
              negrito=False)
        texto(s, f"Guarda-redes: {self.gr.nome}", 14, (200, 215, 245), (WIDTH - 30, 30), ancora="midright",
              negrito=False)
        # Tempo para rematar (num jogo a sério os adversários estão a chegar)
        if self.limite and self.estado == "mirar":
            k = max(0.0, self.tempo_restante / self.limite)
            ret = pygame.Rect(0, 0, 54, 54)
            ret.center = (52, 136)                          # (ao centro está o marcador e à direita o punho do stick)
            pygame.draw.circle(s, (10, 14, 28), ret.center, 30)
            cor = (90, 220, 120) if k > 0.4 else (240, 80, 70)
            if k > 0:
                pygame.draw.arc(s, cor, ret, math.pi / 2, math.pi / 2 + 2 * math.pi * k, 6)
            texto(s, f"{math.ceil(self.tempo_restante)}", 18, (255, 255, 255), ret.center)
        # Velocidade: o jogador continua a patinar a 50 % enquanto prepara o remate
        if self.vel_corrida > 5:
            agora = math.hypot(*self.vel)
            barra_v = pygame.Rect(WIDTH - 330, HEIGHT - 96, 300, 20)
            texto(s, "VELOCIDADE", 13, (230, 236, 255), (barra_v.right, barra_v.top - 12), ancora="midright")
            pygame.draw.rect(s, (10, 14, 28), barra_v.inflate(6, 6), border_radius=8)
            cheio_v = round(barra_v.width * min(1.0, agora / max(1.0, self.vel_corrida)))
            for i in range(cheio_v):
                k = i / barra_v.width
                pygame.draw.line(s, (int(60 + 180 * k), int(110 - 50 * k), int(255 - 195 * k)),
                                 (barra_v.left + i, barra_v.top), (barra_v.left + i, barra_v.bottom - 1))
            pygame.draw.rect(s, (220, 230, 250), barra_v, 2, border_radius=6)
            pct = round(100 * agora / self.vel_corrida)
            texto(s, f"Corrida: {kmh(self.vel_corrida):.0f} km/h  →  a rematar: {kmh(agora):.0f} km/h ({pct}%)",
                  11, (220, 230, 250), (barra_v.right, barra_v.bottom + 12), ancora="midright", negrito=False)
        if self.defensores and self.estado == "mirar":
            n = sum(1 for d in self.defensores if (p := self._proj(d["x"], d["y"])) and p[2] < self.z_baliza - 2)
            if n:
                texto(s, f"Defesas à frente: {n}", 14, (255, 190, 120), (30, 80), ancora="midleft", negrito=False)
        if self.estado == "mirar":
            dica = ("Rato ou setas: apontar     Manter X ou o botão do rato: força (larga para rematar)"
                    "     ESC: cancelar")
            faixa = pygame.Surface((WIDTH, 34), pygame.SRCALPHA)
            faixa.fill((6, 10, 22, 190))
            s.blit(faixa, (0, HEIGHT - 34))
            texto(s, dica, 13, (220, 230, 250), (WIDTH // 2, HEIGHT - 17), negrito=False)

    def _desenhar_resultado(self, s):
        r = self._decisao["resultado"]
        txt, cor = {"golo": ("GOLO!", (255, 220, 60)), "defesa": ("DEFESA!", (120, 255, 160)),
                    "bloqueado": ("BLOQUEADO!", (255, 150, 70)),
                    "poste": ("POSTE!", (130, 200, 255)), "fora": ("FORA!", (255, 140, 120))}[r]
        t = self._res_t
        esc = (0.4 + 0.9 * t / 0.12) if t < 0.12 else 1.0 + 0.25 * math.exp(-(t - 0.12) * 10)
        img = titulo_estilizado(txt, pygame.font.SysFont("Arial Black", 100), tuple(min(255, c + 60) for c in cor),
                                cor, contorno=10)
        img = pygame.transform.rotozoom(img, -5, esc * 0.9)
        s.blit(img, img.get_rect(center=(WIDTH // 2, 190)))
        if r == "bloqueado":
            texto(s, f"{self._decisao['bloqueador'].nome} meteu-se à frente da bola", 16, (230, 236, 255),
                  (WIDTH // 2, 262), sombra=True)
        elif r != "golo":
            vel_kmh = kmh(self._decisao["velocidade"])
            extra = "  •  guarda-redes tapado" if self._decisao.get("tapado") else ""
            texto(s, f"Remate a {vel_kmh:.0f} km/h{extra}", 16, (230, 236, 255), (WIDTH // 2, 262), sombra=True)

    def _buffer(self, nome: str) -> pygame.Surface:
        """Superfícies de ecrã inteiro reaproveitadas (criar uma nova em cada frame é lento)."""
        if not hasattr(self, "_buffers"):
            self._buffers = {}
        if nome not in self._buffers:
            self._buffers[nome] = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        b = self._buffers[nome]
        b.fill((0, 0, 0, 0))
        return b

    def _preparar_cena(self):
        """Fundo, tabelas, campo e rede não mudam durante o remate: desenham-se uma vez."""
        if self._cena is None:
            self._cena = pygame.Surface((WIDTH, HEIGHT))
        self._cena.blit(self._fundo, (0, 0))
        self._desenhar_campo(self._cena)
        self._reflexos(self._cena)
        self._desenhar_tabelas(self._cena)
        self._desenhar_baliza(self._cena, frente=False)
        self._frente = self._buffer("frente")
        self._desenhar_baliza(self._frente, frente=True)

    def draw(self):
        s = self.screen
        # A cena fixa só é refeita quando a câmara anda (o jogador continua a patinar)
        if self._cena is None or (self._pos_cena and math.dist(self._pos_cena, self.pos) > 1.5):
            self._preparar_cena()
            self._pos_cena = tuple(self.pos)
        s.blit(self._cena, (0, 0))
        if self.estado == "resultado" and self._decisao["resultado"] == "golo":
            self._desenhar_ondulacao(s)
        pos_bola = None if self.estado in ("mirar", "golpe") else self._pos_bola()
        z_bola = 0.0
        bola_atras = False
        if pos_bola:
            z_bola = self._cam(pos_bola[0], pos_bola[1])[1]
            if self.estado == "voo" and self._voo_t < getattr(self, "_mistura", 0.14):
                z_bola = 0.0           # ainda a sair do stick: fica à frente de tudo
            bola_atras = (pos_bola[0] - self.gx) * self.fora_dir > 0
            if bola_atras:
                self._desenhar_bola(s, pos_bola)
        self._desenhar_gr(s)
        s.blit(self._frente, (0, 0))
        # Defesas e bola por ordem de profundidade: a bola fica tapada por quem está mais perto
        if pos_bola and not bola_atras:
            self._desenhar_defensores(s, z_bola, 1e9)
            self._desenhar_bola(s, pos_bola)
            self._desenhar_defensores(s, 0, z_bola)
        else:
            self._desenhar_defensores(s, 0, 1e9)
        if self.estado in ("mirar", "golpe"):
            # A bola parada fica no chão; o stick (por cima) desce até ela no golpe
            vx, vy, _vz = self.bola_vista
            self._desenhar_bola_ecra(s, vx, vy, RAIO_BOLA_ECRA, vy + 4)
        self._desenhar_stick(s)
        self._desenhar_impacto(s)
        if self.estado == "mirar":
            self._desenhar_mira(s)
        self._desenhar_interface(s)
        if self.estado == "resultado":
            self._desenhar_resultado(s)
