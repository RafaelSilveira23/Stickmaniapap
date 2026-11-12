# -*- coding: utf-8 -*-
"""
comando.py - jogar com um comando (Xbox, PlayStation ou outro compatível).

Em vez de mudar todos os ecrãs, o comando é "traduzido" para as teclas que o jogo já usa:
  - os botões passam a eventos de tecla (KEYDOWN / KEYUP) postos na fila do pygame;
  - o stick e as setas do comando ficam "premidos" como as setas do teclado, e o
    teclas() junta-os ao pygame.key.get_pressed().
Assim os menus, o jogo, o remate na primeira pessoa e o online funcionam sem alterações.

Botões (nomes do comando da Xbox; no da PlayStation: A = X, B = O, X = quadrado, Y = triângulo):
  Nos menus:  stick / setas = escolher,  A ou START = confirmar,  B ou BACK = voltar,
              LB / RB = mudar de separador
  No jogo:    stick / setas = mexer,  A = passe (ou pedir a bola),  B = rematar,
              X / Y / LB = trocar de jogador,  RB / RT / LT = acelerar,  START = pausa
  No remate:  stick = apontar,  B ou A (manter e largar) = força,  BACK = cancelar
"""
import pygame

try:
    from pygame._sdl2 import controller as _sdl_controller
except ImportError:                       # versões do pygame sem o módulo dos comandos
    _sdl_controller = None

LIMIAR_STICK = 0.5          # quanto é preciso inclinar o stick (0 a 1)
LIMIAR_GATILHO = 0.4
REPETIR_INICIO = 0.38       # nos menus, manter o stick para baixo: espera e depois repete
REPETIR_PASSO = 0.12

# Teclas que cada botão "carrega", conforme o ecrã
MAPA = {
    "menu": {"a": pygame.K_RETURN, "start": pygame.K_RETURN, "b": pygame.K_ESCAPE,
             "back": pygame.K_ESCAPE, "lb": pygame.K_q, "rb": pygame.K_e},
    "jogo": {"a": pygame.K_z, "b": pygame.K_x, "x": pygame.K_c, "y": pygame.K_c, "lb": pygame.K_c,
             "rb": pygame.K_LSHIFT, "rt": pygame.K_LSHIFT, "lt": pygame.K_LSHIFT,
             "start": pygame.K_ESCAPE, "back": pygame.K_ESCAPE},
    "pov": {"a": pygame.K_RETURN, "b": pygame.K_x, "back": pygame.K_ESCAPE},
}
SETAS = {"cima": pygame.K_UP, "baixo": pygame.K_DOWN, "esq": pygame.K_LEFT, "dir": pygame.K_RIGHT}

_comandos = []              # comandos ligados (Controller do SDL ou Joystick simples)
_n_joysticks = -1
_carregados = {}            # botão -> tecla que está "premida" por causa dele
_setas_ant = set()
_repetir = {}               # seta -> tempo até à próxima repetição (menus)
_ultimo_t = 0


def _ligar():
    """(Re)lê os comandos ligados. Corre quando se liga ou desliga um comando."""
    global _comandos, _n_joysticks
    if not pygame.joystick.get_init():
        pygame.joystick.init()
    if _sdl_controller is not None and not _sdl_controller.get_init():
        _sdl_controller.init()
    _n_joysticks = pygame.joystick.get_count()
    _comandos = []
    for i in range(_n_joysticks):
        try:
            if _sdl_controller is not None and _sdl_controller.is_controller(i):
                _comandos.append(("sdl", _sdl_controller.Controller(i)))
            else:
                j = pygame.joystick.Joystick(i)
                j.init()
                _comandos.append(("joy", j))
        except pygame.error:
            pass


def ligado() -> bool:
    """True se há pelo menos um comando ligado (o painel do jogo mostra os botões do comando)."""
    return bool(_comandos)


