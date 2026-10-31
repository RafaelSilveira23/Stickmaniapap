# -*- coding: utf-8 -*-
"""ai.py - Inteligência Artificial dos jogadores controlados pelo computador.

Cada jogador da IA tem um PAPEL que define a sua posição tática:
  'avancado'  - fica mais à frente, é quem mais ataca
  'medio'     - liga ataque e defesa
  'defesa'    - fica atrás, perto da própria baliza

Em cada frame a IA escolhe um de quatro comportamentos:
  ATACAR     - tem a bola: finta, passa a um colega livre ou remata para o canto
  DEFENDER   - o adversário tem a bola: o mais perto pressiona, o segundo faz cobertura,
               os outros fecham os espaços entre a bola e a baliza
  APOIAR     - um colega tem a bola: abre espaço para receber o passe
  PERSEGUIR  - bola solta: só o jogador mais perto vai buscá-la (onde a bola VAI estar)

A IA não move o jogador diretamente: só diz a velocidade que quer (set_target).
O player.py aplica essa velocidade com inércia.
"""
import math
import random

import pygame

from settings import RINK_X, RINK_Y, RINK_W, RINK_H

# Velocidades base da IA (ajustadas pelo perfil de dificuldade)
VEL_NORMAL = 175
VEL_SPRINT = 270
VEL_DEFESA = 155

# Distância a que um jogador da IA tenta apanhar a bola
RAIO_PERSEGUIR = 180

# Distância mínima entre jogadores da mesma equipa (para não andarem colados)
SEP_MIN = 62

# Velocidade do passe (igual à do ball.py)
_VEL_PASSE = 400

# ── Perfis de Dificuldade da IA ─────────────────────────────────────────
DIFICULDADES = {
    "facil": {
        "id": "facil",
        "nome": "Fácil",
        "vel_normal": 140,
        "vel_sprint": 205,
        "vel_defesa": 120,
        "raio_perseguir": 135,
        "remate_cooldown": 2.2,
        "passe_cooldown": 1.8,
        "dist_remate": 170,
        "erro_mira": 0.22,           # ~12.5 graus de dispersão
        "agressividade": 0.30,
        "reacao": 0.35,              # segundos que a IA demora a reagir a uma mudança de posse
        "descricao": "IA mais calma, velocidade moderada e desarme suave",
        "cor": (80, 200, 120),
    },
    "normal": {
        "id": "normal",
        "nome": "Normal",
        "vel_normal": 175,
        "vel_sprint": 265,
        "vel_defesa": 150,
        "raio_perseguir": 190,
        "remate_cooldown": 1.4,
        "passe_cooldown": 1.0,
        "dist_remate": 225,
        "erro_mira": 0.08,           # ~4.5 graus de dispersão
        "agressividade": 0.60,
        "reacao": 0.20,
        "descricao": "IA equilibrada com boa ocupação de espaços e pressão moderada",
        "cor": (60, 160, 255),
    },
    "dificil": {
        "id": "dificil",
        "nome": "Difícil",
        "vel_normal": 215,
        "vel_sprint": 320,
        "vel_defesa": 185,
        "raio_perseguir": 265,
        "remate_cooldown": 0.75,
        "passe_cooldown": 0.5,
        "dist_remate": 290,
        "erro_mira": 0.02,           # remates cirúrgicos
        "agressividade": 0.90,
        "reacao": 0.08,
        "descricao": "IA veloz, pressão agressiva, passes rápidos e pontaria de elite",
        "cor": (255, 75, 75),
    }
}

# Limites onde a IA pode mandar um jogador (dentro do rinque, longe das tabelas)
_MARGEM = 30
_X_MIN, _X_MAX = RINK_X + _MARGEM, RINK_X + RINK_W - _MARGEM
_Y_MIN, _Y_MAX = RINK_Y + _MARGEM, RINK_Y + RINK_H - _MARGEM
_CENTRO_Y = RINK_Y + RINK_H / 2
_CENTRO_X = RINK_X + RINK_W / 2


def _dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def _dist_ponto_segmento(px, py, ax, ay, bx, by):
    """Distância do ponto P ao segmento AB (e 't' = onde fica a projeção, 0..1)."""
    abx, aby = bx - ax, by - ay
    comp2 = abx * abx + aby * aby
    if comp2 == 0:
        return _dist(px, py, ax, ay), 0.0
    t = max(0.0, min(1.0, ((px - ax) * abx + (py - ay) * aby) / comp2))
    return _dist(px, py, ax + abx * t, ay + aby * t), t


