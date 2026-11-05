# -*- coding: utf-8 -*-
"""game.py - game loop com IA real, posicionamento tático, mini-mapa e cartão de jogador."""
import json
import math
import os
import pygame
import fontes
from settings import *
from rink import Rink
from player import Player
from ball import Ball
from ai import AgentIA
from goalkeeper import Goalkeeper
from ui import HUDController
from team import EQUIPAS_LISTA, obter_info_equipa, obter_plantel
from menu import MenuPrincipal, EcraControlos, TeamSelectMenu, MenuPausa, EcraFimJogo
from cores import definir_equipamentos, misturar, cor_texto_sobre
from componentes import COR_DESTAQUE
from graficos import sombra_suave
from sons import som
from efeitos import Efeitos, contornar
from remate_pov import RematePOV, MEIA_BOCA
import random
from carreira import Campeonato, CAMINHO_BD, PASTA_SAVES, FORCA_EQUIPAS
from carreira_menu import EcraCarreiraEscolha, EcraCampeonato
from carreira_jogador import CarreiraJogador, CAMINHO_BD_JOGADOR, atributos as atributos_jogador, calcular_nota
from carreira_jogador_menu import EcraCriarJogador, EcraCarreiraJogador

DURACAO_PARTE = 60 * 5   # 5 minutos por parte
DIFICULDADE_EQUIPA_HUMANA = "normal"   # nível dos colegas e do GR do jogador humano
RAIO_GR_CORPO = 30                       # distância mínima entre um jogador e um guarda-redes

# Formação em losango com 4 jogadores de campo (como no hóquei em patins real):
# (distância à linha do meio, desvio vertical, atributos (velocidade, remate, passe, defesa)).
# A ordem é a mesma de team.POSICOES_FORMACAO: avançado, médio, médio, defesa.
FORMACAO = [
    (70,    0, (87, 86, 75, 57)),     # avançado (o jogador humano começa aqui)
    (210, -95, (81, 79, 86, 72)),     # médio
    (210,  95, (80, 77, 88, 74)),     # médio
    (350,   0, (75, 65, 76, 88)),     # defesa
]
CAMINHO_DEFINICOES = os.path.join(PASTA_SAVES, "definicoes.json")


