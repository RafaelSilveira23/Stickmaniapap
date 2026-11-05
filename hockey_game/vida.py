# -*- coding: utf-8 -*-
"""vida.py - a vida do jogador na carreira de jogador (escolhas ao estilo dos jogos de "simulação de vida").

Além do hóquei, o jogador tem uma vida: idade, dinheiro e cinco valores de 0 a 100:
  forma      - condição física (cansaço). Pouca forma = joga pior e lesiona-se mais
  moral      - felicidade. Moral alta = joga melhor
  treinador  - confiança do treinador. Abaixo de 25 vai para o banco no jogo seguinte
  fama       - quanto o público o conhece. Ajuda a ter propostas de outros clubes e patrocínios
  estudos    - a escola (e depois a universidade). Não conta no hóquei, mas conta na vida

PESSOAS: a mãe, o pai, o melhor amigo e (se acontecer) um namoro. Cada pessoa tem uma relação de
0 a 100 que desce aos poucos se não lhe ligares; uma vez por semana podes passar tempo com cada uma,
conversar, pedir conselho ou oferecer uma prenda. As relações mexem na moral e em alguns eventos.

Depois de cada jornada:
  1. a vida muda sozinha: salário, cansaço do jogo, moral do resultado, confiança do treinador pela nota;
  2. pode haver uma lesão (mais provável com pouca forma);
  3. aparece um EVENTO com escolhas. Algumas escolhas têm CONSEQUÊNCIAS mais tarde: deixam um
     "seguimento" que, passadas umas jornadas, traz um evento novo (a polémica nas redes dá um
     processo disciplinar, o primeiro encontro pode dar um pedido de namoro, ...).
Em cada semana pode-se fazer uma ATIVIDADE. Há também BENS (carta, carro, casa própria, agente,
braçadeira de capitão) com efeitos em todas as jornadas, e CONQUISTAS (primeiro golo, hat-trick, ...).
Tudo o que acontece fica no DIÁRIO.

As escolhas mexem no hóquei de quatro formas:
  • modificador() soma-se aos atributos do jogador nos jogos (forma e moral);
  • lesões e banco: o jogador não joga (o jogo da equipa é simulado sem ele);
  • alguns eventos mudam o geral (treino extra, seleção nacional);
  • a fama (e ter agente) melhora as propostas no fim da época.
"""
import json
import random

VALORES = ("forma", "moral", "treinador", "fama", "estudos")
PAPEIS = ("mae", "pai", "amigo", "namoro")
NOME_VALOR = {"forma": "Forma", "moral": "Moral", "treinador": "Treinador", "fama": "Fama",
              "estudos": "Estudos", "dinheiro": "Dinheiro", "geral": "Geral", "lesao": "Lesão",
              "mae": "Mãe", "pai": "Pai", "amigo": "Amigo", "namoro": "Namoro"}
NOME_PAPEL = {"mae": "Mãe", "pai": "Pai", "amigo": "Melhor amigo", "namoro": "Namoro"}
INICIO = {"idade": 17, "forma": 70, "moral": 65, "treinador": 50, "fama": 10, "estudos": 60, "dinheiro": 300}
NOMES_AMIGO = ("Rui", "Tiago", "Diogo", "João", "Miguel", "André", "Bruno", "Gonçalo", "Duarte", "Simão")
NOMES_NAMORO = ("Inês", "Beatriz", "Mariana", "Carolina", "Rita", "Sofia", "Leonor", "Matilde", "Tomás", "Afonso")

