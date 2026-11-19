# -*- coding: utf-8 -*-
"""goalkeeper.py - Guarda-redes com sprites próprios e IA de defesa.

Diferenças em relação ao Player de campo:
  - Move-se em frente à baliza: sai um pouco da linha para tapar o ângulo (fica na linha entre
    a bola e o meio da baliza) e encosta-se ao poste quando a bola está de lado
  - Tem inércia (acelera e trava), como os jogadores
  - Atira-se à bola (estirada) quando o remate vai para onde ele não chega a andar; durante a
    estirada chega mais longe, mas depois fica uns instantes no chão
  - Afasta a bola quando ela fica solta e devagar mesmo à frente dele
  - Não apanha a bola nem remata
"""
import os
import math
import random
import pygame
from settings import *
from animation import AnimationController, load_single_frame
from cores import cor_texto_sobre, escurecer_stick
from player import sombra_oval

# Tamanho do sprite do guarda-redes no ecrã
GR_SIZE     = (56, 56)
_TELA_GR    = (GR_SIZE[0] + 16, GR_SIZE[1] + 12)   # espaço extra para a sombra e a inclinação
GR_ACCEL    = 2400     # aceleração (px/s²)

# Distância a que o GR reage à bola e entra em modo "defender"

# Estirada (mergulho para o lado)
ESTIRADA_DUR    = 0.32     # s a voar para o lado
ESTIRADA_VEL    = 1.5      # vezes a velocidade normal
ESTIRADA_ALCANCE = 6       # px a mais de alcance durante a estirada (corpo esticado)
NO_CHAO_DUR     = 0.55     # s no chão depois da estirada (quase não se mexe)
AFASTAR_VEL     = 380      # px/s com que afasta uma bola solta à frente dele


def _pasta_gr():
    from caminhos import PASTA_SPRITES
    return os.path.join(PASTA_SPRITES, "hd", "frames", "guarda_redes")


