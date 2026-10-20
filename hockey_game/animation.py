"""animation.py - carrega e gere animações de sprites.

Conceito:
  Uma Animation guarda uma lista de imagens (frames) e um temporizador.
  A cada update(dt) o tempo avança; quando chega ao limite, passa para o frame seguinte.
  O código do jogador só precisa de chamar update(dt) e ler .imagem para saber o que desenhar.
"""
import os
import pygame


class Animation:
    """Uma sequência de frames para uma animação específica (ex: correr para cima)."""

    def __init__(self, frames: list[pygame.Surface], fps: float = 8.0, loop: bool = True):
        """
        frames : lista de Surfaces já carregadas
        fps    : velocidade da animação (frames por segundo)
        loop   : True = repete; False = pára no último frame
        """
        self.frames = frames
        self.frame_time = 1.0 / fps  # quantos segundos cada frame dura
        self.loop = loop
        self._timer = 0.0
        self._index = 0
        self.finished = False  # útil para animações que não fazem loop (remate, passe)

    @property
    def imagem(self) -> pygame.Surface:
        return self.frames[self._index]

    def update(self, dt: float):
        if self.finished:
            return
        self._timer += dt
        if self._timer >= self.frame_time:
            self._timer -= self.frame_time
            self._index += 1
            if self._index >= len(self.frames):
                if self.loop:
                    self._index = 0
                else:
                    self._index = len(self.frames) - 1
                    self.finished = True

    def reset(self):
        self._index = 0
        self._timer = 0.0
        self.finished = False


# ---------------------------------------------------------------------------
# Funções utilitárias de carregamento
# ---------------------------------------------------------------------------

def _load_image(path: str, scale: tuple[int, int] | None = None) -> pygame.Surface:
    """Carrega uma imagem com transparência; faz scale se pedido."""
    img = pygame.image.load(path).convert_alpha()
    if scale:
        img = pygame.transform.scale(img, scale)
    return img


def load_animation_from_folder(
    folder: str,
    prefix: str,
    count: int | None = None,
    fps: float = 8.0,
    loop: bool = True,
    scale: tuple[int, int] | None = None,
) -> Animation:
    """
    Carrega frames com nomes do tipo: <prefix>_01.png, <prefix>_02.png, ...
    Se count=None, deteta automaticamente quantos ficheiros existem.
    Ex: load_animation_from_folder("frames/azul", "correr_cima")
        → descobre e carrega todos os correr_cima_NN.png existentes
    """
    if count is None:
        # Detetar automaticamente quantos frames existem
        count = 0
        while True:
            filename = f"{prefix}_{count + 1:02d}.png"
            if os.path.exists(os.path.join(folder, filename)):
                count += 1
            else:
                break
        if count == 0:
            raise FileNotFoundError(
                f"Nenhum frame encontrado para '{prefix}' em '{folder}'"
            )

    frames = []
    for i in range(1, count + 1):
        filename = f"{prefix}_{i:02d}.png"
        full_path = os.path.join(folder, filename)
        frames.append(_load_image(full_path, scale))
    return Animation(frames, fps=fps, loop=loop)


def load_single_frame(path: str, scale: tuple[int, int] | None = None) -> Animation:
    """Para frames únicos (ex: parado com uma única imagem)."""
    return Animation([_load_image(path, scale)], fps=1.0, loop=True)


class AnimationController:
    """
    Gere o conjunto de animações de um personagem.
    Cada estado (ex: 'correr_cima') tem uma Animation associada.
    Quando o estado muda, a nova animação começa do zero.
    """

    def __init__(self, animations: dict[str, Animation]):
        """
        animations: dicionário estado → Animation
                    ex: {'parado': anim_parado, 'correr_cima': anim_correr_cima, ...}
        """
        self._anims = animations
        self._estado_atual = next(iter(animations))  # começa no primeiro estado

    @property
    def estado(self) -> str:
        return self._estado_atual

    @estado.setter
    def estado(self, novo: str):
        if novo != self._estado_atual and novo in self._anims:
            self._anims[novo].reset()
            self._estado_atual = novo

    @property
    def imagem(self) -> pygame.Surface:
        return self._anims[self._estado_atual].imagem

    @property
    def finished(self) -> bool:
        return self._anims[self._estado_atual].finished

    def update(self, dt: float):
        self._anims[self._estado_atual].update(dt)