def _ler() -> tuple[set, set]:
    """Botões premidos e direções do stick/setas, juntando todos os comandos ligados."""
    botoes, setas = set(), set()
    for tipo, c in _comandos:
        try:
            if tipo == "sdl":
                for nome, b in (("a", pygame.CONTROLLER_BUTTON_A), ("b", pygame.CONTROLLER_BUTTON_B),
                                ("x", pygame.CONTROLLER_BUTTON_X), ("y", pygame.CONTROLLER_BUTTON_Y),
                                ("lb", pygame.CONTROLLER_BUTTON_LEFTSHOULDER),
                                ("rb", pygame.CONTROLLER_BUTTON_RIGHTSHOULDER),
                                ("start", pygame.CONTROLLER_BUTTON_START),
                                ("back", pygame.CONTROLLER_BUTTON_BACK),
                                ("cima", pygame.CONTROLLER_BUTTON_DPAD_UP),
                                ("baixo", pygame.CONTROLLER_BUTTON_DPAD_DOWN),
                                ("esq", pygame.CONTROLLER_BUTTON_DPAD_LEFT),
                                ("dir", pygame.CONTROLLER_BUTTON_DPAD_RIGHT)):
                    if c.get_button(b):
                        (setas if nome in SETAS else botoes).add(nome)
                ax = c.get_axis(pygame.CONTROLLER_AXIS_LEFTX) / 32767
                ay = c.get_axis(pygame.CONTROLLER_AXIS_LEFTY) / 32767
                if c.get_axis(pygame.CONTROLLER_AXIS_TRIGGERLEFT) / 32767 > LIMIAR_GATILHO:
                    botoes.add("lt")
                if c.get_axis(pygame.CONTROLLER_AXIS_TRIGGERRIGHT) / 32767 > LIMIAR_GATILHO:
                    botoes.add("rt")
            else:
                # Comando genérico: a ordem mais comum dos botões (A, B, X, Y, LB, RB, BACK, START)
                nomes = ("a", "b", "x", "y", "lb", "rb", "back", "start")
                for i, nome in enumerate(nomes[:c.get_numbuttons()]):
                    if c.get_button(i):
                        botoes.add(nome)
                ax = c.get_axis(0) if c.get_numaxes() > 0 else 0.0
                ay = c.get_axis(1) if c.get_numaxes() > 1 else 0.0
                if c.get_numhats() > 0:
                    hx, hy = c.get_hat(0)
                    if hx < 0: setas.add("esq")
                    if hx > 0: setas.add("dir")
                    if hy > 0: setas.add("cima")
                    if hy < 0: setas.add("baixo")
        except pygame.error:
            continue
        if ax < -LIMIAR_STICK: setas.add("esq")
        if ax > LIMIAR_STICK: setas.add("dir")
        if ay < -LIMIAR_STICK: setas.add("cima")
        if ay > LIMIAR_STICK: setas.add("baixo")
    return botoes, setas


def _tecla(tipo, key):
    """Põe na fila um evento de tecla igual ao do teclado (marcado com comando=True)."""
    pygame.event.post(pygame.event.Event(tipo, key=key, mod=0, unicode="", scancode=0, comando=True))


def processar(contexto: str):
    """
    Lê o comando e põe os eventos de tecla na fila. Chamar uma vez por frame, ANTES de ler os
    eventos. contexto: "menu", "jogo" (partida a decorrer) ou "pov" (remate na primeira pessoa).
    """
    global _setas_ant, _ultimo_t
    agora = pygame.time.get_ticks()
    dt = min(0.1, (agora - _ultimo_t) / 1000) if _ultimo_t else 0.0
    _ultimo_t = agora
    if pygame.joystick.get_init() is False or pygame.joystick.get_count() != _n_joysticks:
        _ligar()
    if not _comandos and not _carregados:
        _setas_ant = set()
        return

    botoes, setas = _ler()
    mapa = MAPA.get(contexto, MAPA["menu"])

    # Botões: carregar ao premir, largar ao soltar (ou se o ecrã mudou e a tecla já não é a mesma)
    for nome in list(_carregados):
        if nome not in botoes or mapa.get(nome) != _carregados[nome]:
            _tecla(pygame.KEYUP, _carregados.pop(nome))
    for nome in botoes:
        if nome not in _carregados and nome in mapa:
            _carregados[nome] = mapa[nome]
            _tecla(pygame.KEYDOWN, mapa[nome])

    # Setas: no jogo contam como teclas mantidas (teclas()); nos menus repetem ao manter
    for nome in setas - _setas_ant:
        _tecla(pygame.KEYDOWN, SETAS[nome])
        _repetir[nome] = REPETIR_INICIO
    for nome in _setas_ant - setas:
        _tecla(pygame.KEYUP, SETAS[nome])
        _repetir.pop(nome, None)
    if contexto == "menu":
        for nome in setas & _setas_ant:
            _repetir[nome] = _repetir.get(nome, REPETIR_INICIO) - dt
            if _repetir[nome] <= 0:
                _repetir[nome] = REPETIR_PASSO
                _tecla(pygame.KEYDOWN, SETAS[nome])
    _setas_ant = setas


class _Teclas:
    """Como o resultado de pygame.key.get_pressed(), mas com as teclas "premidas" pelo comando."""

    def __init__(self, base):
        self._base = base
        self._comando = set(_carregados.values()) | {SETAS[n] for n in _setas_ant}

    def __getitem__(self, key):
        return bool(self._base[key]) or key in self._comando


def teclas():
    """Usar em vez de pygame.key.get_pressed() para o comando também contar."""
    return _Teclas(pygame.key.get_pressed())
