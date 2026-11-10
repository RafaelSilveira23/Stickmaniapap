# -*- coding: utf-8 -*-
"""analise_simulacao.py - verifica se os resultados simulados do modo carreira fazem sentido.

Simula muitas épocas completas (numa base de dados em memória) e mostra:
  - golos por jogo, percentagem de empates e de goleadas, maior número de golos;
  - "surpresas": jogos em que a equipa muito mais fraca (12+ pontos de força) ganhou;
  - para cada equipa, quantas vezes foi campeã da sua divisão, a posição média e quantas vezes
    ganhou a Taça Europeia.
Cada época começa com as divisões iniciais (sem subidas nem descidas), para as médias serem comparáveis.

Uso:  python ferramentas/analise_simulacao.py [número de épocas]
"""
import collections
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hockey_game"))
from carreira import Campeonato, FORCA_EQUIPAS, LIGA1, LIGA2  # noqa: E402


def main(epocas: int = 400):
    camp = Campeonato(":memory:")
    campeoes = collections.Counter()
    europa = collections.Counter()
    posicoes = collections.defaultdict(list)
    jogos = golos = empates = goleadas = grandes = surpresas = maximo = 0
    for e in range(epocas):
        camp.novo("fc_porto", "normal", semente=e, continuar=False)
        camp.simular_resto_da_epoca(semente=10_000 + e)
        for p in camp.con.execute("SELECT * FROM partida WHERE torneio_id = ?", (camp.torneio_id,)):
            a, b = p["golos_casa"], p["golos_fora"]
            jogos += 1
            golos += a + b
            maximo = max(maximo, a, b)
            empates += a == b
            goleadas += abs(a - b) >= 6
            fc, ff = FORCA_EQUIPAS[p["casa_id"]], FORCA_EQUIPAS[p["fora_id"]]
            if abs(fc - ff) >= 12:
                grandes += 1
                surpresas += (fc > ff and a < b) or (ff > fc and b < a)
        for liga in (LIGA1, LIGA2):
            tabela = camp.classificacao(liga)
            campeoes[tabela[0]["equipa_id"]] += 1
            for i, linha in enumerate(tabela, start=1):
                posicoes[linha["equipa_id"]].append(i)
        europa[camp.resumo_epoca()["europa"]] += 1

    print(f"{epocas} épocas, {jogos} jogos")
    print(f"golos por jogo: {golos / jogos:.2f}   empates: {100 * empates / jogos:.1f} %   "
          f"goleadas (6+ golos de diferença): {100 * goleadas / jogos:.1f} %   máximo de golos: {maximo}")
    print(f"surpresas (a equipa muito mais fraca ganhou): {100 * surpresas / max(1, grandes):.1f} %")
    print()
    print(f"{'equipa':16s} {'força':>5s} {'campeã':>8s} {'posição média':>14s} {'Taça Europeia':>14s}")
    for eq, forca in sorted(FORCA_EQUIPAS.items(), key=lambda x: -x[1]):
        media = f"{sum(posicoes[eq]) / len(posicoes[eq]):14.2f}" if posicoes[eq] else f"{'-':>14s}"
        campea = f"{100 * campeoes[eq] / epocas:7.1f}%" if posicoes[eq] else f"{'-':>8s}"
        print(f"{eq:16s} {forca:5d} {campea} {media} {100 * europa[eq] / epocas:13.1f}%")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 400)