# Categoria de cada evento (o ecrã usa-a para a cor e o ícone do cartão)
CATEGORIAS = ("hoquei", "festa", "escola", "dinheiro", "familia", "amor", "imprensa", "saude")

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
CREATE TABLE IF NOT EXISTS pessoa (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    atleta_id  INTEGER NOT NULL REFERENCES atleta(id),
    papel      TEXT NOT NULL CHECK (papel IN ('mae', 'pai', 'amigo', 'namoro')),
    nome       TEXT NOT NULL,
    relacao    INTEGER NOT NULL CHECK (relacao BETWEEN 0 AND 100),
    interagiu  INTEGER NOT NULL DEFAULT 0,                            -- 1 = já falaste com ela esta semana
    ativa      INTEGER NOT NULL DEFAULT 1                             -- 0 = o namoro acabou
);
CREATE TABLE IF NOT EXISTS seguimento (                               -- consequências que chegam mais tarde
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    atleta_id  INTEGER NOT NULL REFERENCES atleta(id),
    evento     TEXT NOT NULL,
    jornadas   INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS marca (                                    -- bens e conquistas ("carro", "conq:hat_trick")
    atleta_id  INTEGER NOT NULL REFERENCES atleta(id),
    chave      TEXT NOT NULL,
    epoca      INTEGER NOT NULL,
    PRIMARY KEY (atleta_id, chave)
);
"""


def _sempre(v, a, c):
    return True


# ====================================================================== #
# Eventos                                                                #
#   efeitos   : forma, moral, treinador, fama, estudos (0-100), dinheiro, #
#               geral, lesao e as relações (mae, pai, amigo, namoro)      #
#   custo     : dinheiro que é preciso ter para escolher a opção          #
#   sorte     : (probabilidade, efeitos extra, texto extra)               #
#   seguinte  : (evento, jornadas) - uma consequência mais tarde          #
#   marca     : um bem que fica (carta, carro, casa_propria, agente, ...) #
#   cond      : quando o evento pode aparecer (v = vida, a = atleta,      #
#               c = contexto: pessoas e marcas)                           #
#   seguimento: True = só aparece como consequência de outra escolha      #
# Nos textos, {amigo} e {namoro} são trocados pelos nomes das pessoas.    #
# ====================================================================== #
EVENTOS = [
    # ---------------------------------------------------------------- festas e amigos
    {"id": "festa", "categoria": "festa", "titulo": "Festa na véspera do jogo",
     "texto": "O {amigo} faz anos e há festa lá em casa. Amanhã tens jogo.",
     "opcoes": [
         {"texto": "Vou e fico até de manhã", "efeitos": {"moral": 14, "forma": -18, "treinador": -6, "amigo": 10},
          "resultado": "Foi uma noite épica, mas acordaste de rastos.",
          "sorte": (0.2, {"lesao": 1}, "A dançar, torceste o tornozelo!"), "seguinte": ("fotos_festa", 1)},
         {"texto": "Vou, mas volto cedo", "efeitos": {"moral": 7, "forma": -4, "amigo": 5},
          "resultado": "Deste os parabéns, comeste bolo e às 23h estavas na cama."},
         {"texto": "Fico em casa a descansar", "efeitos": {"moral": -5, "forma": 6, "treinador": 2, "amigo": -8},
          "resultado": "O {amigo} ficou um bocado chateado, mas estás fresco."}]},
    {"id": "fotos_festa", "categoria": "imprensa", "seguimento": True, "titulo": "Fotos da festa nas redes",
     "texto": "Alguém publicou fotos tuas na festa às 5 da manhã. O clube já viu.",
     "opcoes": [
         {"texto": "Peço desculpa ao treinador", "efeitos": {"treinador": 6, "moral": -3},
          "resultado": "Ele aceitou, mas disse que não quer ver aquilo outra vez."},
         {"texto": "Faço uma piada sobre isso", "efeitos": {"fama": 8, "treinador": -8},
          "resultado": "Os adeptos acharam piada. O treinador nem por isso."}]},
    {"id": "jogo_consola", "categoria": "festa", "titulo": "Noite de consola",
     "texto": "Os teus colegas de equipa vão fazer um torneio de videojogos até tarde.",
     "opcoes": [
         {"texto": "Jogo até às 3 da manhã", "efeitos": {"moral": 8, "forma": -10},
          "resultado": "Ganhaste o torneio! Mas o despertador custou."},
         {"texto": "Jogo uma hora e vou dormir", "efeitos": {"moral": 4, "treinador": 2},
          "resultado": "Equilíbrio perfeito."}]},
    {"id": "amigo_dinheiro", "categoria": "dinheiro", "titulo": "O {amigo} precisa de dinheiro",
     "texto": "O {amigo} pede-te 300 € emprestados. Diz que paga daqui a umas semanas.",
     "cond": lambda v, a, c: v["dinheiro"] >= 300,
     "opcoes": [
         {"texto": "Empresto", "efeitos": {"dinheiro": -300, "amigo": 12}, "custo": 300,
          "resultado": "Ele agradeceu-te muito.", "seguinte": ("amigo_paga", 3)},
         {"texto": "Digo que não posso", "efeitos": {"amigo": -10},
          "resultado": "Ele disse que percebia, mas ficou desiludido."}]},
    {"id": "amigo_paga", "categoria": "dinheiro", "seguimento": True, "titulo": "O dinheiro emprestado",
     "texto": "Passaram umas semanas desde que emprestaste 300 € ao {amigo}.",
     "opcoes": [
         {"texto": "Pergunto-lhe pelo dinheiro", "efeitos": {},
          "resultado": "Ele pediu desculpa pela demora...",
          "sorte": (0.7, {"dinheiro": 320, "amigo": 5}, "e devolveu-te 320 €, com juros e tudo!")},
         {"texto": "Deixo passar", "efeitos": {"amigo": 8, "moral": -2},
          "resultado": "Amigos são amigos. Ele nunca mais tocou no assunto."}]},
    {"id": "padel", "categoria": "festa", "titulo": "Padel com a equipa",
     "texto": "Os colegas combinaram um torneio de padel no dia de folga.",
     "opcoes": [
         {"texto": "Vou jogar", "efeitos": {"moral": 7, "treinador": 3, "forma": -3},
          "resultado": "Perdeste na final, mas o balneário está mais unido."},
         {"texto": "Fico com o {amigo}", "efeitos": {"amigo": 8, "moral": 3},
          "resultado": "Passaste a tarde com o teu melhor amigo."}]},
    # ---------------------------------------------------------------- escola
    {"id": "teste", "categoria": "escola", "titulo": "Teste de Matemática",
     "texto": "Amanhã tens teste de Matemática e ainda não abriste o livro. O treino é à mesma hora do estudo.",
     "cond": lambda v, a, c: v["idade"] <= 19,
     "opcoes": [
         {"texto": "Falto ao treino para estudar", "efeitos": {"estudos": 14, "treinador": -7, "mae": 4},
          "resultado": "Tiveste 16 valores! O treinador não gostou muito da falta."},
         {"texto": "Treino e estudo à noite", "efeitos": {"estudos": 6, "forma": -8},
          "resultado": "Dormiste pouco, mas safaste-te com um 12."},
         {"texto": "Vou ao treino e logo se vê", "efeitos": {"estudos": -10, "treinador": 3, "pai": -5},
          "resultado": "Tiveste 7 valores. Os teus pais não ficaram nada contentes.",
          "sorte": (0.3, {"moral": -6}, "Ficaste de castigo ao fim de semana.")}]},
    {"id": "pai_estudos", "categoria": "familia", "titulo": "O teu pai quer falar contigo",
     "texto": "O teu pai viu as notas e diz que o hóquei não pode vir antes da escola.",
     "cond": lambda v, a, c: v["idade"] <= 19 and v["estudos"] < 50,
     "opcoes": [
         {"texto": "Prometo estudar mais", "efeitos": {"pai": 10, "estudos": 6, "moral": -2},
          "resultado": "Ele deu-te um abraço. Agora é cumprir."},
         {"texto": "Digo que vou ser profissional", "efeitos": {"pai": -12, "moral": 3},
          "resultado": "Ele saiu da sala sem dizer nada."}]},
    {"id": "baile", "categoria": "escola", "titulo": "Baile de finalistas",
     "texto": "É o baile de finalistas do 12.º ano. Na manhã seguinte há treino.",
     "cond": lambda v, a, c: v["idade"] == 18,
     "opcoes": [
         {"texto": "Vou ao baile (fato: 120 €)", "efeitos": {"moral": 15, "dinheiro": -120, "forma": -6, "amigo": 6},
          "custo": 120, "resultado": "Uma noite para recordar para sempre."},
         {"texto": "Não vou, há treino", "efeitos": {"moral": -8, "treinador": 4},
          "resultado": "Viste as fotos no dia seguinte..."}]},
    {"id": "universidade", "categoria": "escola", "titulo": "Exames nacionais",
     "texto": "Estás no 12.º ano e os exames estão à porta. As semanas de estudo coincidem com o fim do campeonato.",
     "cond": lambda v, a, c: v["idade"] == 18,
     "opcoes": [
         {"texto": "Estudo a sério", "efeitos": {"estudos": 18, "forma": -6, "treinador": -4, "mae": 5},
          "resultado": "Preparaste-te bem para os exames."},
         {"texto": "O hóquei vem primeiro", "efeitos": {"estudos": -12, "treinador": 6},
          "resultado": "Treinaste todos os dias. Os exames... logo se vê."}]},
    {"id": "faculdade", "categoria": "escola", "titulo": "Época de exames na faculdade",
     "texto": "Entraste em Desporto na universidade. Esta semana tens dois exames e um jogo grande.",
     "cond": lambda v, a, c: v["idade"] >= 19 and v["estudos"] >= 55,
     "opcoes": [
         {"texto": "Faço os dois exames", "efeitos": {"estudos": 10, "forma": -5},
          "resultado": "Passaste aos dois. Que semana!"},
         {"texto": "Adio um exame", "efeitos": {"estudos": -4, "moral": 3},
          "resultado": "Fica para a época de recurso."}]},
    # ---------------------------------------------------------------- dinheiro e bens
    {"id": "patrocinio", "categoria": "dinheiro", "titulo": "Proposta de patrocínio",
     "texto": "Uma marca de bebidas energéticas quer pagar-te para publicares fotos com a lata.",
     "cond": lambda v, a, c: v["fama"] >= 15,
     "opcoes": [
         {"texto": "Aceito (750 €)", "efeitos": {"dinheiro": 750, "fama": 6, "treinador": -3},
          "resultado": "Ganhaste dinheiro, mas o treinador acha que te estás a distrair."},
         {"texto": "Recuso, quero focar-me no hóquei", "efeitos": {"treinador": 4, "moral": -2},
          "resultado": "O treinador soube e gostou da tua atitude."}]},
    {"id": "carta", "categoria": "dinheiro", "titulo": "Carta de condução",
     "texto": "Fizeste 18 anos. A escola de condução tem uma promoção: carta por 600 €.",
     "cond": lambda v, a, c: v["idade"] >= 18 and "carta" not in c["marcas"],
     "opcoes": [
         {"texto": "Tiro a carta (600 €)", "efeitos": {"dinheiro": -600, "moral": 6, "forma": -2}, "custo": 600,
          "marca": "carta", "resultado": "Passaste à primeira!",
          "sorte": (0.25, {"moral": -8, "dinheiro": -100}, "Ups... chumbaste no exame de condução e pagaste mais 100 € para repetir.")},
         {"texto": "Fica para depois", "efeitos": {},
          "resultado": "Continuas a precisar de boleia do teu pai.", }]},
    {"id": "carro", "categoria": "dinheiro", "titulo": "Carro novo?",
     "texto": "Viste um carro em segunda mão por 4 000 €.",
     "cond": lambda v, a, c: "carta" in c["marcas"] and "carro" not in c["marcas"] and v["dinheiro"] >= 4000,
     "opcoes": [
         {"texto": "Compro o carro", "efeitos": {"dinheiro": -4000, "moral": 15, "fama": 3}, "custo": 4000,
          "marca": "carro", "resultado": "Já não precisas de boleia para os treinos!", "seguinte": ("multa", 3)},
         {"texto": "Guardo o dinheiro", "efeitos": {"moral": -2},
          "resultado": "Continuas a ir de autocarro, mas a conta bancária agradece."}]},
    {"id": "multa", "categoria": "dinheiro", "seguimento": True, "titulo": "Multa de velocidade",
     "texto": "Chegou uma carta: o radar apanhou o teu carro a 90 km/h numa zona de 50.",
     "opcoes": [
         {"texto": "Pago a multa (250 €)", "efeitos": {"dinheiro": -250, "moral": -4},
          "resultado": "Lição aprendida."},
         {"texto": "Digo que era o meu pai a conduzir", "efeitos": {"pai": -15},
          "resultado": "O teu pai ficou furioso quando soube.",
          "sorte": (0.5, {"fama": -6, "dinheiro": -400}, "E a polícia descobriu: multa a dobrar e notícia no jornal.")}]},
    {"id": "sair_casa", "categoria": "familia", "titulo": "Sair de casa dos pais",
     "texto": "Há um T1 perto do pavilhão por 120 € por semana. Os teus pais dizem que ainda és novo.",
     "cond": lambda v, a, c: v["idade"] >= 19 and v["dinheiro"] >= 2500 and "casa_propria" not in c["marcas"],
     "opcoes": [
         {"texto": "Mudo-me (entrada de 1 000 €)", "efeitos": {"dinheiro": -1000, "moral": 12, "mae": -8}, "custo": 1000,
          "marca": "casa_propria", "resultado": "A tua própria casa! A renda é paga todas as semanas."},
         {"texto": "Fico em casa mais um ano", "efeitos": {"mae": 6, "pai": 4},
          "resultado": "A comida da tua mãe continua a ser a melhor."}]},
    {"id": "investir", "categoria": "dinheiro", "titulo": "Investir as poupanças?",
     "texto": "O {amigo} tem um negócio de camisolas de hóquei personalizadas e precisa de 1 000 €.",
     "cond": lambda v, a, c: v["dinheiro"] >= 1000,
     "opcoes": [
         {"texto": "Invisto 1 000 €", "efeitos": {"dinheiro": -1000, "amigo": 10}, "custo": 1000,
          "resultado": "Agora é esperar para ver como corre.", "seguinte": ("investimento", 3)},
         {"texto": "Não arrisco", "efeitos": {"amigo": -3},
          "resultado": "O dinheiro continua na conta."}]},
    {"id": "investimento", "categoria": "dinheiro", "seguimento": True, "titulo": "O negócio das camisolas",
     "texto": "O {amigo} liga-te: tem novidades sobre o negócio em que investiste.",
     "opcoes": [
         {"texto": "Conta lá!", "efeitos": {},
          "resultado": "Venderam as camisolas todas...",
          "sorte": (0.55, {"dinheiro": 2500, "moral": 10, "amigo": 5}, "e recebeste 2 500 €!")}]},
    {"id": "agente", "categoria": "dinheiro", "titulo": "Um agente quer representar-te",
     "texto": "Um agente de jogadores diz que te arranja contratos melhores em troca de uma comissão.",
     "cond": lambda v, a, c: v["fama"] >= 30 and "agente" not in c["marcas"],
     "opcoes": [
         {"texto": "Assino com o agente", "efeitos": {"moral": 4}, "marca": "agente",
          "resultado": "A partir de agora o teu salário sobe 15 % e as propostas vão ser melhores."},
         {"texto": "Prefiro tratar de tudo sozinho", "efeitos": {},
          "resultado": "Continuas a negociar sozinho."}]},
    {"id": "anuncio", "categoria": "imprensa", "titulo": "Anúncio na televisão",
     "texto": "Uma marca de desporto quer filmar um anúncio contigo. Pagam 2 000 €, mas é num dia de treino.",
     "cond": lambda v, a, c: v["fama"] >= 50,
     "opcoes": [
         {"texto": "Faço o anúncio", "efeitos": {"dinheiro": 2000, "fama": 10, "treinador": -8},
          "resultado": "Agora toda a gente te reconhece na rua."},
         {"texto": "Peço para mudar o dia", "efeitos": {"fama": 3},
          "resultado": "Aceitaram, mas pagaram menos: 800 €.", "sorte": (1.0, {"dinheiro": 800}, "")}]},
    # ---------------------------------------------------------------- família
    {"id": "avo", "categoria": "familia", "titulo": "A tua avó está doente",
     "texto": "A tua avó foi para o hospital. O jogo é no dia da visita.",
     "opcoes": [
         {"texto": "Vou visitá-la e falto ao jogo", "efeitos": {"moral": 6, "treinador": -12, "mae": 10},
          "resultado": "Ela ficou muito feliz. O treinador compreendeu... mais ou menos.", "falta_jogo": True},
         {"texto": "Vou ao jogo e dedico-lhe um golo", "efeitos": {"moral": -4, "treinador": 4, "mae": -4},
          "resultado": "Ela viu o jogo na televisão do hospital."}]},
    {"id": "mae_anos", "categoria": "familia", "titulo": "A tua mãe faz anos",
     "texto": "É o aniversário da tua mãe e tu quase te esquecias.",
     "opcoes": [
         {"texto": "Jantar num restaurante (80 €)", "efeitos": {"mae": 15, "dinheiro": -80, "moral": 5}, "custo": 80,
          "resultado": "Ela não parou de sorrir a noite toda."},
         {"texto": "Faço-lhe um bolo", "efeitos": {"mae": 10, "moral": 3},
          "resultado": "Ficou meio torto, mas ela adorou."},
         {"texto": "Mando uma mensagem", "efeitos": {"mae": -8},
          "resultado": "\"Obrigada, filho.\" Só isso."}]},
    {"id": "discussao_casa", "categoria": "familia", "titulo": "Discussão em casa",
     "texto": "Há dias que mal falas com os teus pais. Hoje ao jantar a conversa azedou.",
     "cond": lambda v, a, c: c["rel"].get("mae", 100) < 35 or c["rel"].get("pai", 100) < 35,
     "opcoes": [
         {"texto": "Peço desculpa e converso", "efeitos": {"mae": 12, "pai": 12, "moral": 4},
          "resultado": "Acabaram a noite a rir com histórias antigas."},
         {"texto": "Saio de casa a bater a porta", "efeitos": {"mae": -10, "pai": -10, "moral": -10},
          "resultado": "Dormiste em casa do {amigo}."}]},
    # ---------------------------------------------------------------- amor
    {"id": "namoro", "categoria": "amor", "titulo": "Primeiro encontro",
     "texto": "Alguém de quem gostas, {pessoa_nova}, convidou-te para jantar no sábado. Domingo de manhã há jogo.",
     "cond": lambda v, a, c: "namoro" not in c["rel"],
     "opcoes": [
         {"texto": "Vou ao jantar", "efeitos": {"moral": 15, "dinheiro": -40, "forma": -3}, "custo": 40,
          "resultado": "Correu muito bem. Estás nas nuvens!", "seguinte": ("pedido_namoro", 2)},
         {"texto": "Proponho outro dia", "efeitos": {"moral": 4},
          "resultado": "Ficou combinado para a semana. Boa!", "seguinte": ("pedido_namoro", 3)}]},
    {"id": "pedido_namoro", "categoria": "amor", "seguimento": True, "titulo": "Vamos namorar?",
     "cond": lambda v, a, c: "namoro" not in c["rel"],
     "texto": "Depois de mais uns encontros, {pessoa_nova} pergunta-te se querem namorar.",
     "opcoes": [
         {"texto": "Sim!", "efeitos": {"moral": 15}, "novo_namoro": True,
          "resultado": "Estão oficialmente a namorar!"},
         {"texto": "Prefiro ficarmos amigos", "efeitos": {"moral": -6},
          "resultado": "Foi uma conversa difícil."}]},
    {"id": "namoro_jogo", "categoria": "amor", "titulo": "Ir ver o jogo",
     "texto": "{namoro} quer ir ver o teu próximo jogo à bancada.",
     "cond": lambda v, a, c: "namoro" in c["rel"],
     "opcoes": [
         {"texto": "Claro! Arranjo-lhe bilhete", "efeitos": {"namoro": 10, "moral": 6},
          "resultado": "Vais jogar com mais vontade."},
         {"texto": "Prefiro que não, fico nervoso", "efeitos": {"namoro": -10},
          "resultado": "Não ficou muito contente com a resposta."}]},
    {"id": "ciumes", "categoria": "amor", "titulo": "Ciúmes",
     "texto": "{namoro} viu comentários de fãs nas tuas fotos e não gostou nada.",
     "cond": lambda v, a, c: "namoro" in c["rel"] and v["fama"] >= 25,
     "opcoes": [
         {"texto": "Converso e tranquilizo", "efeitos": {"namoro": 8, "moral": -2},
          "resultado": "Ficou tudo esclarecido."},
         {"texto": "Digo que é exagero", "efeitos": {"namoro": -15, "moral": -5},
          "resultado": "Acabaram a noite sem se falar."}]},
    {"id": "aniversario_namoro", "categoria": "amor", "titulo": "Meses de namoro",
     "texto": "Fazem meses de namoro. {namoro} preparou uma surpresa.",
     "cond": lambda v, a, c: c["rel"].get("namoro", 0) >= 60,
     "opcoes": [
         {"texto": "Retribuo com um fim de semana fora (200 €)", "efeitos": {"namoro": 15, "moral": 12,
                                                                             "dinheiro": -200, "forma": 4},
          "custo": 200, "resultado": "Dois dias na praia. Perfeito."},
         {"texto": "Agradeço e jantamos em casa", "efeitos": {"namoro": 6, "moral": 6},
          "resultado": "Simples, mas especial."}]},
    # ---------------------------------------------------------------- imprensa e redes
    {"id": "redes", "categoria": "imprensa", "titulo": "Polémica nas redes sociais",
     "texto": "Um adepto rival goza contigo num vídeo que está a ficar viral.",
     "opcoes": [
         {"texto": "Respondo à letra", "efeitos": {"fama": 10, "treinador": -10, "moral": 4},
          "resultado": "O teu vídeo teve milhares de visualizações...", "seguinte": ("processo", 1)},
         {"texto": "Respondo com humor", "efeitos": {"fama": 7, "moral": 5},
          "resultado": "Toda a gente achou piada. Ganhaste seguidores."},
         {"texto": "Ignoro", "efeitos": {"moral": -3},
          "resultado": "Passou ao fim de dois dias."}]},
    {"id": "processo", "categoria": "imprensa", "seguimento": True, "titulo": "Processo disciplinar",
     "texto": "Por causa da resposta nas redes, o clube abriu-te um processo disciplinar.",
     "opcoes": [
         {"texto": "Aceito a multa (500 €)", "efeitos": {"dinheiro": -500, "treinador": 6},
          "resultado": "Assunto encerrado."},
         {"texto": "Contesto o processo", "efeitos": {},
          "resultado": "Foste ouvido pela direção...",
          "sorte": (0.5, {"fama": 5, "moral": 8}, "e deram-te razão!")}]},
    {"id": "entrevista", "categoria": "imprensa", "titulo": "Entrevista na televisão",
     "texto": "Um canal desportivo quer entrevistar-te sobre a época do clube.",
     "cond": lambda v, a, c: v["fama"] >= 25,
     "opcoes": [
         {"texto": "Elogio a equipa e o treinador", "efeitos": {"treinador": 8, "fama": 4},
          "resultado": "Resposta de profissional. O balneário gostou."},
         {"texto": "Digo que mereço jogar mais", "efeitos": {"fama": 9, "treinador": -12},
          "resultado": "A frase foi manchete. O treinador não achou piada."}]},
    {"id": "jornalista", "categoria": "imprensa", "titulo": "Rumores de transferência",
     "texto": "Um jornal diz que um grande clube está interessado em ti. Perguntam-te se é verdade.",
     "cond": lambda v, a, c: v["fama"] >= 40,
     "opcoes": [
         {"texto": "\"Estou focado no meu clube\"", "efeitos": {"treinador": 8},
          "resultado": "Resposta perfeita para o balneário."},
         {"texto": "\"Quem sabe...\"", "efeitos": {"fama": 10, "treinador": -10, "moral": 4},
          "resultado": "A frase deu que falar a semana toda."}]},
    {"id": "caridade", "categoria": "imprensa", "titulo": "Torneio solidário",
     "texto": "Pedem-te para ires a um torneio de hóquei para crianças, no teu dia de folga.",
     "opcoes": [
         {"texto": "Vou e dou autógrafos", "efeitos": {"fama": 6, "moral": 8, "forma": -4},
          "resultado": "As crianças adoraram. Saíste no jornal da terra."},
         {"texto": "Prefiro descansar", "efeitos": {"forma": 5},
          "resultado": "Ficaste no sofá a ver séries."}]},
    {"id": "aposta", "categoria": "imprensa", "titulo": "Um conhecido propõe uma aposta",
     "texto": "Um conhecido diz que ganhas 500 € se apostares contra a tua própria equipa.",
     "opcoes": [
         {"texto": "Nem pensar! E aviso o clube", "efeitos": {"treinador": 10, "fama": 4, "moral": 3},
          "resultado": "O clube agradeceu a tua honestidade."},
         {"texto": "Recuso e não digo nada", "efeitos": {},
          "resultado": "Fingiste que nunca aconteceu.", "seguinte": ("investigacao", 3)}]},
    {"id": "investigacao", "categoria": "imprensa", "seguimento": True, "titulo": "Investigação às apostas",
     "texto": "A polícia está a investigar apostas ilegais no hóquei e quer falar contigo.",
     "opcoes": [
         {"texto": "Conto tudo o que sei", "efeitos": {"treinador": 4, "fama": 3},
          "resultado": "Ajudaste a investigação. O clube está do teu lado."},
         {"texto": "Digo que não sei de nada", "efeitos": {},
          "resultado": "Saíste da esquadra com o coração aos saltos.",
          "sorte": (0.35, {"fama": -12, "treinador": -15, "moral": -10},
                    "Uma testemunha disse que sabias. Foste suspenso um jogo.")}]},
    # ---------------------------------------------------------------- hóquei
    {"id": "treinador_extra", "categoria": "hoquei", "titulo": "O treinador chama-te",
     "texto": "O treinador quer que fiques depois do treino a trabalhar o remate.",
     "opcoes": [
         {"texto": "Claro, fico o tempo que for preciso", "efeitos": {"geral": 0.8, "forma": -8, "treinador": 8},
          "resultado": "Uma hora de remates. Sentes que estás melhor."},
         {"texto": "Hoje não posso", "efeitos": {"treinador": -6},
          "resultado": "Ele não disse nada, mas reparaste na cara dele."}]},
    {"id": "selecao", "categoria": "hoquei", "titulo": "Convocatória da seleção!",
     "texto": "Foste convocado para a seleção nacional!",
     "cond": lambda v, a, c: a["geral"] >= 72 and v["fama"] >= 35,
     "opcoes": [
         {"texto": "Aceito, é um sonho!", "efeitos": {"fama": 15, "moral": 12, "geral": 1.0, "forma": -10,
                                                       "pai": 8, "mae": 8},
          "marca": "selecao", "resultado": "Vestiste a camisola de Portugal!", "seguinte": ("selecao_jogo", 1)},
         {"texto": "Recuso para descansar", "efeitos": {"forma": 10, "fama": -5, "moral": -6},
          "resultado": "Descansaste, mas ficaste a pensar no que perdeste."}]},
    {"id": "selecao_jogo", "categoria": "hoquei", "seguimento": True, "titulo": "Jogo pela seleção",
     "texto": "Portugal joga contra Espanha e o selecionador põe-te a titular.",
     "opcoes": [
         {"texto": "Dou tudo em campo", "efeitos": {"forma": -6},
          "resultado": "Que jogo!",
          "sorte": (0.45, {"fama": 15, "moral": 10, "geral": 0.5}, "Marcaste o golo da vitória! O país inteiro fala de ti.")},
         {"texto": "Jogo pela equipa", "efeitos": {"fama": 4, "geral": 0.3},
          "resultado": "Fizeste um jogo seguro e o selecionador gostou."}]},
    {"id": "capitao", "categoria": "hoquei", "titulo": "Braçadeira de capitão",
     "texto": "O treinador quer que sejas o novo capitão de equipa.",
     "cond": lambda v, a, c: v["treinador"] >= 72 and v["idade"] >= 19 and "capitao" not in c["marcas"],
     "opcoes": [
         {"texto": "Aceito com orgulho", "efeitos": {"fama": 8, "moral": 10, "treinador": 6}, "marca": "capitao",
          "resultado": "És o capitão! A tua fama sobe um pouco todas as jornadas."},
         {"texto": "Ainda não me sinto preparado", "efeitos": {"treinador": -4},
          "resultado": "O treinador respeitou, mas ficou surpreendido."}]},
    {"id": "colega_lesionado", "categoria": "saude", "titulo": "Um colega lesionou-se",
     "texto": "Um colega de equipa partiu o pulso no treino e está muito em baixo.",
     "opcoes": [
         {"texto": "Visito-o em casa", "efeitos": {"moral": 4, "treinador": 4},
          "resultado": "Ele agradeceu muito. O balneário está mais unido."},
         {"texto": "Mando mensagem de apoio", "efeitos": {"moral": 1},
          "resultado": "Ele respondeu com um polegar para cima."}]},
    {"id": "dieta", "categoria": "saude", "titulo": "Nutricionista do clube",
     "texto": "O nutricionista do clube propõe-te um plano de alimentação mais rigoroso.",
     "opcoes": [
         {"texto": "Sigo o plano à risca", "efeitos": {"forma": 12, "moral": -5},
          "resultado": "Adeus hambúrgueres... mas sentes-te mais leve no rinque."},
         {"texto": "Sigo mais ou menos", "efeitos": {"forma": 4},
          "resultado": "Pelo menos trocaste os refrigerantes por água."}]},
    {"id": "lesao_leve", "categoria": "saude", "titulo": "Dores no joelho",
     "texto": "Sentes uma dor no joelho desde o último treino.",
     "opcoes": [
         {"texto": "Vou ao fisioterapeuta (120 €)", "efeitos": {"dinheiro": -120, "forma": 6}, "custo": 120,
          "resultado": "Era só uma inflamação. Uns dias de gelo e estás pronto."},
         {"texto": "Jogo na mesma", "efeitos": {"treinador": 3},
          "resultado": "Aguentaste...",
          "sorte": (0.45, {"lesao": 2, "moral": -8}, "...até que o joelho cedeu. Duas jornadas de fora!")}]},
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
     "efeitos": {"moral": 12, "forma": -4, "dinheiro": -40, "amigo": 8}, "custo": 40},
    {"id": "estudar", "nome": "Estudar", "descricao": "Pôr a matéria da escola em dia",
     "efeitos": {"estudos": 12, "moral": -3}},
    {"id": "redes", "nome": "Publicar nas redes", "descricao": "Vídeos de treinos e golos",
     "efeitos": {"fama": 5},
     "sorte": (0.15, {"fama": 6, "treinador": -8, "moral": -4}, "Uma frase tua foi mal interpretada... polémica!")},
    {"id": "fisioterapia", "nome": "Fisioterapia", "descricao": "Recuperar mais depressa da lesão",
     "efeitos": {"lesao": -1, "dinheiro": -150}, "custo": 150, "so_lesionado": True},
]

# Interações com as pessoas (uma por pessoa por semana)
ACOES_PESSOA = {
    "tempo": {"nome": "Passar tempo", "rel": 8, "efeitos": {"moral": 2, "forma": -1}},
    "conversar": {"nome": "Conversar", "rel": 4, "efeitos": {"moral": 1}},
    "conselho": {"nome": "Pedir conselho", "rel": 3, "efeitos": {"moral": 1}},
    "prenda": {"nome": "Prenda (60 €)", "rel": 12, "efeitos": {"dinheiro": -60, "moral": 1}, "custo": 60},
}
TEXTOS_PESSOA = {
    ("mae", "tempo"): ["Almoçaste com a tua mãe. Fez o teu prato preferido.",
                       "Foste às compras com a tua mãe e ela contou-te histórias de quando eras pequeno."],
    ("pai", "tempo"): ["Foste com o teu pai ver um jogo de futebol.", "Lavaram o carro juntos ao domingo."],
    ("amigo", "tempo"): ["Passaste a tarde com o {amigo} a jogar à bola na rua, como antigamente.",
                         "Tu e o {amigo} foram ao cinema e comeram pipocas até mais não."],
    ("namoro", "tempo"): ["Passeaste com {namoro} à beira-rio ao pôr do sol.",
                          "Cozinharam juntos. A cozinha ficou num caos, mas valeu a pena."],
    ("mae", "conselho"): ["A tua mãe disse-te: \"Faz o que gostas, mas nunca deixes a escola.\""],
    ("pai", "conselho"): ["O teu pai disse-te: \"No rinque e na vida, quem trabalha mais ganha.\""],
    ("amigo", "conselho"): ["O {amigo} disse-te para não levares as críticas tão a peito."],
    ("namoro", "conselho"): ["{namoro} disse-te que acredita em ti, aconteça o que acontecer."],
}

# Conquistas: (id, nome, descrição)
CONQUISTAS = [
    ("primeiro_golo", "Primeiro golo", "Marca o primeiro golo da carreira"),
    ("hat_trick", "Hat-trick", "Marca 3 golos num jogo"),
    ("goleador", "Goleador", "Chega aos 25 golos na carreira"),
    ("nota_9", "Exibição de sonho", "Tem nota 9 ou mais num jogo"),
    ("campeao", "Campeão nacional", "Ganha o campeonato"),
    ("selecao", "Internacional", "Joga pela seleção nacional"),
    ("grande", "Num grande", "Assina pelo FC Porto, Benfica ou Sporting"),
    ("craque", "Craque", "Chega a 80 de geral"),
    ("poupado", "Mealheiro cheio", "Junta 10 000 €"),
    ("carro", "Ao volante", "Compra o primeiro carro"),
    ("apaixonado", "Apaixonado", "Começa um namoro"),
    ("finalista", "12.º ano feito", "Acaba o secundário com boas notas"),
    ("capitao", "Capitão", "Recebe a braçadeira de capitão"),
    ("veterano", "Veterano", "Chega à 5.ª época"),
]
NOME_CONQUISTA = {c[0]: c[1] for c in CONQUISTAS}


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
        """Cria a vida do jogador atual e as suas pessoas (se ainda não existirem)."""
        aid = self._atleta_id
        if aid is None:
            return
        with self.con:
            self.con.execute(
                "INSERT OR IGNORE INTO vida (atleta_id, idade, forma, moral, treinador, fama, estudos, dinheiro) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (aid, INICIO["idade"], INICIO["forma"], INICIO["moral"], INICIO["treinador"], INICIO["fama"],
                 INICIO["estudos"], INICIO["dinheiro"]))
            existe = self.con.execute("SELECT COUNT(*) FROM pessoa WHERE atleta_id = ?", (aid,)).fetchone()[0]
            if not existe:
                amigo = random.Random(aid * 7919).choice(NOMES_AMIGO)
                self.con.executemany(
                    "INSERT INTO pessoa (atleta_id, papel, nome, relacao) VALUES (?, ?, ?, ?)",
                    [(aid, "mae", "Mãe", 80), (aid, "pai", "Pai", 75), (aid, "amigo", amigo, 70)])

    @property
    def estado(self) -> dict:
        self.garantir()
        l = self.con.execute("SELECT * FROM vida WHERE atleta_id = ?", (self._atleta_id,)).fetchone()
        return dict(l)

    def pessoas(self) -> list:
        """As pessoas da vida do jogador (mãe, pai, melhor amigo e, se houver, o namoro)."""
        self.garantir()
        return [dict(l) for l in self.con.execute(
            "SELECT * FROM pessoa WHERE atleta_id = ? AND ativa = 1 ORDER BY id", (self._atleta_id,))]

    def _contexto(self) -> dict:
        pes = self.pessoas()
        return {"rel": {p["papel"]: p["relacao"] for p in pes},
                "nomes": {p["papel"]: p["nome"] for p in pes},
                "marcas": self.marcas()}

    def marcas(self) -> set:
        return {l["chave"] for l in self.con.execute("SELECT chave FROM marca WHERE atleta_id = ?",
                                                     (self._atleta_id,))}

    def _marcar(self, chave: str) -> bool:
        cur = self.con.execute("INSERT OR IGNORE INTO marca (atleta_id, chave, epoca) VALUES (?, ?, ?)",
                               (self._atleta_id, chave, self.cj.camp.info["epoca"]))
        return cur.rowcount > 0

    def formatar(self, txt: str, extra: dict | None = None) -> str:
        """Troca {amigo}, {namoro} e {pessoa_nova} pelos nomes das pessoas."""
        nomes = self._contexto()["nomes"]
        dados = {"amigo": nomes.get("amigo", "teu amigo"), "namoro": nomes.get("namoro", "A tua cara-metade"),
                 "pessoa_nova": self._pessoa_nova()}
        dados.update(extra or {})
        try:
            return txt.format(**dados)
        except (KeyError, IndexError):
            return txt

    def _pessoa_nova(self) -> str:
        """Nome de quem aparece nos eventos de amor (sempre o mesmo para o mesmo jogador e época)."""
        a = self.cj.atleta
        return random.Random(a["id"] * 31 + a["epoca"]).choice(NOMES_NAMORO)

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
        """Aplica os efeitos à vida, às relações e ao geral do jogador. Devolve o que mudou de facto."""
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
                if novo != v["dinheiro"]:
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
            elif k in PAPEIS:
                p = self.con.execute("SELECT id, relacao FROM pessoa WHERE atleta_id = ? AND papel = ? AND ativa = 1",
                                     (self._atleta_id, k)).fetchone()
                if p:
                    novo = _limitar(p["relacao"] + d)
                    if novo != p["relacao"]:
                        mudou[k] = novo - p["relacao"]
                        self.con.execute("UPDATE pessoa SET relacao = ? WHERE id = ?", (novo, p["id"]))
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
        marcas = self.marcas()
        frases = []
        a = self.cj.atleta
        salario = int(FORCA_EQUIPAS.get(a["equipa_id"], 75) * 4 + v["fama"] * 3)
        if "agente" in marcas:
            salario = int(salario * 1.15)                # o agente negociou um contrato melhor
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
        # Bens com efeito em todas as jornadas
        if "casa_propria" in marcas:
            efeitos["dinheiro"] -= 120
            efeitos["moral"] += 1
        if "capitao" in marcas:
            efeitos["fama"] += 1
        # As pessoas: a relação desce aos poucos; boas relações dão moral, más relações tiram
        pes = self.pessoas()
        for p in pes:
            descida = {"amigo": 2, "namoro": 3}.get(p["papel"], 1)
            self.con.execute("UPDATE pessoa SET relacao = MAX(0, relacao - ?), interagiu = 0 WHERE id = ?",
                             (descida, p["id"]))
        if pes:
            media = sum(p["relacao"] for p in pes) / len(pes)
            efeitos["moral"] += 1 if media >= 65 else (-3 if media < 35 else 0)
        self.con.execute("UPDATE vida SET banco = 0, atividade_feita = 0 WHERE atleta_id = ?", (self._atleta_id,))
        mudou = self.aplicar(efeitos)
        frases.append(f"Salário: +{salario} €" + (" (renda: −120 €)" if "casa_propria" in marcas else ""))
        # Namoro com a relação muito baixa: acaba
        namoro = next((p for p in self.pessoas() if p["papel"] == "namoro"), None)
        if namoro and namoro["relacao"] < 15:
            self.con.execute("UPDATE pessoa SET ativa = 0 WHERE id = ?", (namoro["id"],))
            self.aplicar({"moral": -15})
            txt = f"O namoro com {namoro['nome']} acabou..."
            frases.append(txt)
            self.registar(txt, {"moral": -15}, "fim_namoro")
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
        # Evento da semana: primeiro as consequências de escolhas antigas, senão um evento ao acaso
        if not self.cj.camp.terminado:
            ev = self._seguimento_pronto()
            if ev is None and rnd.random() < 0.75:
                ev = self._sortear_evento()
            if ev:
                self.con.execute("UPDATE vida SET evento_pendente = ? WHERE atleta_id = ?",
                                 (ev["id"], self._atleta_id))
        frases += [f"Conquista: {n}" for n in self.verificar_conquistas()]
        return frases

    def _seguimento_pronto(self):
        """Desconta uma jornada às consequências à espera e devolve a primeira que chegou (ou None)."""
        self.con.execute("UPDATE seguimento SET jornadas = jornadas - 1 WHERE atleta_id = ?", (self._atleta_id,))
        linha = self.con.execute("SELECT * FROM seguimento WHERE atleta_id = ? AND jornadas <= 0 ORDER BY id LIMIT 1",
                                 (self._atleta_id,)).fetchone()
        if not linha:
            return None
        self.con.execute("DELETE FROM seguimento WHERE id = ?", (linha["id"],))
        ev = EVENTOS_POR_ID.get(linha["evento"])
        if ev and ev.get("cond", _sempre)(self.estado, self.cj.atleta, self._contexto()):
            return ev
        return None

    def _sortear_evento(self):
        v, a, c = self.estado, self.cj.atleta, self._contexto()
        recentes = {l["evento"] for l in self.diario(14)}
        bons = [e for e in EVENTOS if not e.get("seguimento") and e.get("cond", _sempre)(v, a, c)]
        possiveis = [e for e in bons if e["id"] not in recentes] or bons
        return self.rnd.choice(possiveis) if possiveis else None

    def evento_atual(self):
        """O evento à espera de escolha (ou None), já com os nomes e com as opções possíveis."""
        eid = self.estado["evento_pendente"]
        if not eid or eid not in EVENTOS_POR_ID:
            return None
        ev = EVENTOS_POR_ID[eid]
        dinheiro = self.estado["dinheiro"]
        opcoes = [dict(o, texto=self.formatar(o["texto"])) for o in ev["opcoes"]]
        return {**ev, "titulo": self.formatar(ev["titulo"]), "texto": self.formatar(ev["texto"]), "opcoes": opcoes,
                "possivel": [dinheiro >= o.get("custo", 0) for o in ev["opcoes"]]}

    def _resolver(self, opcao: dict, evento_id: str, titulo: str) -> dict:
        efeitos = dict(opcao.get("efeitos", {}))
        texto = self.formatar(opcao.get("resultado", ""))
        sorte = opcao.get("sorte")
        if sorte and self.rnd.random() < sorte[0]:
            for k, d in sorte[1].items():
                efeitos[k] = efeitos.get(k, 0) + d
            texto = (texto + " " + self.formatar(sorte[2])).strip()
        mudou = self.aplicar(efeitos)
        if opcao.get("falta_jogo") or "Foste suspenso" in texto:
            self.con.execute("UPDATE vida SET banco = 1 WHERE atleta_id = ?", (self._atleta_id,))
            texto += " Não vais jogar a próxima jornada."
        if opcao.get("marca"):
            self._marcar(opcao["marca"])
        if opcao.get("seguinte"):
            ev_id, n = opcao["seguinte"]
            self.con.execute("INSERT INTO seguimento (atleta_id, evento, jornadas) VALUES (?, ?, ?)",
                             (self._atleta_id, ev_id, n))
        if opcao.get("novo_namoro"):
            nome = self._pessoa_nova()
            self.con.execute("INSERT INTO pessoa (atleta_id, papel, nome, relacao) VALUES (?, 'namoro', ?, 70)",
                             (self._atleta_id, nome))
        self.registar(f"{titulo}: {self.formatar(opcao['texto']).lower()}. {texto}", mudou, evento_id)
        return {"titulo": titulo, "escolha": self.formatar(opcao["texto"]), "texto": texto, "efeitos": mudou,
                "conquistas": self.verificar_conquistas()}

    def escolher(self, i: int) -> dict:
        ev = self.evento_atual()
        if ev is None:
            raise RuntimeError("não há nenhum evento à espera")
        if not ev["possivel"][i]:
            raise ValueError("não tens dinheiro para essa opção")
        original = EVENTOS_POR_ID[ev["id"]]
        with self.con:
            self.con.execute("UPDATE vida SET evento_pendente = NULL WHERE atleta_id = ?", (self._atleta_id,))
            return self._resolver(original["opcoes"][i], ev["id"], ev["titulo"])

    # ------------------------------------------------------------------ #
    # Atividades e pessoas                                                 #
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

    def interagir(self, papel: str, acao: str) -> dict:
        """Uma interação com uma pessoa (uma por pessoa por semana): sobe a relação e a moral."""
        p = next((x for x in self.pessoas() if x["papel"] == papel), None)
        if p is None:
            raise ValueError("essa pessoa não está na tua vida")
        if p["interagiu"]:
            raise RuntimeError("já estiveste com essa pessoa esta semana")
        ac = ACOES_PESSOA[acao]
        if self.estado["dinheiro"] < ac.get("custo", 0):
            raise ValueError("não tens dinheiro para isso")
        efeitos = dict(ac["efeitos"], **{papel: ac["rel"]})
        textos = TEXTOS_PESSOA.get((papel, acao))
        if textos:
            texto = self.rnd.choice(textos)
        elif acao == "prenda":
            destino = {"mae": "à tua mãe", "pai": "ao teu pai"}.get(papel, "a " + p["nome"])
            texto = f"Ofereceste uma prenda {destino}. Adorou!"
        else:
            quem = {"mae": "a tua mãe", "pai": "o teu pai"}.get(papel, p["nome"])
            texto = f"Estiveste a conversar com {quem}. Fez-te bem."
        # O pai que dá conselhos põe-te a estudar; a mãe acalma; o namoro dá forças
        if acao == "conselho":
            efeitos.update({"pai": {"estudos": 4}, "mae": {"moral": 3}, "amigo": {"moral": 2},
                            "namoro": {"moral": 3}}[papel])
            efeitos[papel] = ac["rel"]
        with self.con:
            self.con.execute("UPDATE pessoa SET interagiu = 1 WHERE id = ?", (p["id"],))
            nome = NOME_PAPEL[papel] if papel in ("mae", "pai") else p["nome"]
            return self._resolver({"texto": f"{ac['nome']} — {nome}", "efeitos": efeitos, "resultado": texto},
                                  f"pessoa_{papel}", "Pessoas")

    # ------------------------------------------------------------------ #
    # Conquistas                                                          #
    # ------------------------------------------------------------------ #
    def conquistas(self) -> list:
        """Lista de todas as conquistas, com a indicação das que já foram desbloqueadas."""
        feitas = {m[5:] for m in self.marcas() if m.startswith("conq:")}
        return [{"id": i, "nome": n, "descricao": d, "feita": i in feitas} for i, n, d in CONQUISTAS]

    def verificar_conquistas(self) -> list:
        """Desbloqueia as conquistas que já foram cumpridas. Devolve os nomes das novas."""
        a = self.cj.atleta
        if a is None:
            return []
        v = self.estado
        marcas = self.marcas()
        est = self.con.execute("SELECT COALESCE(SUM(golos), 0) AS total, COALESCE(MAX(golos), 0) AS maximo, "
                               "COALESCE(MAX(nota), 0) AS nota FROM atuacao WHERE atleta_id = ?",
                               (a["id"],)).fetchone()
        camp = self.cj.camp
        cumpridas = {
            "primeiro_golo": est["total"] >= 1,
            "hat_trick": est["maximo"] >= 3,
            "goleador": est["total"] >= 25,
            "nota_9": est["nota"] >= 9,
            "campeao": camp.terminado and camp.posicao_do_jogador() == 1,
            "selecao": "selecao" in marcas,
            "grande": a["equipa_id"] in ("fc_porto", "benfica", "sporting"),
            "craque": a["geral"] >= 80,
            "poupado": v["dinheiro"] >= 10000,
            "carro": "carro" in marcas,
            "apaixonado": any(p["papel"] == "namoro" for p in self.pessoas()),
            "finalista": "finalista" in marcas,
            "capitao": "capitao" in marcas,
            "veterano": a["epoca"] >= 5,
        }
        novas = []
        for cid, ok in cumpridas.items():
            if ok and f"conq:{cid}" not in marcas:
                self._marcar(f"conq:{cid}")
                novas.append(NOME_CONQUISTA[cid])
                self.registar(f"Conquista desbloqueada: {NOME_CONQUISTA[cid]}!", {}, "conquista")
        return novas

    # ------------------------------------------------------------------ #
    def nova_epoca(self) -> list:
        """Fim de época: faz anos, recupera as forças e a escola dá a nota do ano."""
        v = self.estado
        frases = [f"Fizeste {v['idade'] + 1} anos!"]
        efeitos = {"forma": 25, "moral": 5}
        if v["idade"] <= 18:
            if v["estudos"] >= 60:
                frases.append("Passaste de ano com boas notas." if v["idade"] < 18
                              else "Acabaste o 12.º ano com boas notas!")
                efeitos["moral"] += 8
                efeitos["mae"] = 6
                efeitos["pai"] = 6
            elif v["estudos"] >= 40:
                frases.append("Passaste de ano à justa.")
            else:
                frases.append("Chumbaste o ano... os teus pais não estão contentes.")
                efeitos["moral"] -= 15
                efeitos["pai"] = -10
        with self.con:
            if v["idade"] == 18 and v["estudos"] >= 60:
                self._marcar("finalista")
            self.con.execute("UPDATE vida SET idade = idade + 1, evento_pendente = NULL, banco = 0, lesao = 0, "
                             "atividade_feita = 0 WHERE atleta_id = ?", (self._atleta_id,))
            self.con.execute("DELETE FROM seguimento WHERE atleta_id = ?", (self._atleta_id,))
            mudou = self.aplicar(efeitos)
            self.registar(" ".join(frases), mudou, "epoca")
            frases += [f"Conquista: {n}" for n in self.verificar_conquistas()]
        return frases