class AgentIA:
    """
    Controla um único jogador da IA.

    Parâmetros
    ----------
    jogador           : o Player que esta IA controla
    papel             : 'avancado', 'medio' ou 'defesa'
    equipa            : 'azul' ou 'vermelho'
    pos_base          : (x, y) posição tática de referência no campo
    baliza_propria    : Rect da baliza que esta equipa defende
    baliza_adversaria : Rect da baliza que esta equipa ataca
    gr_adversario     : guarda-redes adversário (para rematar para o lado contrário)
    """

    def __init__(self, jogador, papel: str, equipa: str,
                 pos_base: tuple,
                 baliza_propria: pygame.Rect,
                 baliza_adversaria: pygame.Rect,
                 dificuldade: str = "normal",
                 gr_adversario=None):
        self.jogador = jogador
        self.papel = papel
        self.equipa = equipa
        self.pos_base = pos_base
        self.baliza_propria = baliza_propria
        self.baliza_adversaria = baliza_adversaria
        self.gr_adversario = gr_adversario

        self.dificuldade = dificuldade
        self.cfg = DIFICULDADES.get(dificuldade, DIFICULDADES["normal"])

        # Para que lado ataca (+1 = para a direita, -1 = para a esquerda)
        self.sentido = 1 if baliza_adversaria.centerx > _CENTRO_X else -1
        # Linhas de golo (a boca de cada baliza)
        self.linha_adv = baliza_adversaria.left if self.sentido > 0 else baliza_adversaria.right
        self.linha_prop = baliza_propria.right if self.sentido > 0 else baliza_propria.left
        self.baliza_y = baliza_adversaria.centery
        self.meia_boca = baliza_adversaria.height / 2

        # Pequena variação para cada jogador não fazer exatamente o mesmo
        self._offset_y = random.uniform(-18, 18)

        # Tempos de espera
        self._remate_cooldown = 0.0
        self._passe_cooldown = 0.0
        self._tempo_com_bola = 0.0
        self._reacao = 0.0            # atraso antes de reagir a uma troca de posse
        self._ultimo_estado = None
        self._lado_finta = random.choice((-1, 1))
        self._a_perseguir = False

    def definir_dificuldade(self, nivel: str):
        """Atualiza a dificuldade e recalibra parâmetros táticos da IA."""
        if nivel in DIFICULDADES:
            self.dificuldade = nivel
            self.cfg = DIFICULDADES[nivel]

    # ------------------------------------------------------------------ #
    # Update principal — chamado cada frame                                #
    # ------------------------------------------------------------------ #

    def update(self, dt: float, bola, colegas: list, adversarios: list):
        """
        Decide o que fazer e define a velocidade alvo do jogador.
        colegas    : jogadores da mesma equipa (sem este)
        adversarios: jogadores da equipa adversária
        """
        j = self.jogador
        self._remate_cooldown = max(0.0, self._remate_cooldown - dt)
        self._passe_cooldown = max(0.0, self._passe_cooldown - dt)

        # Jogador no chão (queda) não decide nada
        if getattr(j, "_estado_action", None) == "colisao":
            j.set_target(0.0, 0.0)
            return

        if j.tem_bola:
            estado = "atacar"
        elif any(a.tem_bola for a in adversarios):
            estado = "defender"
        elif any(c.tem_bola for c in colegas):
            estado = "apoiar"
        else:
            estado = "perseguir"

        # Tempo de reação: quando a posse muda, a IA demora um pouco a reagir
        if estado != self._ultimo_estado:
            if self._ultimo_estado is not None and estado in ("defender", "apoiar"):
                self._reacao = self.cfg.get("reacao", 0.2) * random.uniform(0.6, 1.2)
            self._ultimo_estado = estado
            if estado != "perseguir":
                self._a_perseguir = False
        if self._reacao > 0:
            self._reacao -= dt
            return   # continua com a velocidade que tinha

        self._tempo_com_bola = self._tempo_com_bola + dt if estado == "atacar" else 0.0

        if estado == "atacar":
            self._estado_atacar(dt, bola, colegas, adversarios)
        elif estado == "defender":
            self._estado_defender(dt, bola, colegas, adversarios)
        elif estado == "apoiar":
            self._estado_apoiar(dt, bola, colegas, adversarios)
        else:
            self._estado_perseguir(dt, bola, colegas)

    # ------------------------------------------------------------------ #
    # ATACAR — tem a bola                                                  #
    # ------------------------------------------------------------------ #

    def _estado_atacar(self, dt, bola, colegas, adversarios):
        j = self.jogador
        frente = (self.linha_adv - j.pos_x) * self.sentido   # distância à linha de golo (>0 = à frente)
        dy = j.pos_y - self.baliza_y

        # 1) Atrás da linha de golo: dar a volta à baliza pelo lado mais perto
        if frente < 25:
            lado = 1 if dy >= 0 else -1
            self._mover_para(self.linha_adv - self.sentido * 90, self.baliza_y + lado * 95,
                             self.cfg.get("vel_normal", VEL_NORMAL), colegas, adversarios, com_bola=True)
            return

        pressao = self._adversario_mais_perto(adversarios)
        sob_pressao = pressao is not None and pressao[1] < 58

        # 2) Rematar: perto, com ângulo e linha de remate livre
        angulo_ok = abs(dy) < frente * 1.1 + 15
        if (frente < self.cfg.get("dist_remate", 225) and angulo_ok and self._remate_cooldown <= 0
                and self._tempo_com_bola > 0.3):
            alvo_y = self._alvo_remate()
            if self._linha_livre(j.pos_x, j.pos_y, self.linha_adv, alvo_y, adversarios, 18):
                v = pygame.math.Vector2(self.linha_adv - j.pos_x, alvo_y - j.pos_y)
                if v.length_squared() > 0:
                    v.normalize_ip()
                    erro = self.cfg.get("erro_mira", 0.08)
                    v = v.rotate_rad(random.uniform(-erro, erro))
                    j.fazer_remate(bola, v)
                    self._remate_cooldown = self.cfg.get("remate_cooldown", 1.4)
                    return

        # 3) Passar: quando está pressionado, ou quando há um colega claramente melhor colocado
        if self._passe_cooldown <= 0 and colegas and self._tempo_com_bola > 0.25:
            alvo = self._melhor_colega_passe(colegas, adversarios)
            if alvo is not None:
                alvo_jog, ganho = alvo
                quer_passar = sob_pressao or (ganho > 170 and random.random() < 0.6 * dt) \
                    or self._tempo_com_bola > 4.5
                if quer_passar:
                    self._passar(bola, alvo_jog)
                    return

        # 4) Conduzir a bola para a zona de remate, fintando quem estiver à frente
        alvo_x = self.linha_adv - self.sentido * 120
        alvo_y = self.baliza_y + max(-70, min(70, dy * 0.6 + self._offset_y))
        if sob_pressao:
            # Finta: sai para o lado contrário ao adversário
            adv = pressao[0]
            lado = 1 if j.pos_y >= adv.pos_y else -1
            if abs(j.pos_y - adv.pos_y) < 6:
                lado = self._lado_finta
            alvo_y = j.pos_y + lado * 80
            alvo_x = j.pos_x + self.sentido * 70
        self._mover_para(alvo_x, alvo_y, self.cfg.get("vel_sprint", VEL_SPRINT) * 0.9,
                         colegas, adversarios, com_bola=True)

    def _alvo_remate(self) -> float:
        """Escolhe o canto da baliza mais longe do guarda-redes."""
        canto = self.meia_boca - 7
        gr = self.gr_adversario
        if gr is not None:
            lado = -1 if gr.pos_y > self.baliza_y else 1
            if abs(gr.pos_y - self.baliza_y) < 3:
                lado = random.choice((-1, 1))
        else:
            lado = random.choice((-1, 1))
        return self.baliza_y + lado * canto

    def _passar(self, bola, alvo):
        j = self.jogador
        # Passe para onde o colega VAI estar (antecipação)
        dist = _dist(j.pos_x, j.pos_y, alvo.pos_x, alvo.pos_y)
        t = dist / _VEL_PASSE
        tx = alvo.pos_x + alvo.vel_x * t
        ty = alvo.pos_y + alvo.vel_y * t
        v = pygame.math.Vector2(tx - j.pos_x, ty - j.pos_y)
        if v.length_squared() == 0:
            return
        v.normalize_ip()
        erro = self.cfg.get("erro_mira", 0.08) * 0.5
        v = v.rotate_rad(random.uniform(-erro, erro))
        j.fazer_passe(bola, v)
        if hasattr(bola, "marcar_recetor"):
            bola.marcar_recetor(alvo)
        self._passe_cooldown = self.cfg.get("passe_cooldown", 1.0)

    # ------------------------------------------------------------------ #
    # DEFENDER — o adversário tem a bola                                   #
    # ------------------------------------------------------------------ #

    def _estado_defender(self, dt, bola, colegas, adversarios):
        j = self.jogador
        portador = next((a for a in adversarios if a.tem_bola), None)
        if portador is None:
            return
        px, py = portador.pos_x, portador.pos_y

        # Posição de cada um na fila para pressionar (0 = o mais perto do portador)
        ordem = self._ordem(px, py, colegas)
        # Ponto entre o portador e a nossa baliza
        gx, gy = self.linha_prop, self.baliza_y
        d_baliza = max(1.0, _dist(px, py, gx, gy))
        ux, uy = (gx - px) / d_baliza, (gy - py) / d_baliza

        if ordem == 0:
            # Pressão: vai ao portador pelo lado da baliza (assim tapa o caminho e disputa a bola)
            self._mover_para(px + ux * 14, py + uy * 14, self.cfg.get("vel_sprint", VEL_SPRINT),
                             colegas, None, chegar=False)
        elif ordem == 1:
            # Cobertura: fica entre o portador e a baliza, a ~110 px do portador
            d = min(110, d_baliza * 0.55)
            self._mover_para(px + ux * d, py + uy * d, self.cfg.get("vel_normal", VEL_NORMAL),
                             colegas, None)
        else:
            tx, ty = self._posicao_tatica(bola.pos_x, bola.pos_y, atacar=False)
            self._mover_para(tx, ty, self.cfg.get("vel_defesa", VEL_DEFESA), colegas, None)

    # ------------------------------------------------------------------ #
    # APOIAR — um colega tem a bola                                        #
    # ------------------------------------------------------------------ #

    def _estado_apoiar(self, dt, bola, colegas, adversarios):
        tx, ty = self._posicao_tatica(bola.pos_x, bola.pos_y, atacar=True)
        # Se um adversário estiver em cima do sítio, procura espaço ao lado
        for a in adversarios:
            if _dist(a.pos_x, a.pos_y, tx, ty) < 45:
                ty += 55 if ty < a.pos_y else -55
                break
        self._mover_para(tx, ty, self.cfg.get("vel_normal", VEL_NORMAL), colegas, None)

    # ------------------------------------------------------------------ #
    # PERSEGUIR — bola solta                                               #
    # ------------------------------------------------------------------ #

    def _estado_perseguir(self, dt, bola, colegas):
        j = self.jogador
        recetor = getattr(bola, "recetor", None)
        if recetor is j:
            vai = True                       # o passe é para mim: vou ao encontro da bola
        elif recetor is not None and recetor in colegas:
            vai = False                      # o passe é para um colega: abro espaço
        else:
            # Quem já ia à bola só desiste se outro colega estiver claramente mais perto
            folga = 25 if self._a_perseguir else 0
            vai = self._ordem(bola.pos_x, bola.pos_y, colegas, folga) == 0
        self._a_perseguir = vai
        if vai:
            # Vai ao ponto onde a bola VAI estar quando lá chegar
            vel = self.cfg.get("vel_sprint", VEL_SPRINT)
            t = _dist(j.pos_x, j.pos_y, bola.pos_x, bola.pos_y) / vel
            t = min(t, 0.8)
            tx = bola.pos_x + bola.vel.x * t
            ty = bola.pos_y + bola.vel.y * t
            self._mover_para(tx, ty, vel, colegas, None, chegar=False)
        else:
            tx, ty = self._posicao_tatica(bola.pos_x, bola.pos_y,
                                          atacar=True if recetor is not None else None)
            self._mover_para(tx, ty, self.cfg.get("vel_normal", VEL_NORMAL), colegas, None)

    # ------------------------------------------------------------------ #
    # Auxiliares                                                           #
    # ------------------------------------------------------------------ #

    def _ordem(self, x, y, colegas, folga: float = 0.0) -> int:
        """Quantos colegas estão mais perto de (x, y) do que este jogador (empates: pelo número).
        'folga' dá vantagem a este jogador (para não trocar de ideias a toda a hora)."""
        j = self.jogador
        d = _dist(j.pos_x, j.pos_y, x, y) - folga
        n = 0
        for c in colegas:
            if getattr(c, "_estado_action", None) == "colisao":
                continue        # quem está no chão não conta
            dc = _dist(c.pos_x, c.pos_y, x, y)
            if dc < d or (dc == d and c.numero < j.numero):
                n += 1
        return n

    def _posicao_tatica(self, bx, by, atacar):
        """
        Posição do jogador na formação, que acompanha a bola.
        atacar=True  -> a equipa tem a bola: sobe no campo e abre espaço
        atacar=False -> a equipa defende: recua e fecha o meio
        atacar=None  -> bola solta: posição intermédia
        """
        base_x, base_y = self.pos_base
        s = self.sentido
        # A formação desloca-se com a bola (35 % do caminho)
        x = base_x + (bx - _CENTRO_X) * 0.35
        y = base_y + (by - _CENTRO_Y) * 0.30
        if atacar:
            avanco = {"avancado": 230, "medio": 150, "defesa": 70}.get(self.papel, 100)
            x += s * avanco
            # Os avançados abrem para as alas para receber
            if self.papel == "avancado":
                y = base_y + (base_y - _CENTRO_Y) * 0.6
        elif atacar is False:
            recuo = {"avancado": 60, "medio": 90, "defesa": 50}.get(self.papel, 60)
            x -= s * recuo
            # Na defesa, aproxima-se do meio (fecha o caminho para a baliza)
            y = y * 0.75 + self.baliza_y * 0.25
        # Nunca para lá da linha de golo adversária nem para trás da nossa
        lim_atq = self.linha_adv - s * 70
        lim_def = self.linha_prop + s * 45
        if s > 0:
            x = max(lim_def, min(lim_atq, x))
        else:
            x = min(lim_def, max(lim_atq, x))
        return x, y + self._offset_y * 0.5

    def _mover_para(self, tx: float, ty: float, velocidade: float,
                    colegas=None, adversarios=None, com_bola=False, chegar=True):
        """
        Define a velocidade alvo para ir até (tx, ty):
          - abranda ao chegar (não passa do sítio e não fica a tremer)
          - afasta-se dos colegas (não andam colados)
          - com a bola, desvia-se dos adversários que estão à frente
        """
        j = self.jogador
        tx = max(_X_MIN, min(_X_MAX, tx))
        ty = max(_Y_MIN, min(_Y_MAX, ty))
        if chegar:
            # Posições táticas nunca em cima do guarda-redes (ir à bola ou pressionar pode)
            tx, ty = self._fora_da_area_gr(tx, ty)
        dx, dy = tx - j.pos_x, ty - j.pos_y
        dist = math.hypot(dx, dy)

        dir_x, dir_y = (dx / dist, dy / dist) if dist > 0.5 else (0.0, 0.0)

        # Separação dos colegas
        sep_x = sep_y = 0.0
        for c in colegas or ():
            ddx, ddy = j.pos_x - c.pos_x, j.pos_y - c.pos_y
            d = math.hypot(ddx, ddy)
            if 0.1 < d < SEP_MIN:
                f = (SEP_MIN - d) / SEP_MIN
                sep_x += ddx / d * f
                sep_y += ddy / d * f

        # Desvio dos adversários que estão à frente (só quando conduz a bola)
        desv_x = desv_y = 0.0
        if com_bola and adversarios and dist > 1:
            for a in adversarios:
                ax, ay = a.pos_x - j.pos_x, a.pos_y - j.pos_y
                d = math.hypot(ax, ay)
                if d < 1 or d > 90:
                    continue
                frente = (ax * dir_x + ay * dir_y) / d
                if frente < 0.2:
                    continue
                # empurra para o lado (perpendicular à direção), para longe do adversário
                lado = 1 if (ax * -dir_y + ay * dir_x) < 0 else -1
                f = (90 - d) / 90 * frente
                desv_x += -dir_y * lado * f * 1.4
                desv_y += dir_x * lado * f * 1.4

        vx = dir_x + sep_x * 1.2 + desv_x
        vy = dir_y + sep_y * 1.2 + desv_y
        n = math.hypot(vx, vy)
        if n < 0.05:
            j.set_target(0.0, 0.0)
            return
        # Abrandar ao chegar ao destino (evita passar e voltar para trás)
        fator = 1.0
        if chegar and dist < 45:
            fator = max(0.0, (dist - 6) / 39)
        vel = velocidade * fator
        if vel < 12 and math.hypot(sep_x, sep_y) < 0.1:
            j.set_target(0.0, 0.0)
            return
        vel = max(vel, 40.0 if math.hypot(sep_x, sep_y) >= 0.1 else vel)
        vx, vy = vx / n * vel, vy / n * vel
        j.set_target(vx, vy)

        # Direção (para o stick, o passe e a animação)
        if vel > 20:
            olhar = pygame.math.Vector2(vx, vy)
            j.vetor_direcao = olhar.normalize()
            if abs(vx) > abs(vy):
                j.direcao = "direita" if vx > 0 else "esquerda"
            else:
                j.direcao = "baixo" if vy > 0 else "cima"

    def _fora_da_area_gr(self, tx, ty):
        """
        A zona logo à frente de cada baliza é do guarda-redes: a IA não escolhe ficar lá
        (antes o defensor que fazia cobertura ia parar em cima do próprio guarda-redes).
        """
        for linha, s in ((self.linha_prop, self.sentido), (self.linha_adv, -self.sentido)):
            frente = (tx - linha) * s           # distância à linha de golo, para o lado do campo
            if abs(ty - self.baliza_y) < 55 and -40 < frente < 50:
                tx = linha + s * 50
        return tx, ty

    def _adversario_mais_perto(self, adversarios):
        """O adversário mais perto que esteja à frente ou ao lado (não conta quem vem atrás)."""
        j = self.jogador
        melhor = None
        for a in adversarios:
            if getattr(a, "_estado_action", None) == "colisao":
                continue
            d = _dist(j.pos_x, j.pos_y, a.pos_x, a.pos_y)
            if (a.pos_x - j.pos_x) * self.sentido < -25:
                continue
            if melhor is None or d < melhor[1]:
                melhor = (a, d)
        return melhor

    def _linha_livre(self, ax, ay, bx, by, adversarios, folga) -> bool:
        """True se nenhum adversário estiver perto da linha A→B."""
        for a in adversarios:
            d, t = _dist_ponto_segmento(a.pos_x, a.pos_y, ax, ay, bx, by)
            if 0.05 < t < 0.97 and d < folga:
                return False
        return True

    def _melhor_colega_passe(self, colegas, adversarios):
        """
        Escolhe o colega mais bem colocado para receber: livre de marcação,
        com linha de passe limpa e o mais perto possível da baliza adversária.
        Devolve (colega, ganho) em que ganho = quanto o passe aproxima a bola da baliza.
        """
        j = self.jogador
        gx, gy = self.linha_adv, self.baliza_y
        d_eu = _dist(j.pos_x, j.pos_y, gx, gy)
        melhor, melhor_pont = None, -1e9
        for c in colegas:
            if getattr(c, "_estado_action", None) == "colisao":
                continue
            d = _dist(j.pos_x, j.pos_y, c.pos_x, c.pos_y)
            if d < 70 or d > 430:
                continue
            if (self.linha_adv - c.pos_x) * self.sentido < 15:
                continue        # colega atrás da baliza adversária: mau sítio
            # Folga maior em passes longos (o adversário tem mais tempo para cortar)
            if not self._linha_livre(j.pos_x, j.pos_y, c.pos_x, c.pos_y, adversarios, 34 + d * 0.1):
                continue
            marcacao = min((_dist(c.pos_x, c.pos_y, a.pos_x, a.pos_y) for a in adversarios), default=999)
            if marcacao < 40:
                continue
            ganho = d_eu - _dist(c.pos_x, c.pos_y, gx, gy)
            pont = ganho + min(marcacao, 150) * 0.6 - d * 0.15
            if pont > melhor_pont:
                melhor, melhor_pont = (c, ganho), pont
        return melhor

    # Compatibilidade com o código antigo
    def _adversario_no_caminho(self, adversarios: list) -> bool:
        j = self.jogador
        return not self._linha_livre(j.pos_x, j.pos_y, self.linha_adv, self.baliza_y, adversarios, 50)