def _pelos_pes(img: pygame.Surface) -> pygame.Surface:
    """
    Põe o boneco com os patins sempre no mesmo sítio da imagem (fundo, ao centro).
    Cada sprite do GR tem o boneco numa posição diferente; sem isto, ao trocar de pose
    (de pé -> agachado -> a defender) o corpo dava um salto.
    """
    caixa = img.get_bounding_rect()
    nova = pygame.Surface(img.get_size(), pygame.SRCALPHA)
    nova.blit(img, (img.get_width() // 2 - caixa.centerx, img.get_height() - 2 - caixa.bottom))
    return nova


def _carregar_animacoes_gr() -> dict:
    pasta = _pasta_gr()
    s = GR_SIZE
    anims = {
        "parado":        load_single_frame(os.path.join(pasta, "parado.png"), scale=s),
        "mover_cima":    load_single_frame(os.path.join(pasta, "mover_cima.png"),    scale=s),
        "mover_baixo":   load_single_frame(os.path.join(pasta, "mover_baixo.png"),   scale=s),
        # Pronto (bola perto): agachado, à espera do remate - uma só pose, sem piscar
        "pronto":        load_single_frame(os.path.join(pasta, "defender_02.png"),   scale=s),
        # Defesa (remate a vir ou bola defendida): estica-se com o stick
        "defender":      load_single_frame(os.path.join(pasta, "defender_01.png"),   scale=s),
    }
    for estado, anim in anims.items():
        # o stick do GR é quase creme (pouco saturado), por isso aceitamos menos saturação
        anim.frames = [_pelos_pes(f) for f in escurecer_stick(("gr", estado, s), anim.frames, sat_min=0.08)]
    return anims


class Goalkeeper(pygame.sprite.Sprite):
    """
    Guarda-redes.

    Parâmetros
    ----------
    equipa       : 'azul' ou 'vermelho'
    lado         : 'esq' ou 'dir' — de que lado do campo fica
    baliza_rect  : pygame.Rect da boca da baliza (geometria de deteção de golos)
    pos_x_fixo   : posição X fixa onde o GR fica (à frente da linha da baliza)
    """

    def __init__(self, equipa: str, lado: str,
                 baliza_rect: pygame.Rect, pos_x_fixo: float,
                 dificuldade: str = "normal"):
        super().__init__()

        self.equipa = equipa
        self.lado   = lado
        self.nome   = "Guarda-redes"
        self.numero = 1
        self.tem_bola = False          # GR nunca tem a bola (não apanha)

        # Animações
        self._anim = AnimationController(_carregar_animacoes_gr())
        self.image = self._anim.imagem

        # Limites verticais: GR move-se dentro da abertura da baliza
        # Margem pequena para o sprite não sair completamente da rede
        margem = GR_SIZE[1] // 4   # 14px — suficiente para parecer dentro
        self._y_min = baliza_rect.top    + margem
        self._y_max = baliza_rect.bottom - margem
        # Garantir que os limites fazem sentido mesmo com balizas pequenas
        if self._y_min >= self._y_max:
            self._y_min = baliza_rect.centery - 10
            self._y_max = baliza_rect.centery + 10

        # Posição inicial: centro da baliza, em cima da linha
        self.pos_x0 = float(pos_x_fixo)            # x da linha (o GR nunca vai para trás disto)
        self.cy0 = float(baliza_rect.centery)
        self.frente = 1 if lado == "esq" else -1   # para que lado é o campo
        self.pos_x = float(pos_x_fixo)
        self.pos_y = float(baliza_rect.centery)

        self.vel_x  = 0.0
        self.vel_y  = 0.0
        self._target_x = self.pos_x
        self._target_y = self.pos_y
        self._mergulho = None       # estirada a decorrer: {"t", "lado"}
        self._no_chao = 0.0         # tempo que ainda fica no chão
        self._lado_chao = 0         # para que lado caiu (para a animação)
        self._afastar_cd = 0.0

        self.rect = self.image.get_rect(center=(round(self.pos_x), round(self.pos_y)))

        # Animação: tempo que ainda falta a mostrar a pose de defesa, se está "pronto" (agachado)
        # e a inclinação atual do corpo (muda aos poucos, para não tremer)
        self._defender_timer = 0.0
        self._pronto = False
        self._angulo = 0.0
        # Memória das últimas posições da bola: o GR reage ao que viu há 'reacao' segundos
        self._tempo = 0.0
        self._historico = []
        self.definir_dificuldade(dificuldade)

    def definir_dificuldade(self, nivel: str):
        self.dificuldade = nivel
        # speed: velocidade máxima | reacao: atraso (s) | raio: alcance do corpo e do stick (px)
        # antecipacao: que parte da trajetória do remate o GR consegue prever (0 a 1)
        if nivel == "facil":
            self.speed, self.reacao, self.raio_defesa, self.antecipacao = 170, 0.22, 13, 0.52
            self.alerta_dist = 175
        elif nivel == "dificil":
            self.speed, self.reacao, self.raio_defesa, self.antecipacao = 260, 0.13, 15, 0.64
            self.alerta_dist = 280
        else:
            self.speed, self.reacao, self.raio_defesa, self.antecipacao = 230, 0.16, 15, 0.56
            self.alerta_dist = 220
        # saida: quanto sai da linha (px) | p_estirada: probabilidade de se atirar quando é preciso
        self.saida, self.p_estirada = {"facil": (10, 0.4), "dificil": (24, 0.8)}.get(nivel, (18, 0.6))

    # ================================================================== #
    # Update principal (chamado pelo game.py)                             #
    # ================================================================== #

    def update(self, dt: float, bola):
        self._tempo += dt
        self._ia_decidir(bola)
        self._mover(dt)
        self._afastar_bola(bola, dt)
        self._atualizar_animacao(dt, bola)

    def raio_atual(self) -> float:
        """Alcance do corpo e do stick: maior durante a estirada, menor no chão."""
        if self._mergulho is not None:
            return self.raio_defesa + ESTIRADA_ALCANCE
        if self._no_chao > 0:
            return self.raio_defesa - 4
        return self.raio_defesa

    def repor(self):
        """No centro da baliza, de pé (início de jogo, depois de um golo)."""
        self.pos_x, self.pos_y = self.pos_x0, self.cy0
        self.vel_x = self.vel_y = 0.0
        self._mergulho = None
        self._no_chao = 0.0
        self._historico.clear()

    # ------------------------------------------------------------------ #
    # IA do guarda-redes                                                   #
    # ------------------------------------------------------------------ #

    def _ia_decidir(self, bola):
        """
        Escolhe para onde o GR vai (_target_x, _target_y) e se se atira à bola.
        O GR não é perfeito: reage à bola de há 'reacao' segundos.
        """
        self._historico.append((self._tempo, bola.pos_x, bola.pos_y, bola.vel.x, bola.vel.y))
        while len(self._historico) > 1 and self._historico[1][0] <= self._tempo - self.reacao:
            self._historico.pop(0)
        _, bx, by, bvx, bvy = self._historico[0]
        if self._mergulho is not None or self._no_chao > 0:
            return                                   # no ar ou no chão não decide nada

        o = self.frente
        frente_bola = (bx - self.pos_x0) * o          # distância da bola à linha, para o campo
        dist = math.hypot(bx - self.pos_x0, by - self.cy0)

        # 1) Posição de base: na linha entre a bola e o meio da baliza, um pouco fora da linha.
        #    Sai mais com a bola à média distância e de frente (tapa o ângulo); com a bola muito
        #    perto fica na linha (para ter tempo de reagir) e com ela longe fica ao centro.
        if frente_bola <= 4:
            # Bola atrás da linha de golo: encostado ao poste do lado da bola
            tx, ty = self.pos_x0, (self._y_max if by > self.cy0 else self._y_min)
        else:
            ang = math.atan2(by - self.cy0, frente_bola)
            perto = max(0.0, min(1.0, (dist - 60) / 120))
            longe = max(0.0, min(1.0, (560 - dist) / 260))
            p = self.saida * perto * longe * max(0.0, math.cos(ang))
            tx = self.pos_x0 + o * p * math.cos(ang)
            # Para o lado: acompanha a bola (até ao poste) e, fora da linha, um pouco mais
            ty = self.cy0 + (by - self.cy0) * (0.4 if dist < self.alerta_dist else 0.25) + p * math.sin(ang)

        # 2) Remate a vir para a baliza: vai para onde a bola vai cruzar (só antecipa parte)
        para_mim = (bvx * o < -150) and bola.dono is None
        if para_mim:
            t_chegada = (self.pos_x - bx) / bvx if bvx else 9.0
            y_cruz = by + bvy * t_chegada
            ty = by + (y_cruz - by) * self.antecipacao
            tx = self.pos_x                           # num remate já não sai nem recua
            self._talvez_estirada(y_cruz, t_chegada)
            if dist < self.alerta_dist:
                self._defender_timer = max(self._defender_timer, 0.25)

        margem = abs(tx - self.pos_x0) * 0.6           # fora da linha pode ir um pouco mais ao lado
        self._target_x = tx
        self._target_y = max(self._y_min - margem, min(self._y_max + margem, ty))

    def _talvez_estirada(self, y_cruz: float, t_chegada: float):
        """Atira-se para o lado se a bola vai passar fora do alcance e não há tempo para lá chegar a andar."""
        if not (0.03 < t_chegada < 0.45):
            return
        falta = y_cruz - self.pos_y
        alcance_andar = self.raio_defesa + self.speed * max(0.0, t_chegada - 0.05) * 0.6
        if abs(falta) <= alcance_andar:
            return                                    # chega lá a andar
        if abs(falta) > self.raio_defesa + ESTIRADA_ALCANCE + self.speed * ESTIRADA_VEL * ESTIRADA_DUR:
            return                                    # nem a voar lá chega (vai para fora)
        if random.random() > self.p_estirada:
            return
        self._mergulho = {"t": 0.0, "lado": 1 if falta > 0 else -1}
        self._defender_timer = ESTIRADA_DUR + NO_CHAO_DUR

    # ------------------------------------------------------------------ #
    # Movimento com inércia                                                #
    # ------------------------------------------------------------------ #

    def _mover(self, dt: float):
        self._afastar_cd = max(0.0, self._afastar_cd - dt)
        if self._mergulho is not None:
            # Estirada: voa para o lado, muito depressa, e desce até ao chão
            m = self._mergulho
            m["t"] += dt
            self.vel_y = m["lado"] * self.speed * ESTIRADA_VEL
            self.vel_x *= 0.8
            if m["t"] >= ESTIRADA_DUR:
                self._mergulho = None
                self._no_chao = NO_CHAO_DUR
                self._lado_chao = m["lado"]
        elif self._no_chao > 0:
            # No chão: trava e quase não se mexe até se levantar
            self._no_chao = max(0.0, self._no_chao - dt)
            self.vel_x *= 0.75
            self.vel_y *= 0.75
        else:
            # Velocidade desejada proporcional à distância ao alvo (abranda ao chegar),
            # e a velocidade real muda no máximo GR_ACCEL por segundo (inércia)
            dx, dy = self._target_x - self.pos_x, self._target_y - self.pos_y
            d = math.hypot(dx, dy)
            if d > 0.5:
                v = min(self.speed, d * 7)
                vdx, vdy = dx / d * v, dy / d * v
            else:
                vdx = vdy = 0.0
            taxa = GR_ACCEL * dt
            ddx, ddy = vdx - self.vel_x, vdy - self.vel_y
            dd = math.hypot(ddx, ddy)
            if dd > taxa:
                ddx, ddy = ddx / dd * taxa, ddy / dd * taxa
            self.vel_x += ddx
            self.vel_y += ddy

        self.pos_x += self.vel_x * dt
        self.pos_y += self.vel_y * dt
        # Nunca para dentro da baliza nem demasiado longe dela
        o = self.frente
        fora = (self.pos_x - self.pos_x0) * o
        if fora < 0:
            self.pos_x, self.vel_x = self.pos_x0, 0.0
        elif fora > self.saida + 4:
            self.pos_x = self.pos_x0 + o * (self.saida + 4)
            self.vel_x = 0.0
        margem = max(0.0, fora) * 0.6
        estirada = 12 if (self._mergulho is not None or self._no_chao > 0) else 0
        lo, hi = self._y_min - margem - estirada, self._y_max + margem + estirada
        if self.pos_y < lo or self.pos_y > hi:
            self.pos_y = max(lo, min(hi, self.pos_y))
            self.vel_y = 0.0
        self.rect.center = (round(self.pos_x), round(self.pos_y))

    def _afastar_bola(self, bola, dt: float):
        """Bola solta e devagar mesmo à frente do GR: ele afasta-a para o lado (não a deixa ali)."""
        if bola.dono is not None or self._afastar_cd > 0 or self._mergulho is not None:
            return
        if bola.vel.length() > 120:
            return
        dx, dy = bola.pos_x - self.pos_x, bola.pos_y - self.pos_y
        if math.hypot(dx, dy) > self.raio_atual() + 12 or dx * self.frente < -4:
            return
        lado = 1 if dy >= 0 else -1
        v = pygame.math.Vector2(self.frente * 0.75, lado * 0.66).normalize() * AFASTAR_VEL
        bola.vel.update(v.x, v.y)
        bola._evento("passe", AFASTAR_VEL)
        self._afastar_cd = 0.8
        self._defender_timer = max(self._defender_timer, 0.3)

    # ------------------------------------------------------------------ #
    # Animação                                                             #
    # ------------------------------------------------------------------ #

    def _atualizar_animacao(self, dt: float, bola):
        self._defender_timer = max(0.0, self._defender_timer - dt)
        # Bola perto: fica agachado, pronto. Sai só um pouco mais longe (para não estar sempre a
        # trocar de pose quando a bola anda à volta do limite). Calculado aqui para funcionar
        # também no convidado do jogo online, que só desenha.
        dist = math.hypot(bola.pos_x - self.pos_x, bola.pos_y - self.pos_y)
        self._pronto = dist < (self.alerta_dist * 1.2 if self._pronto else self.alerta_dist)

        # Prioridade: defesa > pronto (agachado, mesmo a deslizar) > a deslizar > parado
        if self._mergulho is not None or self._no_chao > 0:
            self._anim.estado = "defender"
        elif self._defender_timer > 0:
            self._anim.estado = "defender"
        elif self._pronto:
            self._anim.estado = "pronto"
        elif abs(self.vel_y) > 8:
            self._anim.estado = "mover_cima" if self.vel_y < 0 else "mover_baixo"
        else:
            self._anim.estado = "parado"

        self._anim.update(dt)
        img = self._anim.imagem
        if self.lado == "dir":
            img = pygame.transform.flip(img, True, False)

        # Pequeno balanço ao deslizar (só de pé: agachado não balança)
        a_deslizar = abs(self.vel_y) > 8 and self._anim.estado in ("mover_cima", "mover_baixo")
        self._fase = (getattr(self, "_fase", 0.0) + dt * 10) if a_deslizar else 0.0
        bob = -round(abs(math.sin(self._fase)) * 2)
        # Ao defender, inclina-se para o lado da bola; a inclinação muda aos poucos
        alvo = 0.0
        if self._mergulho is not None or self._no_chao > 0:
            # Estirada: o corpo deita-se para o lado do mergulho (e fica deitado no chão)
            lado = self._mergulho["lado"] if self._mergulho is not None else self._lado_chao
            inclinacao = 62 if self._mergulho is not None else 75
            alvo = -lado * inclinacao if self.lado == "esq" else lado * inclinacao
        elif self._anim.estado == "defender":
            dy = max(-1.0, min(1.0, (bola.pos_y - self.pos_y) / 40))
            alvo = -dy * 14 if self.lado == "esq" else dy * 14
        self._angulo += (alvo - self._angulo) * min(1.0, dt * (22 if self._mergulho is not None else 14))
        if abs(self._angulo) < 0.3:
            self._angulo = 0.0

        tela = pygame.Surface(_TELA_GR, pygame.SRCALPHA)
        cx = _TELA_GR[0] // 2
        pes_y = _TELA_GR[1] // 2 + GR_SIZE[1] // 2 - 2
        sombra = sombra_oval(40, 11)
        tela.blit(sombra, (cx - sombra.get_width() // 2, pes_y - 8))
        if self._angulo:
            # Roda à volta dos patins (não do centro da imagem): os pés ficam no chão
            iw, ih = img.get_size()
            pivo = pygame.math.Vector2(0, ih / 2 - 2).rotate(-self._angulo)
            img = pygame.transform.rotozoom(img, self._angulo, 1.0)
            centro = (cx - pivo.x, pes_y + bob - pivo.y)
        else:
            centro = (cx, pes_y + bob - (img.get_height() / 2 - 2))
        tela.blit(img, img.get_rect(center=(round(centro[0]), round(centro[1]))))
        self.image = tela
        self.rect = self.image.get_rect(center=(round(self.pos_x), round(self.pos_y)))

    # ------------------------------------------------------------------ #
    # Bloquear a bola (chamado por game.py após update da bola)           #
    # ------------------------------------------------------------------ #

    def bloquear_bola(self, bola, pos_anterior=None) -> bool:
        """
        Verifica se o GR defende a bola. Se sim, a bola ressalta no corpo/stick dele.

        A bola anda ~10 px por frame, por isso não basta ver onde ela está agora: podia
        "saltar" por cima do GR entre dois frames. Por isso vemos o caminho todo que a bola
        fez neste frame (o segmento entre a posição anterior e a atual) e procuramos o ponto
        desse caminho mais perto do GR.
        Retorna True se defendeu.
        """
        if bola.dono is not None:
            return False

        raio_colisao = self.raio_atual() + 5   # corpo/stick do GR + raio da bola
        ax, ay = pos_anterior if pos_anterior is not None else (bola.pos_x, bola.pos_y)
        bx, by = bola.pos_x, bola.pos_y
        sx, sy = bx - ax, by - ay
        comp2 = sx * sx + sy * sy
        t = 1.0
        if comp2 > 1e-9:
            t = max(0.0, min(1.0, ((self.pos_x - ax) * sx + (self.pos_y - ay) * sy) / comp2))
        px, py = ax + sx * t, ay + sy * t          # ponto do caminho mais perto do GR
        dist = math.hypot(px - self.pos_x, py - self.pos_y)
        if dist >= raio_colisao:
            return False
        if dist < 0.1:
            # Bola a vir direitinha ao centro do GR: ressalta para a frente da baliza
            nx, ny = (1.0, 0.0) if self.lado == "esq" else (-1.0, 0.0)
        else:
            nx, ny = (px - self.pos_x) / dist, (py - self.pos_y) / dist
        dot = bola.vel.x * nx + bola.vel.y * ny
        if dot >= 0:
            return False                           # a bola já se está a afastar do GR
        bola.vel.x -= 2 * dot * nx
        bola.vel.y -= 2 * dot * ny
        bola.vel *= 0.8
        # A bola fica encostada ao GR, do lado de onde veio
        bola.pos_x = self.pos_x + nx * (raio_colisao + 1)
        bola.pos_y = self.pos_y + ny * (raio_colisao + 1)
        # Uma defesa manda sempre a bola para a FRENTE da baliza (antes, um toque de raspão
        # podia desviar a bola e ela continuava a entrar, o que parecia um "frango").
        frente = 1.0 if self.lado == "esq" else -1.0
        if bola.vel.x * frente < 60:
            bola.vel.x = frente * max(60.0, abs(bola.vel.x) * 0.6)
        if (bola.pos_x - self.pos_x) * frente < 6:
            bola.pos_x = self.pos_x + frente * 6
        self._defender_timer = 0.5
        return True

    # ------------------------------------------------------------------ #
    # Desenho extra (número por cima)                                      #
    # ------------------------------------------------------------------ #

    def draw_extra(self, screen: pygame.Surface, font: pygame.font.Font):
        """Etiqueta 'GR' com a cor do equipamento da equipa."""
        kit = getattr(self, "kit", None)
        fundo = kit["principal"] if kit else (20, 30, 60)
        cor_txt = cor_texto_sobre(fundo)
        t = font.render("GR", True, cor_txt)
        caixa = pygame.Rect(0, 0, t.get_width() + 8, t.get_height() + 2)
        caixa.midbottom = (self.rect.centerx, self.rect.top - 1)
        pygame.draw.rect(screen, fundo, caixa, border_radius=4)
        pygame.draw.rect(screen, (255, 255, 255), caixa, 1, border_radius=4)
        screen.blit(t, (caixa.centerx - t.get_width() // 2, caixa.centery - t.get_height() // 2))
