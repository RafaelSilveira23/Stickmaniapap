# -*- coding: utf-8 -*-
"""vida.py - a vida do jogador na carreira de jogador (escolhas ao estilo dos jogos de "simulação de vida").

Além do hóquei, o jogador tem uma vida: idade, dinheiro e cinco valores de 0 a 100:
  forma      - condição física (cansaço). Pouca forma = joga pior e lesiona-se mais
  moral      - felicidade. Moral alta = joga melhor
  treinador  - confiança do treinador. Abaixo de 25 vai para o banco no jogo seguinte
  fama       - quanto o público o conhece. Ajuda a ter propostas de outros clubes e patrocínios
  estudos    - a escola (e depois a universidade). Não conta no hóquei, mas conta na vida

Depois de cada jornada:
  1. a vida muda sozinha: salário, cansaço do jogo, moral do resultado, confiança do treinador pela nota;
  2. pode haver uma lesão (mais provável com pouca forma);
  3. aparece um EVENTO com escolhas (festa na véspera do jogo, teste na escola, patrocínio, ...).
Em cada semana pode-se fazer uma ATIVIDADE (treino extra, descansar, estudar, sair com os amigos, ...).
Tudo o que acontece fica no DIÁRIO.

As escolhas mexem no hóquei de quatro formas:
  • modificador() soma-se aos atributos do jogador nos jogos (forma e moral);
  • lesões e banco: o jogador não joga (o jogo da equipa é simulado sem ele);
  • alguns eventos mudam o geral (treino extra, preparador físico, seleção nacional);
  • a fama baixa a nota média precisa para haver propostas no fim da época.
"""
import json
import random

VALORES = ("forma", "moral", "treinador", "fama", "estudos")
NOME_VALOR = {"forma": "Forma", "moral": "Moral", "treinador": "Treinador", "fama": "Fama",
              "estudos": "Estudos", "dinheiro": "Dinheiro", "geral": "Geral", "lesao": "Lesão"}
INICIO = {"idade": 17, "forma": 70, "moral": 65, "treinador": 50, "fama": 10, "estudos": 60, "dinheiro": 300}

_ESQUEMA_VIDA = """
CREATE TABLE IF NOT EXISTS vida (
    atleta_id        INTEGER PRIMARY KEY REFERENCES atleta(id),
    idade            INTEGER NOT NULL CHECK (idade BETWEEN 14 AND 60),
    forma            INTEGER NOT NULL CHECK (forma BETWEEN 0 AND 100),
    moral            INTEGER NOT NULL CHECK (moral BETWEEN 0 AND 100),
    treinador        INTEGER NOT NULL CHECK (treinador BETWEEN 0 AND 100),
    fama             INTEGER NOT NULL CHECK (fama BETWEEN 0 AND 100),
    estudos          INTEGER NOT NULL CHECK (estudos BETWEEN 0 AND 100),
    dinheiro         INTEGER NOT NULL CHECK (dinheiro >= 0),
    lesao            INTEGER NOT NULL DEFAULT 0 CHECK (lesao >= 0),   -- jornadas que ainda falta recuperar
    banco            INTEGER NOT NULL DEFAULT 0,                      -- 1 = suplente no próximo jogo
    evento_pendente  TEXT,                                            -- id do evento à espera de escolha
    atividade_feita  INTEGER NOT NULL DEFAULT 0                       -- 1 = já fez a atividade desta semana
);
CREATE TABLE IF NOT EXISTS diario (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    atleta_id  INTEGER NOT NULL REFERENCES atleta(id),
    epoca      INTEGER NOT NULL,
    jornada    INTEGER NOT NULL,
    evento     TEXT,
    texto      TEXT NOT NULL,
    efeitos    TEXT NOT NULL DEFAULT '{}'
);
"""


