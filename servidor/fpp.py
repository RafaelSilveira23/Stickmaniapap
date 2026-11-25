"""fpp.py - lê os jogos reais do campeonato no portal de resultados da Federação (hp.fpp.pt).

O modo EQUIPA DE SONHO (fantasy) dá pontos aos jogadores pelo que fazem nos jogos reais do
Campeonato Placard (1.ª divisão). Este módulo vai buscar esses dados:

  • o calendário da competição  -> jogos, jornadas, equipas e resultados   (/Competicao/<id>)
  • a ficha de cada jogo         -> convocados, quem foi do cinco inicial    (/jogo/<id>)
                                    e quem jogou
  • as estatísticas do jogo      -> golos e cartões de cada jogador          (/Views/ajax_estatisticasJogo.php)

Cada jogador é identificado pelo número da federação (aparece no endereço da fotografia,
ex.: FED_166747), por isso dois jogadores com o mesmo nome nunca se confundem.

Só usa a biblioteca normal do Python (urllib e expressões regulares). Para não sobrecarregar o
site da FPP, o servidor só lê os jogos que acabaram e ainda não tinha lido, e espera um pouco
entre pedidos (ver liga_fantasy.py).
"""
import html
import re
import time
import urllib.parse
import urllib.request

BASE = "https://hp.fpp.pt"
COMPETICAO = 493                 # Campeonato Placard HP - Fase Regular, época 2026/27
AGENTE = "StickMania/1.0 (jogo escolar de hoquei em patins)"
PAUSA_ENTRE_PEDIDOS = 0.5        # segundos


def descarregar(caminho: str, tentativas: int = 2) -> str:
    """Página do portal (caminho relativo, ex.: '/jogo/18731'). Lança OSError se não conseguir."""
    url = caminho if caminho.startswith("http") else BASE + caminho
    erro = None
    for i in range(tentativas):
        try:
            pedido = urllib.request.Request(url, headers={"User-Agent": AGENTE})
            with urllib.request.urlopen(pedido, timeout=20) as r:
                return r.read().decode("utf-8", errors="replace")
        except OSError as e:
            erro = e
            time.sleep(1 + i)
    raise OSError(f"não foi possível ler {url}: {erro}")


def _texto(fragmento: str) -> str:
    """HTML -> texto simples (sem etiquetas e com os espaços arrumados)."""
    t = re.sub(r"<[^>]+>", " ", fragmento)
    return " ".join(html.unescape(t).split())


def _fed(fragmento: str) -> int | None:
    m = re.search(r"FED_(\d+)\.", fragmento)
    return int(m.group(1)) if m else None


# ====================================================================== #
# Calendário                                                             #
# ====================================================================== #

def ler_calendario(pagina: str) -> list:
    """
    Jogos da competição: [{"id" (da ficha, None se ainda não tem), "jornada", "numero" (único na competição), "data", "hora", "casa_id", "casa",
    "fora_id", "fora", "golos_casa", "golos_fora"}]. Os golos são None se o jogo ainda não se jogou.
    """
    jogos = []
    jornada = 0
    # Percorre as linhas da tabela pela ordem: os títulos das jornadas e os jogos
    for m in re.finditer(r"<tr>(.*?)</tr>", pagina, re.S):
        linha = m.group(1)
        titulo = re.search(r'class="titulo-jornada">\s*(\d+)\s*ª\s*Jornada', linha, re.I)
        if titulo:
            jornada = int(titulo.group(1))
            continue
        jogo = re.search(r'href="/jogo/(\d+)"', linha)          # só existe depois de o jogo ter ficha
        equipas = re.findall(r'href="/Equipa/\d+/(\d+)"><p class="[^"]*">(.*?)</p>', linha, re.S)
        if len(equipas) != 2 or not jornada:
            continue
        datas = re.findall(r'<p class="data">(.*?)</p>', linha, re.S)
        numero = _texto(datas[0]) if datas else ""
        data_hora = _texto(datas[1]).split() if len(datas) > 1 else []
        res = re.search(r'<p class="resultado"\s*>(.*?)</p>', linha, re.S)
        golos = re.match(r"(\d+)\s*-\s*(\d+)$", _texto(res.group(1))) if res else None
        jogos.append({
            "id": int(jogo.group(1)) if jogo else None, "jornada": jornada,
            "numero": int(numero) if numero.isdigit() else 0,
            "data": data_hora[0] if data_hora else "", "hora": data_hora[1] if len(data_hora) > 1 else "",
            "casa_id": int(equipas[0][0]), "casa": _texto(equipas[0][1]),
            "fora_id": int(equipas[1][0]), "fora": _texto(equipas[1][1]),
            "golos_casa": int(golos.group(1)) if golos else None,
            "golos_fora": int(golos.group(2)) if golos else None,
        })
    return jogos


# ====================================================================== #
# Ficha de jogo                                                          #
# ====================================================================== #