class Game:
    def __init__(self):
        pygame.init()
        definicoes = self._ler_definicoes()
        self.ecra_inteiro = bool(definicoes.get("ecra_inteiro", False))
        self.estilo_arcade = bool(definicoes.get("estilo_arcade", True))
        self.screen = self._criar_janela()

        # Som (se não houver placa de som, o jogo continua sem som)
        som.iniciar()
        som.definir_volumes(self._ler_volume(definicoes, "vol_efeitos", 0.8),
                            self._ler_volume(definicoes, "vol_publico", 0.5))
        self._nivel_publico = None
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()

        self.font_num = fontes.SysFont("Arial", 12, bold=True)
        self.font_big = fontes.SysFont("Arial", 44, bold=True)
        self.font_med = fontes.SysFont("Arial", 26, bold=True)

        self.equipa_casa_id = "fc_porto"
        self.equipa_fora_id = "riba_dave"
        self.dificuldade    = "normal"

        self.rink = Rink(equipa_casa=self.equipa_casa_id)
        self.hud  = HUDController()

        # ── Criar jogadores e agentes IA ─────────────────────────────────
        self._criar_equipas()

        # ── Bola ─────────────────────────────────────────────────────────
        cx = RINK_X + RINK_W // 2
        cy = RINK_Y + RINK_H // 2
        self.bola = Ball((cx, cy))
        self.sprites_bola = pygame.sprite.GroupSingle(self.bola)

        # Jogador humano começa com a bola
        self.bola.definir_dono(self.jogador_humano)
        self.jogador_humano.tem_bola = True
        self.bola.seguir_jogador(self.jogador_humano)

        # ── Estado do jogo e Menu de Seleção ─────────────────────────────
        # Estados: "menu_principal", "controlos", "menu_selecao", "carreira_escolha",
        #          "carreira" (ecrã do campeonato) ou "jogo"
        self.estado         = "menu_principal"
        self.menu_principal = MenuPrincipal(self.screen, self.equipa_casa_id, self.equipa_fora_id,
                                            arena=self.rink._surf)
        self.menu           = TeamSelectMenu(self.screen, self.equipa_casa_id, self.equipa_fora_id)
        self.ecra_controlos = EcraControlos(self.screen)
        self.ecra_controlos.vol_efeitos = som.vol_efeitos
        self.ecra_controlos.vol_publico = som.vol_publico
        self.menu_pausa     = MenuPausa(self.screen)
        self.ecra_fim       = EcraFimJogo(self.screen)
        self._origem_controlos = "menu_principal"   # para onde volta o ecrã de controlos
        self.pausado        = False

        # ── Modo carreira ────────────────────────────────────────────────
        self.caminho_carreira = CAMINHO_BD
        self.carreira        = None    # Campeonato (aberto só quando se entra no modo carreira)
        self.modo_carreira   = False   # True durante um jogo do campeonato
        self.ecra_carreira   = None
        self.ecra_campeonato = None
        self._jornada_carreira = None

        # ── Carreira de jogador: nos jogos só se controla o próprio jogador ──
        self.caminho_carreira_jogador = CAMINHO_BD_JOGADOR
        self.carreira_jog    = None      # CarreiraJogador (aberta só quando é precisa)
        self.modo_jogador    = False     # True durante um jogo da carreira de jogador
        self.ecra_cj         = None
        self.ecra_cj_criar   = None
        self._cj_jogador     = None      # o Player que é o jogador da carreira
        self.stats_jogador   = {}
        self._cj_dono_ant    = None
        self._cj_assist      = None      # (colega que recebeu o meu passe, instante)
        self._cj_t           = 0.0
        self._cj_pedido_cd   = 0.0

        self.golos_azul     = 0
        self.golos_vermelho = 0
        self.marcadores     = []
        self.efeitos        = Efeitos()      # estilo arcade (liga/desliga nas Definições)
        self.efeitos.ativo  = self.estilo_arcade
        self._reposicao_pendente = None      # depois de um golo, a festa dura um pouco antes de repor
        self.remate_pov     = None           # ecrã do remate na primeira pessoa (quando está aberto)
        self.modo_teste     = False          # MODO TESTE: só o jogador contra o guarda-redes
        self.teste          = {"remates": 0, "golos": 0, "defesas": 0, "fora": 0}
        self._teste_espera  = 0.0
        self._teste_livre   = 0.0
        self._dono_anterior = None
        self.parte          = 1
        self.tempo_restante = float(DURACAO_PARTE)
        self.jogo_ativo     = False
        self.fim_jogo       = False
        self._msg_texto     = ""
        self._msg_timer     = 0.0

        # ── Sistema de Faltas e Disciplina ─────────────────────────────
        self.faltas_azul     = 0
        self.faltas_vermelho = 0
        self._falta_ativa    = False
        self._falta_timer    = 0.0
        self._falta_cooldown = 0.0
        self._msg_falta      = ""
        self._msg_falta_sub  = ""
        self._falta_tipo     = "livre"     # "livre", "livre_direto", "penalti"

        # ── Dificuldade da IA ──────────────────────────────────────────
        self.dificuldade     = "normal"    # "facil", "normal", "dificil"

        # ── Sistema de Mira de Remate ────────────────────────────────────
        self._mira_ativa        = False      # True quando está em modo de mira
        self._mira_forca        = 0.0       # 0.0 a 1.0 — posição atual da barra
        self._mira_forca_dir    = 1.0       # direção da oscilação (+1 ou -1)
        self._mira_vel          = 1.2       # velocidade de oscilação da barra (ciclos/s)
        self._mira_direcao      = pygame.math.Vector2(1, 0)  # direção apontada
        self._mira_confirmada   = False

        self.running    = True
        self.show_debug = False

    # ================================================================== #
    # Criação das equipas com posições táticas e atributos                #
    # ================================================================== #

    def _criar_equipas(self):
        cx = RINK_X + RINK_W // 2
        cy = RINK_Y + RINK_H // 2
        r  = self.rink

        # Equipamentos: cores de cada equipa (a visitante usa o alternativo se as cores chocarem)
        self.kit_casa, self.kit_fora = definir_equipamentos(self.equipa_casa_id, self.equipa_fora_id)

        bal_prop_azul = r.baliza_dir
        bal_adv_azul  = r.baliza_esq
        bal_prop_verm = r.baliza_esq
        bal_adv_verm  = r.baliza_dir

        # ── As duas equipas: 4 jogadores de campo com os nomes do plantel de cada clube ──
        # A equipa azul (a do jogador) fica do lado direito e a vermelha do esquerdo.
        self.equipa_azul       = pygame.sprite.Group()
        self.equipa_vermelha   = pygame.sprite.Group()
        self.agentes_azul      = []
        self.agentes_vermelhos = []
        self.jogador_humano    = None
        self.jogador_humano2   = None

        for equipa, lado, equipa_id, kit in (("azul", 1, self.equipa_casa_id, self.kit_casa),
                                             ("vermelho", -1, self.equipa_fora_id, self.kit_fora)):
            plantel = obter_plantel(equipa_id)["jogadores"]
            for i, ((dx, dy, stats), (nome, papel, num)) in enumerate(zip(FORMACAO, plantel)):
                pos = (cx + lado * dx, cy + dy)
                humano = equipa == "azul" and i == 0
                p = Player(equipa, pos, numero=num, nome=nome, humano=humano, teclas="wasd",
                           kit=kit)
                p.equipa_id       = equipa_id
                p.papel           = papel
                p.stat_velocidade = stats[0]
                p.stat_remate     = stats[1]
                p.stat_passe      = stats[2]
                p.stat_defesa     = stats[3]
                if equipa == "azul":
                    pos_base = self._pos_tatica_azul(papel, pos)
                    p.pos_tatica = pos_base
                    self.equipa_azul.add(p)
                    if humano:
                        self.jogador_humano = p
                        p.selecionado = True
                    else:
                        self.agentes_azul.append(AgentIA(p, papel, "azul", pos_base,
                                                         bal_prop_azul, bal_adv_azul,
                                                         dificuldade=DIFICULDADE_EQUIPA_HUMANA))
                else:
                    pos_base = self._pos_tatica_verm(papel, pos)
                    p.pos_tatica = pos_base
                    self.equipa_vermelha.add(p)
                    self.agentes_vermelhos.append(AgentIA(p, papel, "vermelho", pos_base,
                                                          bal_prop_verm, bal_adv_verm,
                                                          dificuldade=self.dificuldade))

        self.todos_jogadores = pygame.sprite.Group(
            *self.equipa_azul, *self.equipa_vermelha
        )

        # ── Guarda-redes (posicionados sobre as linhas de golo) ──────────
        self.gr_azul = Goalkeeper(
            equipa="azul", lado="dir",
            baliza_rect=r.zona_gr_dir,
            pos_x_fixo=r.linha_golo_dir_x - 4,
            dificuldade=DIFICULDADE_EQUIPA_HUMANA
        )
        self.gr_vermelho = Goalkeeper(
            equipa="vermelho", lado="esq",
            baliza_rect=r.zona_gr_esq,
            pos_x_fixo=r.linha_golo_esq_x + 4,
            dificuldade=self.dificuldade
        )
        self.gr_azul.kit     = self.kit_casa
        self.gr_vermelho.kit = self.kit_fora
        self.gr_azul.nome     = obter_plantel(self.equipa_casa_id)["guarda_redes"]
        self.gr_vermelho.nome = obter_plantel(self.equipa_fora_id)["guarda_redes"]
        self.grupo_gr = pygame.sprite.Group(self.gr_azul, self.gr_vermelho)
        # A IA precisa de saber onde está o GR adversário para rematar para o outro canto
        # A força de cada clube (a mesma do modo carreira) também conta um pouco no jogo
        for a in self.agentes_azul:
            a.gr_adversario = self.gr_vermelho
            a.definir_forca(FORCA_EQUIPAS.get(self.equipa_casa_id, 79))
        for a in self.agentes_vermelhos:
            a.gr_adversario = self.gr_azul
            a.definir_forca(FORCA_EQUIPAS.get(self.equipa_fora_id, 79))

    def _pos_tatica_azul(self, papel: str, pos_inicial: tuple) -> tuple:
        cx = RINK_X + RINK_W // 2
        if papel == "avancado":
            return (cx + 90, pos_inicial[1])
        elif papel == "medio":
            return (cx + 220, pos_inicial[1])
        else:
            return (cx + 360, pos_inicial[1])

    def _pos_tatica_verm(self, papel: str, pos_inicial: tuple) -> tuple:
        cx = RINK_X + RINK_W // 2
        if papel == "avancado":
            return (cx - 90, pos_inicial[1])
        elif papel == "medio":
            return (cx - 220, pos_inicial[1])
        else:
            return (cx - 360, pos_inicial[1])

    # ================================================================== #
    # Game Loop                                                            #
    # ================================================================== #

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()

    # ================================================================== #
    # Eventos                                                              #
    # ================================================================== #

    # ------------------------------------------------------------------ #
    # Janela e definições                                                  #
    # ------------------------------------------------------------------ #

    def _criar_janela(self) -> pygame.Surface:
        """
        Janela de 1280x720. Com SCALED o jogo pode ir para ecrã inteiro (a imagem é
        ampliada mantendo a proporção) e com vsync o desenho fica sincronizado com o
        monitor (sem "rasgos" na imagem). Se o computador não suportar, usa a janela simples.
        """
        # Ícone da janela: o emblema dos sticks cruzados
        try:
            from graficos import CAMINHO_EMBLEMA
            pygame.display.set_icon(pygame.transform.smoothscale(pygame.image.load(CAMINHO_EMBLEMA), (64, 64)))
        except (pygame.error, OSError, ImportError):
            pass
        flags = pygame.SCALED | (pygame.FULLSCREEN if self.ecra_inteiro else 0)
        for tentativa in ({"vsync": 1}, {}):
            try:
                return pygame.display.set_mode((WIDTH, HEIGHT), flags, **tentativa)
            except pygame.error:
                pass
        self.ecra_inteiro = False
        return pygame.display.set_mode((WIDTH, HEIGHT))

    @staticmethod
    def _ler_definicoes() -> dict:
        try:
            with open(CAMINHO_DEFINICOES, encoding="utf-8") as f:
                dados = json.load(f)
            return dados if isinstance(dados, dict) else {}
        except (OSError, ValueError):
            return {}

    @staticmethod
    def _ler_volume(definicoes: dict, chave: str, omissao: float) -> float:
        try:
            return max(0.0, min(1.0, float(definicoes.get(chave, omissao))))
        except (TypeError, ValueError):
            return omissao

    def _gravar_definicoes(self):
        try:
            os.makedirs(os.path.dirname(CAMINHO_DEFINICOES), exist_ok=True)
            with open(CAMINHO_DEFINICOES, "w", encoding="utf-8") as f:
                json.dump({"ecra_inteiro": self.ecra_inteiro, "estilo_arcade": self.estilo_arcade,
                           "vol_efeitos": som.vol_efeitos, "vol_publico": som.vol_publico}, f)
        except OSError:
            pass          # não conseguir gravar não impede de jogar

    def alternar_ecra_inteiro(self):
        try:
            pygame.display.toggle_fullscreen()
            self.ecra_inteiro = not self.ecra_inteiro
            self._gravar_definicoes()
        except pygame.error:
            pass

    def _som_acao(self, acao):
        """Som dos menus: 'confirmar' nas escolhas, 'voltar' ao sair de um ecrã."""
        if not acao or acao in ("sair", "volume_efeitos", "volume_publico"):
            return
        if isinstance(acao, tuple):
            acao = acao[0]
        if acao == "mover":
            som.ui("mover")
        elif acao in ("voltar", "menu", "desistir"):
            som.ui("voltar")
        else:
            som.ui("confirmar")

    def _atualizar_publico(self):
        """Barulho de fundo do pavilhão: forte no jogo, baixo na pausa e nos menus."""
        if self.estado == "jogo" and not self.pausado and not self.fim_jogo:
            nivel = 1.0
        elif self.estado in ("jogo", "controlos") and (self.pausado or self.fim_jogo):
            nivel = 0.45 if self.fim_jogo else 0.3
        else:
            nivel = 0.3
        if nivel != self._nivel_publico:
            self._nivel_publico = nivel
            som.publico(nivel)

    def _tocar_sons_bola(self):
        """Transforma os acontecimentos da bola (tacada, tabela, poste, defesa) em sons."""
        cam = self.rink.camera
        for tipo, forca, x, y in self.bola.eventos:
            sx, sy = cam.projetar(x, y)
            self._efeitos_bola(tipo, forca, sx, sy)
            if tipo == "tacada":
                if forca >= 420:
                    som.tocar("remate", 0.55 + 0.45 * min(1.0, forca / 650), sx)
                elif forca >= 150:
                    som.tocar("passe", 0.75, sx)
            elif tipo == "tabela":
                som.tocar("tabela", min(1.0, 0.25 + forca / 600), sx)
            elif tipo == "poste":
                som.tocar("poste", min(1.0, 0.3 + forca / 500), sx)
                if forca > 300:
                    som.tocar("publico_uh", 0.8)
            elif tipo == "defesa":
                som.tocar("defesa", min(1.0, 0.35 + forca / 600), sx)
                if forca > 420:
                    som.tocar("publico_uh", 0.7)
        self.bola.eventos.clear()

    def _efeitos_bola(self, tipo: str, forca: float, sx: float, sy: float):
        """Estilo arcade: faíscas, tremer e textos conforme o que aconteceu à bola."""
        ef = self.efeitos
        if tipo == "tacada" and forca >= 420:
            ef.pausa(0.05)
            ef.tremer(3, 0.15)
            ef.faiscas(sx, sy, (255, 235, 140), 12, 300)
        elif tipo == "tabela" and forca > 200:
            ef.poeira(sx, sy, 7)
            if forca > 380:
                ef.tremer(min(5, forca / 110), 0.18)
        elif tipo == "poste":
            ef.faiscas(sx, sy, (210, 230, 255), 16, 340)
            ef.tremer(6, 0.3)
            ef.pausa(0.07)
            ef.texto_pop("POSTE!", sx, sy - 50, (120, 200, 255), 34)
        elif tipo == "defesa" and forca > 250:
            ef.faiscas(sx, sy, (255, 255, 255), 10, 240)
            ef.tremer(3.5, 0.2)
            ef.pausa(0.05)
            if forca > 380:
                ef.texto_pop("DEFESA!", sx, sy - 60, (120, 255, 160), 34)

    def _efeitos_posse(self):
        """Estilo arcade: quando a bola muda de equipa num choque, aparece "ROUBO!"."""
        dono = self.bola.dono
        ant = self._dono_anterior
        if dono is not None and ant is not None and dono is not ant and dono.equipa != ant.equipa:
            if math.hypot(dono.pos_x - ant.pos_x, dono.pos_y - ant.pos_y) < 70:
                sx, sy = self.rink.camera.projetar(dono.pos_x, dono.pos_y)
                self.efeitos.pausa(0.04)
                self.efeitos.tremer(2.5, 0.15)
                self.efeitos.faiscas(sx, sy - 20, (255, 200, 90), 8, 200)
                self.efeitos.texto_pop("ROUBO!", sx, sy - 70, (255, 170, 60), 26)
        if dono is not None:
            self._dono_anterior = dono

    def _abrir_definicoes(self, origem: str):
        self._origem_controlos = origem
        self.ecra_controlos.arena = self.rink._surf
        self.estado = "controlos"

    def handle_events(self):
        # F11 funciona em qualquer ecrã (os outros eventos voltam para a fila, pela mesma ordem)
        teclas = pygame.event.get(pygame.KEYDOWN)
        if any(e.key == pygame.K_F11 for e in teclas):
            self.alternar_ecra_inteiro()
        for e in teclas:
            if e.key != pygame.K_F11:
                pygame.event.post(e)
        self.ecra_controlos.ecra_inteiro = self.ecra_inteiro
        self.ecra_controlos.estilo_arcade = self.estilo_arcade

        # ── Menus (cada ecrã devolve uma "ação") ──────────────────────────
        if self.estado == "menu_principal":
            for event in pygame.event.get():
                acao = self.menu_principal.handle_event(event)
                self._som_acao(acao)
                if acao == "jogar":
                    self.abrir_selecao_equipas()
                elif acao == "carreira":
                    self.abrir_escolha_carreira()
                elif acao == "carreira_jogador":
                    self.abrir_carreira_jogador()
                elif acao == "teste":
                    self.iniciar_teste()
                elif acao == "definicoes":
                    self._abrir_definicoes("menu_principal")
                elif acao == "sair":
                    self.running = False
            return

        if self.estado == "controlos":
            for event in pygame.event.get():
                acao = self.ecra_controlos.handle_event(event)
                self._som_acao(acao)
                if acao == "ecra_inteiro":
                    self.alternar_ecra_inteiro()
                elif acao == "estilo_arcade":
                    self.estilo_arcade = not self.estilo_arcade
                    self.efeitos.ativo = self.estilo_arcade
                    self._gravar_definicoes()
                elif acao in ("volume_efeitos", "volume_publico"):
                    som.definir_volumes(self.ecra_controlos.vol_efeitos, self.ecra_controlos.vol_publico)
                    if acao == "volume_efeitos":
                        som.tocar("passe")              # para se ouvir o volume novo
                    self._gravar_definicoes()
                elif acao == "voltar":
                    # Se veio da pausa, volta ao jogo (que continua em pausa)
                    self.estado = "jogo" if self._origem_controlos == "pausa" else "menu_principal"
                elif acao == "sair":
                    self.running = False
            return

        if self.estado == "carreira_escolha":
            for event in pygame.event.get():
                acao = self.ecra_carreira.handle_event(event)
                self._som_acao(acao)
                if acao == "comecar":
                    self._abrir_carreira().novo(self.ecra_carreira.equipa, self.ecra_carreira.dificuldade)
                    self.abrir_campeonato()
                elif acao == "voltar":
                    self.ir_para_menu_principal()
                elif acao == "sair":
                    self.running = False
            return

        if self.estado == "carreira":
            for event in pygame.event.get():
                acao = self.ecra_campeonato.handle_event(event)
                self._som_acao(acao)
                if acao == "jogar":
                    self.iniciar_jogo_carreira()
                elif acao == "simular":
                    self.simular_jogo_carreira()
                elif acao == "simular_epoca":
                    self.simular_epoca_carreira()
                elif acao == "nova_epoca":
                    c = self.carreira
                    c.novo(c.equipa_jogador, c.dificuldade)
                    self.abrir_campeonato()
                elif acao == "nova_carreira":
                    self.abrir_escolha_carreira(nova=True)
                elif acao == "menu":
                    self.ir_para_menu_principal()
                elif acao == "sair":
                    self.running = False
            return

        if self.estado == "cj_criar":
            for event in pygame.event.get():
                acao = self.ecra_cj_criar.handle_event(event)
                self._som_acao(acao)
                if acao == "comecar":
                    e = self.ecra_cj_criar
                    self._abrir_cj().novo(e.nome, e.numero, e.posicao, e.equipa)
                    self.abrir_carreira_jogador()
                elif acao == "voltar":
                    self.ir_para_menu_principal()
                elif acao == "sair":
                    self.running = False
            return

        if self.estado == "cj":
            for event in pygame.event.get():
                acao = self.ecra_cj.handle_event(event)
                self._som_acao(acao)
                if acao == "jogar":
                    self.iniciar_jogo_cj()
                elif acao == "simular":
                    self.abrir_carreira_jogador(aviso=self.carreira_jog.simular_jogo())
                elif acao == "simular_epoca":
                    self.carreira_jog.simular_resto_da_epoca()
                    self.abrir_carreira_jogador()
                elif acao == "ficar":
                    self.carreira_jog.continuar()
                    self.abrir_carreira_jogador()
                elif acao and acao.startswith("assinar:"):
                    self.carreira_jog.continuar(acao.split(":", 1)[1])
                    self.abrir_carreira_jogador()
                elif acao == "nova_carreira":
                    self.abrir_criar_jogador()
                elif acao == "menu":
                    self.ir_para_menu_principal()
                elif acao == "sair":
                    self.running = False
            return

        if self.estado == "menu_selecao":
            for event in pygame.event.get():
                res = self.menu.handle_event(event)
                self._som_acao(res)
                if res == "iniciar":
                    c_id, f_id = self.menu.get_equipas()
                    self.iniciar_partida(c_id, f_id, dificuldade=self.menu.get_dificuldade())
                elif res == "voltar":
                    c_id, f_id = self.menu.get_equipas()
                    self.dificuldade = self.menu.get_dificuldade()
                    self.ir_para_menu_principal(c_id, f_id)
                elif res == "sair":
                    self.running = False
            return

        # ── Jogo em pausa ────────────────────────────────────────────────
        if self.pausado:
            for event in pygame.event.get():
                acao = self.menu_pausa.handle_event(event)
                self._som_acao(acao)
                if acao == "continuar":
                    self.pausado = False
                elif acao == "reiniciar":
                    self.iniciar_partida(self.equipa_casa_id, self.equipa_fora_id, self.dificuldade)
                elif acao == "controlos":
                    self._abrir_definicoes("pausa")
                elif acao == "desistir":
                    if self.modo_jogador:
                        self.abrir_carreira_jogador()    # o jogo não conta
                    else:
                        self.abrir_campeonato()          # o jogo não conta
                elif acao == "menu":
                    self.ir_para_menu_principal()
                elif acao == "sair":
                    self.running = False
            return

        # ── Fim do jogo ──────────────────────────────────────────────────
        if self.fim_jogo:
            for event in pygame.event.get():
                acao = self.ecra_fim.handle_event(event)
                self._som_acao(acao)
                if acao == "continuar" and self.modo_jogador:
                    self._registar_jogo_cj()
                elif acao == "continuar" and self.modo_carreira:
                    jornada = self.carreira.registar_jogo_do_jogador(
                        self.golos_azul, self.golos_vermelho,
                        marcadores_eu=[m["nome"] for m in self.marcadores if m["equipa"] == "azul"],
                        marcadores_adv=[m["nome"] for m in self.marcadores if m["equipa"] == "vermelho"])
                    self.abrir_campeonato(destaque=jornada)
                elif acao == "reiniciar":
                    self.iniciar_partida(self.equipa_casa_id, self.equipa_fora_id, self.dificuldade)
                elif acao == "equipas":
                    self.abrir_selecao_equipas()
                elif acao == "menu":
                    self.ir_para_menu_principal()
                elif acao == "sair":
                    self.running = False
            return

        # ── Remate na primeira pessoa ────────────────────────────────────
        if self.remate_pov is not None:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                else:
                    self.remate_pov.handle_event(event)
            return

        # ── Partida a decorrer ───────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_p, pygame.K_m):
                    # ESC com a mira aberta cancela o remate; caso contrário abre a pausa
                    if event.key == pygame.K_ESCAPE and self._mira_ativa:
                        self._mira_ativa = False
                    else:
                        self.abrir_pausa()
                elif event.key == pygame.K_F3:
                    self.show_debug = not self.show_debug
                elif self.modo_teste and event.key == pygame.K_r:
                    self._teste_novo_remate()
                elif self.modo_carreira and event.key in (pygame.K_F4, pygame.K_t, pygame.K_y, pygame.K_1,
                                                          pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5,
                                                          pygame.K_6, pygame.K_7, pygame.K_8):
                    pass   # no campeonato não se pode trocar de equipa nem de dificuldade a meio
                elif event.key == pygame.K_F4:
                    # Alternar dificuldade em jogo
                    ordem_dif = ["facil", "normal", "dificil"]
                    idx_dif = ordem_dif.index(self.dificuldade) if self.dificuldade in ordem_dif else 1
                    prox_dif = ordem_dif[(idx_dif + 1) % len(ordem_dif)]
                    self.definir_dificuldade(prox_dif)
                elif event.key == pygame.K_z:
                    if self.modo_jogador and not self.jogador_humano.tem_bola:
                        self._pedir_bola()
                    else:
                        self._acao_passe()
                elif event.key == pygame.K_x:
                    self._acao_remate()
                elif event.key in (pygame.K_TAB, pygame.K_c, pygame.K_SPACE):
                    if self.modo_jogador:
                        self._pedir_bola()           # só controlas o teu jogador: pede a bola
                    else:
                        self._selecionar_jogador_proximo()
                elif event.key == pygame.K_t:
                    self.alternar_equipa_casa()
                elif event.key == pygame.K_y:
                    self.alternar_equipa_fora()
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                                   pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8):
                    idx = event.key - pygame.K_1
                    if 0 <= idx < len(EQUIPAS_LISTA):
                        self.mudar_equipa_casa(EQUIPAS_LISTA[idx])
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Confirmar mira com clique esquerdo
                if self._mira_ativa and event.button == 1:
                    mpos = self.rink.camera.desprojetar(*pygame.mouse.get_pos())
                    bx = round(self.jogador_humano.pos_x)
                    by = round(self.jogador_humano.pos_y)
                    v = pygame.math.Vector2(mpos[0] - bx, mpos[1] - by)
                    if v.length_squared() > 0:
                        self._mira_direcao = v.normalize()
                    self._confirmar_remate()
                    continue  # não processar clique noutros elementos
                # Botão de pausa no canto superior direito
                if event.pos[0] >= WIDTH - 56 and event.pos[1] <= 56:
                    self.abrir_pausa()
                else:
                    self._tratar_clique_botoes(event.pos)

    def _tratar_clique_botoes(self, pos):
        for chave, btn in self.hud.btn_rects.items():
            if btn["rect"].collidepoint(pos):
                if chave == "passe":
                    self._acao_passe()
                elif chave == "remate":
                    self._acao_remate()
                elif chave in ("defender", "acelerar"):
                    self._selecionar_jogador_proximo()
                return

    # ================================================================== #
    # Ações do Jogador Humano                                              #
    # ================================================================== #

    def _direcao_vec(self, jogador=None) -> pygame.math.Vector2:
        if jogador is None:
            jogador = self.jogador_humano
        if hasattr(jogador, "vetor_direcao") and jogador.vetor_direcao.length_squared() > 0:
            return pygame.math.Vector2(jogador.vetor_direcao)
        mapa = {"direita":(1,0),"esquerda":(-1,0),"cima":(0,-1),"baixo":(0,1)}
        return pygame.math.Vector2(mapa.get(jogador.direcao, (-1, 0)))

    def _acao_passe(self):
        if self.jogador_humano.tem_bola and self.jogo_ativo:
            direcao = self._direcao_vec(self.jogador_humano)
            melhor_colega = None
            melhor_score = -1.0

            # Procura o colega azul mais bem posicionado na direção apontada
            for j in self.equipa_azul:
                if j == self.jogador_humano:
                    continue
                to_j = pygame.math.Vector2(j.pos_x - self.jogador_humano.pos_x,
                                           j.pos_y - self.jogador_humano.pos_y)
                dist = to_j.length()
                if 30 < dist < 500:
                    dot = direcao.dot(to_j.normalize())
                    if dot > 0.35:
                        score = dot * (1.0 - (dist / 1200.0))
                        if score > melhor_score:
                            melhor_score = score
                            melhor_colega = j

            if melhor_colega:
                dir_passe = pygame.math.Vector2(melhor_colega.pos_x - self.jogador_humano.pos_x,
                                                melhor_colega.pos_y - self.jogador_humano.pos_y).normalize()
                self.jogador_humano.fazer_passe(self.bola, dir_passe)
                self.bola.marcar_recetor(melhor_colega)
            else:
                self.jogador_humano.fazer_passe(self.bola, direcao)

    def _acao_remate(self):
        """Ao premir X com a bola: abre o remate na primeira pessoa (apontar e escolher a força)."""
        if not self.jogo_ativo or self.remate_pov is not None:
            return
        j = self.jogador_humano
        if not j.tem_bola:
            return
        self._cj_contar("remates")
        gx, cy = self.rink.linha_golo_esq_x, self.rink.rect.centery
        if j.pos_x - gx < 30:
            # Atrás da linha de golo não se vê a baliza: remate rápido para o meio dela
            v = pygame.math.Vector2(gx - j.pos_x, cy - j.pos_y)
            if v.length_squared() > 0:
                from ball import REMATE_FORCA
                j.fazer_remate_com_forca(self.bola, v.normalize(), REMATE_FORCA * 0.7)
            return
        self.remate_pov = RematePOV(self.screen, self.rink, j, self.gr_vermelho, self.dificuldade,
                                    limite_tempo=None if self.modo_teste else 5.0,
                                    cor_linhas=self.rink.cor_linhas,
                                    defensores=list(self.equipa_vermelha),
                                    velocidade=(j.vel_x, j.vel_y), placar=self._placar_pov())

    def _placar_pov(self):
        """Resultado e tempo para o marcador eletrónico do pavilhão (no ecrã do remate)."""
        if self.modo_teste:
            tempo = "TESTE"
        else:
            m, sg = divmod(max(0, int(self.tempo_restante)), 60)
            tempo = f"{m:02d}:{sg:02d}"
        return (obter_info_equipa(self.equipa_casa_id)["sigla"], self.golos_azul,
                obter_info_equipa(self.equipa_fora_id)["sigla"], self.golos_vermelho, tempo)

    def _aplicar_remate(self, res):
        """Depois do remate na primeira pessoa, põe a bola no sítio certo do jogo 2D."""
        self.remate_pov = None
        if res is None:                     # cancelou com ESC: continua com a bola
            return
        j, b = self.jogador_humano, self.bola
        gx, cy = self.rink.linha_golo_esq_x, self.rink.rect.centery
        r, u, v = res["resultado"], res["u"], res["velocidade"]
        lado = 1 if u >= 0 else -1
        # O jogador continuou a patinar durante o remate: fica onde chegou, a 50 % da velocidade
        j.pos_x, j.pos_y = res["pos"]
        j.vel_x, j.vel_y = res["vel"]
        j.rect.center = (round(j.pos_x), round(j.pos_y))
        b.pos_x, b.pos_y = j.pos_x, j.pos_y
        j._comecar_acao("remate", 0.30)
        j.tem_bola = False
        b.libertar(pygame.math.Vector2(0, 0), dono_anterior=j)
        b.eventos.clear()                   # os sons já tocaram no ecrã do remate
        if self.modo_teste:
            self.teste["remates"] += 1
            chave = {"golo": "golos", "defesa": "defesas", "bloqueado": "defesas"}.get(r, "fora")
            self.teste[chave] += 1
            self._teste_espera = 1.6
        if r == "bloqueado":
            # A bola bate no defesa e ressalta para trás (para o lado de quem rematou)
            dx_, dy_ = res["pos_bloqueio"]
            vx, vy = j.pos_x - dx_, j.pos_y - dy_
            n = math.hypot(vx, vy) or 1
            b.pos_x, b.pos_y = dx_ + vx / n * 20, dy_ + vy / n * 20
            b.vel.update(vx / n * v * 0.25 + random.uniform(-60, 60), vy / n * v * 0.25 + random.uniform(-60, 60))
            sx, sy = self.rink.camera.projetar(b.pos_x, b.pos_y)
            self._efeitos_bola("defesa", v, sx, sy)
            self.efeitos.texto_pop("BLOQUEADO!", sx, sy - 60, (255, 150, 70), 30)
        elif r == "golo":
            b.pos_x, b.pos_y = gx - 16, cy + max(-28, min(28, u))
            b.vel.update(-60, 0)
            self._golo("azul")
        elif r == "defesa":
            self.gr_vermelho.pos_y = cy + res["u_gr"]
            b.pos_x, b.pos_y = gx + 26, cy + res["u_gr"] + lado * 8
            b.vel.update(v * 0.3, random.uniform(-1, 1) * v * 0.2)
            sx, sy = self.rink.camera.projetar(gx, b.pos_y)
            self._efeitos_bola("defesa", v, sx, sy)
        elif r == "poste":
            b.pos_x, b.pos_y = gx + 8, cy + lado * (MEIA_BOCA + 7)
            b.vel.update(v * 0.35, lado * v * 0.25)
            sx, sy = self.rink.camera.projetar(gx, b.pos_y)
            self._efeitos_bola("poste", v, sx, sy)
        else:
            if abs(u) > MEIA_BOCA + 3:      # ao lado da baliza
                b.pos_x, b.pos_y = gx - 10, cy + lado * min(abs(u) + 10, 75)
                b.vel.update(-v * 0.3, lado * 40)
            else:                           # por cima da barra: cai atrás da baliza
                b.pos_x, b.pos_y = gx - 70, cy + u
                b.vel.update(-v * 0.2, lado * 40)
        b.rect.center = (round(b.pos_x), round(b.pos_y))

    # ------------------------------------------------------------------ #
    # MODO TESTE: treinar remates contra o guarda-redes                   #
    # ------------------------------------------------------------------ #

    def iniciar_teste(self):
        """Só o jogador e o guarda-redes adversário; remates ilimitados e contagem dos golos."""
        self.iniciar_partida(self.equipa_casa_id, self.equipa_fora_id)
        self.modo_teste = True
        humano = self.jogador_humano
        for j in list(self.equipa_azul):
            if j is not humano:
                self.equipa_azul.remove(j)
        self.agentes_azul = []
        self.equipa_vermelha.empty()
        self.agentes_vermelhos = []
        self.todos_jogadores = pygame.sprite.Group(humano)
        self.tempo_restante = 1e9
        self.teste = {"remates": 0, "golos": 0, "defesas": 0, "fora": 0}
        self._teste_novo_remate()
        self._msg_texto = "MODO TESTE  •  aproxima-te e carrega em X"
        self._msg_timer = 2.5
        self._msg_equipa = "azul"

    def _teste_novo_remate(self):
        """Põe o jogador com a bola num sítio novo à frente da baliza."""
        r = self.rink.rect
        gx, cy = self.rink.linha_golo_esq_x, r.centery
        j = self.jogador_humano
        j.pos_x = gx + random.uniform(130, 420)
        j.pos_y = max(r.top + 40, min(r.bottom - 40, cy + random.uniform(-170, 170)))
        j.vel_x = j.vel_y = 0.0
        j.set_target(0.0, 0.0)
        j.rect.center = (round(j.pos_x), round(j.pos_y))
        self.bola.repor((j.pos_x, j.pos_y))
        self.bola.definir_dono(j)
        j.tem_bola = True
        self.bola.seguir_jogador(j)
        self.gr_vermelho.pos_y = float(cy)
        self._teste_espera = 0.0
        self._teste_livre = 0.0
        self._reposicao_pendente = None

    def _update_teste(self, dt: float):
        """Depois de cada remate (ou se a bola ficar perdida), o jogador volta a ter a bola."""
        if self._reposicao_pendente is not None:
            return
        if self._teste_espera > 0:
            self._teste_espera -= dt
            if self._teste_espera <= 0:
                self._teste_novo_remate()
            return
        if self.bola.dono is None and self.bola.vel.length() < 20:
            self._teste_livre += dt
            if self._teste_livre > 2.0:
                self._teste_novo_remate()
        else:
            self._teste_livre = 0.0

    def _confirmar_remate(self):
        if not self._mira_ativa:
            return
        self._mira_ativa = False
        from ball import REMATE_FORCA
        # Força entre 30% e 100% da força máxima
        forca_real = (0.30 + self._mira_forca * 0.70) * REMATE_FORCA
        vec = pygame.math.Vector2(self._mira_direcao)
        if vec.length_squared() == 0:
            vec = pygame.math.Vector2(1, 0)
        self.jogador_humano.fazer_remate_com_forca(self.bola, vec.normalize(), forca_real)

    def _selecionar_jogador_proximo(self):
        """TAB / C: passa o controlo para o jogador azul mais perto da bola."""
        melhor = None
        melhor_dist = float("inf")
        for j in self.equipa_azul:
            if j.humano:
                continue
            d = math.hypot(j.pos_x - self.bola.pos_x, j.pos_y - self.bola.pos_y)
            if d < melhor_dist:
                melhor_dist = d
                melhor = j
        if melhor:
            self._trocar_humano(melhor)

    def _trocar_humano(self, novo: Player):
        if novo == self.jogador_humano:
            return
        if self.modo_jogador and self._cj_jogador is not None and novo is not self._cj_jogador:
            return            # carreira de jogador: o controlo nunca passa para outro jogador

        antigo = self.jogador_humano
        antigo.humano      = False
        antigo.selecionado = False
        antigo.set_target(0.0, 0.0)

        papel    = getattr(antigo, "papel", "avancado")
        pos_base = getattr(antigo, "pos_tatica", self._pos_tatica_azul(papel, (antigo.pos_x, antigo.pos_y)))
        agente   = AgentIA(antigo, papel, "azul", pos_base,
                           self.rink.baliza_dir, self.rink.baliza_esq,
                           dificuldade=DIFICULDADE_EQUIPA_HUMANA,
                           gr_adversario=getattr(self, "gr_vermelho", None))
        agente.definir_forca(FORCA_EQUIPAS.get(self.equipa_casa_id, 79))
        self.agentes_azul.append(agente)

        self.agentes_azul = [a for a in self.agentes_azul if a.jogador != novo]
        novo.humano      = True
        novo.selecionado = True
        self.jogador_humano = novo

    # ================================================================== #
    # Update                                                               #
    # ================================================================== #

    def update(self, dt: float):
        self._atualizar_publico()
        if self.estado == "menu_principal":
            self.menu_principal.update(dt)
            return
        if self.estado == "controlos":
            self.ecra_controlos.update(dt)
            return
        if self.estado == "menu_selecao":
            self.menu.update(dt)
            return
        if self.estado == "carreira_escolha":
            self.ecra_carreira.update(dt)
            return
        if self.estado == "carreira":
            self.ecra_campeonato.update(dt)
            return
        if self.estado == "cj_criar":
            self.ecra_cj_criar.update(dt)
            return
        if self.estado == "cj":
            self.ecra_cj.update(dt)
            return
        if self.pausado:
            self.menu_pausa.update(dt)
            return
        if self.fim_jogo:
            self.ecra_fim.update(dt)
            return

        if not self.jogo_ativo:
            return

        if self.remate_pov is not None:
            self.remate_pov.update(dt)
            if self.remate_pov.terminado:
                self._aplicar_remate(self.remate_pov.resultado)
            return
        if self.modo_teste:
            self._update_teste(dt)

        # Estilo arcade: pausa curta nos impactos e câmara lenta depois dos golos
        dt_real = dt
        dt = self.efeitos.tempo(dt)
        if self._reposicao_pendente is not None:
            saida, falta = self._reposicao_pendente
            falta -= dt_real
            if falta <= 0:
                self._reposicao_pendente = None
                self._repor_posicoes(saida=saida)
            else:
                self._reposicao_pendente = (saida, falta)
        if dt <= 0:
            if self._msg_timer > 0:
                self._msg_timer -= dt_real
            return

        # Cronómetro
        self.tempo_restante -= dt
        if self.tempo_restante <= 0:
            self._fim_de_parte()
            return

        # Modo de mira ativa: slow-motion e atualizar direção pelo rato
        if self._mira_ativa:
            dt_real = dt
            dt = dt_real * 0.15  # slow-motion durante a mira

            # Atualizar direção pelo rato em tempo real
            mpos = self.rink.camera.desprojetar(*pygame.mouse.get_pos())
            bx = round(self.jogador_humano.pos_x)
            by = round(self.jogador_humano.pos_y)
            v = pygame.math.Vector2(mpos[0] - bx, mpos[1] - by)
            if v.length_squared() > 10:
                self._mira_direcao = v.normalize()

            # Oscilar a barra de força
            self._mira_forca += self._mira_forca_dir * self._mira_vel * dt_real
            if self._mira_forca >= 1.0:
                self._mira_forca = 1.0
                self._mira_forca_dir = -1.0
            elif self._mira_forca <= 0.0:
                self._mira_forca = 0.0
                self._mira_forca_dir = 1.0

        # Auto-seleção inteligente
        self._auto_selecionar()

        # IA Vermelha
        lista_verm = list(self.equipa_vermelha)
        lista_azul = list(self.equipa_azul)
        for agente in self.agentes_vermelhos:
            colegas = [j for j in lista_verm if j != agente.jogador]
            agente.update(dt, self.bola, colegas, lista_azul)

        # IA Azul (colegas de equipa)
        for agente in self.agentes_azul:
            colegas_com_humano = [j for j in lista_azul if j != agente.jogador]
            agente.update(dt, self.bola, colegas_com_humano, lista_verm)

        # Atualizar todos os jogadores (com colisão contra as balizas do campo)
        for j in self.todos_jogadores:
            j.update(dt, self.rink.rect, self.bola, self.rink)

        # Gestão de timers de falta
        if self._falta_cooldown > 0:
            self._falta_cooldown = max(0.0, self._falta_cooldown - dt)
        if self._falta_timer > 0:
            self._falta_timer = max(0.0, self._falta_timer - dt)
            if self._falta_timer <= 0:
                self._falta_ativa = False

        # Colisões físicas entre jogadores (separação, desarmes limpos e faltas)
        todos = list(self.todos_jogadores)
        falta_detetada = None
        for i in range(len(todos)):
            for k in range(i + 1, len(todos)):
                evento = todos[i].empurrar_separar(todos[k], self.bola)
                if evento and evento.get("tipo") == "falta" and not falta_detetada and self._falta_cooldown <= 0:
                    falta_detetada = evento

        # Os jogadores de campo também chocam com os guarda-redes (antes atravessavam-nos).
        # Só o jogador é empurrado: o guarda-redes não sai da baliza.
        for gr in (self.gr_azul, self.gr_vermelho):
            for j in todos:
                j.afastar_de(gr.pos_x, gr.pos_y, RAIO_GR_CORPO)

        if falta_detetada and self.jogo_ativo and self._reposicao_pendente is None:
            self.assinalar_falta(falta_detetada["infrator"], falta_detetada["vitima"], falta_detetada.get("pos"))

        # Atualizar bola (com física de tabelas e balizas)
        # Guarda-redes primeiro (posicionam-se), depois a bola (que já testa as defesas deles)
        self.gr_azul.update(dt, self.bola)
        self.gr_vermelho.update(dt, self.bola)
        resultado = self.bola.update(dt, self.rink, todos_jogadores=todos,
                                     guarda_redes=(self.gr_azul, self.gr_vermelho))

        self._tocar_sons_bola()

        self._efeitos_posse()
        if self.modo_jogador:
            self._seguir_jogador_cj(dt)

        # Golos (durante a festa de um golo, a bola ainda na rede não conta outra vez)
        if self._reposicao_pendente is not None:
            resultado = None
        if resultado == "golo_azul":
            self._golo("azul")
        elif resultado == "golo_vermelho":
            self._golo("vermelho")

        if self._msg_timer > 0:
            self._msg_timer -= dt

    def _auto_selecionar(self):
        # Se um colega apanhou a bola, passa o controlo imediatamente para ele
        if self.bola.dono is not None:
            if self.bola.dono in self.equipa_azul and self.bola.dono != self.jogador_humano:
                self._trocar_humano(self.bola.dono)
            return

        if self.jogador_humano.tem_bola:
            return

        # Durante um remate ou passe rápido, não troca a meio da trajetória
        if self.bola.vel.length() > 220:
            return

        dist_humano = math.hypot(
            self.jogador_humano.pos_x - self.bola.pos_x,
            self.jogador_humano.pos_y - self.bola.pos_y
        )
        melhor = self.jogador_humano
        melhor_dist = dist_humano
        for j in self.equipa_azul:
            if j == self.jogador_humano:
                continue
            d = math.hypot(j.pos_x - self.bola.pos_x, j.pos_y - self.bola.pos_y)
            if d < melhor_dist - 80:
                melhor_dist = d
                melhor = j
        if melhor != self.jogador_humano:
            self._trocar_humano(melhor)

    # ------------------------------------------------------------------ #
    # Gestão e Alternância de Equipas                                     #
    # ------------------------------------------------------------------ #

    def iniciar_partida(self, casa_id: str, fora_id: str, dificuldade: str = None):
        """Inicia uma partida completa com as equipas selecionadas no menu e nível de IA."""
        self.equipa_casa_id = casa_id
        self.equipa_fora_id = fora_id
        if dificuldade:
            self.dificuldade = dificuldade
        self.modo_jogador = False          # a carreira de jogador liga-o depois (iniciar_jogo_cj)
        self._cj_jogador = None

        # Repor estados da partida anterior (mira aberta, pausa, ...)
        self._cancelar_mira()
        self.pausado = False
        self.modo_teste = False
        self.remate_pov = None

        # Reiniciar contadores de faltas
        self.faltas_azul     = 0
        self.faltas_vermelho = 0
        self._falta_ativa    = False
        self._falta_timer    = 0.0
        self._falta_cooldown = 0.0

        # Atualizar o ringue com o emblema oficial da equipa da casa
        self.rink.definir_equipa_casa(self.equipa_casa_id)

        # Recriar os jogadores de campo e guarda-redes com as novas equipas
        self._criar_equipas()

        # Repor bola no centro e dar a posse ao jogador humano
        cx = RINK_X + RINK_W // 2
        cy = RINK_Y + RINK_H // 2
        self.bola.repor((cx, cy))
        self.bola.definir_dono(self.jogador_humano)
        self.jogador_humano.tem_bola = True
        self.bola.seguir_jogador(self.jogador_humano)

        # Reiniciar marcador e cronómetro
        self.golos_azul     = 0
        self.golos_vermelho = 0
        self.marcadores     = []        # golos deste jogo: {"equipa", "nome", "minuto"}
        self.parte          = 1
        self.tempo_restante = float(DURACAO_PARTE)
        self.jogo_ativo     = True
        self.fim_jogo       = False
        self.estado         = "jogo"
        self.bola.eventos.clear()
        self.efeitos.reiniciar()
        self._reposicao_pendente = None
        self._dono_anterior = None
        som.tocar("apito_curto")                # apito de início

        info_c = obter_info_equipa(casa_id)
        info_f = obter_info_equipa(fora_id)
        self._msg_texto     = f"{info_c['nome']}  vs  {info_f['nome']}"
        self._msg_timer     = 2.5

    def definir_dificuldade(self, nivel: str):
        """
        Define a dificuldade da equipa ADVERSÁRIA (jogadores e guarda-redes).
        Os colegas e o guarda-redes do jogador humano ficam sempre no nível normal,
        senão no "Difícil" a nossa equipa também ficava mais forte.
        """
        self.dificuldade = nivel
        for agente in self.agentes_vermelhos:
            agente.definir_dificuldade(nivel)
        if hasattr(self, "gr_vermelho"):
            self.gr_vermelho.definir_dificuldade(nivel)

        nomes = {"facil": "FÁCIL", "normal": "NORMAL", "dificil": "DIFÍCIL"}
        self._msg_texto = f"Dificuldade da IA: {nomes.get(nivel, nivel.upper())}"
        self._msg_timer = 2.0

    def assinalar_falta(self, infrator, vitima, pos=None):
        """Assinala falta com apito oficial, registo no placar e reposição de posse."""
        if self._falta_cooldown > 0 or not self.jogo_ativo:
            return

        self._falta_cooldown = 3.2
        self._falta_timer    = 2.2
        self._falta_ativa    = True
        som.tocar("apito_curto")

        # Incrementar faltas da equipa infratora
        if infrator.equipa == "azul":
            self.faltas_azul += 1
            total_faltas = self.faltas_azul
            info_infrator = obter_info_equipa(self.equipa_casa_id)
            info_vitima   = obter_info_equipa(self.equipa_fora_id)
        else:
            self.faltas_vermelho += 1
            total_faltas = self.faltas_vermelho
            info_infrator = obter_info_equipa(self.equipa_fora_id)
            info_vitima   = obter_info_equipa(self.equipa_casa_id)

        cx = RINK_X + RINK_W // 2
        cy = RINK_Y + RINK_H // 2
        r = self.rink

        f_x = pos[0] if pos else vitima.pos_x
        f_y = pos[1] if pos else vitima.pos_y

        # Verificar se ocorreu na grande área adversária (Penálti)
        is_penalti = False
        if vitima.equipa == "azul":
            if f_x < r.linha_golo_esq_x + 130 and abs(f_y - cy) < 100:
                is_penalti = True
        else:
            if f_x > r.linha_golo_dir_x - 130 and abs(f_y - cy) < 100:
                is_penalti = True

        is_livre_direto = (total_faltas >= 10 and (total_faltas == 10 or total_faltas % 5 == 0))

        if is_penalti:
            self._falta_tipo = "penalti"
            self._msg_falta = "GRANDE PENALIDADE  •  PENÁLTI!"
            self._msg_falta_sub = f"Falta cometida por {infrator.nome} ({info_infrator['sigla']}) dentro da área"
            pos_bola = (r.linha_golo_esq_x + 95 if vitima.equipa == 'azul' else r.linha_golo_dir_x - 95, cy)
        elif is_livre_direto:
            self._falta_tipo = "livre_direto"
            self._msg_falta = f"{total_faltas}.ª FALTA DE EQUIPA  •  LIVRE DIRETO!"
            self._msg_falta_sub = f"Livre Direto para {info_vitima['nome']} (limite de 10 faltas atingido)"
            pos_bola = (cx - 150 if vitima.equipa == 'azul' else cx + 150, cy)
        else:
            self._falta_tipo = "livre"
            self._msg_falta = f"FALTA!  LIVRE: {info_vitima['nome'].upper()}"
            self._msg_falta_sub = f"Infração de {infrator.nome} ({info_infrator['sigla']})  •  Faltas de Equipa: {total_faltas}"
            # Clampar bola dentro do campo de jogo
            pos_bola = (max(r.rect.left + 70, min(r.rect.right - 70, f_x)),
                        max(r.rect.top + 45,  min(r.rect.bottom - 45, f_y)))

        # Repor a bola no ponto do livre
        self.bola.parar()
        self.bola.pos_x = float(pos_bola[0])
        self.bola.pos_y = float(pos_bola[1])
        self.bola.rect.center = (round(self.bola.pos_x), round(self.bola.pos_y))

        # Atribuir posse de bola à equipa que sofreu a falta
        if vitima.equipa == "azul":
            self._trocar_humano(vitima)
            self.jogador_humano.pos_x = float(pos_bola[0])
            self.jogador_humano.pos_y = float(pos_bola[1])
            self.jogador_humano.rect.center = (round(self.jogador_humano.pos_x), round(self.jogador_humano.pos_y))
            self.jogador_humano.set_target(0.0, 0.0)
            self.bola.definir_dono(self.jogador_humano)
            self.jogador_humano.tem_bola = True
            self.bola.seguir_jogador(self.jogador_humano)
        else:
            vitima.pos_x = float(pos_bola[0])
            vitima.pos_y = float(pos_bola[1])
            vitima.rect.center = (round(vitima.pos_x), round(vitima.pos_y))
            vitima.set_target(0.0, 0.0)
            self.bola.definir_dono(vitima)
            vitima.tem_bola = True
            self.bola.seguir_jogador(vitima)

        # Quem marca o livre fica protegido durante um instante
        if self.bola.dono is not None:
            self.bola.dono._cooldown_desarme = 1.0

        # Afastar os defesas adversários para a distância regulamentar (mínimo 90px)
        for j in self.todos_jogadores:
            if j.equipa == infrator.equipa:
                dist = math.hypot(j.pos_x - pos_bola[0], j.pos_y - pos_bola[1])
                if dist < 90 and dist > 0.1:
                    nx = (j.pos_x - pos_bola[0]) / dist
                    ny = (j.pos_y - pos_bola[1]) / dist
                    j.pos_x = pos_bola[0] + nx * 105
                    j.pos_y = pos_bola[1] + ny * 105
                    j.rect.center = (round(j.pos_x), round(j.pos_y))
                    j.set_target(0.0, 0.0)

    def _cancelar_mira(self):
        self._mira_ativa = False
        self._mira_forca = 0.0

    def abrir_pausa(self):
        if self.jogo_ativo and not self.fim_jogo:
            self._cancelar_mira()
            self.pausado = True
            self.menu_pausa = MenuPausa(self.screen, modo_carreira=self.modo_carreira, modo_teste=self.modo_teste)

    def abrir_selecao_equipas(self):
        """Vai para o ecrã de seleção de equipas, mantendo as últimas escolhas e a dificuldade."""
        self._cancelar_mira()
        self.modo_carreira = False
        self.pausado = False
        self.jogo_ativo = False
        self.fim_jogo = False
        self.estado = "menu_selecao"
        self.menu = TeamSelectMenu(self.screen, self.equipa_casa_id, self.equipa_fora_id,
                                   dificuldade=self.dificuldade, arena=self.rink._surf)

    # Mantido por compatibilidade com o código antigo
    voltar_ao_menu = abrir_selecao_equipas

    # ------------------------------------------------------------------ #
    # Modo carreira                                                       #
    # ------------------------------------------------------------------ #

    def _abrir_carreira(self) -> Campeonato:
        """Abre a base de dados do campeonato (só na primeira vez que é preciso)."""
        if self.carreira is None:
            self.carreira = Campeonato(self.caminho_carreira)
        return self.carreira

    def abrir_escolha_carreira(self, nova: bool = False):
        """Menu principal -> Modo carreira: continua o campeonato guardado ou escolhe uma equipa."""
        camp = self._abrir_carreira()
        if camp.existe and not nova:
            self.abrir_campeonato()
            return
        equipa = camp.equipa_jogador if camp.existe else self.equipa_casa_id
        dif = camp.dificuldade if camp.existe else self.dificuldade
        self.ecra_carreira = EcraCarreiraEscolha(self.screen, equipa, dif, arena=self.rink._surf)
        self.estado = "carreira_escolha"

    def abrir_campeonato(self, destaque: int | None = None, aviso: tuple | None = None):
        """Ecrã do campeonato (classificação, próximo jogo, resultados)."""
        self._cancelar_mira()
        self.modo_carreira = False
        self.pausado = False
        self.jogo_ativo = False
        self.fim_jogo = False
        self.ecra_campeonato = EcraCampeonato(self.screen, self.carreira, destaque,
                                              arena=self.rink._surf, aviso=aviso)
        self.estado = "carreira"

    def simular_jogo_carreira(self):
        """Simula o próximo jogo do jogador (em vez de o jogar) e mostra o resultado num cartão."""
        camp = self.carreira
        jogo = camp.proximo_jogo()
        if jogo is None:
            return
        jornada, g_eu, g_adv = camp.simular_jogo_do_jogador()
        if g_eu > g_adv:
            txt, cor = "VITÓRIA", (50, 170, 90)
            som.tocar("golo", 0.7)
        elif g_eu < g_adv:
            txt, cor = "DERROTA", (200, 60, 60)
            som.tocar("apito_final", 0.6)
        else:
            txt, cor = "EMPATE", (200, 150, 30)
            som.tocar("apito_final", 0.6)
        em_casa = jogo["casa_id"] == camp.equipa_jogador
        aviso = {"tipo": "jogo", "jornada": jornada, "casa": jogo["casa_id"], "fora": jogo["fora_id"],
                 "gc": g_eu if em_casa else g_adv, "gf": g_adv if em_casa else g_eu, "texto": txt, "cor": cor}
        self.abrir_campeonato(destaque=jornada, aviso=aviso)

    def simular_epoca_carreira(self):
        """Simula todas as jornadas que faltam até ao fim do campeonato."""
        camp = self.carreira
        n = camp.simular_resto_da_epoca()
        if n == 0:
            return
        pos = camp.posicao_do_jogador()
        if pos == 1:
            som.tocar("golo")
            txt, cor = "CAMPEÃO!", (50, 170, 90)
        else:
            som.tocar("apito_final", 0.6)
            txt, cor = f"{pos}.º LUGAR", (50, 110, 210)
        aviso = {"tipo": "epoca", "jornadas": n, "posicao": pos, "texto": txt, "cor": cor}
        self.abrir_campeonato(destaque=camp.ultima_jornada_jogada(), aviso=aviso)

    def iniciar_jogo_carreira(self):
        """Joga o próximo jogo do campeonato. A equipa do jogador é sempre a que ele controla."""
        camp = self.carreira
        jogo = camp.proximo_jogo()
        if jogo is None:
            return
        eu = camp.equipa_jogador
        em_casa = jogo["casa_id"] == eu
        adversario = jogo["fora_id"] if em_casa else jogo["casa_id"]
        self._jornada_carreira = jogo["jornada"]
        self.iniciar_partida(eu, adversario, dificuldade=camp.dificuldade)
        self.modo_carreira = True
        if not em_casa:
            # Jogo fora: joga-se no pavilhão do adversário (emblema e cores do ringue dele)
            self.rink.definir_equipa_casa(adversario)
        local = "EM CASA" if em_casa else "FORA"
        self._msg_texto = f"JORNADA {jogo['jornada']}  •  {local}"
        self._msg_timer = 2.5
        self._msg_equipa = "azul"

    # ------------------------------------------------------------------ #
    # Carreira de jogador (só se controla o próprio jogador)              #
    # ------------------------------------------------------------------ #

    def _abrir_cj(self) -> CarreiraJogador:
        """Abre a base de dados da carreira de jogador (só na primeira vez que é preciso)."""
        if self.carreira_jog is None:
            self.carreira_jog = CarreiraJogador(self.caminho_carreira_jogador)
        return self.carreira_jog

    def abrir_criar_jogador(self):
        self._cancelar_mira()
        self._abrir_cj()
        self.ecra_cj_criar = EcraCriarJogador(self.screen, arena=self.rink._surf)
        self.estado = "cj_criar"

    def abrir_carreira_jogador(self, aviso: dict | None = None):
        """Painel da carreira de jogador (ou o ecrã para criar o jogador, se ainda não há nenhum)."""
        cj = self._abrir_cj()
        self._cancelar_mira()
        self.modo_jogador = False
        self.modo_carreira = False
        self.pausado = False
        self.jogo_ativo = False
        self.fim_jogo = False
        self.remate_pov = None
        if not cj.existe:
            self.abrir_criar_jogador()
            return
        self.ecra_cj = EcraCarreiraJogador(self.screen, cj, arena=self.rink._surf, aviso=aviso)
        self.estado = "cj"

    def iniciar_jogo_cj(self):
        """Joga o próximo jogo da carreira: o clube do jogador é a equipa azul e só se controla ele."""
        cj = self.carreira_jog
        jogo = cj.camp.proximo_jogo()
        if jogo is None or not cj.vida.pode_jogar()[0]:
            return
        a = cj.atleta
        eu = a["equipa_id"]
        em_casa = jogo["casa_id"] == eu
        adversario = jogo["fora_id"] if em_casa else jogo["casa_id"]
        self._jornada_carreira = jogo["jornada"]
        self.iniciar_partida(eu, adversario, dificuldade="normal")
        self.modo_carreira = True          # o resultado conta: sem "reiniciar" nem trocar de equipa
        if not em_casa:
            self.rink.definir_equipa_casa(adversario)
        self._preparar_jogador_cj(a)
        local = "EM CASA" if em_casa else "FORA"
        self._msg_texto = f"JORNADA {jogo['jornada']}  •  {local}  •  {a['nome']}"
        self._msg_timer = 2.5
        self._msg_equipa = "azul"

    def _preparar_jogador_cj(self, a):
        """
        Põe o jogador da carreira em campo, no lugar de quem joga na mesma posição, e prende o
        controlo nele. Fica com o nome, o número e os atributos do jogador criado.
        """
        alvo = next((j for j in self.equipa_azul if getattr(j, "papel", "") == a["posicao"]),
                    self.jogador_humano)
        antigo = self.jogador_humano
        if alvo is not antigo:
            # Troca de lugar com quem ia dar a saída de bola, e fica ele com a bola
            alvo.pos_x, antigo.pos_x = antigo.pos_x, alvo.pos_x
            alvo.pos_y, antigo.pos_y = antigo.pos_y, alvo.pos_y
            for j in (alvo, antigo):
                j.rect.center = (round(j.pos_x), round(j.pos_y))
            self._trocar_humano(alvo)
            antigo.tem_bola = False
            self.bola.definir_dono(alvo)
            alvo.tem_bola = True
            self.bola.seguir_jogador(alvo)
        alvo.nome = a["nome"]
        alvo.numero = a["numero"]
        # A vida conta: forma e moral somam (ou tiram) aos atributos (vida.py)
        at = atributos_jogador(a["geral"] + self.carreira_jog.vida.modificador(), a["posicao"])
        alvo.stat_velocidade = at["velocidade"]
        alvo.stat_remate = at["remate"]
        alvo.stat_passe = at["passe"]
        alvo.stat_defesa = at["defesa"]
        self._cj_jogador = alvo
        self.modo_jogador = True
        self.stats_jogador = {k: 0 for k in ("golos", "assistencias", "remates", "passes", "recuperacoes", "perdas")}
        self._cj_dono_ant = self.bola.dono
        self._cj_assist = None
        self._cj_t = 0.0
        self._cj_pedido_cd = 0.0
        self._cj_pedido_msg = 0.0

    def _cj_contar(self, chave: str, n: int = 1):
        if self.modo_jogador and chave in self.stats_jogador:
            self.stats_jogador[chave] += n

    def _seguir_jogador_cj(self, dt: float):
        """
        Estatísticas do jogador, vendo quem tem a bola em cada frame:
          eu -> colega      = passe certo (e o colega pode dar-me uma assistência)
          eu -> adversário  = bola perdida
          adversário -> eu  = bola recuperada (desarme ou interceção)
        """
        self._cj_t += dt
        self._cj_pedido_cd = max(0.0, self._cj_pedido_cd - dt)
        self._cj_pedido_msg = max(0.0, getattr(self, "_cj_pedido_msg", 0.0) - dt)
        dono = self.bola.dono
        if not isinstance(dono, Player) or dono is self._cj_dono_ant:
            return
        eu, ant = self._cj_jogador, self._cj_dono_ant
        self._cj_dono_ant = dono
        if ant is eu:
            if dono.equipa == eu.equipa:
                self._cj_contar("passes")
                self._cj_assist = (dono, self._cj_t)
            else:
                self._cj_contar("perdas")
        elif dono is eu and ant is not None and ant.equipa != eu.equipa:
            self._cj_contar("recuperacoes")

    def _cj_golo(self, equipa: str, marcador):
        """Golo: conta o golo do jogador, ou a assistência se o último passe dele foi para quem marcou."""
        eu = self._cj_jogador
        if equipa == "azul" and eu is not None:
            if marcador is eu:
                self._cj_contar("golos")
            elif self._cj_assist and self._cj_assist[0] is marcador and self._cj_t - self._cj_assist[1] < 10:
                self._cj_contar("assistencias")
        self._cj_assist = None
        self._cj_dono_ant = None           # a saída de bola depois do golo não conta como recuperação

    def _pedir_bola(self):
        """Carreira de jogador: pede a bola ao colega que a tem (ele passa logo)."""
        eu = self._cj_jogador or self.jogador_humano
        if self._cj_pedido_cd > 0 or eu.tem_bola:
            return
        for agente in self.agentes_azul:
            if agente.jogador.tem_bola:
                agente._passar(self.bola, eu)
                self._cj_pedido_cd = 1.0
                self._cj_pedido_msg = 1.0
                sx, sy = self.rink.camera.projetar(eu.pos_x, eu.pos_y)
                self.efeitos.texto_pop("BOLA!", sx, sy - 70, (120, 230, 255), 24)
                som.tocar("passe", 0.4)
                return

    def _nota_ao_vivo(self) -> float:
        return calcular_nota(self.stats_jogador, self.golos_azul, self.golos_vermelho)

    def _resumo_jogo_cj(self) -> dict:
        eu = self._cj_jogador
        return dict(self.stats_jogador, nome=eu.nome if eu else "", nota=self._nota_ao_vivo())

    def _registar_jogo_cj(self):
        """Fim de um jogo da carreira de jogador: grava o resultado e a atuação e volta ao painel."""
        resumo = self.carreira_jog.registar_jogo(
            self.golos_azul, self.golos_vermelho, dict(self.stats_jogador),
            marcadores_eu=[m["nome"] for m in self.marcadores if m["equipa"] == "azul"],
            marcadores_adv=[m["nome"] for m in self.marcadores if m["equipa"] == "vermelho"])
        self.abrir_carreira_jogador(aviso=resumo)

    def _draw_hud_jogador(self):
        """Cartão do jogador por baixo do marcador: nome, nota ao vivo e estatísticas do jogo."""
        eu = self._cj_jogador
        if eu is None:
            return
        from carreira_jogador_menu import cor_nota
        s = self.screen
        caixa = pygame.Rect(WIDTH - 420, 12, 330, 52)       # ao lado do botão de pausa
        painel_hud = pygame.Surface(caixa.size, pygame.SRCALPHA)
        pygame.draw.rect(painel_hud, (8, 12, 26, 215), painel_hud.get_rect(), border_radius=10)
        pygame.draw.rect(painel_hud, (*self.kit_casa["principal"], 255), painel_hud.get_rect(), 2, border_radius=10)
        s.blit(painel_hud, caixa)
        nota = self._nota_ao_vivo()
        centro = (caixa.left + 30, caixa.centery)
        pygame.draw.circle(s, cor_nota(nota), centro, 21)
        txt = self.font_num.render(f"{nota:.1f}".replace(".", ","), True, (15, 20, 35))
        s.blit(txt, txt.get_rect(center=centro))
        f = self.font_num
        nome = f.render(f"{eu.numero}  {eu.nome.upper()}", True, (255, 255, 255))
        s.blit(nome, (caixa.left + 60, caixa.top + 9))
        st = self.stats_jogador
        if getattr(self, "_cj_pedido_msg", 0) > 0:
            linha, cor = "A pedir a bola...", (120, 230, 255)
        else:
            linha = (f"G {st['golos']}   A {st['assistencias']}   REM {st['remates']}   "
                     f"PAS {st['passes']}   REC {st['recuperacoes']}")
            cor = (190, 205, 235)
        s.blit(f.render(linha, True, cor), (caixa.left + 60, caixa.top + 29))

    def ir_para_menu_principal(self, casa_id: str = None, fora_id: str = None):
        self._cancelar_mira()
        self.modo_teste = False
        self.remate_pov = None
        self.modo_carreira = False
        self.modo_jogador = False
        self.pausado = False
        self.jogo_ativo = False
        self.fim_jogo = False
        if casa_id:
            self.equipa_casa_id = casa_id
        if fora_id:
            self.equipa_fora_id = fora_id
        self.estado = "menu_principal"
        self.menu_principal = MenuPrincipal(self.screen, self.equipa_casa_id, self.equipa_fora_id,
                                            arena=self.rink._surf)

    def _atualizar_equipamentos(self):
        """Recalcula os equipamentos das duas equipas e aplica-os aos jogadores."""
        self.kit_casa, self.kit_fora = definir_equipamentos(self.equipa_casa_id, self.equipa_fora_id)
        for j in self.equipa_azul:
            j.aplicar_equipamento(self.kit_casa)
        for j in self.equipa_vermelha:
            j.aplicar_equipamento(self.kit_fora)
        self.gr_azul.kit     = self.kit_casa
        self.gr_vermelho.kit = self.kit_fora

    def mudar_equipa_casa(self, equipa_id: str):
        if equipa_id == self.equipa_fora_id:
            return  # as duas equipas não podem ser iguais
        self.equipa_casa_id = equipa_id
        self.rink.definir_equipa_casa(equipa_id)
        for j, (nome, _p, num) in zip(self.equipa_azul, obter_plantel(equipa_id)["jogadores"]):
            j.equipa_id, j.nome, j.numero = equipa_id, nome, num
        self.gr_azul.nome = obter_plantel(equipa_id)["guarda_redes"]
        for a in self.agentes_azul:
            a.definir_forca(FORCA_EQUIPAS.get(equipa_id, 79))
        self._atualizar_equipamentos()
        info = obter_info_equipa(equipa_id)
        self._msg_texto = f"Equipa da Casa: {info['nome']}"
        self._msg_timer = 2.0

    def mudar_equipa_fora(self, equipa_id: str):
        if equipa_id == self.equipa_casa_id:
            return  # as duas equipas não podem ser iguais
        self.equipa_fora_id = equipa_id
        for j, (nome, _p, num) in zip(self.equipa_vermelha, obter_plantel(equipa_id)["jogadores"]):
            j.equipa_id, j.nome, j.numero = equipa_id, nome, num
        self.gr_vermelho.nome = obter_plantel(equipa_id)["guarda_redes"]
        for a in self.agentes_vermelhos:
            a.definir_forca(FORCA_EQUIPAS.get(equipa_id, 79))
        self._atualizar_equipamentos()
        info = obter_info_equipa(equipa_id)
        self._msg_texto = f"Equipa Visitante: {info['nome']}"
        self._msg_timer = 2.0

    def alternar_equipa_casa(self):
        idx = EQUIPAS_LISTA.index(self.equipa_casa_id) if self.equipa_casa_id in EQUIPAS_LISTA else 0
        prox_idx = (idx + 1) % len(EQUIPAS_LISTA)
        if EQUIPAS_LISTA[prox_idx] == self.equipa_fora_id:
            prox_idx = (prox_idx + 1) % len(EQUIPAS_LISTA)
        self.mudar_equipa_casa(EQUIPAS_LISTA[prox_idx])

    def alternar_equipa_fora(self):
        idx = EQUIPAS_LISTA.index(self.equipa_fora_id) if self.equipa_fora_id in EQUIPAS_LISTA else 0
        prox_idx = (idx + 1) % len(EQUIPAS_LISTA)
        if EQUIPAS_LISTA[prox_idx] == self.equipa_casa_id:
            prox_idx = (prox_idx + 1) % len(EQUIPAS_LISTA)
        self.mudar_equipa_fora(EQUIPAS_LISTA[prox_idx])

    # ------------------------------------------------------------------ #
    # Golos e Fim de Parte                                                #
    # ------------------------------------------------------------------ #

    def _golo(self, equipa: str):
        info_casa = obter_info_equipa(self.equipa_casa_id)
        info_fora = obter_info_equipa(self.equipa_fora_id)
        # Marcador: o último jogador da equipa que marcou a tocar na bola
        marcador = self.bola.ultimo_por_equipa.get(equipa)
        nome = marcador.nome if marcador is not None else None
        if self.modo_jogador:
            self._cj_golo(equipa, marcador)
        decorrido = (self.parte - 1) * DURACAO_PARTE + (DURACAO_PARTE - max(0.0, self.tempo_restante))
        self.marcadores.append({"equipa": equipa, "nome": nome, "minuto": int(decorrido // 60) + 1})
        if equipa == "azul":
            self.golos_azul += 1
            self._msg_texto = f"GOLO!  {info_casa['nome'].upper()}"
        else:
            self.golos_vermelho += 1
            self._msg_texto = f"GOLO!  {info_fora['nome'].upper()}"
        if nome:
            self._msg_texto += f"  •  {nome}"
        self._msg_timer = 2.5
        self._msg_equipa = equipa
        som.tocar("golo")
        # Recomeça com a bola a equipa que sofreu o golo
        saida = "vermelho" if equipa == "azul" else "azul"
        if self.efeitos.ativo:
            # Festa: câmara lenta, ecrã a tremer, confetes e "GOLO!" gigante; só depois se repõe
            kit = self.kit_casa if equipa == "azul" else self.kit_fora
            info = info_casa if equipa == "azul" else info_fora
            cam = self.rink.camera
            gx = self.rink.linha_golo_esq_x if equipa == "azul" else self.rink.linha_golo_dir_x
            sx, sy = cam.projetar(gx, self.rink.rect.centery)
            self.efeitos.golo(info["nome"], nome, kit["principal"])
            self.efeitos.confetis(sx, sy, [kit["principal"], kit.get("secundaria", (255, 255, 255)),
                                           (255, 220, 60), (255, 255, 255)], 90)
            self.efeitos.tremer(11, 0.5)
            self.efeitos.flash(0.9)
            self.efeitos.camara_lenta(1.5, 0.25)
            self._reposicao_pendente = (saida, 2.0)
        else:
            self._repor_posicoes(saida=saida)

    def _repor_posicoes(self, saida: str = "azul"):
        """Volta a pôr todos nas posições iniciais. 'saida' = equipa que fica com a bola."""
        self._cancelar_mira()
        if self.modo_teste:
            self._teste_novo_remate()
            return
        cx = RINK_X + RINK_W // 2
        cy = RINK_Y + RINK_H // 2
        self.bola.repor((cx, cy))

        posicoes_azul = [(cx + dx, cy + dy) for dx, dy, _ in FORMACAO]
        posicoes_verm = [(cx - dx, cy + dy) for dx, dy, _ in FORMACAO]
        for j, pos in zip(list(self.equipa_azul), posicoes_azul):
            j.pos_x, j.pos_y = float(pos[0]), float(pos[1])
            j.vel_x = j.vel_y = 0.0
            j.set_target(0.0, 0.0)
            j.rect.center = pos
            j.tem_bola = False

        for j, pos in zip(list(self.equipa_vermelha), posicoes_verm):
            j.pos_x, j.pos_y = float(pos[0]), float(pos[1])
            j.vel_x = j.vel_y = 0.0
            j.set_target(0.0, 0.0)
            j.rect.center = pos
            j.tem_bola = False

        # Dá a bola à equipa que faz a saída (humano, ou o primeiro avançado vermelho)
        if saida == "azul":
            dono = self.jogador_humano
        else:
            dono = list(self.equipa_vermelha)[0]
        self.bola.definir_dono(dono)
        dono.tem_bola = True
        self.bola.seguir_jogador(dono)
        self._dono_anterior = dono          # a saída de bola não conta como "roubo"
        for j in self.todos_jogadores:
            j._bloqueio_desarme = 0.0
            j._estado_action = None
        dono._cooldown_desarme = 1.0

        # Repor guarda-redes
        self.gr_azul.pos_y     = float(self.rink.rect.centery)
        self.gr_vermelho.pos_y = float(self.rink.rect.centery)

    def _fim_de_parte(self):
        if self.parte == 1:
            self.parte = 2
            self.tempo_restante = float(DURACAO_PARTE)
            self._msg_texto = "Intervalo  —  2.ª Parte"
            self._msg_timer = 3.0
            som.tocar("apito_longo")
            self._repor_posicoes(saida="vermelho")
        else:
            self._cancelar_mira()
            self.jogo_ativo = False
            self.fim_jogo   = True
            som.tocar("apito_final")
            self.ecra_fim   = EcraFimJogo(self.screen, modo_carreira=self.modo_carreira,
                                          jornada=self._jornada_carreira,
                                          jogador=self._resumo_jogo_cj() if self.modo_jogador else None)

    # ================================================================== #
    # Desenho Principal                                                    #
    # ================================================================== #

    def draw(self):
        if self.estado == "menu_principal":
            self.menu_principal.draw()
        elif self.estado == "menu_selecao":
            self.menu.draw()
        elif self.estado == "carreira_escolha":
            self.ecra_carreira.draw()
        elif self.estado == "carreira":
            self.ecra_campeonato.draw()
        elif self.estado == "cj_criar":
            self.ecra_cj_criar.draw()
        elif self.estado == "cj":
            self.ecra_cj.draw()
        elif self.estado == "controlos":
            if self._origem_controlos == "pausa":
                self._draw_cena()
                self.ecra_controlos.draw(por_cima_do_jogo=True)
            else:
                self.ecra_controlos.draw()
        elif self.remate_pov is not None:
            self.remate_pov.draw()
        else:
            self._draw_cena()
            if self.pausado:
                self.menu_pausa.draw(self)
            elif self.fim_jogo:
                self.ecra_fim.draw(self)
        self._transicao()
        pygame.display.flip()

    # Duração da transição entre ecrãs (segundos)
    _DURACAO_TRANSICAO = 0.28

    def _chave_ecra(self):
        """Identifica o ecrã que está à vista; quando muda, faz-se uma transição."""
        ecras = {"menu_principal": "menu_principal", "menu_selecao": "menu", "carreira_escolha": "ecra_carreira",
                 "carreira": "ecra_campeonato", "cj_criar": "ecra_cj_criar", "cj": "ecra_cj",
                 "controlos": "ecra_controlos"}
        obj = getattr(self, ecras.get(self.estado, ""), None)
        return (self.estado, id(obj), self.pausado, self.fim_jogo, self.remate_pov is not None)

    def _transicao(self):
        """
        Transição suave entre ecrãs: a imagem do ecrã anterior desaparece aos poucos por cima
        do novo (fade de 0,28 s). Guarda-se uma cópia de cada frame para isso.
        """
        if self._DURACAO_TRANSICAO <= 0:          # transições desligadas (capturas de ecrã automáticas)
            return
        agora = pygame.time.get_ticks() / 1000
        chave = self._chave_ecra()
        anterior = getattr(self, "_frame_anterior", None)
        if chave != getattr(self, "_chave_anterior", None) and anterior is not None:
            self._fade = (anterior.copy(), agora)
        self._chave_anterior = chave
        fade = getattr(self, "_fade", None)
        if fade is not None:
            k = (agora - fade[1]) / self._DURACAO_TRANSICAO
            if k >= 1:
                self._fade = None
            else:
                img = fade[0]
                img.set_alpha(int(255 * (1 - k) ** 2))
                self.screen.blit(img, (0, 0))
        if getattr(self, "_frame_anterior", None) is None or self._frame_anterior.get_size() != self.screen.get_size():
            self._frame_anterior = self.screen.copy()
        else:
            self._frame_anterior.blit(self.screen, (0, 0))

    def _draw_cena(self):
        """Desenha o ringue, os jogadores e o HUD (sem os menus por cima)."""
        self.screen.fill(COR_FUNDO)

        # 1. Ringue e Balizas traseiras
        self.rink.draw(self.screen)

        cam = self.rink.camera

        # 2. Raspas dos patins (ficam no chão, por baixo dos jogadores)
        for j in self.todos_jogadores:
            j.draw_rastos(self.screen, cam)

        # 3. Jogadores, guarda-redes, bola e balizas, por ordem de profundidade:
        #    quem está mais ao fundo do campo é desenhado primeiro (fica por trás).
        r = self.rink
        atores = sorted(list(self.todos_jogadores) + list(self.grupo_gr), key=lambda s: s.pos_y)

        b = self.bola
        bola_na_rede = (r.baliza_topo_y <= b.pos_y <= r.baliza_base_y and
                        (b.pos_x < r.linha_golo_esq_x or b.pos_x > r.linha_golo_dir_x))

        # A bola também entra na ordem de profundidade: se passar atrás de um jogador ou do
        # guarda-redes, fica tapada por ele (antes era sempre desenhada por cima de todos).
        # A bola no stick conta um pouco mais à frente, para ficar à frente de quem a conduz.
        def profundidade(s):
            if s is b:
                return b.pos_y + (8 if b.dono is not None else 0)
            return s.pos_y

        itens = list(atores) + ([] if bola_na_rede else [b])
        itens.sort(key=profundidade)
        # Atrás das balizas = os pés estão mais ao fundo do que o poste de cima
        atras  = [a for a in itens if profundidade(a) < r.baliza_topo_y]
        frente = [a for a in itens if profundidade(a) >= r.baliza_topo_y]

        def desenhar(a):
            if a is b:
                self._desenhar_bola(cam)
            else:
                self._desenhar_ator(a, cam)

        for a in atras:
            desenhar(a)
        if bola_na_rede:
            self._desenhar_bola(cam)

        # 4. Travessas, postes da frente e rede lateral das balizas
        self.rink.draw_frente(self.screen)

        for a in frente:
            desenhar(a)

        # 5. Indicadores por cima dos jogadores (usam o retângulo no ecrã)
        for a in atores:
            guardado = a.rect
            a.rect = getattr(a, "rect_ecra", a.rect)
            if a in self.grupo_gr:
                a.draw_extra(self.screen, self.font_num)
            else:
                a.draw_extra(self.screen, self.font_num, self.show_debug)
            a.rect = guardado

        # Estilo arcade: partículas por cima do campo e o ecrã a tremer (o marcador não treme)
        if self.efeitos.ativo:
            self.efeitos.desenhar_mundo(self.screen)
            dx, dy = self.efeitos.deslocamento()
            if dx or dy:
                copia = self.screen.copy()
                self.screen.fill(COR_FUNDO)
                self.screen.blit(copia, (dx, dy))

        # 6. Mira e marcador superior
        self._draw_mira()
        self.hud.draw_top_bar(self.screen, self)
        self.hud.draw_foul_banner(self.screen, self)

        # 7. Painel Inferior (Mini-mapa, Cartão de Jogador e Controlos)
        self.hud.draw_bottom_panel(self.screen, self)
        if self.modo_jogador:
            self._draw_hud_jogador()

        # 8. Mensagens (golo, intervalo, ...)
        golo_arcade = self.efeitos.ativo and self._msg_texto.startswith("GOLO")
        if self._msg_timer > 0 and not self.fim_jogo and not golo_arcade:
            self._draw_mensagem(self._msg_texto)
        self.efeitos.desenhar_ui(self.screen)
        if self.show_debug:
            self._draw_debug()

    # Distância (no mundo) entre o centro do jogador e os patins: a câmara põe os patins no chão
    _PES = 22

    def _desenhar_ator(self, a, cam):
        """Desenha um jogador/guarda-redes no ecrã: posição e tamanho dados pela câmara."""
        k = cam.escala(a.pos_y)
        img = a.image
        w, h = img.get_size()
        if abs(k - 1.0) > 0.01:
            img = pygame.transform.smoothscale(img, (max(1, round(w * k)), max(1, round(h * k))))
        sx, sy = cam.projetar(a.pos_x, a.pos_y)
        rect = img.get_rect()
        rect.centerx = round(sx)
        # Os patins (centro da imagem + _PES) ficam no ponto do chão projetado
        rect.top = round(sy - (h / 2 + self._PES) * k)
        if self.efeitos.ativo:
            # Contorno grosso, como num desenho animado
            self.screen.blit(contornar(img, 2), rect.move(-2, -2))
        else:
            self.screen.blit(img, rect)
        # Para os indicadores (triângulo, "GR") usamos só a parte visível do sprite
        a.rect_ecra = img.get_bounding_rect().move(rect.topleft)

    def _desenhar_bola(self, cam):
        b = self.bola
        k = cam.fator(b.pos_y) * 1.1      # a bola cresce menos do que os jogadores
        img = b.image
        if abs(k - 1.0) > 0.01:
            img = pygame.transform.smoothscale(
                img, (max(1, round(img.get_width() * k)), max(1, round(img.get_height() * k))))
        sx, sy = cam.projetar(b.pos_x, b.pos_y)
        # Sombra suave no chão, um pouco abaixo e à direita (a luz vem de cima, à esquerda)
        sombra = sombra_suave(max(4, round(20 * k)), max(2, round(8 * k)), 120)
        self.screen.blit(sombra, sombra.get_rect(center=(round(sx + 2 * k), round(sy + 5 * k))))
        self.efeitos.bola(sx, sy, b.vel.length(), b.dono is None)
        if self.efeitos.ativo:
            self.efeitos.desenhar_rasto(self.screen)
            img = contornar(img, 1)
        self.screen.blit(img, img.get_rect(center=(round(sx), round(sy))))

    def _draw_mensagem(self, texto: str):
        """Faixa horizontal a meio do ringue; nos golos usa as cores da equipa que marcou."""
        cy = RINK_Y + RINK_H // 2
        altura = 96
        cor = (20, 40, 90)
        if texto.startswith("GOLO"):
            kit = self.kit_casa if getattr(self, "_msg_equipa", "azul") == "azul" else self.kit_fora
            cor = kit["principal"]

        # Entra a deslizar e desvanece no fim
        alpha = int(225 * min(1.0, self._msg_timer / 0.4))
        faixa = pygame.Surface((WIDTH, altura), pygame.SRCALPHA)
        for y in range(altura):
            t = abs(y - altura / 2) / (altura / 2)
            c = misturar(cor, (5, 8, 18), 0.25 + 0.5 * t)
            pygame.draw.line(faixa, (*c, alpha), (0, y), (WIDTH, y))
        pygame.draw.line(faixa, (*COR_DESTAQUE, alpha), (0, 0), (WIDTH, 0), 3)
        pygame.draw.line(faixa, (*COR_DESTAQUE, alpha), (0, altura - 3), (WIDTH, altura - 3), 3)
        self.screen.blit(faixa, (0, cy - altura // 2))

        cor_txt = cor_texto_sobre(misturar(cor, (5, 8, 18), 0.25))
        for c, off in [((0, 0, 0), 3), (cor_txt, 0)]:
            t = self.font_big.render(texto, True, c)
            self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2 + off,
                                 cy - t.get_height() // 2 + off))

    def _draw_debug(self):
        fps = self.font_num.render(f"FPS: {self.clock.get_fps():.0f}", True, (255, 255, 100))
        self.screen.blit(fps, (WIDTH - 120, HUD_H + 8))
        dono = self.bola.dono.nome if self.bola.dono else "livre"
        db = self.font_num.render(f"Bola: {dono}", True, (200, 255, 200))
        self.screen.blit(db, (WIDTH - 120, HUD_H + 24))

    def _draw_mira(self):
        """Desenha a linha de mira e barra de força estilo 8 Ball Pool."""
        if not self._mira_ativa or not self.jogador_humano.tem_bola:
            return

        screen = self.screen
        cam = self.rink.camera
        bx = self.jogador_humano.pos_x
        by = self.jogador_humano.pos_y
        direc = self._mira_direcao

        # ── 1. Linha tracejada de trajetória ──────────────────────────────
        comprimento_linha = 220
        num_tracos = 14
        taco = comprimento_linha / (num_tracos * 2)
        surf_linha = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        for i in range(num_tracos):
            t_ini = (i * 2)       * taco
            t_fim = (i * 2 + 1.2) * taco
            px_ini = bx + direc.x * t_ini
            py_ini = by + direc.y * t_ini
            px_fim = bx + direc.x * t_fim
            py_fim = by + direc.y * t_fim
            # Cor varia com a força: verde (fraco) → amarelo → vermelho (forte)
            f = self._mira_forca
            r = int(255 * min(f * 2, 1.0))
            g = int(255 * min((1 - f) * 2, 1.0))
            cor_linha = (r, g, 30, 210)
            pygame.draw.line(surf_linha, cor_linha,
                             cam.projetar(px_ini, py_ini),
                             cam.projetar(px_fim, py_fim), 3)

        screen.blit(surf_linha, (0, 0))

        # ── 2. Círculo de mira no fim da linha ────────────────────────────
        alvo = cam.projetar(bx + direc.x * comprimento_linha, by + direc.y * comprimento_linha)
        pygame.draw.circle(screen, (255, 255, 100, 180), (round(alvo[0]), round(alvo[1])), 8, 2)

        # ── 3. Barra de Força (estilo 8 Ball Pool) ────────────────────────
        ex, ey = cam.projetar(bx, by)
        bar_x  = round(ex) - 60
        bar_y  = round(ey) + 14
        bar_w  = 120
        bar_h  = 14

        # Fundo da barra
        pygame.draw.rect(screen, (20, 20, 20), (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4), border_radius=8)
        pygame.draw.rect(screen, (50, 50, 60), (bar_x, bar_y, bar_w, bar_h), border_radius=6)

        # Preenchimento da barra com gradiente de cor
        fill_w = int(bar_w * self._mira_forca)
        if fill_w > 0:
            f = self._mira_forca
            r = int(255 * min(f * 2, 1.0))
            g = int(255 * min((1 - f) * 2, 1.0))
            pygame.draw.rect(screen, (r, g, 20), (bar_x, bar_y, fill_w, bar_h), border_radius=6)

        # Borda da barra
        pygame.draw.rect(screen, (200, 200, 200), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=6)

        # Texto "FORÇA"
        f_txt = fontes.SysFont("Arial", 11, bold=True)
        pct = int(self._mira_forca * 100)
        t = f_txt.render(f"FORÇA  {pct}%", True, (255, 255, 255))
        screen.blit(t, (bar_x + bar_w // 2 - t.get_width() // 2, bar_y - 18))

        # ── 4. Instrução ──────────────────────────────────────────────────
        fi = fontes.SysFont("Arial", 13, bold=True)
        ti = fi.render("[X] ou Clique para rematar  •  [ESC] para cancelar", True, (220, 220, 100))
        screen.blit(ti, (WIDTH // 2 - ti.get_width() // 2, HEIGHT - 30))