# ====================================================================== #
# Eventos: cada um tem opções; cada opção tem efeitos e, às vezes, sorte  #
#   efeitos: forma, moral, treinador, fama, estudos (0-100), dinheiro (€), #
#            geral (soma ao geral do jogador), lesao (jornadas sem jogar)  #
#   custo  : dinheiro que é preciso ter para escolher a opção              #
#   sorte  : (probabilidade, efeitos extra, texto extra)                   #
#   cond   : quando o evento pode aparecer (v = vida, a = atleta)          #
# ====================================================================== #
EVENTOS = [
    {"id": "festa", "titulo": "Festa na véspera do jogo",
     "texto": "O teu melhor amigo faz anos e há festa lá em casa. Amanhã tens jogo.",
     "opcoes": [
         {"texto": "Vou e fico até de manhã", "efeitos": {"moral": 14, "forma": -18, "treinador": -6},
          "resultado": "Foi uma noite épica, mas acordaste de rastos.",
          "sorte": (0.2, {"lesao": 1}, "A dançar, torceste o tornozelo!")},
         {"texto": "Vou, mas volto cedo", "efeitos": {"moral": 7, "forma": -4},
          "resultado": "Deste os parabéns, comeste bolo e às 23h estavas na cama."},
         {"texto": "Fico em casa a descansar", "efeitos": {"moral": -5, "forma": 6, "treinador": 2},
          "resultado": "Os teus amigos ficaram um bocado chateados, mas estás fresco."}]},
    {"id": "teste", "titulo": "Teste de Matemática",
     "texto": "Amanhã tens teste de Matemática e ainda não abriste o livro. O treino é à mesma hora do estudo.",
     "cond": lambda v, a: v["idade"] <= 19,
     "opcoes": [
         {"texto": "Falto ao treino para estudar", "efeitos": {"estudos": 14, "treinador": -7},
          "resultado": "Tiveste 16 valores! O treinador não gostou muito da falta."},
         {"texto": "Treino e estudo à noite", "efeitos": {"estudos": 6, "forma": -8},
          "resultado": "Dormiste pouco, mas safaste-te com um 12."},
         {"texto": "Vou ao treino e logo se vê", "efeitos": {"estudos": -10, "treinador": 3},
          "resultado": "Tiveste 7 valores. Os teus pais não ficaram nada contentes.",
          "sorte": (0.3, {"moral": -6}, "Ficaste de castigo ao fim de semana.")}]},
    {"id": "patrocinio", "titulo": "Proposta de patrocínio",
     "texto": "Uma marca de bebidas energéticas quer pagar-te para publicares fotos com a lata.",
     "cond": lambda v, a: v["fama"] >= 15,
     "opcoes": [
         {"texto": "Aceito (750 €)", "efeitos": {"dinheiro": 750, "fama": 6, "treinador": -3},
          "resultado": "Ganhaste dinheiro, mas o treinador acha que te estás a distrair."},
         {"texto": "Recuso, quero focar-me no hóquei", "efeitos": {"treinador": 4, "moral": -2},
          "resultado": "O treinador soube e gostou da tua atitude."}]},
    {"id": "redes", "titulo": "Polémica nas redes sociais",
     "texto": "Um adepto rival goza contigo num vídeo que está a ficar viral.",
     "opcoes": [
         {"texto": "Respondo à letra", "efeitos": {"fama": 10, "treinador": -10, "moral": 4},
          "resultado": "O teu vídeo teve milhares de visualizações... e o clube abriu um processo disciplinar."},
         {"texto": "Respondo com humor", "efeitos": {"fama": 7, "moral": 5},
          "resultado": "Toda a gente achou piada. Ganhaste seguidores."},
         {"texto": "Ignoro", "efeitos": {"moral": -3},
          "resultado": "Passou ao fim de dois dias."}]},
    {"id": "carro", "titulo": "Carro novo?",
     "texto": "Tiraste a carta! Viste um carro em segunda mão por 4 000 €.",
     "cond": lambda v, a: v["idade"] >= 18 and v["dinheiro"] >= 4000,
     "opcoes": [
         {"texto": "Compro o carro", "efeitos": {"dinheiro": -4000, "moral": 15, "fama": 3}, "custo": 4000,
          "resultado": "Já não precisas de boleia para os treinos!"},
         {"texto": "Guardo o dinheiro", "efeitos": {"moral": -2},
          "resultado": "Continuas a ir de autocarro, mas a conta bancária agradece."}]},
    {"id": "avo", "titulo": "A tua avó está doente",
     "texto": "A tua avó foi para o hospital. O jogo é no dia da visita.",
     "opcoes": [
         {"texto": "Vou visitá-la e falto ao jogo", "efeitos": {"moral": 6, "treinador": -12, "lesao": 0},
          "resultado": "Ela ficou muito feliz. O treinador compreendeu... mais ou menos.", "falta_jogo": True},
         {"texto": "Vou ao jogo e dedico-lhe um golo", "efeitos": {"moral": -4, "treinador": 4},
          "resultado": "Ela viu o jogo na televisão do hospital."}]},
    {"id": "treinador_extra", "titulo": "O treinador chama-te",
     "texto": "O treinador quer que fiques depois do treino a trabalhar o remate.",
     "opcoes": [
         {"texto": "Claro, fico o tempo que for preciso", "efeitos": {"geral": 0.8, "forma": -8, "treinador": 8},
          "resultado": "Uma hora de remates. Sentes que estás melhor."},
         {"texto": "Hoje não posso", "efeitos": {"treinador": -6},
          "resultado": "Ele não disse nada, mas reparaste na cara dele."}]},
    {"id": "selecao", "titulo": "Convocatória da seleção!",
     "texto": "Foste convocado para a seleção nacional de sub-20!",
     "cond": lambda v, a: a["geral"] >= 72 and v["fama"] >= 35,
     "opcoes": [
         {"texto": "Aceito, é um sonho!", "efeitos": {"fama": 15, "moral": 12, "geral": 1.0, "forma": -10},
          "resultado": "Jogaste com os melhores do país. Que experiência!"},
         {"texto": "Recuso para descansar", "efeitos": {"forma": 10, "fama": -5, "moral": -6},
          "resultado": "Descansaste, mas ficaste a pensar no que perdeste."}]},
    {"id": "namoro", "titulo": "Primeiro encontro",
     "texto": "Uma pessoa de quem gostas convidou-te para jantar no sábado. Domingo de manhã há jogo.",
     "opcoes": [
         {"texto": "Vou ao jantar", "efeitos": {"moral": 15, "dinheiro": -40, "forma": -3}, "custo": 40,
          "resultado": "Correu muito bem. Estás nas nuvens!"},
         {"texto": "Proponho outro dia", "efeitos": {"moral": 4},
          "resultado": "Ficou combinado para a semana. Boa!"}]},
    {"id": "lesao_leve", "titulo": "Dores no joelho",
     "texto": "Sentes uma dor no joelho desde o último treino.",
     "opcoes": [
         {"texto": "Vou ao fisioterapeuta (120 €)", "efeitos": {"dinheiro": -120, "forma": 6}, "custo": 120,
          "resultado": "Era só uma inflamação. Uns dias de gelo e estás pronto."},
         {"texto": "Jogo na mesma", "efeitos": {"treinador": 3},
          "resultado": "Aguentaste...",
          "sorte": (0.45, {"lesao": 2, "moral": -8}, "...até que o joelho cedeu. Duas jornadas de fora!")}]},
    {"id": "entrevista", "titulo": "Entrevista na televisão",
     "texto": "Um canal desportivo quer entrevistar-te sobre a época do clube.",
     "cond": lambda v, a: v["fama"] >= 25,
     "opcoes": [
         {"texto": "Elogio a equipa e o treinador", "efeitos": {"treinador": 8, "fama": 4},
          "resultado": "Resposta de profissional. O balneário gostou."},
         {"texto": "Digo que mereço jogar mais", "efeitos": {"fama": 9, "treinador": -12},
          "resultado": "A frase foi manchete. O treinador não achou piada."}]},
    {"id": "caridade", "titulo": "Torneio solidário",
     "texto": "Pedem-te para ires a um torneio de hóquei para crianças, no teu dia de folga.",
     "opcoes": [
         {"texto": "Vou e dou autógrafos", "efeitos": {"fama": 6, "moral": 8, "forma": -4},
          "resultado": "As crianças adoraram. Saíste no jornal da terra."},
         {"texto": "Prefiro descansar", "efeitos": {"forma": 5},
          "resultado": "Ficaste no sofá a ver séries."}]},
    {"id": "jogo_consola", "titulo": "Noite de consola",
     "texto": "Os teus colegas de equipa vão fazer um torneio de videojogos até tarde.",
     "opcoes": [
         {"texto": "Jogo até às 3 da manhã", "efeitos": {"moral": 8, "forma": -10},
          "resultado": "Ganhaste o torneio! Mas o despertador custou."},
         {"texto": "Jogo uma hora e vou dormir", "efeitos": {"moral": 4, "treinador": 2},
          "resultado": "Equilíbrio perfeito."}]},
    {"id": "dieta", "titulo": "Nutricionista do clube",
     "texto": "O nutricionista do clube propõe-te um plano de alimentação mais rigoroso.",
     "opcoes": [
         {"texto": "Sigo o plano à risca", "efeitos": {"forma": 12, "moral": -5},
          "resultado": "Adeus hambúrgueres... mas sentes-te mais leve no rinque."},
         {"texto": "Sigo mais ou menos", "efeitos": {"forma": 4},
          "resultado": "Pelo menos trocaste os refrigerantes por água."}]},
    {"id": "aposta", "titulo": "Um conhecido propõe uma aposta",
     "texto": "Um conhecido diz que ganhas 500 € se apostares contra a tua própria equipa.",
     "opcoes": [
         {"texto": "Nem pensar! E aviso o clube", "efeitos": {"treinador": 10, "fama": 4, "moral": 3},
          "resultado": "O clube agradeceu a tua honestidade."},
         {"texto": "Recuso e não digo nada", "efeitos": {},
          "resultado": "Fingiste que nunca aconteceu."}]},
    {"id": "universidade", "titulo": "Exames nacionais",
     "texto": "Estás no 12.º ano e os exames estão à porta. As semanas de estudo coincidem com o fim do campeonato.",
     "cond": lambda v, a: v["idade"] == 18,
     "opcoes": [
         {"texto": "Estudo a sério", "efeitos": {"estudos": 18, "forma": -6, "treinador": -4},
          "resultado": "Preparaste-te bem para os exames."},
         {"texto": "O hóquei vem primeiro", "efeitos": {"estudos": -12, "treinador": 6},
          "resultado": "Treinaste todos os dias. Os exames... logo se vê."}]},
    {"id": "investir", "titulo": "Investir as poupanças?",
     "texto": "Um amigo diz que tem um negócio de camisolas de hóquei personalizadas e precisa de 1 000 €.",
     "cond": lambda v, a: v["dinheiro"] >= 1000,
     "opcoes": [
         {"texto": "Invisto 1 000 €", "efeitos": {"dinheiro": -1000}, "custo": 1000,
          "resultado": "Agora é esperar.",
          "sorte": (0.5, {"dinheiro": 2500, "moral": 10}, "O negócio correu bem: recebeste 2 500 €!")},
         {"texto": "Não arrisco", "efeitos": {},
          "resultado": "O dinheiro continua na conta."}]},
]
EVENTOS_POR_ID = {e["id"]: e for e in EVENTOS}

