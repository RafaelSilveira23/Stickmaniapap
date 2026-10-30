# -*- coding: utf-8 -*-
"""player.py - jogador com inércia, colisões entre jogadores e pick-up correto."""
import os
import random
import math
import pygame
from settings import *
from animation import AnimationController, load_animation_from_names
from cores import recolorir_frames, escurecer_stick

# ---------- Constantes ----------
PLAYER_SPEED   = 200
PLAYER_SPRINT  = 260      # reduzido (era 330 — demasiado rápido)
PLAYER_SIZE    = (52, 52)
# Margem à volta do sprite para caber a sombra, a inclinação e o balanço
_MARGEM_X, _MARGEM_Y = 8, 4
TAMANHO_TELA   = (PLAYER_SIZE[0] + 2 * _MARGEM_X, PLAYER_SIZE[1] + 2 * _MARGEM_Y)
PICK_UP_DIST   = 30
ACELERACAO     = 2000
SEP_JOGADORES  = 38

# Constantes de animação
_BLEND_DURACAO  = 0.08    # segundos de transição suave entre estados
_FPS_ANIM_BASE  = 6.0     # fps de animação mínimo (parado)
_FPS_ANIM_MAX   = 12.0    # fps de animação máximo (correr a fundo)
_FPS_SPRINT_ADD = 3.0     # fps extra durante sprint
_FPS_COM_BOLA_IDLE = 1.5  # fps de animação quando tem bola e está parado

# Efeitos de movimento
_VIRAR_DURACAO  = 0.12    # segundos que o jogador demora a "dar a volta"
_INCLINACAO_MAX = 6.0     # graus de inclinação para a frente a correr

# Duração e intensidade do shake de colisão
_SHAKE_DURACAO  = 0.20    # segundos de shake após colisão
_SHAKE_AMP      = 2       # amplitude do shake em px


def _lerp_fixo(atual: float, alvo: float, max_step: float) -> float:
    """Move 'atual' em direção a 'alvo' no máximo 'max_step' por chamada."""
    diff = alvo - atual
    if abs(diff) <= max_step:
        return alvo
    return atual + max_step * (1.0 if diff > 0 else -1.0)


def _pasta_sprites(equipa: str) -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "..", "sprites_v2", "hd", "frames", equipa)


# Todos os sprites estão desenhados virados para a DIREITA.
# Para andar para a esquerda, o frame é espelhado no código (ver _compor_imagem).
#
# Os ficheiros "correr_cima/baixo/esquerda" originais são todos vistas de lado e
# com pequenas diferenças entre si (cabelo, stick), o que fazia o jogador "tremer".
# Por isso montamos UM ciclo de patinagem com os 4 frames mais consistentes
# e usamo-lo em todas as direções.
_ANIMACOES_JOGADOR = [
    # (estado, ficheiros, fps, loop)
    ("parado",   ["parado_01", "parado_02", "parado_03"],                       2.0, True),
    ("correr",   ["correr_esquerda_01", "correr_esquerda_02",
                  "correr_esquerda_03", "correr_cima_02"],                      9.0, True),
    # com_bola_04 não entra: esse frame já tem uma bola desenhada (ficavam duas bolas)
    ("com_bola", ["com_bola_01", "com_bola_02", "com_bola_03"],                 8.0, True),
    ("passe",    ["passe_01", "passe_02", "passe_03"],                         10.0, False),
    ("remate",   ["remate_01", "remate_02"],                                   10.0, False),
    ("colisao",  ["colisao_01", "colisao_02", "colisao_03"],                    8.0, False),
]


def _carregar_animacoes(equipa: str, kit: dict | None = None) -> dict:
    """
    Carrega as animações do jogador.
    Se for dado um 'kit' (cores do equipamento), usa os sprites base azuis
    e pinta-os com as cores da equipa.
    """
    pasta = _pasta_sprites("azul" if kit else equipa)
    s = PLAYER_SIZE
    anims = {}
    for estado, nomes, fps, loop in _ANIMACOES_JOGADOR:
        anim = load_animation_from_names(pasta, nomes, fps=fps, loop=loop, scale=s)
        anim.frames = escurecer_stick(("jogador", estado, s), anim.frames)
        if kit:
            anim.frames = recolorir_frames((estado, s, "v2"), anim.frames, kit)
        anims[estado] = anim
    return anims