def ler_ficha(pagina: str) -> dict:
    """
    Convocados de cada equipa e os dados para pedir as estatísticas:
    {"casa": [jogador], "fora": [jogador], "estatisticas": "epoca=...&jogoNumero=..."}
    jogador = {"fed", "numero", "nome", "cinco" (foi do cinco inicial), "jogou"}
    Na FPP, "(5i)" = cinco inicial e "(J)" = entrou durante o jogo; sem nada = não jogou.
    """
    inicio = pagina.find('id="Equipas"')
    fim = pagina.find('id="Estatisticas"', inicio)
    bloco = pagina[inicio:fim if fim > 0 else None]
    partes = re.split(r"<!--\s*Equipa\s*2\s*-->", bloco)
    lados = {}
    for lado, parte in zip(("casa", "fora"), partes):
        jogadores = []
        so_jogadores = parte.split("<h3>Técnicos</h3>")[0]
        for m in re.finditer(r'<div class="player">(.*?)</div>', so_jogadores, re.S):
            fed = _fed(m.group(1))
            p = re.search(r"<p>(.*?)</p>", m.group(1), re.S)
            if fed is None or not p:
                continue
            txt = _texto(p.group(1))
            d = re.match(r"N\.º\s*(\d+)\s*-\s*(.*?)\s*(\((5i|J)\))?$", txt)
            if not d:
                continue
            jogadores.append({"fed": fed, "numero": int(d.group(1)), "nome": d.group(2).strip(),
                              "cinco": d.group(4) == "5i", "jogou": d.group(4) in ("5i", "J")})
        lados[lado] = jogadores
    est = re.search(r'url:\s*"/Views/ajax_estatisticasJogo\.php",\s*data:\s*\'([^\']*)\'', pagina)
    return {"casa": lados.get("casa", []), "fora": lados.get("fora", []),
            "estatisticas": html.unescape(est.group(1)) if est else None}


def ler_estatisticas(pagina: str) -> dict:
    """
    Golos e cartões de um jogo: {"golos": {fed: n}, "amarelos": {fed: n}, "azuis": {fed: n}, "vermelhos": {fed: n}}.
    (Os cartões também podem ser do treinador: esses ficam de fora porque não são cartas do jogo.)
    """
    res = {"golos": {}, "amarelos": {}, "azuis": {}, "vermelhos": {}}
    golos_sec = pagina.split("<h3>Disciplina</h3>")[0]
    disc_sec = pagina.split("<h3>Disciplina</h3>")[1] if "<h3>Disciplina</h3>" in pagina else ""
    for m in re.finditer(r'<li class="player-item">(.*?)</li>', golos_sec, re.S):
        fed = _fed(m.group(1))
        n = re.search(r'class="goal-count">\s*(\d+)', m.group(1))
        if fed is not None and n:
            res["golos"][fed] = res["golos"].get(fed, 0) + int(n.group(1))
    for m in re.finditer(r'<li class="player-item">(.*?)</li>', disc_sec, re.S):
        fed = _fed(m.group(1))
        if fed is None:
            continue
        for classe, txt in re.findall(r"<span\s+class='([a-z\-]*card[a-z\-]*)'>([^<]*)<", m.group(1)):
            n = re.match(r"\s*(\d+)", txt)
            n = int(n.group(1)) if n else 1
            t = txt.lower()
            tipo = ("vermelhos" if ("vermelh" in t or "red" in classe) else
                    "azuis" if ("azu" in t or "blue" in classe) else "amarelos")
            # A FPP repete a mesma linha para cada cartão: guarda-se o maior número visto
            res[tipo][fed] = max(res[tipo].get(fed, 0), n)
    return res


def ler_cronologia(pagina: str) -> dict:
    """
    Cronologia do jogo (lance a lance): cada golo e cada cartão, com o jogador e o lado
    (time-team1 = equipa da casa, time-team2 = visitante).
    É mais fiável do que o resumo das estatísticas, que na FPP às vezes repete jogadores ou
    esquece golos. Devolve o mesmo formato que ler_estatisticas, mais "golos_lado" (casa, fora).
    """
    res = {"golos": {}, "amarelos": {}, "azuis": {}, "vermelhos": {}, "golos_lado": [0, 0], "eventos": []}
    blocos = re.split(r"<div class='time d-flex", pagina)
    for b in blocos[1:]:
        # Os golos dizem o lado; os cartões não (mas trazem o jogador, que é o que conta)
        lado = 0 if "time-team1" in b[:200] else (1 if "time-team2" in b[:200] else None)
        tit = re.search(r"<strong>\s*(.*?)\s*</strong>", b, re.S)
        if not tit:
            continue
        evento = re.sub(r"\s*\(?\d+:\d+\)?\s*$", "", _texto(tit.group(1))).lower()
        fed = _fed(b)
        res["eventos"].append((lado, evento, fed))
        if lado is not None and (evento.startswith("golo") or "auto" in evento):
            res["golos_lado"][lado] += 1
            # Um autogolo conta para a equipa, mas não para o jogador
            if fed is not None and "auto" not in evento:
                res["golos"][fed] = res["golos"].get(fed, 0) + 1
        elif evento.startswith("cart") and fed is not None:
            tipo = ("vermelhos" if "vermelh" in evento else "azuis" if "azu" in evento else
                    "amarelos" if "amarel" in evento else None)
            if tipo:
                res[tipo][fed] = res[tipo].get(fed, 0) + 1
    return res


def ler_jogo(jogo_id: int) -> dict:
    """Ficha e cronologia de um jogo (dois pedidos ao portal)."""
    pagina = descarregar(f"/jogo/{jogo_id}")
    ficha = ler_ficha(pagina)
    crono = re.search(r'url:\s*"/Views/ajax_jogo\.php",\s*data:\s*\'([^\']*)\'', pagina)
    est = {"golos": {}, "amarelos": {}, "azuis": {}, "vermelhos": {}, "golos_lado": [0, 0], "eventos": []}
    if crono:
        time.sleep(PAUSA_ENTRE_PEDIDOS)
        est = ler_cronologia(descarregar("/Views/ajax_jogo.php?" + html.unescape(crono.group(1))))
    ficha.update(est)
    return ficha


def ler_competicao(competicao: int = COMPETICAO) -> list:
    return ler_calendario(descarregar(f"/Competicao/{competicao}"))