# Atividades: uma por semana (por jornada)
ATIVIDADES = [
    {"id": "treino_extra", "nome": "Treino extra", "descricao": "Treinas mais uma hora com a bola",
     "efeitos": {"geral": 0.5, "forma": -8, "treinador": 5}},
    {"id": "ginasio", "nome": "Ginásio", "descricao": "Trabalho físico com o preparador",
     "efeitos": {"forma": 10, "dinheiro": -30}, "custo": 30},
    {"id": "descansar", "nome": "Descansar", "descricao": "Dormir bem e recuperar",
     "efeitos": {"forma": 15, "moral": 2}},
    {"id": "amigos", "nome": "Sair com os amigos", "descricao": "Cinema, jantar e conversa",
     "efeitos": {"moral": 12, "forma": -4, "dinheiro": -40}, "custo": 40},
    {"id": "estudar", "nome": "Estudar", "descricao": "Pôr a matéria da escola em dia",
     "efeitos": {"estudos": 12, "moral": -3}},
    {"id": "redes", "nome": "Publicar nas redes", "descricao": "Vídeos de treinos e golos",
     "efeitos": {"fama": 5},
     "sorte": (0.15, {"fama": 6, "treinador": -8, "moral": -4}, "Uma frase tua foi mal interpretada... polémica!")},
    {"id": "familia", "nome": "Tempo com a família", "descricao": "Almoço de domingo em casa dos avós",
     "efeitos": {"moral": 9, "estudos": 2}},
    {"id": "fisioterapia", "nome": "Fisioterapia", "descricao": "Recuperar mais depressa da lesão",
     "efeitos": {"lesao": -1, "dinheiro": -150}, "custo": 150, "so_lesionado": True},
]