# Sombra oval por baixo dos patins (igual para todos os jogadores)
_sombra_cache = {}


def sombra_oval(largura: int, altura: int, alpha: int = 70) -> pygame.Surface:
    chave = (largura, altura, alpha)
    if chave not in _sombra_cache:
        s = pygame.Surface((largura * 2, altura * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (20, 12, 4, alpha), s.get_rect())
        _sombra_cache[chave] = pygame.transform.smoothscale(s, (largura, altura))
    return _sombra_cache[chave]


class Player(pygame.sprite.Sprite):
    """
    Jogador de campo.
    A velocidade usa inércia: não muda instantaneamente, acelera/trava gradualmente.
    """

    def __init__(self, equipa: str, pos: tuple, numero: int = 10,
                 nome: str = "Jogador", humano: bool = False,
                 teclas: str = "wasd", kit: dict | None = None):
        """
        teclas : 'wasd' (jogador 1) ou 'ijkl' (jogador 2)
        kit    : cores do equipamento (ver cores.definir_equipamentos)
        """
        super().__init__()

        self.equipa  = equipa
        self.numero  = numero
        self.nome    = nome
        self.humano  = humano
        self.teclas  = teclas   # esquema de teclas para este jogador

        self.stat_velocidade = 80
        self.stat_remate     = 75
        self.stat_passe      = 70
        self.stat_defesa     = 65

        self.kit = kit
        self._anim = AnimationController(_carregar_animacoes(equipa, kit))

        self.pos_x = float(pos[0])
        self.pos_y = float(pos[1])

        # --- Efeitos visuais da animação ---
        self._virado_esq   = (equipa == "azul")   # para que lado o sprite está virado
        self._virar_timer  = 0.0    # "achatamento" rápido quando o jogador dá a volta
        self._inclinacao   = 0.0    # graus: inclina-se para a frente ao acelerar
        self._fase_passada = 0.0    # fase do balanço (sobe/desce a cada passada)
        self._particulas   = []     # raspas dos patins: [x, y, vx, vy, vida, vida_max]
        self._shake_offset = (0, 0)

        self.image = pygame.Surface(TAMANHO_TELA, pygame.SRCALPHA)
        self.rect  = self.image.get_rect(center=pos)
        self._compor_imagem()

        # Velocidade atual (com inércia)
        self.vel_x = 0.0
        self.vel_y = 0.0

        # Velocidade alvo (definida pelo input ou pela IA a cada frame)
        self._target_vx = 0.0
        self._target_vy = 0.0

        self.tem_bola   = False
        self.selecionado = False
        self.direcao    = "esquerda" if equipa == "azul" else "direita"
        self.vetor_direcao = pygame.math.Vector2(-1.0 if equipa == "azul" else 1.0, 0.0)

        self._estado_action = None
        self._action_timer  = 0.0

        # --- Estado de animação com transição suave ---
        self._estado_anterior = None   # último estado antes da mudança
        self._blend_timer     = 0.0    # temporizador de blend (0.08s)

        # Sprint activo (guardado para FPS dinâmico)
        self._sprint_ativo = False

        # Shake de colisão
        self._shake_timer  = 0.0       # tempo restante de shake

        # Estabilidade física e gestão de quedas/faltas
        self._imunidade_queda_timer = 0.0   # tempo restante de imunidade a nova queda
        self._desestabilizado_timer = 0.0   # tempo de ligeiro desequilíbrio após desarme limpo
        self._cooldown_desarme      = 0.0   # cooldown entre desarmes para evitar perda instantânea

    def aplicar_equipamento(self, kit: dict):
        """Troca as cores do equipamento (ex.: quando se muda de equipa a meio do jogo)."""
        estado = self._anim.estado
        self.kit = kit
        self._anim = AnimationController(_carregar_animacoes(self.equipa, kit))
        self._anim.estado = estado
        self._compor_imagem()

    # ================================================================== #
    # Update principal                                                     #
    # ================================================================== #

    def update(self, dt: float, rink_rect: pygame.Rect, bola=None, rink=None):
        if self._imunidade_queda_timer > 0:
            self._imunidade_queda_timer = max(0.0, self._imunidade_queda_timer - dt)
        if self._desestabilizado_timer > 0:
            self._desestabilizado_timer = max(0.0, self._desestabilizado_timer - dt)
        if self._cooldown_desarme > 0:
            self._cooldown_desarme = max(0.0, self._cooldown_desarme - dt)

        if self.humano:
            self._input_humano()

        self._aplicar_inercia(dt)
        self._mover(dt, rink_rect, rink)
        self._gerir_bola(bola)
        self._atualizar_animacao(dt)

    # ------------------------------------------------------------------ #
    # Input humano                                                         #
    # ------------------------------------------------------------------ #

    def _input_humano(self):
        keys = pygame.key.get_pressed()
        vx, vy = 0.0, 0.0

        if self.teclas == "wasd":
            if keys[pygame.K_LEFT]  or keys[pygame.K_a]: vx -= 1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: vx += 1
            if keys[pygame.K_UP]    or keys[pygame.K_w]: vy -= 1
            if keys[pygame.K_DOWN]  or keys[pygame.K_s]: vy += 1
            sprint = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        else:  # "ijkl" — jogador 2
            if keys[pygame.K_j]: vx -= 1
            if keys[pygame.K_l]: vx += 1
            if keys[pygame.K_i]: vy -= 1
            if keys[pygame.K_k]: vy += 1
            sprint = keys[pygame.K_RSHIFT]

        self._sprint_ativo = bool(sprint)
        spd = PLAYER_SPRINT if sprint else PLAYER_SPEED

        if vx != 0 and vy != 0:
            vx *= 0.7071
            vy *= 0.7071

        self._target_vx = vx * spd
        self._target_vy = vy * spd

        # Direção guardada para o passe/remate (suporta 8 direções incluindo diagonais)
        if vx != 0 or vy != 0:
            self.vetor_direcao = pygame.math.Vector2(vx, vy).normalize()
            # Detecção de 8 direções mais precisa usando ângulo do vetor
            ax, ay = abs(vx), abs(vy)
            if ay > ax * 1.5:
                self.direcao = "baixo" if vy > 0 else "cima"
            else:
                self.direcao = "direita" if vx > 0 else "esquerda"

    # ------------------------------------------------------------------ #
    # Inércia: suaviza a mudança de velocidade                            #
    # ------------------------------------------------------------------ #

    def _aplicar_inercia(self, dt: float):
        """Suaviza a mudança de velocidade com taxa fixa por segundo tanto para humanos como IA."""
        taxa = ACELERACAO * dt   # px/s * dt = px/frame

        if self._estado_action in ("remate", "colisao"):
            self.vel_x = _lerp_fixo(self.vel_x, 0.0,            taxa * 0.8)
            self.vel_y = _lerp_fixo(self.vel_y, 0.0,            taxa * 0.8)
        elif self._desestabilizado_timer > 0:
            # Jogador desestabilizado após toque tem velocidade temporariamente reduzida
            self.vel_x = _lerp_fixo(self.vel_x, self._target_vx * 0.65, taxa)
            self.vel_y = _lerp_fixo(self.vel_y, self._target_vy * 0.65, taxa)
        else:
            self.vel_x = _lerp_fixo(self.vel_x, self._target_vx, taxa)
            self.vel_y = _lerp_fixo(self.vel_y, self._target_vy, taxa)

    # ------------------------------------------------------------------ #
    # API para a IA definir a velocidade alvo                             #
    # ------------------------------------------------------------------ #

    def set_target(self, vx: float, vy: float):
        """Usado pelo AgentIA para definir para onde o jogador se deve mover."""
        self._target_vx = vx
        self._target_vy = vy

    # ------------------------------------------------------------------ #
    # Movimento e colisão com paredes                                      #
    # ------------------------------------------------------------------ #

    def _mover(self, dt: float, rink_rect: pygame.Rect, rink=None):
        self.pos_x += self.vel_x * dt
        self.pos_y += self.vel_y * dt

        mx = PLAYER_SIZE[0] // 2
        my = PLAYER_SIZE[1] // 2

        self.pos_x = max(rink_rect.left  + mx, min(rink_rect.right  - mx, self.pos_x))
        self.pos_y = max(rink_rect.top   + my, min(rink_rect.bottom - my, self.pos_y))

        # Não atravessar a estrutura e redes das balizas (permite patinar livremente atrás delas)
        if rink is not None:
            for obs in (rink.obstaculo_baliza_esq, rink.obstaculo_baliza_dir):
                if obs.collidepoint(self.pos_x, self.pos_y):
                    dx_left   = abs(self.pos_x - obs.left)
                    dx_right  = abs(self.pos_x - obs.right)
                    dy_top    = abs(self.pos_y - obs.top)
                    dy_bottom = abs(self.pos_y - obs.bottom)
                    min_dist = min(dx_left, dx_right, dy_top, dy_bottom)

                    if min_dist == dx_left:
                        self.pos_x = obs.left - mx
                    elif min_dist == dx_right:
                        self.pos_x = obs.right + mx
                    elif min_dist == dy_top:
                        self.pos_y = obs.top - my
                    else:
                        self.pos_y = obs.bottom + my

        self.rect.center = (round(self.pos_x), round(self.pos_y))

    # ------------------------------------------------------------------ #
    # Colisões entre jogadores (separação física)                         #
    # ------------------------------------------------------------------ #

    def empurrar_separar(self, outro: "Player", bola=None) -> dict | None:
        """
        Se dois jogadores se sobrepõem, empurra-os para fora um do outro.
        Gera desarmes limpos (sem queda) na maioria das disputas, e quedas/faltas
        apenas em choques a alta velocidade ou cargas por trás.
        Retorna dicionário com dados da falta ou None.
        """
        dx = self.pos_x - outro.pos_x
        dy = self.pos_y - outro.pos_y
        dist = (dx * dx + dy * dy) ** 0.5

        if dist >= SEP_JOGADORES or dist <= 0.1:
            return None

        # Sobreposição física → empurrar metade cada
        overlap = (SEP_JOGADORES - dist) / 2
        nx = dx / dist
        ny = dy / dist
        self.pos_x  += nx * overlap
        self.pos_y  += ny * overlap
        outro.pos_x -= nx * overlap
        outro.pos_y -= ny * overlap
        self.rect.center  = (round(self.pos_x),  round(self.pos_y))
        outro.rect.center = (round(outro.pos_x), round(outro.pos_y))

        # Se pertencerem à mesma equipa, não há desarme nem falta
        if self.equipa == outro.equipa:
            return None

        # Determinar quem é o portador e o defensor
        portador = None
        defensor = None
        dir_impacto = None

        if outro.tem_bola:
            portador = outro
            defensor = self
            dir_impacto = pygame.math.Vector2(-nx, -ny)
        elif self.tem_bola:
            portador = self
            defensor = outro
            dir_impacto = pygame.math.Vector2(nx, ny)

        if not portador:
            return None

        # Cooldown para não processar múltiplos desarmes consecutivos
        if portador._cooldown_desarme > 0:
            return None

        portador._cooldown_desarme = 0.40

        # Velocidade e agressividade da abordagem
        vel_def = math.hypot(defensor.vel_x, defensor.vel_y)
        is_sprint = getattr(defensor, "_sprint_ativo", False) or (vel_def > 210)

        # Verificar se a carga foi por trás
        carga_por_tras = False
        if hasattr(portador, "vetor_direcao") and portador.vetor_direcao.length_squared() > 0:
            v_def_vec = pygame.math.Vector2(defensor.vel_x, defensor.vel_y)
            if v_def_vec.length_squared() > 0:
                dot = portador.vetor_direcao.dot(v_def_vec.normalize())
                if dot > 0.50 and vel_def > 130:
                    carga_por_tras = True

        # Decisão de Queda vs Desarme Limpo:
        # Jogadores caem MUITO MENOS, apenas sob choque violento!
        deve_cair = False
        if portador._imunidade_queda_timer <= 0:
            if is_sprint and vel_def > 200:
                deve_cair = (random.random() < 0.28)
            elif carga_por_tras:
                deve_cair = (random.random() < 0.40)
            elif vel_def > 250:
                deve_cair = (random.random() < 0.32)

        if deve_cair:
            # Queda espetacular com falta
            portador.sofrer_queda(bola, dir_impacto)
            portador._imunidade_queda_timer = 2.5
            return {
                "tipo": "falta",
                "infrator": defensor,
                "vitima": portador,
                "queda": True,
                "pos": (portador.pos_x, portador.pos_y)
            }
        else:
            # Desarme limpo: a bola solta-se mas o jogador FICA EM PÉ!
            portador.desarme_limpo(bola, dir_impacto)

            # Pequena probabilidade de falta por obstrução em cargas rápidas mesmo sem queda
            if (is_sprint or carga_por_tras) and random.random() < 0.12:
                return {
                    "tipo": "falta",
                    "infrator": defensor,
                    "vitima": portador,
                    "queda": False,
                    "pos": (portador.pos_x, portador.pos_y)
                }

            return None

    # ------------------------------------------------------------------ #
    # Interação com a bola                                                 #
    # ------------------------------------------------------------------ #

    def _gerir_bola(self, bola):
        if bola is None:
            return

        if self.tem_bola:
            bola.seguir_jogador(self)
            return

        if bola.dono is not None:
            return

        # Jogador atordoado por colisão não apanha a bola de imediato
        if self._estado_action == "colisao":
            return

        dist = ((self.pos_x - bola.pos_x) ** 2 + (self.pos_y - bola.pos_y) ** 2) ** 0.5

        # Só apanha se a bola estiver ao alcance e respeitar o cooldown do dono anterior
        if dist < PICK_UP_DIST and bola.pode_ser_apanhada_por(self):
            bola.definir_dono(self)
            self.tem_bola = True

    # ------------------------------------------------------------------ #
    # Ações                                                                #
    # ------------------------------------------------------------------ #

    def fazer_passe(self, bola, direcao_vec: pygame.math.Vector2):
        if not self.tem_bola or bola is None:
            return
        self._comecar_acao("passe", 0.30)
        self.tem_bola = False
        from ball import PASSE_FORCA
        if direcao_vec.length_squared() == 0:
            direcao_vec = pygame.math.Vector2(1, 0)
        self._olhar_para(direcao_vec)
        bola.libertar(direcao_vec.normalize() * PASSE_FORCA, dono_anterior=self)

    def fazer_remate(self, bola, direcao_vec: pygame.math.Vector2):
        if not self.tem_bola or bola is None:
            return
        self._comecar_acao("remate", 0.30)
        self.tem_bola = False
        from ball import REMATE_FORCA
        if direcao_vec.length_squared() == 0:
            direcao_vec = pygame.math.Vector2(1, 0)
        self._olhar_para(direcao_vec)
        bola.libertar(direcao_vec.normalize() * REMATE_FORCA, dono_anterior=self)

    def fazer_remate_com_forca(self, bola, direcao_vec: pygame.math.Vector2, forca: float):
        """Remata com uma força específica (em px/s) em vez da força padrão."""
        if not self.tem_bola or bola is None:
            return
        self._comecar_acao("remate", 0.30)
        self.tem_bola = False
        if direcao_vec.length_squared() == 0:
            direcao_vec = pygame.math.Vector2(1, 0)
        self._olhar_para(direcao_vec)
        bola.libertar(direcao_vec.normalize() * forca, dono_anterior=self)

    def desarme_limpo(self, bola=None, direcao_impacto=None):
        """Desarme ou perda de posse normal: o jogador NÃO cai ao chão e continua a patinar."""
        if self.tem_bola:
            self.tem_bola = False
            if bola is not None:
                if direcao_impacto and direcao_impacto.length_squared() > 0:
                    v = direcao_impacto.normalize() * 95
                else:
                    v = pygame.math.Vector2(50, 50)
                bola.libertar(v, dono_anterior=self)

        # Apenas um pequeno tremor e abrandamento momentâneo (sem animação de queda!)
        self._shake_timer = 0.12
        self._desestabilizado_timer = 0.22

    def sofrer_queda(self, bola=None, direcao_impacto=None):
        """Queda ao chão após carga violenta ou falta sofrida."""
        if self.tem_bola:
            self.tem_bola = False
            if bola is not None:
                if direcao_impacto and direcao_impacto.length_squared() > 0:
                    v = direcao_impacto.normalize() * 130
                else:
                    v = pygame.math.Vector2(65, 65)
                bola.libertar(v, dono_anterior=self)
        self._comecar_acao("colisao", 0.65)
        self._shake_timer = _SHAKE_DURACAO

    def sofrer_colisao(self, bola=None, direcao_impacto=None):
        """Compatibilidade: chamada genérica usa desarme limpo."""
        self.desarme_limpo(bola, direcao_impacto)

    def _olhar_para(self, direcao_vec: pygame.math.Vector2):
        """Vira o sprite para o lado do passe/remate."""
        if abs(direcao_vec.x) > 0.2:
            self._virado_esq = direcao_vec.x < 0

    def _comecar_acao(self, acao: str, duracao: float):
        self._estado_action = acao
        self._action_timer  = duracao
        self._anim.estado   = acao

    # ------------------------------------------------------------------ #
    # Animação                                                             #
    # ------------------------------------------------------------------ #

    def _atualizar_animacao(self, dt: float):
        # Atualizar shake de colisão
        if self._shake_timer > 0:
            self._shake_timer -= dt
            if self._shake_timer > 0:
                self._shake_offset = (
                    random.randint(-_SHAKE_AMP, _SHAKE_AMP),
                    random.randint(-_SHAKE_AMP, _SHAKE_AMP)
                )
            else:
                self._shake_timer  = 0.0
                self._shake_offset = (0, 0)

        if self._estado_action is not None:
            self._action_timer -= dt
            if self._action_timer <= 0 or self._anim.finished:
                self._estado_action = None

        vel_atual = (self.vel_x ** 2 + self.vel_y ** 2) ** 0.5
        self._atualizar_lado(dt)
        self._atualizar_inclinacao(dt, vel_atual)
        self._atualizar_particulas(dt, vel_atual)

        if self._estado_action is None:
            em_movimento = abs(self.vel_x) > 8 or abs(self.vel_y) > 8

            if self.tem_bola:
                novo_estado = "com_bola"
            elif em_movimento:
                novo_estado = "correr"
            else:
                novo_estado = "parado"

            # Transição suave — blend_timer evita pop visual entre estados
            estado_atual = self._anim.estado
            if novo_estado != estado_atual:
                if self._blend_timer <= 0:
                    # Iniciar período de blend: mantém o frame anterior por 0.08s
                    self._estado_anterior = estado_atual
                    self._blend_timer     = _BLEND_DURACAO
                # Durante o blend, não muda ainda
            else:
                # Mesmo estado → cancelar qualquer blend pendente
                self._blend_timer = 0.0

            if self._blend_timer > 0:
                self._blend_timer -= dt
                if self._blend_timer <= 0:
                    # Blend concluído → aplicar novo estado
                    self._blend_timer = 0.0
                    self._anim.estado = novo_estado
                # Enquanto blend ativo, manter estado anterior (já está definido)
            else:
                self._anim.estado = novo_estado

            # FPS dinâmico conforme velocidade actual
            fps_anim  = _FPS_ANIM_BASE + (vel_atual / PLAYER_SPEED) * (_FPS_ANIM_MAX - _FPS_ANIM_BASE)
            if self._sprint_ativo:
                fps_anim += _FPS_SPRINT_ADD

            # Quando parado com bola → fps lento (idle com bola)
            if self.tem_bola and not em_movimento:
                fps_anim = _FPS_COM_BOLA_IDLE

            # Aplicar FPS dinâmico à animação de corrida/com_bola
            # (não tocar em passe/remate/colisao que têm fps fixo)
            estado_anim_atual = self._anim.estado
            if estado_anim_atual in self._anim._anims:
                anim_obj = self._anim._anims[estado_anim_atual]
                if hasattr(anim_obj, "frame_time") and estado_anim_atual not in ("passe", "remate", "colisao", "parado"):
                    anim_obj.frame_time = 1.0 / max(fps_anim, 0.5)

            # Balanço: o corpo sobe e desce duas vezes por ciclo de 4 frames (uma por passada)
            if em_movimento:
                self._fase_passada += dt * fps_anim * math.pi / 2
            else:
                self._fase_passada = 0.0

        self._anim.update(dt)
        self._compor_imagem()

    # ------------------------------------------------------------------ #
    # Efeitos procedimentais (feitos no código, sem sprites novos)        #
    # ------------------------------------------------------------------ #

    def _atualizar_lado(self, dt: float):
        """Decide se o sprite fica virado para a esquerda ou para a direita."""
        if self._virar_timer > 0:
            self._virar_timer = max(0.0, self._virar_timer - dt)

        # Durante a queda o jogador não se vira
        if self._estado_action == "colisao":
            return

        # Com a bola (ou a passar/rematar) olha para onde aponta o stick;
        # sem bola olha para onde está a patinar.
        if self.tem_bola or self._estado_action in ("passe", "remate"):
            dx = self.vetor_direcao.x
            limite = 0.25
        else:
            dx = self.vel_x
            limite = 25.0

        if abs(dx) > limite:
            quer_esq = dx < 0
            if quer_esq != self._virado_esq:
                self._virado_esq  = quer_esq
                self._virar_timer = _VIRAR_DURACAO
                # Ao dar a volta a alta velocidade os patins raspam no piso
                if (self.vel_x ** 2 + self.vel_y ** 2) > 120 ** 2:
                    self._emitir_raspas(6)

    def _atualizar_inclinacao(self, dt: float, vel_atual: float):
        """O jogador inclina-se para a frente ao patinar e para trás ao travar."""
        alvo = 0.0
        if self._estado_action != "colisao" and vel_atual > 8:
            # Para a frente, proporcional à velocidade horizontal
            frente = abs(self.vel_x) / PLAYER_SPEED
            alvo = _INCLINACAO_MAX * min(frente, 1.3)
            # Travagem: velocidade alvo menor (ou ao contrário) → inclina para trás
            alvo_vel = (self._target_vx ** 2 + self._target_vy ** 2) ** 0.5
            contra = self.vel_x * self._target_vx + self.vel_y * self._target_vy
            if alvo_vel < vel_atual * 0.5 or contra < 0:
                alvo = -_INCLINACAO_MAX * 0.6 * min(vel_atual / PLAYER_SPEED, 1.0)
        self._inclinacao = _lerp_fixo(self._inclinacao, alvo, 60.0 * dt)

    def _emitir_raspas(self, n: int, forca: float = 1.0):
        """Cria partículas de 'pó' a sair dos patins."""
        pes_x = self.pos_x
        pes_y = self.pos_y + PLAYER_SIZE[1] // 2 - 4
        for _ in range(n):
            ang = random.uniform(0, 2 * math.pi)
            v   = random.uniform(20, 70) * forca
            # Saem sobretudo para trás do movimento
            vx = -self.vel_x * 0.25 + math.cos(ang) * v
            vy = -self.vel_y * 0.25 + math.sin(ang) * v * 0.5 - 15
            vida = random.uniform(0.25, 0.5)
            self._particulas.append([pes_x + random.uniform(-6, 6), pes_y, vx, vy, vida, vida])

    def _atualizar_particulas(self, dt: float, vel_atual: float):
        # Travagens fortes e sprints rápidos largam raspas dos patins
        if self._estado_action != "colisao" and vel_atual > 140:
            contra = self.vel_x * self._target_vx + self.vel_y * self._target_vy
            alvo_vel = (self._target_vx ** 2 + self._target_vy ** 2) ** 0.5
            if contra < 0 or alvo_vel < vel_atual * 0.4:
                if random.random() < 0.6:
                    self._emitir_raspas(2)
            elif self._sprint_ativo and vel_atual > 220 and random.random() < 0.15:
                self._emitir_raspas(1, 0.6)

        vivas = []
        for p in self._particulas:
            p[4] -= dt
            if p[4] > 0:
                p[0] += p[2] * dt
                p[1] += p[3] * dt
                p[2] *= 0.90
                p[3] *= 0.90
                vivas.append(p)
        self._particulas = vivas[-40:]

    def _compor_imagem(self):
        """
        Monta a imagem final do jogador:
          sombra no chão + frame (espelhado se for para a esquerda)
          + inclinação + balanço da passada + tremor das colisões.
        """
        frame = self._anim.imagem
        if self._virado_esq:
            frame = pygame.transform.flip(frame, True, False)

        # Ao dar a volta, o sprite "estreita" por instantes (dá ideia de rodar o corpo)
        if self._virar_timer > 0:
            t = self._virar_timer / _VIRAR_DURACAO          # 1 → 0
            larg = max(8, int(PLAYER_SIZE[0] * (1.0 - 0.45 * math.sin(t * math.pi))))
            frame = pygame.transform.smoothscale(frame, (larg, PLAYER_SIZE[1]))

        # Inclinação (positivo = topo para a esquerda no pygame)
        angulo = self._inclinacao if self._virado_esq else -self._inclinacao
        if abs(angulo) > 0.5:
            frame = pygame.transform.rotozoom(frame, angulo, 1.0)

        bob = 0
        if self._anim.estado in ("correr", "com_bola") and self._fase_passada:
            bob = -round(abs(math.sin(self._fase_passada)) * 2)

        tela = pygame.Surface(TAMANHO_TELA, pygame.SRCALPHA)
        cx = TAMANHO_TELA[0] // 2
        pes_y = _MARGEM_Y + PLAYER_SIZE[1] - 2

        # Sombra: encolhe um pouco quando o corpo sobe
        larg_sombra = 30 + bob * 2 if self._anim.estado != "colisao" else 44
        sombra = sombra_oval(larg_sombra, 9)
        tela.blit(sombra, (cx - sombra.get_width() // 2, pes_y - 5))

        sx, sy = self._shake_offset
        # Rodamos à volta dos pés, para os patins ficarem sempre no chão:
        # o centro do sprite fica a meia altura, inclinado pelo mesmo ângulo.
        meia = PLAYER_SIZE[1] / 2
        rad = math.radians(angulo)
        centro = (cx + sx - meia * math.sin(rad),
                  pes_y + 1 + bob + sy - meia * math.cos(rad))
        tela.blit(frame, frame.get_rect(center=(round(centro[0]), round(centro[1]))))

        self.image = tela

    def draw_rastos(self, screen: pygame.Surface, camera=None):
        """Desenha as raspas dos patins (chamado ANTES de desenhar os jogadores)."""
        for x, y, _vx, _vy, vida, vida_max in self._particulas:
            t = vida / vida_max
            raio = 1 + int(2 * t)
            if camera is not None:
                # As raspas nascem nos patins (abaixo do centro); a câmara põe os patins em pos_y
                x, y = camera.projetar(x, y - PLAYER_SIZE[1] // 2 + 4)
            cor = (250, 238, 215, int(170 * t))
            s = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, cor, (raio, raio), raio)
            screen.blit(s, (int(x) - raio, int(y) - raio))

    # ------------------------------------------------------------------ #
    # Desenho extra                                                        #
    # ------------------------------------------------------------------ #

    def draw_extra(self, screen: pygame.Surface, font: pygame.font.Font, show_debug: bool = False):
        if self.selecionado:
            cx = self.rect.centerx
            ty = self.rect.top - 6
            # Indicador de seleção triangular azul com rebordo (igual ao mockup)
            # Indicador de seleção na cor do equipamento, com rebordo branco para se ver sempre
            cor = self.kit["principal"] if self.kit else (30, 140, 255)
            pts_fora  = [(cx, ty + 3), (cx - 9, ty - 12), (cx + 9, ty - 12)]
            pts_borda = [(cx, ty + 1), (cx - 7, ty - 10), (cx + 7, ty - 10)]
            pts_cor   = [(cx, ty - 1), (cx - 5, ty - 8),  (cx + 5, ty - 8)]
            pygame.draw.polygon(screen, (10, 14, 24), pts_fora)
            pygame.draw.polygon(screen, (255, 255, 255), pts_borda)
            pygame.draw.polygon(screen, cor, pts_cor)

        if show_debug:
            # Número apenas em modo debug
            for cor, off in [((0,0,0), 1), ((255,255,255), 0)]:
                t = font.render(str(self.numero), True, cor)
                screen.blit(t, (self.rect.centerx - t.get_width()//2 + off,
                                self.rect.top - t.get_height() - 2 + off))