def _limitar(v):
    return max(0, min(100, int(round(v))))


class Vida:
    """A vida do jogador da carreira (cj = CarreiraJogador)."""

    def __init__(self, cj, rnd=None):
        self.cj = cj
        self.con = cj.con
        self.rnd = rnd or random.Random()
        with self.con:
            self.con.executescript(_ESQUEMA_VIDA)

    # ------------------------------------------------------------------ #
    @property
    def _atleta_id(self):
        a = self.cj.atleta
        return a["id"] if a else None

    def garantir(self):
        """Cria a vida do jogador atual (se ainda não existir)."""
        aid = self._atleta_id
        if aid is None:
            return
        with self.con:
            self.con.execute(
                "INSERT OR IGNORE INTO vida (atleta_id, idade, forma, moral, treinador, fama, estudos, dinheiro) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (aid, INICIO["idade"], INICIO["forma"], INICIO["moral"], INICIO["treinador"], INICIO["fama"],
                 INICIO["estudos"], INICIO["dinheiro"]))

    @property
    def estado(self) -> dict:
        self.garantir()
        l = self.con.execute("SELECT * FROM vida WHERE atleta_id = ?", (self._atleta_id,)).fetchone()
        return dict(l)

    def modificador(self) -> float:
        """
        Quanto a vida soma aos atributos do jogador nos jogos (entre −8 e +5):
          (forma − 60) / 8 + (moral − 60) / 12
        Forma 90 e moral 80 dão +5; forma 30 e moral 40 dão −5,4.
        """
        v = self.estado
        return max(-8.0, min(5.0, (v["forma"] - 60) / 8 + (v["moral"] - 60) / 12))

    def pode_jogar(self) -> tuple[bool, str]:
        v = self.estado
        if v["lesao"] > 0:
            return False, f"LESIONADO ({v['lesao']} jornada{'s' if v['lesao'] > 1 else ''})"
        if v["banco"]:
            return False, "NO BANCO (o treinador não confia em ti)"
        return True, ""

    # ------------------------------------------------------------------ #
    def aplicar(self, efeitos: dict) -> dict:
        """Aplica os efeitos à vida (e ao geral do jogador). Devolve o que mudou de facto."""
        v = self.estado
        mudou = {}
        for k, d in efeitos.items():
            if not d:
                continue
            if k in VALORES:
                novo = _limitar(v[k] + d)
                if novo != v[k]:
                    mudou[k] = novo - v[k]
                    v[k] = novo
            elif k == "dinheiro":
                novo = max(0, v["dinheiro"] + int(d))
                mudou[k] = novo - v["dinheiro"]
                v["dinheiro"] = novo
            elif k == "lesao":
                novo = max(0, v["lesao"] + int(d))
                if novo != v["lesao"]:
                    mudou[k] = novo - v["lesao"]
                    v["lesao"] = novo
            elif k == "geral":
                a = self.cj.atleta
                from carreira_jogador import GERAL_MIN, GERAL_MAX
                novo = round(max(GERAL_MIN, min(GERAL_MAX, a["geral"] + d)), 2)
                mudou[k] = round(novo - a["geral"], 2)
                self.con.execute("UPDATE atleta SET geral = ? WHERE id = ?", (novo, a["id"]))
        self.con.execute(
            "UPDATE vida SET forma = ?, moral = ?, treinador = ?, fama = ?, estudos = ?, dinheiro = ?, lesao = ? "
            "WHERE atleta_id = ?", (v["forma"], v["moral"], v["treinador"], v["fama"], v["estudos"], v["dinheiro"],
                                    v["lesao"], self._atleta_id))
        return mudou

    def registar(self, texto: str, efeitos: dict | None = None, evento: str | None = None):
        camp = self.cj.camp
        self.con.execute(
            "INSERT INTO diario (atleta_id, epoca, jornada, evento, texto, efeitos) VALUES (?, ?, ?, ?, ?, ?)",
            (self._atleta_id, camp.info["epoca"], camp.ultima_jornada_jogada(), evento, texto,
             json.dumps(efeitos or {}, ensure_ascii=False)))

    def diario(self, n: int = 8) -> list:
        """Últimas n entradas do diário (a mais recente primeiro)."""
        linhas = self.con.execute("SELECT * FROM diario WHERE atleta_id = ? ORDER BY id DESC LIMIT ?",
                                  (self._atleta_id, n)).fetchall()
        return [dict(l, efeitos=json.loads(l["efeitos"])) for l in linhas]

    # ------------------------------------------------------------------ #
    # Depois de cada jornada                                               #
    # ------------------------------------------------------------------ #
    def depois_do_jogo(self, jogou: bool, nota: float | None, g_eu: int, g_adv: int, golos: int = 0) -> list:
        """
        O que muda na vida depois de uma jornada. Devolve uma lista de frases (para o cartão do jogo).
        Chamado dentro da transação que grava o jogo.
        """
        from carreira import FORCA_EQUIPAS
        rnd = self.rnd
        v = self.estado
        frases = []
        a = self.cj.atleta
        salario = int(FORCA_EQUIPAS.get(a["equipa_id"], 75) * 4 + v["fama"] * 3)
        # Cada valor volta aos poucos ao normal (forma 75, moral 60, treinador 50) e o jogo cansa
        efeitos = {"dinheiro": salario,
                   "forma": (-3 if jogou else 4) + round((75 - v["forma"]) * 0.2)}
        efeitos["moral"] = (6 if g_eu > g_adv else (-6 if g_eu < g_adv else 0)) + round((60 - v["moral"]) * 0.1)
        if jogou and nota is not None:
            efeitos["moral"] += 5 if nota >= 7.5 else (-5 if nota < 5.5 else 0)
            efeitos["treinador"] = round((nota - 6.6) * 4 + (50 - v["treinador"]) * 0.12)
            efeitos["fama"] = golos + (2 if nota >= 8 else 0) - 1
        else:
            efeitos["fama"] = -1
        if v["lesao"] > 0:
            efeitos["lesao"] = -1                       # mais uma jornada de recuperação
        self.con.execute("UPDATE vida SET banco = 0, atividade_feita = 0 WHERE atleta_id = ?", (self._atleta_id,))
        mudou = self.aplicar(efeitos)
        frases.append(f"Salário: +{salario} €")
        v = self.estado
        # Lesão: mais provável com pouca forma (só quem jogou se pode lesionar)
        if jogou:
            prob = 0.03 + max(0, 50 - v["forma"]) / 400
            if rnd.random() < prob:
                n = rnd.choice((1, 1, 2, 3))
                self.aplicar({"lesao": n, "moral": -10})
                txt = f"Lesionaste-te! Ficas {n} jornada{'s' if n > 1 else ''} de fora."
                frases.append(txt)
                self.registar(txt, {"lesao": n, "moral": -10}, "lesao")
        # Treinador sem confiança: banco no próximo jogo
        v = self.estado
        if v["treinador"] < 25 and v["lesao"] == 0:
            self.con.execute("UPDATE vida SET banco = 1 WHERE atleta_id = ?", (self._atleta_id,))
            self.aplicar({"treinador": 10})          # no banco, o treinador volta a dar-lhe uma hipótese
            txt = "O treinador perdeu a confiança em ti: vais para o banco no próximo jogo."
            frases.append(txt)
            self.registar(txt, {}, "banco")
        self.registar("Jornada: " + ", ".join(f"{NOME_VALOR[k]} {d:+}" for k, d in mudou.items() if k != "dinheiro")
                      + f" e salário de {salario} €", mudou, "jornada")
        # Evento com escolhas (em 3 de cada 4 jornadas)
        if not self.cj.camp.terminado and rnd.random() < 0.75:
            ev = self._sortear_evento()
            if ev:
                self.con.execute("UPDATE vida SET evento_pendente = ? WHERE atleta_id = ?",
                                 (ev["id"], self._atleta_id))
        return frases

    def _sortear_evento(self):
        v, a = self.estado, self.cj.atleta
        recentes = {l["evento"] for l in self.diario(12)}
        possiveis = [e for e in EVENTOS if e["id"] not in recentes and e.get("cond", lambda v, a: True)(v, a)]
        if not possiveis:
            possiveis = [e for e in EVENTOS if e.get("cond", lambda v, a: True)(v, a)]
        return self.rnd.choice(possiveis) if possiveis else None

    def evento_atual(self):
        """O evento à espera de escolha (ou None), com a indicação das opções possíveis."""
        eid = self.estado["evento_pendente"]
        if not eid or eid not in EVENTOS_POR_ID:
            return None
        ev = EVENTOS_POR_ID[eid]
        dinheiro = self.estado["dinheiro"]
        return {**ev, "possivel": [dinheiro >= o.get("custo", 0) for o in ev["opcoes"]]}

    def _resolver(self, opcao: dict, evento_id: str, titulo: str) -> dict:
        efeitos = dict(opcao.get("efeitos", {}))
        texto = opcao.get("resultado", "")
        sorte = opcao.get("sorte")
        if sorte and self.rnd.random() < sorte[0]:
            for k, d in sorte[1].items():
                efeitos[k] = efeitos.get(k, 0) + d
            texto = (texto + " " + sorte[2]).strip()
        mudou = self.aplicar(efeitos)
        if opcao.get("falta_jogo"):
            self.con.execute("UPDATE vida SET banco = 1 WHERE atleta_id = ?", (self._atleta_id,))
            texto += " Não vais jogar a próxima jornada."
        self.registar(f"{titulo}: {opcao['texto'].lower()}. {texto}", mudou, evento_id)
        return {"titulo": titulo, "escolha": opcao["texto"], "texto": texto, "efeitos": mudou}

    def escolher(self, i: int) -> dict:
        ev = self.evento_atual()
        if ev is None:
            raise RuntimeError("não há nenhum evento à espera")
        if not ev["possivel"][i]:
            raise ValueError("não tens dinheiro para essa opção")
        with self.con:
            self.con.execute("UPDATE vida SET evento_pendente = NULL WHERE atleta_id = ?", (self._atleta_id,))
            return self._resolver(ev["opcoes"][i], ev["id"], ev["titulo"])

    # ------------------------------------------------------------------ #
    # Atividades                                                          #
    # ------------------------------------------------------------------ #
    def atividades(self) -> list:
        v = self.estado
        lista = []
        for at in ATIVIDADES:
            if at.get("so_lesionado") and v["lesao"] == 0:
                continue
            ok = not v["atividade_feita"] and v["dinheiro"] >= at.get("custo", 0)
            lista.append({**at, "possivel": ok})
        return lista

    def fazer_atividade(self, atividade_id: str) -> dict:
        at = next(a for a in ATIVIDADES if a["id"] == atividade_id)
        v = self.estado
        if v["atividade_feita"]:
            raise RuntimeError("já fizeste a atividade desta semana")
        if v["dinheiro"] < at.get("custo", 0):
            raise ValueError("não tens dinheiro para isso")
        with self.con:
            self.con.execute("UPDATE vida SET atividade_feita = 1 WHERE atleta_id = ?", (self._atleta_id,))
            return self._resolver({"texto": at["nome"], "efeitos": at["efeitos"], "sorte": at.get("sorte"),
                                   "resultado": at["descricao"] + "."}, "atividade", "Atividade")

    # ------------------------------------------------------------------ #
    def nova_epoca(self) -> list:
        """Fim de época: faz anos, recupera as forças e a escola dá a nota do ano."""
        v = self.estado
        frases = [f"Fizeste {v['idade'] + 1} anos!"]
        efeitos = {"forma": 25, "moral": 5}
        if v["idade"] <= 18:
            if v["estudos"] >= 60:
                frases.append("Passaste de ano com boas notas.")
                efeitos["moral"] += 8
            elif v["estudos"] >= 40:
                frases.append("Passaste de ano à justa.")
            else:
                frases.append("Chumbaste o ano... os teus pais não estão contentes.")
                efeitos["moral"] -= 15
        with self.con:
            self.con.execute("UPDATE vida SET idade = idade + 1, evento_pendente = NULL, banco = 0, lesao = 0, "
                             "atividade_feita = 0 WHERE atleta_id = ?", (self._atleta_id,))
            mudou = self.aplicar(efeitos)
            self.registar(" ".join(frases), mudou, "epoca")
        return frases
